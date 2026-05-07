---
description: Idea-to-MVP analysis for enriching the agents/ wiki and, when requested, updating roadmap plans.
argument-hint: "<idea-or-context>"
---

Run Idea-to-MVP analysis against the existing `agents/` wiki using the `wur-guidelines` skill.

This is a wiki operation, not an execution command. It turns a prompt, idea, feedback, or rough project context into durable wiki knowledge and optional roadmap planning updates.

Source: $ARGUMENTS

## Contract

- If `agents/` does not exist, stop and tell the user to run `/wur:init` first. Do not silently run `/wur:init`.
- Treat `$ARGUMENTS` as raw idea/context, not an unconditional implementation request.
- Run from the main repo. Do not create or enter a worktree.
- Do not change project source code, tests, or app configs.
- Do not run `/wur:start`, `/wur:test`, `/wur:done`, or `/wur:abort`.
- Do not mark any Work Unit `active`, `accepted`, or `done`.
- Planning changes may create or revise `planned` Work Units only.
- Do not require flags. `/wur:wiki:ima <idea-or-context>` is the full command shape.
- Infer roadmap intent from natural language. Phrases such as "update roadmap", "adjust the plan", "add this feature", "change scope", "rework MVP", or "phase/WU should include..." mean roadmap planning changes are in scope.
- Infer phase focus from natural language. Phrases such as "phase 2", "PHASE_2", "current phase", or a named phase file mean read and focus that phase and its fix ledger when present.
- Only update roadmap files when the user intent calls for roadmap planning changes. If the prompt is only research/idea capture, leave roadmap files unchanged and report suggested roadmap updates.

## Procedure

1. Read `agents/SCHEMA.md`, `agents/index.md`, `agents/project/PHILOSOPHY.md`, `agents/project/USAGE.md`, and `agents/roadmap/ALL.md`.
2. Infer whether `$ARGUMENTS` points to a specific phase, current phase, roadmap, WU, or feature scope. If it does, read the relevant `agents/roadmap/PHASE_{n}.md`, `agents/roadmap/PHASE_{n}_FIX.md` if present, and recent `agents/roadmap/log.md` entries.
3. Save the prompt or supplied context into `agents/raw/` with a slugified filename unless it already exists as a file path. Preserve the original wording as raw input.
4. Run the IMA stations:

   - **INTAKE** — extract the core idea, target users, constraints, explicit asks, unknowns, and non-goals.
   - **DISCOVER** — identify what must be researched. Use existing `agents/` content first. Use web search only when the current request or risk profile needs fresh external facts; cite sources in the research page if used.
   - **DEFINE** — write the MVP shape: users, core outcome, scope, constraints, success metrics, and failure modes.
   - **DECIDE** — separate must-have from nice-to-have using impact vs feasibility. Record tradeoffs and rejected options.
   - **ROADMAP** — produce roadmap implications: new phases, phase edits, candidate Work Units, risks, and verification ideas.

5. Write one research page in `agents/research/`:

   ```markdown
   ---
   type: research
   status: done
   tags: [research]
   source: {raw-file-or-conversation}
   added: {YYYY-MM-DD}
   informs: []
   ---

   # IMA: {Short Title}

   > [[roadmap/ALL]] · [[index]]

   ## Intake
   ## Discover
   ## Define
   ## Decide
   ## Roadmap Implications
   ## Open Questions
   ```

6. Create or update focused docs pages in `agents/docs/` only when the idea yields durable concepts, decisions, or constraints worth reusing. Do not create one page per thought.
7. If roadmap planning changes are **not** implied by the user's natural-language intent, leave roadmap files unchanged. In the report, list proposed roadmap edits under "Suggested roadmap updates".
8. If roadmap planning changes **are** implied by the user's natural-language intent:
   - Update `agents/roadmap/ALL.md` and/or `agents/roadmap/PHASE_{n}.md` surgically.
   - Keep existing active execution state intact.
   - New or revised WUs must be `planned`.
   - If the requested change conflicts with an active WU, record the conflict and mark it as needing client decision instead of silently changing the active WU.
9. Update `agents/index.md` with any new research/docs pages.
10. Append one line to `agents/roadmap/log.md`:

   ```markdown
   | {today} | wiki-ima | {slug} analyzed; roadmap update: {yes/no} |
   ```

11. If `agents/graph/ontology.yaml` exists, mention that the derived graph is now stale and suggest running `/wur:wiki:graph extract`.
12. Report: raw source stored, pages created/updated, roadmap files changed or suggested, contradictions found, open questions, and next safe command.

## Guardrails

- IMA enriches planning. It does not execute.
- It may update roadmap plans when the client asks, but it must not advance execution state.
- It should prefer one well-structured research page and a few durable docs updates over many small markdown files.
- It should preserve the original dream/intent while still making feasibility and scope decisions explicit.
