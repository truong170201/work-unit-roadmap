from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ROOT / "commands"


def read_command(rel_path: str) -> str:
    return (COMMANDS / rel_path).read_text(encoding="utf-8")


class WurCommandContractTestCase(unittest.TestCase):
    def assert_contains_all(self, text: str, snippets: list[str]) -> None:
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)

    def assert_contains_none(self, text: str, snippets: list[str]) -> None:
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                self.assertNotIn(snippet, text)

    def test_init_contract_installs_and_verifies_enforcement(self) -> None:
        text = read_command("init.md")
        self.assert_contains_all(
            text,
            [
                "If yes, stop and report",
                'argument-hint: "[project-context]"',
                "Project context is resolved in this order",
                "$ARGUMENTS` is optional supplemental context",
                "existing `agents/` project files already contain enough project context",
                "If both `$ARGUMENTS` and existing project context are empty",
                "Do not create a placeholder-only `agents/` workspace",
                "{project description}",
                "Ensure `.worktrees/` is in `.gitignore`",
                "Install enforcement git hooks",
                "Write each hook file with the exact content",
                "Verify the install (do not skip)",
                "Hooks without verification are theater",
                "git commit -m \"WU-TW-000: bootstrap agents/ workspace\"",
            ],
        )

    def test_start_contract_requires_agents_worktree_baseline_and_tiny_wu(self) -> None:
        text = read_command("start.md")
        self.assert_contains_all(
            text,
            [
                "If `agents/` does not exist, stop",
                "if another phase is already `active`, stop",
                "git worktree add .worktrees/phase-{n} -b feature/phase-{n}",
                "Verify with `git branch --show-current`",
                "Verify clean baseline: run tests",
                "type: phase",
                "test_status: not-run",
                "planned -> active -> ready-for-review -> accepted -> done",
                "git commit -m \"WU-TW-{k}: init phase {n} roadmap\"",
            ],
        )

    def test_test_contract_records_pass_waive_or_opens_fix_round(self) -> None:
        text = read_command("test.md")
        self.assert_contains_all(
            text,
            [
                "there must be an active phase",
                "otherwise stop and resolve the mismatch first",
                "If `$ARGUMENTS` is empty or unrecognized, stop",
                "test_status: failing",
                "git worktree add .worktrees/fix-{n}-{slug}",
                "Create or reuse `agents/roadmap/PHASE_{n}_FIX.md`",
                "Do not create a new fix-round file per bug batch",
                "Fix WU status moves to `ready-for-review`",
                "test_status: pass",
                "test_status: waived",
                "test_waive_reason: {reason from $ARGUMENTS}",
                "Never mark a phase done without `/wur:done`",
            ],
        )
        self.assert_contains_none(
            text,
            [
                "Create `agents/roadmap/FIX_P{n}_{slug}.md`",
                "When all fix WUs are done",
            ],
        )

    def test_done_contract_gates_closeout_and_preserves_history(self) -> None:
        text = read_command("done.md")
        self.assert_contains_all(
            text,
            [
                "This command may run only when the current user request explicitly invokes `/wur:done`",
                "If the agent merely believes the phase is ready, stop",
                "Active Work Unit` must be `none`",
                "allow `test_status: pass`",
                "allow `test_status: waived` only if `test_waive_reason` is non-empty",
                "git merge --no-ff fix/phase-{n}-{slug}",
                "git merge --no-ff \"feature/phase-{n}\"",
                "run the tests again on the merged result",
                "git worktree remove .worktrees/phase-{n}",
                "git branch -d feature/phase-{n}",
                "client-confirmed `done`",
                "mark the phase row `done`",
                "Commit Index table in `agents/roadmap/ALL.md` exceeds 30 rows",
                "git commit -m \"WU-P{n}-close: mark phase {n} done\"",
            ],
        )

    def test_abort_contract_requires_trace_and_never_merges(self) -> None:
        text = read_command("abort.md")
        self.assert_contains_all(
            text,
            [
                "they never reach the default branch",
                "Use `/wur:done`",
                "Refuse to abort if any commits",
                "unless** the user explicitly confirms loss",
                "status: aborted",
                "abort_mode: soft",
                "abort_mode: waived",
                "abort_mode: hard",
                "clear `Active phase`",
                "clear `Active Work Unit`",
                "git commit -m \"WU-P{n}-abort: abandon phase {n} ({mode})\"",
            ],
        )

    def test_upgrade_contract_is_migration_not_reset(self) -> None:
        text = read_command("upgrade.md")
        self.assert_contains_all(
            text,
            [
                "Treat current state as raw input",
                "`/wur:upgrade` is **not** an escape hatch",
                "Refuse if any phase is active",
                "Verify clean working tree",
                "Create backup tag",
                "Never overwrite anything that already exists",
                "No data loss",
                "Status values cannot regress",
                "do not commit",
                "delete the backup tag",
            ],
        )

    def test_graph_contract_keeps_markdown_canonical_and_artifacts_derived(self) -> None:
        text = read_command("wiki/graph.md")
        self.assert_contains_all(
            text,
            [
                "Markdown under `agents/` remains canonical",
                "graph files are stale or missing, rebuild them",
                "`nodes.jsonl`",
                "`edges.jsonl`",
                "`graph.sqlite`",
                "`graph.graphml`",
                "Do not rewrite canonical pages during extract",
                "cite canonical pages from `agents/`, not the derived JSONL/GraphML files",
            ],
        )


if __name__ == "__main__":
    unittest.main()
