---
description: Start a new phase — create worktree with feature branch, init phase file, verify clean baseline.
argument-hint: "<phase-number>"
---

Start Phase $ARGUMENTS using the `wur-guidelines` skill. Invoke `using-git-worktrees` to create the worktree.

1. If `agents/` does not exist, stop and instruct the user to run `/wur:init` first.
2. Read `agents/project/PHILOSOPHY.md` and `agents/project/USAGE.md` if not already read this session.
3. Read `agents/roadmap/ALL.md` — extract the default branch, confirm the target phase is planned, confirm no blocker exists, and enforce the phase gate:
   - if another phase is already `active`, stop — finish or close that phase first
   - if `PHASE_{n}` is already the active phase and its worktree exists, stop — resume it instead of re-starting
   - otherwise continue
4. Invoke `using-git-worktrees` to create the worktree — it handles gitignore verification internally:

   ```bash
   git fetch origin "$base" 2>/dev/null || true
   git worktree add .worktrees/phase-{n} -b feature/phase-{n} "$base"
   cd .worktrees/phase-{n}
   ```

   **All steps from here onwards use `.worktrees/phase-{n}/` as the working directory.** Verify with `git branch --show-current` — must show `feature/phase-{n}`.

5. Run project setup (auto-detect: `npm install`, `pip install`, `cargo build`, etc.).
6. Verify clean baseline: run tests. If no test suite exists, confirm the codebase is in a known-good state and document this in `agents/project/USAGE.md` under "Verification".
7. Create `agents/roadmap/PHASE_{n}.md` using this template:

   ```markdown
   ---
   type: phase
   phase: {n}
   status: active
   tags: []
   depends_on: []
   opened: {YYYY-MM-DD}
   closed: null
   test_status: not-run
   test_waive_reason: null
   ---

   # PHASE_{n}: {phase name}

   > [← Roadmap](ALL.md) · [Philosophy](../project/PHILOSOPHY.md) · [Usage](../project/USAGE.md)

   ## Goal
   {One concrete phase goal.}

   ## Observable Outcome
   {What can be observed when this phase is complete.}

   ## Success Criteria
   - {Measurable condition 1}

   ## Exit Gate
   - {Required check before moving to next phase}

   ## Out of Scope
   - {Explicitly excluded work}

   ## Dependencies
   - {Prior phase or WU, or "none"}

   ## Work Units
   | ID | Goal | Acceptance Criteria | Scope | Dependencies | Verification | Status | Commit |
   |---|---|---|---|---|---|---|---|

   ## Fix Rounds
   _Fix rounds are tracked in separate files. Links appear here as rounds are opened._

   | Round | File | Branch | Status |
   |---|---|---|---|

   ## Verification Strategy
   - {Phase-level verification}

   ## Completion Log
   | Work Unit | Completed At | Commit | Verification Evidence | Notes |
   |---|---|---|---|---|
   ```

8. Update `agents/roadmap/ALL.md`: add the phase row with `Status=active`; file column links to `PHASE_{n}.md`.
9. Append one line to `agents/roadmap/log.md`:

   ```
   | {today} | phase-open | PHASE_{n} started — branch: feature/phase-{n}, worktree: .worktrees/phase-{n} |
   ```

   Add one line to `agents/index.md` under the `## Roadmap` section (create section if absent):
   ```
   - [[roadmap/PHASE_{n}]] — {phase goal one-liner} · status: active
   ```

10. Commit the phase setup as a Tiny WU on the feature branch:

    ```bash
    git add agents/roadmap/ agents/index.md agents/project/USAGE.md
    git commit -m "WU-TW-{k}: init phase {n} roadmap"
    ```

11. Report: worktree path, branch, base branch, tests baseline, ready for first Work Unit.
