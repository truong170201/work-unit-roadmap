---
name: wur-guidelines
description: "You MUST use this before any implementation work. Enforces roadmap-driven development: atomic Work Units, verification evidence, clean git history, one commit per completed WU. Use when planning, executing, tracking, resuming, or repairing roadmap-driven work."
---

# Work Unit Roadmap

Produce real project results with clear tracking, clean commits, and recoverable history. Operate like a senior engineer: precise, scoped, test-oriented, accountable.

```text
Small task, verify, commit. Repeat.
```

## Scope Boundary

WUR is intentionally narrow:
- **Wiki = plan** — `agents/` stores roadmap, phase state, research, decisions, reports, and the derived graph contract.
- **Outside wiki = execution** — worktrees, branches, hooks, commits, merge/abort/fix flow.
- **Outside wiki = checks** — local deterministic scripts such as lint, stats, graph extract/query, and consistency checks.

WUR does **not** define hosted CI/CD, deployment pipelines, cloud services, or project-specific runtime infrastructure. Those live outside WUR.

<HARD-GATE>
Before modifying any project source code, tests, or application configs, you MUST have:
1. Read the active phase file and confirmed the current Work Unit
2. Confirmed you are inside the correct worktree (`.worktrees/phase-{n}` or `.worktrees/fix-{n}-*`)
3. Understood the acceptance criteria and verification steps

**Exempt — run from the main repo, no worktree required:**
- **`/wur:init`** — creates `agents/` scaffolding; writing `.gitignore` here is setup, not implementation
- **`/wur:start`** — creates the worktree itself; satisfies this gate for all work that follows
- **`/wur:status`** — read-only
- **`/wur:wiki:*`** — knowledge management, not implementation; no phase file or worktree needed

This gate applies to every line of code/test/config changed during implementation, regardless of perceived simplicity.
</HARD-GATE>

## Checklist

**Applies to implementation work only.** Wiki operations (`/wur:wiki:*`) and workspace/phase setup (`/wur:init`, `/wur:start`) do not follow this checklist — they have their own command procedures.

You MUST complete these in order:

1. **Read roadmap** — `agents/roadmap/ALL.md` → find active phase, active WU, latest completed unit, blockers
2. **Read phase file** — `agents/roadmap/PHASE_{n}.md` → acceptance criteria, scope, dependencies, verification
3. **Confirm repo state** — `git status`, `git diff`, `git log -1 --oneline`
4. **Enter worktree** — `cd .worktrees/phase-{n}` (or `fix-{n}-*`), then verify with `git branch --show-current` — must show `feature/phase-{n}`. If the worktree does not exist, stop and run `/wur:start {n}` first. **Never run implementation commands from the main repo.**
5. **Implement one WU** — exactly one goal, bounded scope, no unrelated changes
6. **Verify** — run the verification command(s) from the WU. Must pass.
7. **Inspect diff** — `git diff --stat`, review changes for scope creep
8. **Update roadmap** — mark WU `done` in the phase file, add commit hash, update ALL.md commit index, append to log.md if applicable
9. **Commit** — one commit per WU, containing **both** implementation files and roadmap updates together: `WU-P{n}-{unit}: {short description}`
10. **Report** — what changed, what was verified, what remains, next safe step

## Minimal Enforcement Model

WUR does not need a planner. It needs a gatekeeper.

**Principle:** The right path should be the easiest path. The wrong path should be blocked — or at minimum leave a trace.

### Non-bypass rules

1. `/wur:init` must stop if `agents/` already exists, unless the user is intentionally resetting the workspace.
2. `/wur:start` must stop if `agents/` does not exist.
3. Implementation must stop if you are not inside the correct worktree.
4. `/wur:done` must stop if any related fix round is still `active`.
5. `/wur:done` requires `test_status = pass` or `test_status = waived` with a non-empty reason.
6. A WU commit must include both implementation changes and roadmap updates together.

### Allowed waives

A waive is valid only when it leaves a trace in the phase file or log.

- intentional workspace reset during `/wur:init`
- no test suite exists
- tooling failure is outside the WU scope
- exploratory/spike phase
- required manual/device environment is unavailable
- graph layer is not enabled, so graph-specific checks are skipped

### Enforcement anchors

To make the rules harder to bypass in real git usage, `/wur:init` should scaffold project-root git hooks:
- `commit-msg` — enforce WU-prefixed commit messages
- `pre-commit` — block implementation commits on the default branch and require roadmap updates with code changes
- `pre-push` — block pushing the default branch while a phase or WU is still active

See `skills/wur-guidelines/references/git-hooks.md` for the minimal hook templates.

## Red Flags

