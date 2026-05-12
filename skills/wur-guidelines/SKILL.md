---
name: wur-guidelines
description: "Use when planning, tracking, contracting, receiving reports, or closing Work Unit Roadmap work. Keeps agents/ as wiki, contracts/ as execution handoff, and client-confirmed closeout only."
---

# Work Unit Roadmap

Produce project results with clear tracking, small Work Units, verification evidence, and recoverable history.

```text
Small task, verify, report, receive. Repeat.
```

## Scope Boundary

WUR is intentionally narrow:
- **Wiki = plan** — `agents/` stores roadmap, phase state, research, decisions, reports, and the derived graph contract.
- **Contract = execution boundary** — `contracts/PHASE_{n}_CONTRACT.md` tells an external executor what to do and where to report.
- **Outside wiki = checks** — local deterministic scripts such as lint, stats, graph extract/query, contract creation, and consistency checks.

WUR does **not** define hosted CI/CD, deployment pipelines, cloud services, project-specific runtime infrastructure, or runtime subagent orchestration.

## WUR Contract Model

`agents/` is the source-of-truth wiki. It is the project second brain: roadmap, research, decisions, design, tech stack, specialist registry, reports, graph contract, and status.

`contracts/rule.md` stores shared execution rules. `contracts/PHASE_{n}_CONTRACT.md` is the phase execution contract. Phase contracts contain task brief, pending Work Units, skipped completed WUs, verification requirements, explicit Allowed Read References, fix rounds, and returned executor reports. `agents/reports/` stores durable WUR reports and summaries: research synthesis, verification, audits, receive summaries, completion reports, archives, and other long-lived project reports.

Rules:
- Do not create `contracts/outbox/` or `contracts/inbox/`.
- Do not create Phase Fix ledgers for new work.
- Executors add or update fix rounds in the same contract file when verification fails; WUR does not need a separate fail helper.
- Executors may update only Status and Commit cells for touched WU rows in the active contract's Pending Work table, plus `## Execution Rounds And Reports`; they must not edit the contract header, goal, success criteria, scope, dependencies, verification text, Allowed Read References, any other contract file, or `agents/`.
- Executor-owned Pending Work statuses may only become `active`, `ready-for-review`, `blocked`, or `deferred`.
- Accepted/done requires explicit current-client approval for exact WU IDs.
- Only reports appended inside the active phase contract are valid WUR receive evidence.
- Reports outside `contracts/` or outside the active phase contract are invalid for WUR receive until copied into the active contract.
- Commit provenance must match the WU context: implementation WUs cite implementation commits; contract/docs cleanup WUs cite contract/docs commits; no-code WUs use `none` with evidence.
- Do not use a docs, contract-cleanup, or planning commit as implementation evidence.
- For every touched WU, update its Pending Work Status and Commit cells before appending the report.
- Executor reports must include lifecycle evidence for every touched WU: before status, suggested after status, result, commit, verification, blockers, and coverage gaps.
- Executor status suggestions without explicit client approval stop at `active`, `ready-for-review`, `blocked`, or `deferred`; WUR receives the report and applies roadmap state in `agents/`.
- External executors may read only the `agents/` paths listed under Allowed Read References; they must not scan all of `agents/` or edit `agents/`.
- Allowed Read References list specific project docs, departments, and specialists for role-aware execution.
- Infer useful specialist lenses from the listed references and WU scope; do not require WUR to assign one person per WU.
- Report which specialist lenses were applied and any material coverage gaps.
- WUR receives and validates reports before updating `agents/`.
- `/wur:start` creates or refreshes `contracts/rule.md` and the phase contract; it does not execute code by itself.
- `/wur:done` only runs after explicit client request.

Sparse worktree guidance belongs in `contracts/rule.md`. The executor first reads the active contract and decides whether there is executable project work. If there is no implementation task, it reports blocked/no-op/clarification-needed without creating a worktree. If implementation requires editing project files, it creates or reuses a sparse worktree that excludes `agents/` and `contracts/`. Keep WUR state in the main project root only; the executor uses the phase contract as the brief and returns a report for WUR to receive.

## Checklist

1. **Read roadmap** — `agents/roadmap/ALL.md` → active phase, active WU, blockers, latest completed unit.
2. **Read phase file** — `agents/roadmap/PHASE_{n}.md` → goal, success criteria, WUs, verification.
3. **Create or refresh contract** — `python skills/wur-guidelines/scripts/wur_contract.py create --phase {n}`.
4. **Executor works from contract** — one WU or scoped phase slice, no edits to `agents/`.
5. **Verify** — run checks scoped to acceptance criteria and changed surface.
6. **Report** — update touched Pending Work Status/Commit cells, then append evidence under `## Execution Rounds And Reports`, including WU lifecycle state suggestions.
7. **Receive** — WUR validates report, then updates roadmap/status/log in `agents/`.
8. **Close only on request** - only `/wur:done` from the current client request can close a phase. Closeout reads the contract ledger: report-backed and client-approved WUs may move to `done`; unreported work is deferred or blocked; skipped completed WUs stay unchanged.

