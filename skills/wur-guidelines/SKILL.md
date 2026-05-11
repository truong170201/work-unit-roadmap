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

`contracts/PHASE_{n}_CONTRACT.md` is the execution contract. one file contains both task instructions and returned execution reports. one file contains both the task brief and report ledger. It includes WUR rules, pending Work Units, skipped completed WUs, verification requirements, optional sparse worktree guidance, and the `## Execution Rounds And Reports` ledger.

Rules:
- Do not create `contracts/outbox/` or `contracts/inbox/`.
- Do not create Phase Fix ledgers for new work.
- Failed work becomes a new execution round in the same contract file.
- External executors may read `agents/` through the contract context, but must not edit `agents/`.
- WUR receives and validates reports before updating `agents/`.
- `/wur:start` creates or refreshes a contract; it does not execute code by itself.
- `/wur:done` only runs after explicit client request.

Optional sparse worktree guidance belongs inside the contract. If isolation is needed, create a worktree that excludes `agents/` and `contracts/`; the executor uses the contract as the brief and returns a report for WUR to receive.

## Checklist

1. **Read roadmap** — `agents/roadmap/ALL.md` → active phase, active WU, blockers, latest completed unit.
2. **Read phase file** — `agents/roadmap/PHASE_{n}.md` → goal, success criteria, WUs, verification.
3. **Create or refresh contract** — `python skills/wur-guidelines/scripts/wur_contract.py create --phase {n}`.
4. **Executor works from contract** — one WU or scoped phase slice, no edits to `agents/`.
5. **Verify** — run checks scoped to acceptance criteria and changed surface.
6. **Report** — append evidence under the contract's `## Execution Rounds And Reports`.
7. **Receive** — WUR validates report, then updates roadmap/status/log in `agents/`.
8. **Close only on request** — only `/wur:done` from the current client request can close a phase.

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
| "One more report file is cleaner" | No. Use one phase contract file to avoid file noise. |
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

software/dev projects should create or maintain `agents/project/DESIGN.md` as the Design Contract: Visual Theme & Atmosphere, Color Palette & Roles, Typography, Component Styling, Layout, Responsive Behavior, and concrete do/don't rules. Backend/API/CLI-only projects still use DESIGN.md for product shape, API ergonomics, CLI output, docs/readme style, error presentation, and developer experience.

Software/dev projects should create or maintain `agents/project/TECH_STACK.md`. Technology Judgment matters: Prefer TypeScript for non-trivial web/app code. Consider Vite + React first for common frontend web apps. Avoid plain HTML/CSS/JS for app-scale work unless explicitly requested. Record material stack choices with verification commands.

Default Stack Suggestions are recommendations, not mandates. Defaults are recommendations, not mandates:
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
  reports/        verification and completion reports
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
