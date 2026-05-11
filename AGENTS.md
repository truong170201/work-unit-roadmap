# Work Unit Roadmap

**MANDATORY FIRST STEP:** Invoke the `using-wur` skill before any response. It teaches how to find and use WUR skills.

## Skills (3)

All live under `skills/`:

- **`using-wur`** — bootstrap. Skill discovery + Red Flags. Invoke first.
- **`wur-guidelines`** — core workflow. Wiki, Work Units, contracts, verification, receive, closeout.
- **`using-git-worktrees`** — optional isolation guidance when a contract asks for a sparse worktree.

## Commands (14)

Phase command procedures live under `commands/`, wiki command procedures under `commands/wiki/`.

Claude Code exposes them as `/wur:*` and `/wur:wiki:*`. Other clients are not bundled as first-class plugin targets; they can reuse the same command files only if their runtime provides a command mechanism, otherwise invoke the same intent in natural language.

```text
/wur:init [project-context] # one-time bootstrap of agents/ workspace (schema v1)
/wur:upgrade               # migrate agents/ between WUR plugin versions (schema bump)
/wur:start {n}             # create or refresh contracts/PHASE_{n}_CONTRACT.md
/wur:test                  # record pass/waive/fail status in agents/ and contract
/wur:done                  # client-confirmed closeout after contract reports are verified
/wur:abort {n}             # abandon a phase with trace
/wur:status                # current phase/WU/contract/wiki summary
/wur:wiki:upgrade          # add/upgrade graph layer on agents/
/wur:wiki:add {src}        # ingest a source into agents/research/
/wur:wiki:ima {idea}       # Idea-to-MVP wiki enrichment; optional roadmap planning updates
/wur:wiki:ask {q}          # query agents/ wiki with citations
/wur:wiki:lint             # structural + semantic health check on agents/
/wur:wiki:stats            # size, status, and graph health for agents/
/wur:wiki:graph {action}   # extract, lint, or query derived graph artifacts
```

## Summary

```text
Small task, verify, report, receive. Repeat.
```

**New project (first time):**
1. Run `/wur:init` once, optionally with project context, or ask "initialize WUR for ..." → creates `agents/` workspace after resolving existing project context; asks only if no context exists.
2. Run `/wur:start 1`, or ask "create the WUR contract for phase 1" → creates or refreshes `contracts/PHASE_1_CONTRACT.md`.

**Every session (returning agent):**
1. Invoke `using-wur` → `wur-guidelines`.
2. Read `agents/project/PHILOSOPHY.md`, `agents/project/USAGE.md`, `agents/project/DESIGN.md`, and `agents/project/TECH_STACK.md` when present.
3. Read `agents/roadmap/ALL.md` → active phase, active WU, blockers, default branch.
4. Read `agents/roadmap/PHASE_{n}.md` → acceptance criteria, verification.
5. Read or create `contracts/PHASE_{n}_CONTRACT.md`.
6. Executor follows the contract and must not modify `agents/`.
7. WUR receives report evidence, updates `agents/`, and reports the next safe step.

**Wiki only (no implementation):**
1. Invoke `using-wur` → `wur-guidelines`.
2. Run `/wur:wiki:upgrade` when available, or ask for the equivalent WUR wiki action, then use add/ima/ask/lint/stats/graph as needed.

If any skill file is missing, stop and report it before proceeding.
