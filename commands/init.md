---
description: Bootstrap the agents/ workspace — create project philosophy, usage, and empty roadmap.
argument-hint: "[project-context]"
---

Initialize the `agents/` workspace using the `wur-guidelines` skill.

Run this once per project, before the first `/wur:start`.

Project context is resolved in this order:

1. `$ARGUMENTS` is optional supplemental context. Treat it as user intent to consider, not an unconditional requirement.
2. If existing `agents/` project files already contain enough project context, use that context for the report and do not ask for a new description.
3. If this is a new workspace, also inspect obvious project files such as `README.md`, package metadata, and the current conversation for a clear project purpose.
4. If both `$ARGUMENTS` and existing project context are empty, stop before writing files and ask the user for a one-sentence project description. Do not create a placeholder-only `agents/` workspace.

1. Check if `agents/` already exists. If yes, stop and report — do not overwrite unless the user explicitly asks for a reset.
2. Detect the default branch (main / master / develop):

   ```bash
   git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' \
     || git rev-parse --verify main 2>/dev/null && echo main \
     || git rev-parse --verify master 2>/dev/null && echo master \
     || git rev-parse --verify develop 2>/dev/null && echo develop
   ```

3. Ensure `.worktrees/` is in `.gitignore`:

   ```bash
   grep -qxF '.worktrees/' .gitignore 2>/dev/null || echo '.worktrees/' >> .gitignore
   ```

4. Install enforcement git hooks. **This step closes the raw-git escape hatch — without it, the rest of WUR is advisory.**

   ```text
   .githooks/
     commit-msg   ← reject commit messages that aren't WU-prefixed or recognized phase merges
     pre-commit   ← block implementation commits on default branch; require roadmap files with code
     pre-push     ← block pushing default branch while phase/WU is still active
   ```

   Idempotent install procedure:

   ```bash
   # 1. If .githooks/ already exists from another tool, do not clobber.
   #    Snapshot, warn, and continue with WUR's hooks alongside.
   if [ -d .githooks ] && [ ! -f .githooks/.wur-managed ]; then
     mv .githooks ".githooks.pre-wur.$(date +%Y%m%d-%H%M%S)"
     echo "WUR: existing .githooks/ moved aside; review before merging." >&2
   fi
   mkdir -p .githooks
   ```

5. **Write each hook file with the exact content from `skills/wur-guidelines/references/git-hooks.md`.** Read every fenced `sh` block in that file and write its body verbatim to `.githooks/<name>`. Do not paraphrase. Do not add comments. The regex/parsing must match the reference byte-for-byte so that future plugin upgrades can detect drift.

6. Mark the directory as WUR-managed and configure git:

   ```bash
   touch .githooks/.wur-managed
   chmod +x .githooks/commit-msg .githooks/pre-commit .githooks/pre-push
   git config core.hooksPath .githooks
   ```

