---
description: Process test results after tests are run — pass/waive records closeout readiness, fail opens or appends to the phase fix ledger.
argument-hint: "[pass | waive: <reason> | fail: <description>]"
---

Process test results using the `wur-guidelines` skill.

Before doing anything else, read `agents/roadmap/ALL.md` and enforce the phase gate:
- there must be an active phase
- the recorded active phase must match the phase branch/worktree you are testing
- otherwise stop and resolve the mismatch first

Call this after tests have been run — either by the user manually or by the agent executing the test suite. Pass the result as `$ARGUMENTS`:
- `pass` — tests passed; record phase closeout readiness only
- `waive: <reason>` — closeout readiness is allowed without a clean pass, but the reason must be recorded
- `fail: <description>` — bugs found; open or append a fix round in the phase fix ledger

This command is the only allowed way to set phase `test_status` before `/wur:done`.

If `$ARGUMENTS` is empty or unrecognized, stop and print this help, do not mutate anything:

```text
Usage: /wur:test pass
       /wur:test waive: <reason>
       /wur:test fail: <description>

  pass    Mark active phase test_status: pass.   Use after tests succeed.
  waive   Mark active phase test_status: waived. Reason is required.
  fail    Open or append a fix round for the active phase. Description is required.
```

## Status Ownership

- Agent-owned WU states: `planned`, `active`, `ready-for-review`, `blocked`, `deferred`.
- Client-owned WU states: `accepted`, `done`.
- After implementation, verification, roadmap update, and commit, the agent moves the WU to `ready-for-review` and reports evidence.
- The agent must not mark a WU `done` merely because verification passed. Client confirmation is required.
- `done` is reserved for client-confirmed phase closeout through `/wur:done`.

If $ARGUMENTS indicates **bugs found**:

1. Update the active phase frontmatter before opening the fix round:
   - `test_status: failing`
   - `test_waive_reason: null`

2. Create fix worktree from phase branch:
   ```bash
   git worktree add .worktrees/fix-{n}-{slug} -b fix/phase-{n}-{slug} feature/phase-{n}
   cd .worktrees/fix-{n}-{slug}
   ```
3. Create or reuse `agents/roadmap/PHASE_{n}_FIX.md`.
   Do not create a new fix-round file per bug batch. One phase gets one fix ledger; each bug batch is a section inside that ledger.

   If the file is missing, create it:

   ```markdown
   ---
   type: fix-round
   phase: {n}
   status: active
   tags: []
   parent: "[[roadmap/PHASE_{n}]]"
   opened: {YYYY-MM-DD}
   closed: null
   ---

   # PHASE_{n}_FIX: Fix Ledger

   > [← Phase {n}](PHASE_{n}.md) · [← Roadmap](ALL.md)

   ## Parent Phase
   [PHASE_{n}.md](PHASE_{n}.md) — {phase goal one-liner}

   ## Branch / Worktree
   - Branch: `fix/phase-{n}-{slug}`
   - Worktree: `.worktrees/fix-{n}-{slug}`

   ## Fix Rounds
   | Round | Trigger | Branch | Status | Opened | Closed |
   |---|---|---|---|---|---|

   ## Fix Work Units
   | ID | Round | Goal | Parent WU | Acceptance Criteria | Scope | Verification | Status | Commit |
   |---|---|---|---|---|---|---|---|---|

   ## Review Log
   | Work Unit | Ready At | Commit | Verification Evidence | Client Decision | Notes |
   |---|---|---|---|---|---|
   ```

4. In `PHASE_{n}_FIX.md`, add or update a Fix Rounds row:
   ```
   | {slug} | {description} | fix/phase-{n}-{slug} | active | {today} | null |
   ```

5. In `agents/roadmap/PHASE_{n}.md`, keep a compact Fix Rounds table that points to the single ledger:
   ```
   | {slug} | [PHASE_{n}_FIX.md](PHASE_{n}_FIX.md#{slug}) | fix/phase-{n}-{slug} | active |
   ```

6. In `agents/roadmap/ALL.md`, set the phase row's Fix Rounds column to the ledger link:
   ```
   [PHASE_{n}_FIX.md](PHASE_{n}_FIX.md)
   ```

7. Append to `agents/roadmap/log.md`:
   ```
   | {today} | fix-open | PHASE_{n}_FIX — {slug}: {description} |
   ```

   Add one line to `agents/index.md` under the `## Roadmap` section only if the ledger is new:
   ```
   - [[roadmap/PHASE_{n}_FIX]] — consolidated fix ledger for PHASE_{n} · status: active
   ```

8. Commit the fix setup as a Tiny WU on the fix branch:

   ```bash
   git add agents/roadmap/ agents/index.md
   git commit -m "WU-TW-{k}: open fix round {slug} for phase {n}"
   ```

9. Implement fix WUs one at a time in the worktree, recording each in `PHASE_{n}_FIX.md`.
   Fix WU status moves to `ready-for-review` after implementation, verification, roadmap update, and commit.
   The agent reports what changed, the commit hash, verification evidence, and asks the client to review or continue.
   The agent must not mark the fix round, fix WU, phase WU, or phase as `done` by itself.

If $ARGUMENTS indicates **all tests pass**:

1. Update the active phase frontmatter:
   - `test_status: pass`
   - `test_waive_reason: null`
2. Append to `agents/roadmap/log.md`:
   ```
   | {today} | test-pass | PHASE_{n} ready for client closeout |
   ```
3. Commit the phase metadata update:
   ```bash
   git add agents/roadmap/
   git commit -m "WU-TW-{k}: record passing test status for phase {n}"
   ```
4. Report: acceptance criteria met, verification evidence recorded, phase is ready for client review.
5. Prompt: "Checks pass and PHASE_{n} is ready for closeout. Send `/wur:done` when you want me to merge and close it."

If $ARGUMENTS indicates **a waive**:

1. Update the active phase frontmatter:
   - `test_status: waived`
   - `test_waive_reason: {reason from $ARGUMENTS}`
2. Append to `agents/roadmap/log.md`:
   ```
   | {today} | test-waive | PHASE_{n} closeout readiness waived — {reason} |
   ```
3. Commit the phase metadata update:
   ```bash
   git add agents/roadmap/
   git commit -m "WU-TW-{k}: waive test status for phase {n}"
   ```
4. Report clearly that closeout is waived, not passed.
5. Prompt: "Verification is waived with a recorded reason. Send `/wur:done` when you want me to merge and close it."

Never mark a phase done without `/wur:done`.
