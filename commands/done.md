---
description: Client confirms phase complete — validate contract reports, update wiki, mark phase done.
argument-hint: ""
---

Close the active phase using the `wur-guidelines` skill.

This command may run only when the current user request explicitly invokes `/wur:done`. If the agent merely believes the phase is ready, stop, report the readiness evidence, and ask the client to send `/wur:done`. Do not infer closeout permission from passing tests, finished reports, clean diffs, or a previous conversation.

1. Read `agents/roadmap/ALL.md` — extract the active phase and enforce the roadmap gate:
   - there must be an active phase
   - `Active Work Unit` must be `none`
   - otherwise stop — phase close is not allowed while a WU is still active
2. Read the active `agents/roadmap/PHASE_{n}.md` frontmatter and enforce the closeout gate:
   - allow `test_status: pass`
   - allow `test_status: waived` only if `test_waive_reason` is non-empty
   - otherwise stop — phase close is not allowed yet
3. Read `contracts/PHASE_{n}_CONTRACT.md` and review the contract's Execution Rounds And Reports. Use the ledger as the selection source: WUs with verified reports and client approval may move forward; skipped WUs already accepted/done stay unchanged; unreported WUs must be deferred or blocked with a reason. Verify every included WU has a report or explicit defer/block reason, no report claims it modified `agents/` directly, commit hashes and changed files are present when implementation changed, and failed rounds have a follow-up round or a recorded client decision.
4. Closeout verification is full-phase verification. Do not use WU-scoped checks as the only closeout evidence. Respect the recorded closeout test status:
   - if `test_status: pass`, run the tests again on the merged result or current default branch result; if they fail, stop and report
   - if `test_status: waived`, do not fabricate a pass; keep the recorded waive reason and proceed with explicit trace
5. Update `agents/roadmap/PHASE_{n}.md`:
   - Update frontmatter: `status: done`, `closed: {today}`
   - Move client-approved WUs to client-confirmed `done`.
   - For any WUs not yet `accepted` or `done`, mark them `deferred` with a brief reason or keep as `blocked` if unresolved.
   - Do NOT mark unreviewed or unverified WUs as `done`.
   - Fill the exit gate verification log.
   - Update the corresponding line in `agents/index.md`: change `status: active` to `status: done`.
6. Update `agents/roadmap/ALL.md`: mark the phase row `done`, record the final commit/reference, clear active WU, set next phase as active if planned.
7. If the Commit Index table in `agents/roadmap/ALL.md` exceeds 30 rows after this update, archive completed phase rows:
   - Create `agents/reports/commit-index-PHASE_{n}.md` with ALL rows for PHASE_{n} from the Commit Index
   - Replace those rows in ALL.md Commit Index with a single summary row: `| PHASE_{n} (archived) | {count} work units | see [[reports/commit-index-PHASE_{n}]] | all verified |`
   - This keeps ALL.md scannable without losing history.
   - Include the new report file in the step 9 commit.
8. Append to `agents/roadmap/log.md`:
   ```text
   | {today} | phase-close | PHASE_{n} closed by client-confirmed `done` |
   ```
9. Commit roadmap updates on the default branch:
   ```bash
   git add agents/roadmap/ agents/index.md agents/reports/ contracts/PHASE_{n}_CONTRACT.md
   git commit -m "WU-P{n}-close: mark phase {n} done"
   ```
10. Report: phase closed, test status (`pass` or `waived`), contract reports reviewed, what was accomplished, what phase is next.