7. Verify the install (do not skip).

   > **Cross-platform:** Git executes hooks through its own bundled `sh.exe` (Windows) or system `sh` (Linux/macOS) — hooks fire correctly from **any** terminal (PowerShell, cmd, Terminal.app, Git Bash). The `chmod +x` step sets the executable bit on Linux/macOS; on Windows it is a no-op and Git for Windows handles hook execution independently of file permissions.
   >
   > The verification commands below use `sh` syntax. Run them from any shell that has `sh` on PATH: Git Bash or WSL on Windows, any terminal on Linux/macOS.

   ```bash
   [ "$(git config --get core.hooksPath)" = ".githooks" ] || { echo "WUR: hooksPath not set"; exit 1; }
   for h in commit-msg pre-commit pre-push; do
     [ -f ".githooks/$h" ] || { echo "WUR: .githooks/$h missing"; exit 1; }
   done

   # Smoke test commit-msg by invoking through `sh` (cross-platform; bypasses chmod on Windows):
   tmpmsg=$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/wur-smoke.$$")
   printf 'bad message\n' > "$tmpmsg"
   if sh .githooks/commit-msg "$tmpmsg" 2>/dev/null; then
     echo "WUR: commit-msg accepts bad messages — install corrupted"
     rm -f "$tmpmsg"
     exit 1
   fi
   printf 'WU-TW-000: bootstrap workspace\n' > "$tmpmsg"
   sh .githooks/commit-msg "$tmpmsg" || { echo "WUR: commit-msg rejects valid WU prefix"; rm -f "$tmpmsg"; exit 1; }
   printf 'Phase 1: merge feature/phase-1\n' > "$tmpmsg"
   sh .githooks/commit-msg "$tmpmsg" || { echo "WUR: commit-msg rejects valid phase-merge"; rm -f "$tmpmsg"; exit 1; }
   printf 'WU-P01-fix: merge fix/phase-1-device-r1\n' > "$tmpmsg"
   sh .githooks/commit-msg "$tmpmsg" || { echo "WUR: commit-msg rejects valid phase-fix merge"; rm -f "$tmpmsg"; exit 1; }
   printf 'WU-P01-abort: abandon phase 1 (hard)\n' > "$tmpmsg"
   sh .githooks/commit-msg "$tmpmsg" || { echo "WUR: commit-msg rejects valid phase-abort"; rm -f "$tmpmsg"; exit 1; }
   rm -f "$tmpmsg"
   ```

   If any check fails, stop and report — do **not** proceed to scaffolding the workspace until enforcement is live. Hooks without verification are theater.

8. Create the workspace:

   ```text
   agents/
     project/
       PHILOSOPHY.md    ← project principles, constraints, non-goals
       USAGE.md         ← how to use the agent in this project (conventions, commands)
       DESIGN.md        ← user-facing design contract for dev projects
       TECH_STACK.md    ← selected stack, default suggestions, overrides, verification
     roadmap/
       ALL.md           ← master index: phases, status, commit log, navigation hub
       log.md           ← append-only session/activity journal (never overwrite)
     departments/       ← project-specific capability map (empty unless domain is clear)
     specialists/       ← project-specific role cards (empty unless domain is clear)
     docs/              ← durable notes, ADRs, synthesis (empty)
     research/          ← ingested external sources, analysis (empty)
     reports/           ← verification reports, completion reports (empty)
     references/        ← external references, API notes, domain material (empty)
     raw/               ← immutable source material for research pages (track in git, empty)
     SCHEMA.md          ← wiki conventions: types, status values, frontmatter schema
     index.md           ← one-line summary of every page; updated on every new page
   ```

9. Fill `agents/project/PHILOSOPHY.md` with a short template:
   - What this project is: `{project description}`
   - Principles the agent must uphold
   - Explicit non-goals
   - Default branch: `{detected}`

