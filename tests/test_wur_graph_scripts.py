from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "wur-guidelines" / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "agents_clean"

EXTRACT = SCRIPTS / "wur_graph_extract.py"
LINT = SCRIPTS / "wur_graph_lint.py"
QUERY = SCRIPTS / "wur_graph_query.py"
STATS = SCRIPTS / "wur_wiki_stats.py"


class WurGraphScriptsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.agents_dir = Path(self.tmpdir.name) / "agents"
        shutil.copytree(FIXTURE, self.agents_dir)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), str(self.agents_dir), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )

    def test_extract_creates_outputs_and_sqlite(self) -> None:
        result = self.run_script(EXTRACT)
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

        graph_dir = self.agents_dir / "graph"
        expected = {
            "nodes.jsonl",
            "edges.jsonl",
            "graph.sqlite",
            "graph.graphml",
            "summary.md",
            "last_extracted.md",
        }
        self.assertTrue(expected.issubset({p.name for p in graph_dir.iterdir()}))

        con = sqlite3.connect(graph_dir / "graph.sqlite")
        try:
            nodes = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            active = con.execute(
                "SELECT id FROM nodes WHERE status = 'active' ORDER BY id"
            ).fetchall()
        finally:
            con.close()
        self.assertEqual(nodes, 6)
        self.assertGreaterEqual(edges, 10)
        self.assertEqual([row[0] for row in active], ["roadmap/PHASE_2"])

    def test_lint_passes_clean_fixture_after_extract(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)
        result = self.run_script(LINT)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("[OK]", result.stdout)
        self.assertNotIn("[ERROR]", result.stdout)

    def test_stats_reports_clean_health(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)
        result = self.run_script(STATS)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("broken links:     0", result.stdout)
        self.assertIn("missing frontmatter: 0", result.stdout)
        self.assertIn("freshness:        OK", result.stdout)

    def test_query_facts_and_path(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)

        facts = self.run_script(QUERY, "facts", "--about", "roadmap/PHASE_2")
        self.assertEqual(facts.returncode, 0, msg=facts.stdout + facts.stderr)
        self.assertIn("depends_on: roadmap/PHASE_1", facts.stdout)
        self.assertIn("verifies←: reports/phase2-verification", facts.stdout)

        path = self.run_script(
            QUERY,
            "path",
            "--from",
            "roadmap/PHASE_1",
            "--to",
            "reports/phase2-verification",
        )
        self.assertEqual(path.returncode, 0, msg=path.stdout + path.stderr)
        self.assertIn("Path (", path.stdout)
        self.assertIn("reports/phase2-verification", path.stdout)

    def test_query_neighbors_edges_and_status_json(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)

        neighbors = self.run_script(QUERY, "neighbors", "--node", "roadmap/PHASE_2")
        self.assertEqual(
            neighbors.returncode, 0, msg=neighbors.stdout + neighbors.stderr
        )
        self.assertIn("roadmap/PHASE_2", neighbors.stdout)
        self.assertIn("reports/phase2-verification", neighbors.stdout)

        edges = self.run_script(QUERY, "edges", "--subject", "roadmap/PHASE_2")
        self.assertEqual(edges.returncode, 0, msg=edges.stdout + edges.stderr)
        self.assertIn("depends_on: roadmap/PHASE_1", edges.stdout)

        status = self.run_script(QUERY, "--json", "status", "--filter", "active")
        self.assertEqual(status.returncode, 0, msg=status.stdout + status.stderr)
        payload = json.loads(status.stdout)
        self.assertEqual(payload["filter"], "active")
        self.assertEqual(
            [node["id"] for node in payload["nodes"]], ["roadmap/PHASE_2"]
        )

    def test_lint_detects_broken_link_and_invalid_tags(self) -> None:
        phase1 = self.agents_dir / "roadmap" / "PHASE_1.md"
        text = phase1.read_text(encoding="utf-8")
        text = text.replace("tags: [infra]", "tags: bad tag")
        text += "\nBroken: [[missing/page]]\n"
        phase1.write_text(text, encoding="utf-8")

        result = self.run_script(LINT)
        self.assertEqual(result.returncode, 1)
        self.assertIn("frontmatter 'tags' must be a YAML list", result.stdout)
        self.assertIn("broken wikilink [[missing/page]]", result.stdout)

    def test_lint_detects_invalid_values_and_bad_extracted_edge(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)

        phase1 = self.agents_dir / "roadmap" / "PHASE_1.md"
        text = phase1.read_text(encoding="utf-8")
        text = text.replace("status: done", "status: shipping")
        phase1.write_text(text, encoding="utf-8")

        report = self.agents_dir / "reports" / "phase2-verification.md"
        text = report.read_text(encoding="utf-8")
        text = text.replace("type: report", "type: artifact")
        report.write_text(text, encoding="utf-8")

        edges = self.agents_dir / "graph" / "edges.jsonl"
        with edges.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "subject": "roadmap/PHASE_2",
                        "predicate": "depends_on",
                        "object": "roadmap/MISSING",
                    }
                )
                + "\n"
            )

        result = self.run_script(LINT)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid status 'shipping'", result.stdout)
        self.assertIn("invalid type 'artifact'", result.stdout)
        self.assertIn(
            "edge object 'roadmap/MISSING' does not match any node ID", result.stdout
        )

    def test_stats_json_output(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)
        result = self.run_script(STATS, "--json")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["total_graph_pages"], 6)
        self.assertEqual(payload["wikilinks"]["broken"], 0)
        self.assertEqual(payload["graph_layer"]["nodes_jsonl"]["count"], 6)

    def test_stats_reports_dirty_fixture_health(self) -> None:
        phase1 = self.agents_dir / "roadmap" / "PHASE_1.md"
        text = phase1.read_text(encoding="utf-8")
        text = text.replace("tags: [infra]", "")
        text += "\nBroken: [[missing/page]]\n"
        phase1.write_text(text, encoding="utf-8")

        result = self.run_script(STATS, "--json")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["wikilinks"]["broken"], 1)
        self.assertEqual(payload["missing_frontmatter"], 1)
        self.assertEqual(payload["errors"], 1)

    def test_query_falls_back_to_jsonl_when_sqlite_missing(self) -> None:
        self.assertEqual(self.run_script(EXTRACT).returncode, 0)
        sqlite_db = self.agents_dir / "graph" / "graph.sqlite"
        sqlite_db.unlink()

        result = self.run_script(QUERY, "facts", "--about", "roadmap/PHASE_2")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("roadmap/PHASE_2", result.stdout)
        self.assertIn("depends_on: roadmap/PHASE_1", result.stdout)

    def test_lint_requires_test_status_on_phase_files(self) -> None:
        phase1 = self.agents_dir / "roadmap" / "PHASE_1.md"
        text = phase1.read_text(encoding="utf-8")
        text = text.replace("test_status: pass\n", "")
        phase1.write_text(text, encoding="utf-8")

        result = self.run_script(LINT)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing frontmatter field 'test_status'", result.stdout)

    def test_phase_fix_ledger_is_supported_without_test_status_noise(self) -> None:
        legacy = self.agents_dir / "roadmap" / "FIX_P2_device-r1.md"
        legacy.unlink()

        for rel in ("roadmap/ALL.md", "roadmap/PHASE_2.md", "index.md"):
            path = self.agents_dir / rel
            text = path.read_text(encoding="utf-8")
            text = text.replace("FIX_P2_device-r1", "PHASE_2_FIX")
            text = text.replace("FIX_P2_device-r1.md", "PHASE_2_FIX.md")
            path.write_text(text, encoding="utf-8")

        (self.agents_dir / "roadmap" / "PHASE_2_FIX.md").write_text(
            """---
type: fix-round
phase: 2
status: done
tags: [ui]
parent: "[[roadmap/PHASE_2]]"
opened: 2026-05-01
closed: 2026-05-02
---

# PHASE_2_FIX: Fix Ledger

Consolidated fixes for [[roadmap/PHASE_2]].
""",
            encoding="utf-8",
        )

        self.assertEqual(self.run_script(EXTRACT).returncode, 0)
        nodes = [
            json.loads(line)
            for line in (self.agents_dir / "graph" / "nodes.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        self.assertIn("roadmap/PHASE_2_FIX", {node["id"] for node in nodes})

        lint = self.run_script(LINT)
        self.assertEqual(lint.returncode, 0, msg=lint.stdout + lint.stderr)
        self.assertNotIn("PHASE_2_FIX.md: PHASE file missing", lint.stdout)


if __name__ == "__main__":
    unittest.main()
