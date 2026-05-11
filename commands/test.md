---
description: Record phase test status or append a failed execution round to the phase contract.
argument-hint: "[pass | waive: <reason> | fail: <description>]"
---

Process test results using the `wur-guidelines` skill.

Before doing anything else, read `agents/roadmap/ALL.md` and enforce the phase gate:
- there must be an active phase
- the active phase must have `contracts/PHASE_{n}_CONTRACT.md`
- if the contract is missing, stop and run `/wur:start {n}` first

Call this after tests have been run by the user or by an executor. Pass the result as `$ARGUMENTS`:
- `pass` — tests passed; record phase closeout readiness only
- `waive: <reason>` — closeout readiness is allowed without a clean pass, but the reason must be recorded
- `fail: <description>` — bugs found; append a new execution round in the same contract file

This command is the only allowed way to set phase `test_status` before `/wur:done`.

Use the phase-level verification strategy before recording `pass` or `waive`. This is broader than normal WU-scoped verification: WU checks prove one bounded change; `/wur:test pass` proves the active phase is ready for client closeout.

If `$ARGUMENTS` is empty or unrecognized, stop and print this help, do not mutate anything:

```text
Usage: /wur:test pass
       /wur:test waive: <reason>
       /wur:test fail: <description>

  pass    Mark active phase test_status: pass.   Use after tests succeed.
  waive   Mark active phase test_status: waived. Reason is required.
  fail    Append a failed execution round to the phase contract. Description is required.
```

## Status Ownership

- Agent-owned WU states: `planned`, `active`, `ready-for-review`, `blocked`, `deferred`.
- Client-owned WU states: `accepted`, `done`.
- External executors report evidence in `contracts/PHASE_{n}_CONTRACT.md`.
- WUR receives and validates evidence before updating `agents/`.
- The agent must not mark a WU `done` merely because verification passed.
- `done` is reserved for client-confirmed phase closeout through `/wur:done`.

If $ARGUMENTS indicates **bugs found**:

1. Update the active phase frontmatter:
   - `test_status: failing`
   - `test_waive_reason: null`
2. Append a new execution round in the same contract file, `contracts/PHASE_{n}_CONTRACT.md`.
3. Do not create `PHASE_{n}_FIX.md`. Do not create fix branches or fix worktrees by default. Failed work is another contract round, not a separate Phase Fix lane.
4. The new round must include failure description, affected WU or phase scope, required verification, and a report slot for the executor.
5. Append to `agents/roadmap/log.md`:

   ```text
   | {today} | contract-fail | PHASE_{n} contract round opened — {description} |
   ```

6. Commit the metadata/contract update:

   ```bash
   git add agents/roadmap/ contracts/PHASE_{n}_CONTRACT.md
   git commit -m "WU-TW-{k}: record failed contract round for phase {n}"
   ```

If $ARGUMENTS indicates **all tests pass**:

1. Update the active phase frontmatter:
   - `test_status: pass`
   - `test_waive_reason: null`
2. Append to `agents/roadmap/log.md`:
   ```text
   | {today} | test-pass | PHASE_{n} ready for client closeout |
   ```
3. Commit the phase metadata update:
   ```bash
   git add agents/roadmap/
   git commit -m "WU-TW-{k}: record passing test status for phase {n}"
   ```
4. Report: acceptance criteria met, verification evidence recorded, phase is ready for client review.
5. Prompt: "Checks pass and PHASE_{n} is ready for closeout. Send `/wur:done` when you want me to close it."

If $ARGUMENTS indicates **a waive**:

1. Update the active phase frontmatter:
   - `test_status: waived`
   - `test_waive_reason: {reason from $ARGUMENTS}`
2. Append to `agents/roadmap/log.md`:
   ```text
   | {today} | test-waive | PHASE_{n} closeout readiness waived — {reason} |
   ```
3. Commit the phase metadata update:
   ```bash
   git add agents/roadmap/
   git commit -m "WU-TW-{k}: waive test status for phase {n}"
   ```
4. Report clearly that closeout is waived, not passed.
5. Prompt: "Verification is waived with a recorded reason. Send `/wur:done` when you want me to close it."

Never mark a phase done without `/wur:done`.