10. Fill `agents/project/USAGE.md` with:
   - How to run tests, lint, build
   - Commit message conventions
   - Any project-specific guardrails

   Create or update `agents/project/DESIGN.md` for software/dev projects:
   - Treat it as the **Design Contract** that implementation must follow.
   - If the user supplied or copied a `DESIGN.md`, preserve it as the source of truth and summarize only missing project-specific constraints.
   - If no design source exists, draft a concise project-specific design contract from `$ARGUMENTS`, README/package metadata, existing docs, and current conversation.
   - If the visual/product direction is unclear, record known constraints and open questions instead of inventing a brand.
   - Backend/API/CLI-only projects still use `DESIGN.md` for product shape, API ergonomics, CLI output, docs/readme style, error presentation, and developer experience.
   - Do not create Work Units from every design note; convert design guidance into acceptance criteria, risks, or `planned` WUs only when material.

   ```markdown
   # Design

   ## Visual Theme & Atmosphere
   {mood, density, product feel, non-goals, known references}

   ## Color Palette & Roles
   {semantic colors and intended use; unknowns allowed}

   ## Typography Rules
   {font choices, hierarchy, scale, readability constraints}

   ## Component Styling
   {buttons, cards, inputs, navigation, states}

   ## Layout Principles
   {spacing, grid, page rhythm, information density}

   ## Responsive Behavior
   {breakpoints, touch targets, collapsing behavior}

   ## Do's and Don'ts
   {guardrails to prevent visual drift}

   ## Agent Prompt Guide
   {short implementation prompts or reminders future agents can reuse}
   ```

   Create or update `agents/project/TECH_STACK.md` for software projects:
   - Capture the detected/current stack if one exists.
   - If no stack exists yet, choose from **Default Stack Suggestions** based on project type.
   - Treat defaults as recommendations, not mandates. Existing stack, explicit user instructions, deployment/runtime constraints, ecosystem maturity, team familiarity, and verification ability override defaults.
   - If project type is unclear, record `Unknown` and ask one focused question before choosing.
   - Record why the chosen stack is appropriate and how to verify it locally.

   ```markdown
   # Tech Stack

   ## Selected Stack
   - Project type: {spa/dashboard/seo/static/mobile/ai/game/other/unknown}
   - Frontend/UI: {chosen stack or unknown}
   - Backend/API: {chosen stack or none/unknown}
   - Database/storage: {chosen stack or none/unknown}
   - Runtime/package manager: {chosen runtime or unknown}

   ## Decision
   - Why this stack fits:
   - Overrides from defaults:
   - Verification commands:

   ## Default Stack Suggestions
   | Project type | Suggested default | Backend / data default |
   |---|---|---|
   | SPA / dashboard / CRM | Vite + React + TypeScript + Tailwind CSS + shadcn/ui + React Router | Supabase, or Node/Bun + PostgreSQL |
   | SEO / marketing / blog | Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui | Next.js API routes + Prisma + PostgreSQL when needed |
   | Static site / docs | Astro + TypeScript + Tailwind CSS, plus Starlight for docs-heavy sites | None by default |
   | Lightweight web app | Vite + Svelte/SvelteKit + TypeScript + Tailwind CSS + shadcn-svelte | SvelteKit backend or PocketBase |
   | Fullstack type-safe | Next.js App Router + TypeScript + tRPC + Tailwind CSS + shadcn/ui + Prisma | PostgreSQL |
   | Realtime app | Vite/Next.js + React + TypeScript + Tailwind CSS + shadcn/ui + WebSocket/Socket.io | Node/Bun + Redis + PostgreSQL |
   | Mobile app | Expo + TypeScript + NativeWind + Tamagui or React Native Paper | Supabase or Firebase |
   | AI app | Next.js or Vite + React + TypeScript + Tailwind CSS + shadcn/ui + OpenAI/Vercel AI SDK | Next.js API routes; LangChain only when useful |
   | Web game 2D | Vite + TypeScript + Phaser | Optional Node/Bun service |
   | Web game 3D | Vite + TypeScript + Three.js or React Three Fiber | Optional Node/Bun service |
   ```

   Detect project departments and specialists from `$ARGUMENTS`, README/package metadata, existing docs, and current conversation:
   - Create `agents/departments/` and `agents/specialists/` folders.
   - If the domain is clear, add only useful project-specific department pages and specialist role cards.
   - If the domain is unclear, ask one focused question before creating roles.
   - Do not create generic specialist placeholders.
   - Add a `## Coverage Matrix` section to each department page. Coverage categories are checklists, not mandatory files: one specialist can cover multiple categories in a small project, but missing critical coverage must be recorded as a `coverage gap`.
   - Start from these default coverage categories: domain expertise, product/strategy, architecture/engineering, design/UX/content, data/AI, security/compliance, QA/testing, operations/support, and platform/tooling/integration.
   - Domain examples are illustrative, not exhaustive. For game projects, check coverage for game design, level design, gameplay/engine, art/technical art, audio, QA/playtest, production, and platform-specific expertise. Platform-specific means Unity, Godot, Unreal, Roblox, mobile, web, console, multiplayer, shader, tooling, or other runtime-specific knowledge when relevant.
   - specialist recommendations do not automatically become Work Units; the coordinator consolidates them into risks, acceptance criteria, rejected suggestions, or `planned` WUs only when material.
   - Implementation-facing specialists must include a `## Technology Judgment` section. Prefer modern mainstream defaults, such as TypeScript for non-trivial web/app code, Vite + React for common frontend web apps, Tailwind CSS + shadcn/ui for common React web UI, and Bun when compatible, while treating explicit user constraints, existing stack, runtime limits, team familiarity, and verification ability as overrides.