These thoughts mean STOP — you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is a tiny fix, no need for a WU" | Every change is a WU. Tiny ones use Tiny WU flow. |
| "I'll just fix this while I'm here" | Unrelated fixes are scope creep. New WU or leave it. |
| "The verification is obvious" | Run the command. Evidence, not assumptions. |
| "I'll update the roadmap later" | Update now. Stale roadmaps cause confusion. |
| "I'll commit the code now, roadmap in a separate commit" | No. One commit = implementation + roadmap update together. Separate roadmap commits pollute git log. |
| "One commit for two WUs is fine" | One WU = one commit. Always. |
| "The test failed but it's probably fine" | Blocked. Do not mark done. Fix or split new WU. |
| "I'll just add one more feature" | Scope creep. New WU in next phase. |
| "I'll just use the main branch for this" | Every phase has a dedicated worktree. Create it. |
| "I'll git checkout to switch feature branches" | No. Use a worktree. The main repo stays on the default branch. |
| "I can skip the phase file read" | Read it. Acceptance criteria change. |
| "I'll just `rm -rf agents/` and re-init" | No. Use `/wur:upgrade`. `/wur:init` refuses populated workspaces for a reason. |
| "I'll bump `schema_version` by hand" | No. Only an automated migration script may bump it. |

## Core Workflow

### Phase & Work Unit

Every phase has: goal, success criteria, exit gate, out of scope, dependencies, Work Units table, verification strategy.

Every Work Unit has: ID, goal, acceptance criteria, scope, dependencies, parent (fix WUs only), verification, status, commit reference.

**Splitting rule** — split before coding if a WU: has >1 goal, touches unrelated modules, mixes feature + refactor, mixes behavior + formatting, needs >1 independent verification, or is too large to revert independently.

**Fix WUs** — created during `/wur:test`. Stored in a **separate file** `agents/roadmap/FIX_P{n}_{slug}.md` — never appended to `PHASE_{n}.md`. Each fix WU carries a `Parent WU` field. The phase file's Fix Rounds table links to the FIX file. Live on `fix/phase-{n}-{slug}` branch in a dedicated worktree.

**Tiny WUs** — for roadmap maintenance, doc updates. Prefix `WU-TW-{number}`. Same flow: implement → verify → commit → update ALL.md.

**Wiki operations** — `/wur:wiki:*` commands are not Work Units. They are knowledge management operations that run from the main repo. No WU ID, no phase file, no worktree, and no ALL.md update required.

**Activity log** — `agents/roadmap/log.md` is an append-only journal. Agents append one line on: phase open, fix round open, fix round close, phase close. Never edit past entries. Use it to navigate "what happened when" without reading every phase file.

### ALL.md Commit Index — mandatory archival

When the Commit Index table exceeds 30 rows:
1. Move completed-phase rows to `agents/reports/commit-index-PHASE_{n}.md`.
2. Replace in ALL.md with: `| PHASE_{n} (archived) | {N} WUs | [[reports/commit-index-PHASE_{n}]] | done |`
3. Commit as a Tiny WU: `WU-TW-{k}: archive PHASE_{n} commit index`

This is not optional. An ALL.md with 70+ rows causes LLM update errors that corrupt roadmap state.

### Task Branch Workflow

All work uses git worktrees under `.worktrees/` for isolation. Never use `git checkout` to switch branches — create a worktree instead.

```text
.worktrees/phase-{n}          ← /wur:start creates via git worktree add -b feature/phase-{n}
.worktrees/fix-{n}-{slug}     ← /wur:test creates via git worktree add -b fix/phase-{n}-{slug}
```

Each worktree is an independent directory with its own branch checked out. No stashing, no switching. Cleanup via `/wur:done`: `git worktree remove` + `git branch -d`.

Wiki operations (`/wur:wiki:*`) and workspace setup run from the main repo — no worktree is created or needed.

**Long-running phases** — if `feature/phase-{n}` lives more than ~3 days, the default branch (`main`/`master`/`develop`) may have moved. Sync inside the phase worktree before the next WU to keep `/wur:done` merges clean:

```bash
cd .worktrees/phase-{n}
git fetch origin
git rebase "origin/$base"   # preferred — keeps WU commits linear
# or, if rebase is risky:
git merge --no-ff "origin/$base" -m "WU-TW-{k}: sync $base into feature/phase-{n}"
```

Resolve conflicts inside the worktree, never on the default branch. The merge or rebase commit becomes a Tiny WU on the feature branch.

**Phase abort** — if a phase was started by mistake or is being abandoned, run `/wur:abort {n}`. Do not manually `git branch -D` — the command also marks the phase `aborted` in the roadmap and records the reason in `log.md`.

### Schema versioning

Every `agents/` workspace declares its layout in `agents/SCHEMA.md` YAML frontmatter:

```yaml
---
schema_version: 1
---
```

The first published layout (the `wiki` layout) is **schema `1`**. When a future WUR plugin ships a new schema, it adds a migration script under `skills/wur-guidelines/references/migrations/v{from}-to-v{to}.md` and bumps the plugin's latest schema number.

Rules:

