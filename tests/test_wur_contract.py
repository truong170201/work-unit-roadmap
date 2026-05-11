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
        (self.agents / "departments").mkdir(parents=True)
        (self.agents / "specialists").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.ts").write_text("export const ok = true;\n", encoding="utf-8")
        (self.agents / "project" / "PHILOSOPHY.md").write_text("# Philosophy\n", encoding="utf-8")
        (self.agents / "project" / "USAGE.md").write_text("# Usage\n", encoding="utf-8")
        (self.agents / "project" / "DESIGN.md").write_text("# Design\n", encoding="utf-8")
        (self.agents / "project" / "TECH_STACK.md").write_text("# Tech Stack\n", encoding="utf-8")
        (self.agents / "departments" / "engineering.md").write_text(
            "# Engineering Department\n", encoding="utf-8"
        )
        (self.agents / "specialists" / "frontend-engineer.md").write_text(
            "# Frontend Engineer\n", encoding="utf-8"
        )
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

    def test_create_phase_contract_skips_completed_work_and_uses_shared_rule_file(self) -> None:
        result = self.run_script("create", "--root", str(self.root), "--phase", "1")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        contracts = sorted((self.root / "contracts").glob("*.md"))
        self.assertEqual([path.name for path in contracts], ["PHASE_1_CONTRACT.md", "rule.md"])
        text = (self.root / "contracts" / "PHASE_1_CONTRACT.md").read_text(
            encoding="utf-8"
        )
        rule = (self.root / "contracts" / "rule.md").read_text(encoding="utf-8")

        self.assertIn("# WUR Contract: PHASE_1", text)
        self.assertIn("Required shared rules: `contracts/rule.md`", text)
        self.assertIn("read before execution", text)
        self.assertIn(
            "Task brief: use this file's Goal, Success Criteria, Pending Work, and Allowed Read References.",
            text,
        )
        self.assertIn(
            "Execution setup: read `contracts/rule.md` before creating a worktree.",
            text,
        )
        self.assertNotIn("## WUR Contract Rules", text)
        self.assertIn("# WUR Contract Rules", rule)
        self.assertIn("Do not modify `agents/`", rule)
        self.assertIn(
            "You may edit only Status and Commit cells for touched WU rows in the active contract's Pending Work table, plus the active contract's `## Execution Rounds And Reports` section.",
            rule,
        )
        self.assertIn(
            "Do not edit the phase contract header, Goal, Success Criteria, Scope, Dependencies, Verification, or Allowed Read References.",
            rule,
        )
        self.assertIn(
            "You may update only the Status and Commit cells for touched WU rows in the active contract's Pending Work table.",
            rule,
        )
        self.assertIn(
            "Pending Work table statuses may only become `active`, `ready-for-review`, `blocked`, or `deferred`.",
            rule,
        )
        self.assertIn(
            "Never set Pending Work rows to `accepted` or `done`; WUR closeout applies those after client confirmation.",
            rule,
        )
        self.assertIn("Do not edit any other `contracts/` file.", rule)
        self.assertIn(
            "Record lifecycle evidence for every touched Work Unit: before status, suggested after status, result, commit, verification, blockers, and coverage gaps.",
            rule,
        )
        self.assertIn(
            "Allowed executor status suggestions: `active`, `ready-for-review`, `blocked`, or `deferred`.",
            rule,
        )
        self.assertIn(
            "Never mark Work Units `accepted`, `done`, or close a phase; WUR coordinator applies `accepted` or `done` only after client confirmation.",
            rule,
        )
        self.assertIn(
            "First read the active phase contract and decide whether there is executable project work.",
            rule,
        )
        self.assertIn(
            "If there is no executable project work, do not create a worktree; append a blocked, no-op, or clarification-needed report instead.",
            rule,
        )
        self.assertIn(
            "If executable project work requires editing project files, create or reuse a sparse execution worktree before modifying those files.",
            rule,
        )
        self.assertIn(
            "The sparse worktree MUST exclude `agents/` and `contracts/`.",
            rule,
        )
        self.assertIn(
            "Do not copy, checkout, or sync `agents/` or `contracts/` into the execution worktree.",
            rule,
        )
        self.assertIn("Worktree Used: yes | no; path/reason: {path or no-code reason}", text)
        self.assertIn("git sparse-checkout init --no-cone", rule)
        self.assertIn("!/agents/", rule)
        self.assertIn("!/contracts/", rule)
        self.assertIn("| WU002 | Card layout", text)
        self.assertIn("| WU003 | Filter state", text)
        self.assertNotIn("| WU001 | Setup shell", text)
        self.assertNotIn("| WU004 | Export CSV", text)
        self.assertIn("## Execution Rounds And Reports", text)
        self.assertIn(
            "Allowed Contract Edits Used: Pending Work Status/Commit cells and `## Execution Rounds And Reports` only",
            text,
        )
        self.assertIn("Pending Work Table Updated: yes | no; rows: {WU ids}", text)
        self.assertIn("Work Unit State Updates:", text)
        self.assertIn(
            "- {WU id}: {before status} -> {suggested status: active | ready-for-review | blocked | deferred}; reason: {evidence}",
            text,
        )

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

    def test_create_refreshes_report_template_but_preserves_received_reports(self) -> None:
        self.assertEqual(
            self.run_script("create", "--root", str(self.root), "--phase", "1").returncode,
            0,
        )
        contract = self.root / "contracts" / "PHASE_1_CONTRACT.md"
        old_tail = """## Execution Rounds And Reports

Keep all execution reports in this same contract file.

### Report Template

```markdown
### Received Report - {round or WU}
Result: pass | failed | blocked | partial
Commit: {hash or none}
Verification: {commands and results}
```

### Received Report - P1-WU02
Result: pass
Suggested After Status: `ready-for-review`
"""
        text = contract.read_text(encoding="utf-8")
        contract.write_text(text[: text.index("## Execution Rounds And Reports")] + old_tail, encoding="utf-8")

        result = self.run_script("create", "--root", str(self.root), "--phase", "1")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        refreshed = contract.read_text(encoding="utf-8")
        self.assertIn("Pending Work Table Updated: yes | no; rows: {WU ids}", refreshed)
        self.assertIn("Worktree Used: yes | no; path/reason: {path or no-code reason}", refreshed)
        self.assertIn("### Received Report - P1-WU02", refreshed)
        self.assertIn("Suggested After Status: `ready-for-review`", refreshed)

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

    def test_contract_teaches_executor_owned_fix_rounds_without_fail_command(self) -> None:
        self.assertEqual(
            self.run_script("create", "--root", str(self.root), "--phase", "1").returncode,
            0,
        )

        contract = self.root / "contracts" / "PHASE_1_CONTRACT.md"
        text = contract.read_text(encoding="utf-8")
        rule = (self.root / "contracts" / "rule.md").read_text(encoding="utf-8")
        self.assertIn("If verification fails, add or update a `### Fix Round R{n} - {scope}` section in the active phase contract.", rule)
        self.assertIn("Do not wait for WUR to generate a separate fix file or run another helper command.", rule)
        self.assertIn("Use one contract ledger for task brief, fix rounds, and reports.", rule)
        self.assertNotIn("wur_contract.py fail", text)
        self.assertEqual(
            [path.name for path in (self.root / "contracts").glob("*.md")],
            ["PHASE_1_CONTRACT.md", "rule.md"],
        )

        result = self.run_script(
            "fail",
            "--root",
            str(self.root),
            "--phase",
            "1",
            "--wu",
            "WU002",
            "--description",
            "Cards overflow on mobile",
            "--verification",
            "npm run test:cards",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice: 'fail'", result.stderr)

    def test_contract_lists_explicit_allowed_read_references_near_ledger(self) -> None:
        result = self.run_script("create", "--root", str(self.root), "--phase", "1")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        text = (self.root / "contracts" / "PHASE_1_CONTRACT.md").read_text(
            encoding="utf-8"
        )

        references_index = text.index("## Allowed Read References")
        self.assertGreater(references_index, text.index("## Pending Work"))
        self.assertLess(references_index, text.index("## Execution Rounds And Reports"))
        self.assertIn("Only read the listed paths when deeper context is needed.", text)
        self.assertIn("Do not scan all of `agents/`.", text)
        self.assertIn("Do not read unlisted `agents/` files unless the client or WUR contract explicitly adds them.", text)
        self.assertIn("Infer useful specialist lenses from the listed references and WU scope.", text)
        self.assertIn("Do not require WUR to assign one person per WU.", text)
        self.assertIn("Report which specialist lenses were applied.", text)
        self.assertIn("- `agents/project/PHILOSOPHY.md`", text)
        self.assertIn("- `agents/project/DESIGN.md`", text)
        self.assertIn("- `agents/project/TECH_STACK.md`", text)
        self.assertIn("- `agents/departments/engineering.md`", text)
        self.assertIn("- `agents/specialists/frontend-engineer.md`", text)
        references = text[references_index : text.index("## Execution Rounds And Reports")]
        self.assertNotIn("- `agents/`", references)


if __name__ == "__main__":
    unittest.main()
