from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "wur-guidelines" / "scripts" / "wur_sync_agents_context.py"

spec = importlib.util.spec_from_file_location("wur_sync_agents_context", SCRIPT)
assert spec is not None and spec.loader is not None
wur_sync_agents_context = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = wur_sync_agents_context
spec.loader.exec_module(wur_sync_agents_context)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


class WurSyncAgentsContextTestCase(unittest.TestCase):
    def init_repo(self, root: Path) -> None:
        git(root, "init", "-b", "main")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Test User")
        (root / "agents" / "roadmap").mkdir(parents=True)
        (root / "agents" / "docs").mkdir(parents=True)
        (root / "agents" / "research").mkdir(parents=True)
        (root / "agents" / "raw").mkdir(parents=True)
        (root / "agents" / "roadmap" / "PHASE_1.md").write_text(
            "planned template\n", encoding="utf-8"
        )
        (root / "agents" / "roadmap" / "ALL.md").write_text(
            "planned all\n", encoding="utf-8"
        )
        (root / "agents" / "roadmap" / "log.md").write_text(
            "main log\n", encoding="utf-8"
        )
        (root / "agents" / "docs" / "existing.md").write_text(
            "existing\n", encoding="utf-8"
        )
        git(root, "add", "agents")
        git(root, "commit", "-m", "init agents")

    def make_phase_branch(self, root: Path) -> None:
        git(root, "checkout", "-b", "feature/phase-1")
        (root / "agents" / "roadmap" / "PHASE_1.md").write_text(
            "done execution state\n", encoding="utf-8"
        )
        (root / "agents" / "roadmap" / "ALL.md").write_text(
            "commit hashes\n", encoding="utf-8"
        )
        (root / "agents" / "roadmap" / "log.md").write_text(
            "phase log\n", encoding="utf-8"
        )
        git(root, "add", "agents/roadmap")
        git(root, "commit", "-m", "phase execution state")
        git(root, "checkout", "main")

    def add_master_context_and_roadmap_drift(self, root: Path) -> None:
        (root / "agents" / "docs" / "new-note.md").write_text(
            "new doc\n", encoding="utf-8"
        )
        (root / "agents" / "research" / "new-research.md").write_text(
            "new research\n", encoding="utf-8"
        )
        (root / "agents" / "raw" / "source.txt").write_text(
            "raw\n", encoding="utf-8"
        )
        (root / "agents" / "roadmap" / "PHASE_1.md").write_text(
            "bad master planning edit\n", encoding="utf-8"
        )
        git(root, "add", "agents")
        git(root, "commit", "-m", "add master context")

    def test_plan_selects_only_new_safe_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            self.make_phase_branch(root)
            self.add_master_context_and_roadmap_drift(root)
            git(root, "checkout", "feature/phase-1")

            plan = wur_sync_agents_context.build_plan("main", str(root))

            self.assertEqual(
                plan.files,
                [
                    "agents/docs/new-note.md",
                    "agents/raw/source.txt",
                    "agents/research/new-research.md",
                ],
            )
            self.assertGreaterEqual(plan.skipped_unsafe, 0)

    def test_sync_imports_new_context_without_overwriting_roadmap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            self.make_phase_branch(root)
            self.add_master_context_and_roadmap_drift(root)
            git(root, "checkout", "feature/phase-1")

            exit_code = wur_sync_agents_context.main(
                ["--cwd", str(root), "--base", "main", "--json"]
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "agents" / "roadmap" / "PHASE_1.md").read_text(
                    encoding="utf-8"
                ),
                "done execution state\n",
            )
            self.assertEqual(
                (root / "agents" / "docs" / "new-note.md").read_text(
                    encoding="utf-8"
                ),
                "new doc\n",
            )
            self.assertIn(
                "sync: import new agents context from default branch",
                git(root, "log", "--oneline", "-1"),
            )

    def test_refuses_default_branch_and_dirty_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            with self.assertRaisesRegex(
                wur_sync_agents_context.SyncError,
                "refusing to sync on default branch",
            ):
                wur_sync_agents_context.build_plan("main", str(root))

            git(root, "checkout", "-b", "feature/phase-1")
            (root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            git(root, "add", "dirty.txt")
            with self.assertRaisesRegex(
                wur_sync_agents_context.SyncError,
                "working tree must be clean",
            ):
                wur_sync_agents_context.build_plan("main", str(root))


if __name__ == "__main__":
    unittest.main()
