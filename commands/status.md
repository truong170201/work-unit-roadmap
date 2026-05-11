---
description: Show current project state — active phase, contract, WU, and wiki health.
argument-hint: ""
---

Show project status using the `wur-guidelines` skill.

`/wur:status` is the read model of the WUR wiki and contract state. It should tell the operator whether progress is safe to continue, blocked, or waived-with-trace.

1. If `agents/roadmap/ALL.md` does not exist, stop and report:

   ```text
   WUR workspace not initialized. Run /wur:init first.
   ```

   This is the only graceful exit. Do not attempt to read other files.

2. Run `git branch --show-current`, `git status`, and `git log -3 --oneline`.
3. Read `agents/roadmap/ALL.md` — extract active phase, active WU, latest completed unit, blockers, and default branch.
4. Read the active `agents/roadmap/PHASE_{n}.md` if one exists — extract `test_status` and `test_waive_reason`.
5. Read `contracts/PHASE_{n}_CONTRACT.md` if it exists — extract pending WUs and latest report status from `## Execution Rounds And Reports`.
6. Read the last 5 lines of `agents/roadmap/log.md` for recent activity.
7. Report in compact format:

```text
Branch:      main
Phase:       2 — Local Study Workflow Depth (active)
Contract:    contracts/PHASE_2_CONTRACT.md
Active WU:   WU-P02-005 — Audio stack migration
Pending:     WU005, WU006
Last report: WU005 R2 — pass, commit abc123
Last done:   WU-P02-004 — PDF annotation storage hardening
Test status: pass  (or: waived — device unavailable)
Blockers:    none  (or: active WU still open)
Uncommitted: 2 files modified (src/hooks/useAudio.ts, ...)
Recent log:
  2026-05-03 | contract-open | PHASE_2 contract refreshed
  2026-05-04 | test-pass     | PHASE_2 ready for client closeout
```
