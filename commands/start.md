---
description: Start or refresh a WUR execution contract for a phase.
argument-hint: "<phase-number> [work-unit-id]"
---

Start Phase $ARGUMENTS using the `wur-guidelines` skill.

`/wur:start` no longer makes WUR execute code directly. It prepares `contracts/rule.md` plus one phase contract file that can be handed to another agent or human executor.

1. If `agents/` does not exist, stop and instruct the user to run `/wur:init` first.
2. Read `agents/project/PHILOSOPHY.md`, `agents/project/USAGE.md`, `agents/project/DESIGN.md` when present, `agents/project/TECH_STACK.md` when present, plus `agents/departments/` and `agents/specialists/` when present if not already read this session.
3. Read `agents/roadmap/ALL.md` and `agents/roadmap/PHASE_{n}.md`:
   - confirm the target phase exists or can be scaffolded from planned roadmap data
   - if another phase is already `active`, stop unless the user explicitly asks to prepare a contract for that active phase
   - skip WUs already `accepted` or `done`
   - keep `planned`, `active`, `ready-for-review`, `blocked`, and `deferred` work available for contract execution
4. If `agents/roadmap/PHASE_{n}.md` is missing but the roadmap says the phase is planned, create the phase file with this minimal template:

   ```markdown
   ---
   type: phase
   phase: {n}
   status: active
   tags: [state-active]
   depends_on: []
   opened: {YYYY-MM-DD}
   closed: null
   test_status: not-run
   test_waive_reason: null
   ---

   # PHASE_{n}: {phase name}

   ## Goal
   {One concrete phase goal.}

   ## Success Criteria
   - {Measurable condition 1}

   ## Work Units
   | ID | Goal | Acceptance Criteria | Scope | Dependencies | Verification | Status | Commit |
   |---|---|---|---|---|---|---|---|

   Status lifecycle: planned -> active -> ready-for-review -> accepted -> done.
   Only the client may move a WU to `accepted` or `done`.
   ```

5. Create or refresh the shared rule file and phase execution contract:

   ```bash
   python skills/wur-guidelines/scripts/wur_contract.py create --phase {n}
   ```

   For a single WU:

   ```bash
   python skills/wur-guidelines/scripts/wur_contract.py create --phase {n} --wu WU003
   ```

6. The result is `contracts/rule.md` plus `contracts/PHASE_{n}_CONTRACT.md`. Shared rules live in `contracts/rule.md`; the phase file contains the task brief, pending WUs, Allowed Read References, and report area. Do not create `contracts/outbox/` or `contracts/inbox/`.
   - The executor may read only the `agents/` paths listed in the contract's Allowed Read References.
   - The executor must not modify `agents/`.
   - The contract should let the executor infer specialist lenses from scope; do not require WUR to assign one person per WU.
7. Do not create a worktree by default. If the executor needs isolation, `contracts/rule.md` contains optional sparse worktree commands that exclude `agents/` and `contracts/`.
8. Update `agents/roadmap/ALL.md` only as planning/status state requires. Do not mark WUs `accepted` or `done` from this command.
9. Append to `agents/roadmap/log.md`:

   ```text
   | {today} | contract-open | PHASE_{n} contract refreshed |
   ```

10. Commit the contract setup as a Tiny WU when files changed:

    ```bash
    git add agents/roadmap/ agents/index.md contracts/
    git commit -m "WU-TW-{k}: create phase {n} contract"
    ```

11. Report: contract path, pending WUs included, skipped completed WUs, and the next safe step. Baseline verification is full enough to establish starting health when the contract asks for a phase-level baseline. Later WU verification is scoped by default to the WU acceptance criteria and changed surface.
