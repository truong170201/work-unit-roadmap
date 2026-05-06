---
description: Process test results after tests are run — pass/waive records closeout state, fail opens fix worktree.
argument-hint: "[pass | waive: <reason> | fail: <description>]"
---

Process test results using the `wur-guidelines` skill.

Before doing anything else, read `agents/roadmap/ALL.md` and enforce the phase gate:
- there must be an active phase
- the recorded active phase must match the phase branch/worktree you are testing
- otherwise stop and resolve the mismatch first

Call this after tests have been run — either by the user manually or by the agent executing the test suite. Pass the result as `$ARGUMENTS`:
- `pass` — tests passed, phase may be closed
- `waive: <reason>` — closeout is allowed without a clean pass, but the reason must be recorded
- `fail: <description>` — bugs found; open a fix round

This command is the only allowed way to set phase `test_status` before `/wur:done`.

If `$ARGUMENTS` is empty or unrecognized, stop and print this help, do not mutate anything:

```text
Usage: /wur:test pass
       /wur:test waive: <reason>
       /wur:test fail: <description>

  pass    Mark active phase test_status: pass.   Use after tests succeed.
  waive   Mark active phase test_status: waived. Reason is required.
  fail    Open a fix round for the active phase. Description is required.
```

If $ARGUMENTS indicates **bugs found**:

1. Update the active phase frontmatter before opening the fix round:
   - `test_status: failing`
   - `test_waive_reason: null`

2. Create fix worktree from phase branch:
   ```bash
   git worktree add .worktrees/fix-{n}-{slug} -b fix/phase-{n}-{slug} feature/phase-{n}
   cd .worktrees/fix-{n}-{slug}
   ```
3. Create `agents/roadmap/FIX_P{n}_{slug}.md` — do NOT append fix WUs to `PHASE_{n}.md`:

   ```markdown
   ---
   type: fix-round
   phase: {n}
   slug: {slug}
   status: active
   tags: []
   parent: "[[roadmap/PHASE_{n}]]"
   opened: {YYYY-MM-DD}
   closed: null
   ---

   # FIX_P{n}_{slug}: {short description of bug batch}

   > [← Phase {n}](PHASE_{n}.md) · [← Roadmap](ALL.md)

   ## Parent Phase
   [PHASE_{n}.md](PHASE_{n}.md) — {phase goal one-liner}

   ## Branch / Worktree
   - Branch: `fix/phase-{n}-{slug}`
   - Worktree: `.worktrees/fix-{n}-{slug}`

   ## Fix Work Units
   | ID | Goal | Parent WU | Acceptance Criteria | Scope | Verification | Status | Commit |
   |---|---|---|---|---|---|---|---|

   ## Completion Log
   | Work Unit | Completed At | Commit | Verification Evidence | Notes |
   |---|---|---|---|---|
   ```

4. In `agents/roadmap/PHASE_{n}.md`, add a row to the Fix Rounds table:
   ```
   | {slug} | [FIX_P{n}_{slug}.md](FIX_P{n}_{slug}.md) | fix/phase-{n}-{slug} | active |
   ```

5. In `agents/roadmap/ALL.md`, update the phase row's Fix Rounds column with the new link.

6. Append to `agents/roadmap/log.md`:
   ```
   | {today} | fix-open | FIX_P{n}_{slug} — {bug count} bugs from {trigger} |
   ```

   Add one line to `agents/index.md` under the `## Roadmap` section (create section if absent):
   ```
   - [[roadmap/FIX_P{n}_{slug}]] — {description} · parent: PHASE_{n} · status: active
   ```

7. Commit the fix setup as a Tiny WU on the fix branch:

   ```bash
   git add agents/roadmap/ agents/index.md
   git commit -m "WU-TW-{k}: open fix round {slug} for phase {n}"
   ```

8. Implement fix WUs one at a time in the worktree, recording each in `FIX_P{n}_{slug}.md`.

9. When all fix WUs are done:
   - Update `FIX_P{n}_{slug}.md` frontmatter: `status: done`, `closed: {today}`
   - Update the Fix Rounds row in `agents/roadmap/PHASE_{n}.md`: change `active` → `done`
   - Update the line in `agents/index.md`: change `status: active` → `status: done`
   - Append to `agents/roadmap/log.md`:
     ```
     | {today} | fix-close | FIX_P{n}_{slug} — {N} fix WUs done |
     ```
   - Commit: `git add agents/roadmap/ agents/index.md && git commit -m "WU-TW-{k}: close fix round {slug} for phase {n}"`
   - Ask: "Ready for `/wur:done`?"

If $ARGUMENTS indicates **all tests pass**:

1. Update the active phase frontmatter:
   - `test_status: pass`
   - `test_waive_reason: null`
2. Append to `agents/roadmap/log.md`:
   ```
   | {today} | test-pass | PHASE_{n} marked pass |
   ```
3. Commit the phase metadata update:
   ```bash
   git add agents/roadmap/
   git commit -m "WU-TW-{k}: record passing test status for phase {n}"
   ```
4. Report: all acceptance criteria met, verification evidence recorded.
5. Prompt: "All checks pass. Ready for `/wur:done` when you are."

If $ARGUMENTS indicates **a waive**:

1. Update the active phase frontmatter:
   - `test_status: waived`
   - `test_waive_reason: {reason from $ARGUMENTS}`
2. Append to `agents/roadmap/log.md`:
   ```
   | {today} | test-waive | PHASE_{n} waived — {reason} |
   ```
3. Commit the phase metadata update:
   ```bash
   git add agents/roadmap/
   git commit -m "WU-TW-{k}: waive test status for phase {n}"
   ```
4. Report clearly that closeout is waived, not passed.
5. Prompt: "Verification waived with recorded reason. Ready for `/wur:done` when you are."

Never mark a phase done without `/wur:done`.