## Minimal Enforcement Model

Principle: the right path should be the easiest path, and the wrong path should be blocked or leave a trace.

Non-bypass rules:
1. `/wur:init` must stop if `agents/` already exists, unless the user is intentionally resetting it.
2. `/wur:start` must stop if `agents/` does not exist.
3. `/wur:start` must produce or refresh `contracts/PHASE_{n}_CONTRACT.md` and skip WUs already `accepted` or `done`.
4. External executors must not edit `agents/` or create new roadmap/fix files.
5. WUR must not trust a report without checking commit hash, changed files, and verification evidence when implementation changed.
6. `/wur:done` requires `test_status = pass` or `test_status = waived` with a non-empty reason.
7. `/wur:done` may run only when the current user request explicitly invokes `/wur:done`.
8. Agents may move WUs to `ready-for-review`; only the client may accept or mark WUs `done`.

Allowed waives leave a trace: no test suite, tooling failure outside scope, exploratory phase, unavailable device/manual environment, or graph layer not enabled.

## Red Flags

| Thought | Reality |
|---|---|
| "I can just edit agents/ from the executor" | No. Executors report; WUR receives and updates `agents/`. |
| "One more executor report file is cleaner" | No. Use one phase contract file to avoid handoff noise. Durable WUR reports and summaries belong in `agents/reports/`. |
| "The fix needs PHASE_N_FIX.md" | No. Add another execution round in the contract. |
| "Tests pass, so I can run `/wur:done`" | No. Report readiness and wait for the client to send `/wur:done`. |
| "The WU is verified, so it is done" | No. Mark `ready-for-review`; `done` is client-confirmed. |
| "I'll just add one more feature" | Scope creep. New WU or next phase. |
| "I can skip the phase file read" | Read it. Acceptance criteria change. |

## Phase & Work Unit

Every phase has: goal, success criteria, exit gate, out of scope, dependencies, Work Units table, and verification strategy.

Every Work Unit has: ID, goal, acceptance criteria, scope, dependencies, verification, status, and commit/report reference.

WU lifecycle:

```text
planned -> active -> ready-for-review -> accepted -> done
```

Agents own `planned`, `active`, `ready-for-review`, `blocked`, and `deferred`. Clients own `accepted` and `done`. After implementation, verification, report receive, and roadmap update, WUR may move the WU to `ready-for-review`. Do not mark a WU `done` because tests passed.

Splitting rule: split before execution if a WU has more than one goal, touches unrelated modules, mixes feature and refactor, mixes behavior and formatting, needs more than one independent verification path, or is too large to revert independently.

## Verification

Verification is scoped by default. Start from the active WU acceptance criteria and the user's request. Do not run full-project verification after every WU by default.

Full-project verification is required only for phase closeout, high-risk/shared changes, schema/graph/script changes, or explicit acceptance criteria.

A scoped verification matrix:

| Work shape | Verification |
|---|---|
| Docs-only WU | markdown/schema/link checks relevant to changed docs |
| Implementation WU | targeted tests plus type/lint/build checks for changed surface |
| Graph/schema/script WU | script tests, meta consistency, graph lint/extract/query |
| Phase closeout | full phase verification and closeout evidence |

Never claim pass without fresh evidence.

## Specialist Registry

Projects may define a lightweight Specialist Registry in `agents/departments/` and `agents/specialists/`. It is project-specific knowledge, not a fixed WUR roster.

Specialists are runtime optional: if the client supports subagents, the coordinator may dispatch the matching role; otherwise it reads the specialist file and applies that role locally. Coordinator owns final planning and execution decisions. Specialist output must be consolidated before it affects roadmap state: one recommendation is not one Work Unit. Recommendations become acceptance criteria, risks, rejected suggestions, or planned WUs only when they are material and fit the active scope. Do not mark WUs `active`, `accepted`, or `done`, close phases, or bypass contract receive from a specialist role.

Coverage Matrix categories are checklists, not mandatory files: domain expertise, product/strategy, architecture/engineering, design/UX/content, data/AI, security/compliance, QA/testing, operations/support, and platform/tooling/integration. Domain examples are illustrative, not exhaustive. For game projects, check game design, level design, gameplay/engine, art/technical art, audio, QA/playtest, production, and platform-specific expertise. Record any material coverage gap.

## Design And Tech Stack

Software/dev projects should create or maintain `agents/project/DESIGN.md` as the Design Contract: Visual Theme & Atmosphere, Color Palette & Roles, Typography, Component Styling, Layout, Responsive Behavior, and concrete do/don't rules. Backend/API/CLI-only projects still use DESIGN.md for product shape, API ergonomics, CLI output, docs/readme style, error presentation, and developer experience.

