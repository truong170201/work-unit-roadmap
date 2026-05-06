# Work Unit Roadmap

**MANDATORY FIRST STEP:** Invoke the `using-wur` skill before any response. It teaches how to find and use WUR skills.

## Skills (3)

All live under `skills/`:

- **`using-wur`** — bootstrap. Skill discovery + Red Flags. Invoke first.
- **`wur-guidelines`** — core workflow. Phases, Work Units, verification, one commit per WU.
- **`using-git-worktrees`** — isolated implementation under `.worktrees/`.

## Commands (13)

Phase command procedures live under `commands/`, wiki command procedures under `commands/wiki/`.

Claude Code exposes them as `/wur:*` and `/wur:wiki:*`. Other clients are not bundled as first-class plugin targets; they can reuse the same command files only if their runtime provides a command mechanism, otherwise invoke the same intent in natural language.

```text
/wur:init [project-context] # one-time bootstrap of agents/ workspace (schema v1)
/wur:upgrade               # migrate agents/ between WUR plugin versions (schema bump)
/wur:start {n}             # create worktree + feature branch, init phase file
/wur:test                  # record pass/waive/fail test status → spawn fix worktree if needed
/wur:done                  # merge phase, cleanup worktrees, close phase
/wur:abort {n}             # abandon a phase: discard worktree + branches, mark aborted
/wur:status                # current phase/WU/worktree summary
/wur:wiki:upgrade          # add/upgrade graph layer on agents/
/wur:wiki:add {src}        # ingest a source into agents/research/
/wur:wiki:ask {q}          # query agents/ wiki with citations
/wur:wiki:lint             # structural + semantic health check on agents/
/wur:wiki:stats            # size, status, and graph health for agents/
/wur:wiki:graph {action}   # extract, lint, or query derived graph artifacts
```

## Summary

```text
Small task, verify, commit. Repeat.
```

**New project (first time):**
1. Run `/wur:init` once, optionally with project context, or ask "initialize WUR for ..." → creates `agents/` workspace after resolving existing project context; asks only if no context exists.
2. Run `/wur:start 1`, or ask "start phase 1 with WUR" → creates worktree and phase file, verify baseline.

**Every session (returning agent):**
1. Invoke `using-wur` → `wur-guidelines`.
2. Read `agents/project/PHILOSOPHY.md`, `agents/project/USAGE.md` (once per project context).
3. Read `agents/roadmap/ALL.md` → active phase, active WU, blockers, default branch.
4. Read `agents/roadmap/PHASE_{n}.md` → acceptance criteria, verification.
5. `cd .worktrees/phase-{n}` — verify with `git branch --show-current`. If the worktree doesn't exist, run `/wur:start {n}` first. Never work from main.
6. Implement one WU → verify → inspect diff → update roadmap + commit together.
7. Report what changed, what was verified, what remains, next safe step.

**Wiki only (no implementation):**
1. Invoke `using-wur` → `wur-guidelines`.
2. Run `/wur:wiki:upgrade` when available, or ask for the equivalent WUR wiki action, then use add/ask/lint/stats/graph as needed. No worktree required.

If any skill file is missing, stop and report it before proceeding.
