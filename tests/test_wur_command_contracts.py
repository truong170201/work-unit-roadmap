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
                "Detect project departments and specialists",
                "Coverage Matrix",
                "Coverage categories are checklists, not mandatory files",
                "domain expertise, product/strategy, architecture/engineering, design/UX/content, data/AI, security/compliance, QA/testing, operations/support, and platform/tooling/integration",
                "game design, level design, gameplay/engine, art/technical art, audio, QA/playtest, production, and platform-specific expertise",
                "Do not create generic specialist placeholders",
                "Create or update `agents/project/DESIGN.md`",
                "for software/dev projects",
                "Design Contract",
                "Visual Theme & Atmosphere",
                "Color Palette & Roles",
                "Component Styling",
                "Technology Judgment",
                "Create or update `agents/project/TECH_STACK.md`",
                "Default Stack Suggestions",
                "Tailwind CSS + shadcn/ui",
                "Operational visibility tags",
                "state-active",
                "needs-review",
                "open-question",
                "contradiction",
                "coverage-gap",
                "test-failing",
                "Tags are observation signals; status fields remain authoritative",
                "specialist recommendations do not automatically become Work Units",
                "git commit -m \"WU-TW-000: bootstrap agents/ workspace\"",
            ],
        )

    def test_start_contract_requires_agents_worktree_baseline_and_tiny_wu(self) -> None:
        text = read_command("start.md")
        self.assert_contains_all(
            text,
            [
                "If `agents/` does not exist, stop",
                "Run `git status --short agents/` before creating the worktree",
                "If any `agents/` path is untracked or modified, stop",
                "git add agents/",
                "worktree only receives tracked files from the base commit",
                "agents/project/DESIGN.md",
                "agents/project/TECH_STACK.md",
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

    def test_verification_contract_is_scoped_by_default(self) -> None:
        skill = (ROOT / "skills" / "wur-guidelines" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        start = read_command("start.md")
        test = read_command("test.md")
        done = read_command("done.md")

        self.assert_contains_all(
            skill,
            [
                "Verification is scoped by default",
                "Start from the active WU acceptance criteria and the user's request",
                "Do not run full-project verification after every WU by default",
                "Full-project verification is required only for phase closeout, high-risk/shared changes, schema/graph/script changes, or explicit acceptance criteria",
                "A scoped verification matrix",
                "Docs-only WU",
                "Implementation WU",
                "Graph/schema/script WU",
                "Phase closeout",
            ],
        )
        self.assert_contains_all(
            start,
            [
                "Baseline verification is full enough to establish starting health",
                "Later WU verification is scoped by default",
            ],
        )
        self.assert_contains_all(
            test,
            [
                "Use the phase-level verification strategy",
                "This is broader than normal WU-scoped verification",
            ],
        )
        self.assert_contains_all(
            done,
            [
                "Closeout verification is full-phase verification",
                "Do not use WU-scoped checks as the only closeout evidence",
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

    def test_ima_contract_enriches_wiki_and_gates_roadmap_execution_state(self) -> None:
        text = read_command("wiki/ima.md")
        self.assert_contains_all(
            text,
            [
                "Idea-to-MVP analysis",
                "argument-hint: \"<idea-or-context>\"",
                "If `agents/` does not exist, stop",
                "Do not silently run `/wur:init`",
                "Treat `$ARGUMENTS` as raw idea/context",
                "Do not require flags",
                "Infer roadmap intent from natural language",
                "Infer phase focus from natural language",
                "Read `agents/project/DESIGN.md` when present",
                "Read `agents/project/TECH_STACK.md` when present",
                "Read `agents/departments/` and `agents/specialists/` when present",
                "Re-check the Specialist Coverage Matrix",
                "Coordinator consolidates specialist output",
                "one specialist recommendation does not equal one Work Unit",
                "INTAKE",
                "DISCOVER",
                "DEFINE",
                "DECIDE",
                "ROADMAP",
                "Only update roadmap files when the user intent calls for roadmap planning changes",
                "Planning changes may create or revise `planned` Work Units",
                "Do not mark any Work Unit `active`, `accepted`, or `done`",
                "Do not run `/wur:start`, `/wur:test`, `/wur:done`, or `/wur:abort`",
                "| {today} | wiki-ima |",
                "suggest running `/wur:wiki:graph extract`",
            ],
        )
        self.assert_contains_none(text, ["--update-roadmap", "--phase {n}"])

    def test_specialist_registry_contract_prevents_roadmap_bloat(self) -> None:
        skill = (ROOT / "skills" / "wur-guidelines" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assert_contains_all(
            skill,
            [
                "Specialist Registry",
                "`agents/departments/`",
                "`agents/specialists/`",
                "`agents/project/DESIGN.md`",
                "software/dev projects should create or maintain",
                "Design Contract",
                "Visual Theme & Atmosphere",
                "Component Styling",
                "project-specific",
                "runtime optional",
                "Coordinator owns final planning and execution decisions",
                "Specialist output must be consolidated",
                "one recommendation is not one Work Unit",
                "Coverage Matrix",
                "coverage gap",
                "domain expertise, product/strategy, architecture/engineering, design/UX/content, data/AI, security/compliance, QA/testing, operations/support, and platform/tooling/integration",
                "Domain examples are illustrative, not exhaustive",
                "game design, level design, gameplay/engine, art/technical art, audio, QA/playtest, production, and platform-specific expertise",
                "Technology Judgment",
                "Default Stack Suggestions",
                "`agents/project/TECH_STACK.md`",
                "Optional Codex App Server Delegation",
                "Codex App Server, not Codex MCP",
                "`skills/wur-guidelines/scripts/wur_codex_delegate.py`",
                "`needs-user`",
                "`--full-access`",
                "Never kill processes by the name `codex`",
                "Tailwind CSS + shadcn/ui",
                "Vite + React + TypeScript",
                "Next.js App Router + TypeScript",
                "Expo + TypeScript + NativeWind",
                "Vite + TypeScript + Phaser",
                "Vite + TypeScript + Three.js",
                "Operational visibility tags",
                "state-active",
                "needs-review",
                "open-question",
                "contradiction",
                "coverage-gap",
                "test-failing",
                "Tags are observation signals; status fields remain authoritative",
                "Prefer TypeScript for non-trivial web/app code",
                "Consider Vite + React first for common frontend web apps",
                "Avoid plain HTML/CSS/JS for app-scale work unless explicitly requested",
                "Defaults are recommendations, not mandates",
                "Record material stack choices",
                "Do not mark WUs `active`, `accepted`, or `done`",
            ],
        )

    def test_active_phase_context_sync_contract_prevents_agents_merge_conflicts(self) -> None:
        skill = (ROOT / "skills" / "wur-guidelines" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        scripts = (ROOT / "skills" / "wur-guidelines" / "scripts" / "README.md").read_text(
            encoding="utf-8"
        )

        self.assert_contains_all(
            skill,
            [
                "Active phase wiki ownership",
                "`agents/roadmap/PHASE_{n}.md`, `agents/roadmap/ALL.md`, and `agents/roadmap/log.md` must be updated in the active phase/fix worktree",
                "Selective context sync",
                "`skills/wur-guidelines/scripts/wur_sync_agents_context.py`",
                "do not `git merge` the default branch into the phase just to get those files",
                "refuses to overwrite `agents/roadmap/`, `agents/index.md`, `agents/SCHEMA.md`, or graph artifacts",
            ],
        )
        self.assert_contains_all(
            readme,
            [
                "Active phase roadmap files are branch-owned",
                "`wur_sync_agents_context.py`",
                "do not `git merge` just to pick up wiki context",
            ],
        )
        self.assert_contains_all(
            scripts,
            [
                "`wur_sync_agents_context.py`",
                "Selectively import new agents/ context files into an active phase",
                "Do not `git merge` only to import new `agents/` context files",
            ],
        )


if __name__ == "__main__":
    unittest.main()