11. Fill `agents/roadmap/ALL.md` with:

   ```markdown
   # Roadmap

   > Navigation: [Philosophy](../project/PHILOSOPHY.md) · [Usage](../project/USAGE.md) · [Log](log.md)

   ## Objective
   {project description}

   ## 80/20 Focus
   - Core outcome: {most important outcome to protect}
   - Highest-impact risks: {short list}
   - Deferred intentionally: {short list}

   ## Current Status
   - Default branch: {detected}
   - Active phase: none
   - Active Work Unit: none
   - Latest completed unit: none
   - Blockers: none

   ## Phases
   | Phase | Goal | Status | File | Contract |
   |---|---|---|---|---|

   ## Commit Index
   | Work Unit | Summary | Commit | Verification |
   |---|---|---|---|

   ## Operating Rules
   - Work in Work Units only. One WU = one commit.
   - Failed work becomes another execution round in `contracts/PHASE_{n}_CONTRACT.md`; do not create Phase Fix ledgers for new work.
   - WU status lifecycle: `planned -> active -> ready-for-review -> accepted -> done`; agents stop at `ready-for-review` unless the client confirms.
   - Append to `log.md` on every contract open, test status change, and phase close.
   - Small task, verify, commit. Repeat.
   ```

   Fill `agents/roadmap/log.md` with:

   ```markdown
   # Activity Log

   Append-only. One line per event. Never edit past entries.

   | Date | Event | Detail |
   |---|---|---|
   | {today} | workspace-init | default branch: {detected} |
   ```

   Fill `agents/SCHEMA.md` with:

   ```markdown
   ---
   schema_version: 1
   ---

   # agents/ Wiki Schema

   > Schema version: **1** (the `wiki` layout). When the WUR plugin ships a newer
   > schema, run `/wur:upgrade` to migrate. Never hand-edit `schema_version`.

   ## Page Types
   | Type | Location | Description |
   |---|---|---|
   | `phase` | `agents/roadmap/PHASE_*.md` | One execution phase |
   | `fix-round` | `agents/roadmap/PHASE_*_FIX.md` | Legacy fix ledger; readable for old work, not created for new work |
   | `fix-round` | `agents/roadmap/FIX_*.md` | Legacy bug fix batch file; readable for old work only |
   | `research` | `agents/research/*.md` | Ingested external source or analysis |
   | `decision` | `agents/docs/*.md` | Architectural decision record |
   | `note` | `agents/docs/*.md` | Durable note, synthesis, or concept page |
   | `report` | `agents/reports/*.md` | Verification or completion report |
   | `department` | `agents/departments/*.md` | Project-specific capability area |
   | `specialist` | `agents/specialists/**/*.md` | Project-specific expert role card |

   ## Status Values
   `planned` · `active` · `done` · `blocked` · `deferred` · `aborted`

   ## Work Unit Status Lifecycle
   `planned -> active -> ready-for-review -> accepted -> done`

   Agents may set `planned`, `active`, `ready-for-review`, `blocked`, and `deferred`.
   Only the client may set `accepted` or `done`.

   ## Graph Scope
   Graph pages (must have frontmatter):
   - `agents/roadmap/PHASE_*.md`
   - `agents/roadmap/PHASE_*_FIX.md`
   - `agents/roadmap/FIX_*.md` (legacy)
   - `agents/research/*.md`
   - `agents/docs/*.md`
   - `agents/reports/*.md`
   - `agents/departments/*.md`
   - `agents/specialists/**/*.md`

   System pages (may omit frontmatter):
   - `agents/project/PHILOSOPHY.md`
   - `agents/project/USAGE.md`
   - `agents/project/DESIGN.md`
   - `agents/project/TECH_STACK.md`
   - `agents/roadmap/ALL.md`
   - `agents/roadmap/log.md`
   - `agents/SCHEMA.md`
   - `agents/index.md`
   - `agents/references/*`
   - `agents/raw/*`

   ## Required Frontmatter (graph pages)
   - `type` — one of the page types above
   - `status` — one of the status values above
   - `tags` — YAML list of lowercase kebab-case strings, even if empty (`tags: []`)

   ## Specialist Registry
   `agents/departments/` and `agents/specialists/` describe project-specific expertise. They are advisory unless explicitly assigned a WU. Runtime subagents are optional; if unavailable, the coordinator applies the role locally. Coordinator owns final planning and execution decisions. Specialist output must be consolidated: one recommendation is not one Work Unit.

   Department pages must include `## Coverage Matrix`. Coverage categories are checklists, not mandatory files. Start from domain expertise, product/strategy, architecture/engineering, design/UX/content, data/AI, security/compliance, QA/testing, operations/support, and platform/tooling/integration. Domain examples are illustrative, not exhaustive. For game projects, check game design, level design, gameplay/engine, art/technical art, audio, QA/playtest, production, and platform-specific expertise. Record any missing critical capability as a `coverage gap`.

   Specialist frontmatter:
   ```yaml
   type: specialist
   status: active
   department: engineering
   role: frontend-architect
   runtime: optional
   tags: [ui]
   ```

   Specialist body must include:
   - `## Use When`
   - `## Inputs`
   - `## Outputs`
   - `## Boundaries`
   - `## Technology Judgment` for implementation-facing roles

   Technology Judgment defaults are recommendations, not mandates. Prefer TypeScript for non-trivial web/app code, consider Vite + React first for common frontend web apps, consider Tailwind CSS + shadcn/ui for common React web UI, consider Bun when compatible, and avoid plain HTML/CSS/JS for app-scale work unless explicitly requested or clearly tiny/static. Create or update `agents/project/TECH_STACK.md` before execution when stack choices matter.

   ## Graph Conventions
   - `depends_on: ["[[roadmap/PHASE_1]]"]` — phase dependency
   - `parent: "[[roadmap/PHASE_1]]"` — legacy fix-round or related page belongs to a phase
   - `verifies: ["[[roadmap/PHASE_1]]"]` — report verifies a phase or legacy fix round
   - `informs: ["[[roadmap/PHASE_1]]"]` — research or docs inform another graph page
   - Use path-style wikilinks like `[[roadmap/PHASE_1]]`, not `[[PHASE_1]]`
   - Every `[[wikilink]]` creates an edge in Obsidian graph view

   ## Tag Conventions

   `tags:` is a YAML list of lowercase kebab-case strings. Always a list, even when empty (`tags: []`). Never a string.

   ### Format rule
   ```yaml
   tags: [auth, breaking-change, spike]   # correct
   tags: [Auth, Breaking Change]            # wrong — uppercase, spaces
   tags: auth                              # wrong — must be a list
   ```

   ### Predefined vocabulary

   Use these names before inventing new ones. Consistent names make graph filtering useful.

   **Scope** — what area of the system this touches:
   | Tag | Meaning |
   |---|---|
   | `api` | External API contract or boundary |
   | `auth` | Authentication or authorization |
   | `data` | Data model, schema, or migration |
   | `infra` | Infrastructure, environment, or deployment |
   | `ui` | User interface |
   | `security` | Security-sensitive change |
   | `performance` | Performance impact |

   **Risk** — signal extra caution:
   | Tag | Meaning |
   |---|---|
   | `breaking-change` | Introduces a breaking change |
   | `migration` | Data or structural migration |
   | `risky` | High-risk, needs extra review |

   **Process** — how the work was done:
   | Tag | Meaning |
   |---|---|
   | `spike` | Exploratory phase — waived tests acceptable |
   | `research` | Knowledge-gathering, no production code |

   **Source** — for `research/` pages only:
   | Tag | Meaning |
   |---|---|
   | `external` | Ingested from external URL or file |
   | `archived` | Source is no longer maintained |

   **Operational visibility tags** — temporary observation signals for Obsidian and graph filtering. Tags are observation signals; status fields remain authoritative.
   | Tag | Meaning |
   |---|---|
   | `state-planned` | Page represents planned work or knowledge |
   | `state-active` | Page is currently in active attention |
   | `state-ready-review` | Work is ready for client or human review |
   | `state-accepted` | Client accepted the WU or decision |
   | `state-done` | Page represents completed work or resolved knowledge |
   | `state-blocked` | Work is blocked |
   | `state-deferred` | Work is intentionally deferred |
   | `state-aborted` | Work was abandoned |
   | `needs-review` | Needs human or specialist review |
   | `needs-client` | Needs client decision or confirmation |
   | `open-question` | Contains an unresolved question |
   | `contradiction` | Contains or tracks a contradiction |
   | `decision-conflict` | Competing decisions must be resolved |
   | `coverage-gap` | Critical specialist/domain coverage is missing |
   | `test-failing` | Verification is failing |
   | `test-waived` | Verification was waived with a recorded reason |
   | `graph-stale` | Derived graph artifacts need refresh |
   | `risk` | Needs extra risk attention |
   | `phase` | Phase page |
   | `work-unit` | Work Unit content or WU-specific page |
   | `fix-round` | Legacy fix ledger or fix-round content |
   | `decision` | Decision content |
   | `report` | Verification or completion report |
   | `specialist` | Specialist role content |
   | `design` | Design contract or design-related content |
   | `tech-stack` | Technology stack content |

   Remove attention tags such as `needs-review`, `open-question`, `contradiction`, `coverage-gap`, `test-failing`, and `graph-stale` when the issue is resolved. Keep the authoritative state in `status`, `test_status`, phase tables, and roadmap files.

   Custom project-specific tags are allowed. They must be lowercase kebab-case and documented in this file under a `## Project Tags` section.

   ### Lint rules (checked by `/wur:wiki:lint`)
   - Every tag must match `^[a-z][a-z0-9-]*$`
   - `tags:` must be a list, not a scalar
   - Unknown tags (not in predefined vocabulary and not in `## Project Tags`) are flagged as warnings, not errors

   Run `/wur:wiki:upgrade` to add `agents/graph/ontology.yaml`, `agents/graph/README.md`, and the full graph layer.
   ```

   Fill `agents/index.md` with:

   ```markdown
   # agents/ Index

   > One line per page. Update when adding or closing pages.

   ## Project
   - [[project/PHILOSOPHY]] — project mission, principles, non-goals
   - [[project/USAGE]] — how to run, test, build, verify
   - [[project/DESIGN]] — user-facing design contract
   - [[project/TECH_STACK]] — selected software stack, defaults, overrides, verification

   ## Roadmap
   - [[roadmap/ALL]] — master dashboard: phases, status, commit index
   - [[roadmap/log]] — append-only activity journal

   ## Departments

   ## Specialists
   ```

12. Commit the workspace bootstrap:

    ```bash
    git add .gitignore .githooks/ agents/
    git commit -m "WU-TW-000: bootstrap agents/ workspace"
    ```

13. Report: workspace created, default branch detected, hooks installed and verified, schema version `1`, `agents/roadmap/log.md` initialized, ready for `/wur:start 1`.