- **`/wur:init` refuses to overwrite** an existing populated `agents/`. Use `/wur:upgrade` for any populated workspace.
- **`/wur:upgrade` treats the current `agents/` as raw input.** It never assumes the workspace is already in the target shape — it always reads the old shape, transforms, then writes the new shape and bumps `schema_version`.
- **`schema_version` is the only authoritative marker.** File layout and naming cannot be inferred — always derive from the schema map for the declared version.
- **Migrations are unidirectional and atomic per step.** Rollback is via `git revert`.
- **Never hand-edit `schema_version`.** The bump is the last action of an automated migration step.

If `agents/SCHEMA.md` is missing the `schema_version` frontmatter (e.g. the workspace was created before versioning), `/wur:upgrade` backfills `schema_version: 1` as the legacy migration step.

### Verification

Run the verification command. Record the result. If it fails: do not commit, fix or split new WU. Never mark `done` without passing verification.

### Wiki & Derived Graph

The `agents/` folder IS the project wiki — roadmap, research, decisions, and docs in one unified place. There is no separate `wiki/` directory.

```text
agents/
  project/         PHILOSOPHY.md · USAGE.md
  roadmap/         ALL.md · PHASE_*.md · FIX_*.md · log.md
  research/        ingested sources and analysis
  docs/            ADRs, durable notes, synthesis
  reports/         verification and completion reports
  references/      external references, API notes
  raw/             immutable source material (tracked)
  SCHEMA.md        wiki conventions: types, status, frontmatter schema
  index.md         one-line summary of every page
  graph/           ontology.yaml · README.md · .gitignore
                   nodes.jsonl · edges.jsonl · summary.md · last_extracted.md  (tracked)
                   graph.sqlite · graph.graphml  (gitignored — binary/large, rebuild anytime)
```

Graph pages use YAML frontmatter with `type`, `status`, `tags` (required — see `agents/SCHEMA.md ## Tag Conventions` for format rules and predefined vocabulary), and typed edges such as `depends_on`, `parent`, `verifies`, and `informs`. The graph layer is optional: run `/wur:wiki:upgrade` to enable it, then `/wur:wiki:graph extract` to compile `nodes.jsonl`, `edges.jsonl`, and `graph.sqlite`. Open `agents/` in Obsidian for instant graph view. Use path-style wikilinks such as `[[roadmap/PHASE_1]]`, not basename-only links.

Wiki operations:
- **upgrade** (`/wur:wiki:upgrade`) — add graph-layer files and conventions
- **ingest** (`/wur:wiki:add`) — add knowledge into `agents/research/`
- **query** (`/wur:wiki:ask`) — index-first, graph-aware when derived artifacts exist
- **lint** (`/wur:wiki:lint`) — structural/semantic checks, plus graph-aware checks when the graph layer exists
- **stats** (`/wur:wiki:stats`) — size, status, and graph health dashboard
- **graph** (`/wur:wiki:graph`) — explicit graph extract/lint/query operations on derived artifacts

### Commands

Full procedures in `commands/<command>.md` (phase) and `commands/wiki/<command>.md` (wiki). Read before executing. They are registered under the plugin namespace `wur`.

```text
/wur:init                                               # one-time project bootstrap
/wur:upgrade                                            # migrate agents/ between WUR plugin versions
/wur:start {n}  /wur:done  /wur:abort {n}  /wur:test  /wur:status
/wur:wiki:upgrade  /wur:wiki:add {src}  /wur:wiki:ask {q}  /wur:wiki:lint  /wur:wiki:stats  /wur:wiki:graph {action}
```

**Commit format:**
- Implementation WU: `WU-P{n}-{unit}: {description}` — e.g. `WU-P01-003: add login validation`
- Tiny WU: `WU-TW-{n}: {description}` — e.g. `WU-TW-001: fix typo in README`
- Phase close (administrative): `WU-P{n}-close: mark phase {n} done`
- Fix-round merge (administrative): `WU-P{n}-fix: merge fix/phase-{n}-{slug}`
- Phase abort (administrative): `WU-P{n}-abort: abandon phase {n} ({mode})`

**Rule**: Only `/wur:done` from the client triggers merge + closeout. `/wur:abort` discards a phase without merging — never use it as a shortcut to skip closeout.

## Multi-Agent Protocol

Skip this section for single-agent projects. Adopt when a second agent joins.

### Merge conflict on `agents/roadmap/log.md`

`log.md` is append-only. When a merge conflict occurs:
1. Keep ALL entries from both sides — never drop a line.
2. Sort by date (first column). If dates are identical, preserve both lines.
3. Use `git checkout --ours agents/roadmap/log.md` then manually append the other side's new lines.
4. Never rebase or squash log entries.

## Senior Agent Behavior

- Be exact and concise. Keep scope controlled. Prefer simple correct changes.
- Ask or block when requirements are ambiguous.
- Preserve project history. Leave the roadmap understandable and the working tree clean.
- Never fake completion, skip verification, skip roadmap updates, or bury unrelated changes.

The next agent should be able to open `agents/project/PHILOSOPHY.md`, `agents/project/USAGE.md`, `agents/roadmap/ALL.md`, the active phase file, inspect recent commits, and understand exactly what happened and what should happen next.
