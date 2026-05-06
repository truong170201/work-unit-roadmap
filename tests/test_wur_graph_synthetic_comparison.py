from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from collections.abc import Iterable
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "wur-guidelines" / "scripts"

WUR_EXTRACT = SCRIPTS / "wur_graph_extract.py"
WUR_LINT = SCRIPTS / "wur_graph_lint.py"
WUR_QUERY = SCRIPTS / "wur_graph_query.py"
WUR_STATS = SCRIPTS / "wur_wiki_stats.py"


def find_raw_plugin_root() -> Path | None:
    candidates = [
        ROOT / "raw" / "llm-wiki-plugin",
        ROOT.parent.parent / "raw" / "llm-wiki-plugin",
    ]
    for candidate in candidates:
        if (candidate / "skills" / "llm-wiki" / "scripts").is_dir():
            return candidate
    return None


RAW_PLUGIN = find_raw_plugin_root()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def predicate_counts(edges: Iterable[dict]) -> Counter[str]:
    return Counter(str(edge["predicate"]) for edge in edges)


class WurGraphSyntheticComparisonTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.agents_dir = Path(self.tmpdir.name) / "agents"
        self.create_synthetic_agents(self.agents_dir)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def run_script(self, script: Path, *args: str, target: Path | None = None):
        return subprocess.run(
            [sys.executable, str(script), str(target or self.agents_dir), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )

    def create_synthetic_agents(self, agents_dir: Path) -> None:
        write(
            agents_dir / "SCHEMA.md",
            """
            ---
            schema_version: 1
            ---

            # agents/ Wiki Schema
            """,
        )
        write(
            agents_dir / "graph" / "ontology.yaml",
            """
            version: 1

            node_types:
              phase:
                maps_from:
                  type: phase
              fix-round:
                maps_from:
                  type: fix-round
              research:
                maps_from:
                  type: research
              decision:
                maps_from:
                  type: decision
              note:
                maps_from:
                  type: note
              report:
                maps_from:
                  type: report

            predicates:
              mentions:
                subject_types: ["*"]
                object_types: ["*"]
                requires_evidence: false
              depends_on:
                subject_types: ["*"]
                object_types: ["*"]
                requires_evidence: false
              parent:
                subject_types: ["*"]
                object_types: ["*"]
                requires_evidence: false
              verifies:
                subject_types: ["*"]
                object_types: ["*"]
                requires_evidence: false
              informs:
                subject_types: ["*"]
                object_types: ["*"]
                requires_evidence: false
            """,
        )
        write(
            agents_dir / "roadmap" / "PHASE_1.md",
            """
            ---
            type: phase
            phase: 1
            status: done
            tags: [workflow]
            test_status: pass
            graph:
              node_id: roadmap/PHASE_1
              node_type: phase
            ---

            # PHASE_1: Foundation

            Foundation phase for [[roadmap/PHASE_2]].
            """,
        )
        write(
            agents_dir / "roadmap" / "PHASE_2.md",
            """
            ---
            type: phase
            phase: 2
            status: active
            tags: [workflow]
            test_status: pass
            depends_on: ["[[roadmap/PHASE_1]]"]
            graph:
              node_id: roadmap/PHASE_2
              node_type: phase
              relationships:
                - predicate: depends_on
                  object: roadmap/PHASE_1
                  confidence: high
                  status: current
            ---

            # PHASE_2: Graph Validation

            Uses [[docs/ADR_001]], [[research/wur-scope]], and
            [[roadmap/FIX_P2_round1]]. Verified by [[reports/phase2-check]].
            """,
        )
        write(
            agents_dir / "roadmap" / "FIX_P2_round1.md",
            """
            ---
            type: fix-round
            phase: 2
            status: done
            tags: [workflow]
            parent: "[[roadmap/PHASE_2]]"
            graph:
              node_id: roadmap/FIX_P2_round1
              node_type: fix-round
              relationships:
                - predicate: parent
                  object: roadmap/PHASE_2
                  confidence: high
                  status: current
            ---

            # FIX_P2_round1

            Follow-up for [[roadmap/PHASE_2]].
            """,
        )
        write(
            agents_dir / "research" / "wur-scope.md",
            """
            ---
            type: research
            status: done
            tags: [workflow]
            informs: ["[[roadmap/PHASE_2]]"]
            graph:
              node_id: research/wur-scope
              node_type: research
              relationships:
                - predicate: informs
                  object: roadmap/PHASE_2
                  confidence: high
                  status: current
            ---

            # WUR Scope Research

            Research informing [[roadmap/PHASE_2]].
            """,
        )
        write(
            agents_dir / "docs" / "ADR_001.md",
            """
            ---
            type: decision
            status: done
            tags: [workflow]
            informs: ["[[roadmap/PHASE_2]]"]
            graph:
              node_id: docs/ADR_001
              node_type: decision
              relationships:
                - predicate: informs
                  object: roadmap/PHASE_2
                  confidence: high
                  status: current
            ---

            # ADR_001

            Decision informing [[roadmap/PHASE_2]].
            """,
        )
        write(
            agents_dir / "reports" / "phase2-check.md",
            """
            ---
            type: report
            status: done
            tags: [workflow]
            verifies: ["[[roadmap/PHASE_2]]"]
            graph:
              node_id: reports/phase2-check
              node_type: report
              relationships:
                - predicate: verifies
                  object: roadmap/PHASE_2
                  confidence: high
                  status: current
            ---

            # Phase 2 Check

            Verification report for [[roadmap/PHASE_2]].
            """,
        )

    def test_wur_handles_synthetic_agents_end_to_end(self) -> None:
        extract = self.run_script(WUR_EXTRACT, "--no-log")
        self.assertEqual(extract.returncode, 0, msg=extract.stdout + extract.stderr)

        nodes = read_jsonl(self.agents_dir / "graph" / "nodes.jsonl")
        edges = read_jsonl(self.agents_dir / "graph" / "edges.jsonl")
        self.assertEqual(len(nodes), 6)
        self.assertEqual(
            predicate_counts(edges),
            Counter(
                {
                    "mentions": 5,
                    "informs": 2,
                    "depends_on": 1,
                    "parent": 1,
                    "verifies": 1,
                }
            ),
        )

        lint = self.run_script(WUR_LINT)
        self.assertEqual(lint.returncode, 0, msg=lint.stdout + lint.stderr)

        stats = self.run_script(WUR_STATS, "--json")
        self.assertEqual(stats.returncode, 0, msg=stats.stdout + stats.stderr)
        stats_payload = json.loads(stats.stdout)
        self.assertEqual(stats_payload["total_graph_pages"], 6)
        self.assertEqual(stats_payload["wikilinks"]["broken"], 0)
        self.assertEqual(stats_payload["missing_frontmatter"], 0)
        self.assertEqual(stats_payload["graph_layer"]["nodes_jsonl"]["count"], 6)

        status = self.run_script(WUR_QUERY, "--json", "status", "--filter", "active")
        self.assertEqual(status.returncode, 0, msg=status.stdout + status.stderr)
        status_payload = json.loads(status.stdout)
        self.assertEqual(
            [node["id"] for node in status_payload["nodes"]], ["roadmap/PHASE_2"]
        )

        (self.agents_dir / "graph" / "graph.sqlite").unlink()
        fallback = self.run_script(WUR_QUERY, "facts", "--about", "roadmap/PHASE_2")
        self.assertEqual(fallback.returncode, 0, msg=fallback.stdout + fallback.stderr)
        self.assertIn("depends_on: roadmap/PHASE_1", fallback.stdout)

    @unittest.skipUnless(RAW_PLUGIN, "raw/llm-wiki-plugin is local ignored data")
    def test_raw_plugin_comparison_on_same_synthetic_input(self) -> None:
        assert RAW_PLUGIN is not None
        raw_scripts = RAW_PLUGIN / "skills" / "llm-wiki" / "scripts"
        raw_extract = raw_scripts / "wiki_graph_extract.py"
        raw_lint = raw_scripts / "wiki_graph_lint.py"
        raw_query = raw_scripts / "wiki_graph_query.py"

        wur_result = self.run_script(WUR_EXTRACT, "--no-log")
        self.assertEqual(
            wur_result.returncode, 0, msg=wur_result.stdout + wur_result.stderr
        )
        wur_edges = read_jsonl(self.agents_dir / "graph" / "edges.jsonl")
        wur_typed = predicate_counts(
            edge for edge in wur_edges if edge["predicate"] != "mentions"
        )

        raw_agents = Path(self.tmpdir.name) / "raw_agents"
        shutil.copytree(self.agents_dir, raw_agents)
        raw_graph = raw_agents / "graph"
        for artifact in (
            "nodes.jsonl",
            "edges.jsonl",
            "graph.sqlite",
            "graph.graphml",
            "summary.md",
            "last_extracted.md",
        ):
            path = raw_graph / artifact
            if path.exists():
                path.unlink()

        extract = subprocess.run(
            [
                sys.executable,
                str(raw_extract),
                str(raw_agents),
                "--ontology",
                str(raw_agents / "graph" / "ontology.yaml"),
                "--formats",
                "jsonl,sqlite",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(extract.returncode, 0, msg=extract.stdout + extract.stderr)

        lint = subprocess.run(
            [
                sys.executable,
                str(raw_lint),
                str(raw_agents),
                "--ontology",
                str(raw_agents / "graph" / "ontology.yaml"),
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(lint.returncode, 0, msg=lint.stdout + lint.stderr)
        lint_payload = json.loads(lint.stdout)
        self.assertEqual(lint_payload["summary"]["unknown_predicates"], 0)
        self.assertEqual(lint_payload["summary"]["broken_object_refs"], 0)

        raw_nodes = read_jsonl(raw_agents / "graph" / "nodes.jsonl")
        raw_edges = read_jsonl(raw_agents / "graph" / "edges.jsonl")
        raw_typed = predicate_counts(
            edge for edge in raw_edges if edge["predicate"] != "mentions"
        )
        self.assertEqual(len(raw_nodes), 6)
        self.assertEqual(raw_typed, wur_typed)

        query = subprocess.run(
            [
                sys.executable,
                str(raw_query),
                str(raw_agents),
                "--json",
                "facts",
                "--about",
                "roadmap/PHASE_2",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(query.returncode, 0, msg=query.stdout + query.stderr)

        (raw_agents / "graph" / "graph.sqlite").unlink()
        no_sqlite = subprocess.run(
            [
                sys.executable,
                str(raw_query),
                str(raw_agents),
                "facts",
                "--about",
                "roadmap/PHASE_2",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertNotEqual(no_sqlite.returncode, 0)
        self.assertIn("graph.sqlite not found", no_sqlite.stderr)

    @unittest.skipUnless(RAW_PLUGIN, "raw/llm-wiki-plugin is local ignored data")
    def test_raw_semantic_lint_is_deeper_but_outside_wur_contract(self) -> None:
        assert RAW_PLUGIN is not None
        raw_lint = (
            RAW_PLUGIN
            / "skills"
            / "llm-wiki"
            / "scripts"
            / "wiki_graph_lint.py"
        )

        phase2 = self.agents_dir / "roadmap" / "PHASE_2.md"
        text = phase2.read_text(encoding="utf-8")
        text = text.replace(
            "predicate: depends_on",
            "predicate: raw_only_unknown_predicate",
            1,
        )
        phase2.write_text(text, encoding="utf-8")

        wur_lint = self.run_script(WUR_LINT)
        self.assertEqual(wur_lint.returncode, 0, msg=wur_lint.stdout + wur_lint.stderr)

        raw_result = subprocess.run(
            [
                sys.executable,
                str(raw_lint),
                str(self.agents_dir),
                "--ontology",
                str(self.agents_dir / "graph" / "ontology.yaml"),
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(
            raw_result.returncode, 0, msg=raw_result.stdout + raw_result.stderr
        )
        payload = json.loads(raw_result.stdout)
        self.assertEqual(payload["summary"]["unknown_predicates"], 1)


if __name__ == "__main__":
    unittest.main()
