---
description: Abort an active phase — mark phase aborted, preserve trace, and stop contract execution.
argument-hint: "<phase-number> [--soft] [-- reason]"
---

Abort Phase $ARGUMENTS using the `wur-guidelines` skill.

Use this when a phase was started by mistake or is intentionally abandoned. Any implementation commits reported by a contract are not merged by this command; they never reach the default branch. Use `/wur:done` when completed work should be accepted into the roadmap closeout path.

Abort modes:

| State | Trigger | Contract handling | Roadmap entry |
|---|---|---|---|
| hard | mistaken phase, no useful work | mark contract aborted | `status: aborted`, `abort_mode: hard` |
| soft | preserve contract/report evidence for manual inspection | leave `contracts/PHASE_{n}_CONTRACT.md` in place | `status: aborted`, `abort_mode: soft` |
| waived | user accepts loss/incompleteness explicitly | mark contract aborted with reason | `status: aborted`, `abort_mode: waived` |

Rules:
- Refuse to abort if any commits referenced by the contract look valuable unless** the user explicitly confirms loss.
- A reason is required for waived.
- Soft is the only mode that leaves recoverable artifacts.
- Aborted work does not become done work.

Procedure:

1. Read `agents/roadmap/ALL.md`; confirm PHASE_{n} is active or abortable.
2. Read `agents/roadmap/PHASE_{n}.md` and `contracts/PHASE_{n}_CONTRACT.md` if present.
3. Inspect contract reports for commit hashes and changed files. Refuse to abort if any commits appear unreviewed unless the user explicitly confirms loss.
4. Update `agents/roadmap/PHASE_{n}.md`:
   - `status: aborted`
   - `closed: {today}`
   - `abort_mode: hard | soft | waived`
   - append `## Abort Reason` with the reason or "no reason given"
5. Update `agents/roadmap/ALL.md`:
   - mark the phase row as `aborted` (suffix `(soft)` if soft)
   - clear `Active phase`
   - clear `Active Work Unit`
   - do not auto-activate the next phase unless the user asked
6. Update `agents/index.md` so the phase line shows `status: aborted`.
7. Append to `agents/roadmap/log.md`:

   ```text
   | {today} | phase-abort | PHASE_{n} aborted ({mode}) — {reason} |
   ```

8. Commit the abort trace:

   ```bash
   git add agents/roadmap/ agents/index.md contracts/PHASE_{n}_CONTRACT.md
   git commit -m "WU-P{n}-abort: abandon phase {n} ({mode})"
   ```

9. Report: phase aborted in `{mode}` mode, reason recorded, what was preserved, what was lost, and what phase is next.