Software/dev projects should create or maintain `agents/project/TECH_STACK.md`. Technology Judgment matters: Prefer TypeScript for non-trivial web/app code. Consider Vite + React first for common frontend web apps. Avoid plain HTML/CSS/JS for app-scale work unless explicitly requested. Record material stack choices with verification commands.

Default Stack Suggestions are recommendations, not mandates:
- SPA/dashboard/CRM: Vite + React + TypeScript + Tailwind CSS + shadcn/ui.
- SEO/marketing/blog: Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui.
- Mobile: Expo + TypeScript + NativeWind.
- 2D browser game: Vite + TypeScript + Phaser.
- 3D browser game: Vite + TypeScript + Three.js.
- AI app: TypeScript UI plus a project-appropriate AI SDK/API layer.

## Operational Visibility Tags

Operational visibility tags:

Use state tags to mirror visible lifecycle when helpful: `state-planned`, `state-active`, `state-ready-review`, `state-accepted`, `state-done`, `state-blocked`, `state-deferred`, `state-aborted`.

Use attention tags only while an issue is live: `needs-review`, `needs-client`, `open-question`, `contradiction`, `decision-conflict`, `coverage-gap`, `test-failing`, `test-waived`, `graph-stale`, `risk`.

Tags are observation signals; status fields remain authoritative. Remove attention tags when the issue is resolved.

## Wiki & Derived Graph

The `agents/` folder IS the project wiki. There is no separate `wiki/` directory.

```text
agents/
  project/        PHILOSOPHY.md · USAGE.md · DESIGN.md · TECH_STACK.md
  roadmap/        ALL.md · PHASE_*.md · log.md
  departments/    project-specific department pages
  specialists/    project-specific specialist pages
  research/       curated research notes
  docs/           decisions, design, architecture notes
  reports/        durable reports and summaries
  references/     external references, API notes
  raw/            immutable source material
  SCHEMA.md       wiki conventions
  index.md        one-line summary of every page
  graph/          ontology.yaml · README.md · nodes.jsonl · edges.jsonl
```

Graph pages use YAML frontmatter with `type`, `status`, `tags`, and typed edges such as `depends_on`, `parent`, `verifies`, and `informs`. The graph layer is optional: run `/wur:wiki:upgrade`, then `/wur:wiki:graph extract` to compile `nodes.jsonl`, `edges.jsonl`, and `graph.sqlite`. Use path-style wikilinks such as `[[roadmap/PHASE_1]]`.

Wiki operations:
- `/wur:wiki:upgrade` — add graph-layer files and conventions
- `/wur:wiki:add` — add knowledge into `agents/research/`
- `/wur:wiki:ima` — enrich the wiki from a prompt, feedback, or idea; optionally update roadmap plans when explicitly requested
- `/wur:wiki:ask` — index-first, graph-aware when derived artifacts exist
- `/wur:wiki:lint` — structural/semantic checks, plus graph-aware checks when enabled
- `/wur:wiki:stats` — size, status, and graph health dashboard
- `/wur:wiki:graph` — explicit graph extract/lint/query operations

## Commands

```text
/wur:init
/wur:upgrade
/wur:start {n}
/wur:test [pass | waive: <reason> | fail: <description>]
/wur:done
/wur:abort {n}
/wur:status
/wur:wiki:upgrade  /wur:wiki:add {src}  /wur:wiki:ima {idea}
/wur:wiki:ask {q}  /wur:wiki:lint  /wur:wiki:stats  /wur:wiki:graph {action}
```

Commit format:
- Implementation WU: `WU-P{n}-{unit}: {description}`
- Tiny WU: `WU-TW-{n}: {description}`
- Phase close: `WU-P{n}-close: mark phase {n} done`
- Phase abort: `WU-P{n}-abort: abandon phase {n} ({mode})`

Rule: Only `/wur:done` from the current client request triggers closeout. An agent must not run `/wur:done` on its own after fixing, testing, or seeing a clean roadmap. It must report readiness and wait for the client to send `/wur:done`.

## Senior Agent Behavior

- Be exact and concise.
- Keep scope controlled.
- Preserve project history.
- Leave the roadmap understandable and the working tree clean.
- Never fake completion, skip verification, skip report receive, or bury unrelated changes.

The next agent should be able to open `agents/project/PHILOSOPHY.md`, `agents/project/USAGE.md`, `agents/project/DESIGN.md` when present, `agents/project/TECH_STACK.md` when present, `agents/roadmap/ALL.md`, the active phase file, `contracts/PHASE_{n}_CONTRACT.md`, inspect recent commits, and understand exactly what happened and what should happen next.
