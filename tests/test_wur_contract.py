from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "wur-guidelines" / "scripts" / "wur_contract.py"


class WurContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.agents = self.root / "agents"
        (self.agents / "roadmap").mkdir(parents=True)
        (self.agents / "project").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.ts").write_text("export const ok = true;\n", encoding="utf-8")
        (self.agents / "project" / "PHILOSOPHY.md").write_text("# Philosophy\n", encoding="utf-8")
        (self.agents / "project" / "USAGE.md").write_text("# Usage\n", encoding="utf-8")
        (self.agents / "project" / "DESIGN.md").write_text("# Design\n", encoding="utf-8")
        (self.agents / "project" / "TECH_STACK.md").write_text("# Tech Stack\n", encoding="utf-8")
        (self.agents / "roadmap" / "PHASE_1.md").write_text(
            """---
type: phase
phase: 1
status: active
tags: [state-active]
test_status: not-run
---

# PHASE_1: Build dashboard

## Goal
Build a dashboard slice.

## Success Criteria
- Dashboard loads
- Cards render

## Work Units
| ID | Goal | Acceptance Criteria | Scope | Dependencies | Verification | Status | Commit |
|---|---|---|---|---|---|---|---|
| WU001 | Setup shell | App starts | src/** | none | npm test | done | abc111 |
| WU002 | Card layout | Responsive cards | src/cards/** | WU001 | npm test -- cards | planned |  |
| WU003 | Filter state | Filters persist | src/filters/** | WU002 | npm test -- filters | active |  |
| WU004 | Export CSV | CSV works | src/export/** | WU003 | npm test -- export | accepted | def222 |
""",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_create_phase_contract_skips_completed_work_and_uses_one_file(self) -> None:
        result = self.run_script("create", "--root", str(self.root), "--phase", "1")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        contracts = sorted((self.root / "contracts").glob("*.md"))
        self.assertEqual([path.name for path in contracts], ["PHASE_1_CONTRACT.md"])
        text = contracts[0].read_text(encoding="utf-8")

        self.assertIn("# WUR Contract: PHASE_1", text)
        self.assertIn("## WUR Contract Rules", text)
        self.assertIn("Do not modify `agents/`", text)
        self.assertIn("Do not modify `contracts/` except this contract report section", text)
        self.assertIn("git sparse-checkout init --no-cone", text)
        self.assertIn("!/agents/", text)
        self.assertIn("!/contracts/", text)
        self.assertIn("| WU002 | Card layout", text)
        self.assertIn("| WU003 | Filter state", text)
        self.assertNotIn("| WU001 | Setup shell", text)
        self.assertNotIn("| WU004 | Export CSV", text)
        self.assertIn("## Execution Rounds And Reports", text)

    def test_create_wu_contract_filters_to_one_pending_work_unit(self) -> None:
        result = self.run_script(
            "create", "--root", str(self.root), "--phase", "1", "--wu", "WU003"
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        text = (self.root / "contracts" / "PHASE_1_CONTRACT.md").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("| WU002 | Card layout", text)
        self.assertIn("| WU003 | Filter state", text)
        self.assertIn("Scope mode: `WU003`", text)

    def test_create_updates_task_section_but_preserves_existing_reports(self) -> None:
        self.assertEqual(
            self.run_script("create", "--root", str(self.root), "--phase", "1").returncode,
            0,
        )
        contract = self.root / "contracts" / "PHASE_1_CONTRACT.md"
        contract.write_text(
            contract.read_text(encoding="utf-8")
            + "\n### Round R1 - WU002\nResult: failed\n",
            encoding="utf-8",
        )

        phase = self.agents / "roadmap" / "PHASE_1.md"
        phase.write_text(
            phase.read_text(encoding="utf-8").replace(
                "| WU002 | Card layout | Responsive cards | src/cards/** | WU001 | npm test -- cards | planned |  |",
                "| WU002 | Card layout | Responsive cards | src/cards/** | WU001 | npm test -- cards | done | 999aaa |",
            ),
            encoding="utf-8",
        )

        result = self.run_script("create", "--root", str(self.root), "--phase", "1")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        text = contract.read_text(encoding="utf-8")
        self.assertNotIn("| WU002 | Card layout", text)
        self.assertIn("| WU003 | Filter state", text)
        self.assertIn("### Round R1 - WU002\nResult: failed", text)

    def test_receive_appends_report_to_same_contract_file(self) -> None:
        self.assertEqual(
            self.run_script("create", "--root", str(self.root), "--phase", "1").returncode,
            0,
        )
        report = self.root / "report.md"
        report.write_text(
            "Result: pass\nCommit: abc123\nVerification: npm test -- cards\n",
            encoding="utf-8",
        )

        result = self.run_script(
            "receive", "--root", str(self.root), "--phase", "1", "--report-file", str(report)
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        text = (self.root / "contracts" / "PHASE_1_CONTRACT.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("### Received Report", text)
        self.assertIn("Result: pass", text)
        self.assertIn("Commit: abc123", text)
        self.assertFalse((self.root / "contracts" / "inbox").exists())
        self.assertFalse((self.root / "contracts" / "outbox").exists())


if __name__ == "__main__":
    unittest.main()
