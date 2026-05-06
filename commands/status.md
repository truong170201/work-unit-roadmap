---
description: Show current project state — active phase, active WU, worktree, uncommitted changes.
argument-hint: ""
---

Show project status using the `wur-guidelines` skill.

`/wur:status` is the read model of the enforcement state. It should tell the operator whether progress is safe to continue, blocked, or waived-with-trace.

1. If `agents/roadmap/ALL.md` does not exist, stop and report:

   ```text
   WUR workspace not initialized. Run /wur:init first.
   ```

   This is the only graceful exit. Do not attempt to read other files.

2. Run `git worktree list`, `git branch --show-current`, `git status`, `git log -3 --oneline`.
3. Read `agents/roadmap/ALL.md` — extract active phase, active WU, open fix rounds, latest completed unit.
4. Read the active `agents/roadmap/PHASE_{n}.md` if one exists — extract `test_status` and `test_waive_reason`.
5. Read the last 5 lines of `agents/roadmap/log.md` for recent activity.
6. Report in compact format:

```text
Worktree:    .worktrees/phase-2
Branch:      feature/phase-2
Phase:       2 — Local Study Workflow Depth (active)
Active WU:   WU-P02-005 — Audio stack migration
Last done:   WU-P02-004 — PDF annotation storage hardening
Test status: pass  (or: waived — device unavailable)
Fix rounds:  none  (or: FIX_P2_device-r1 — active, 3/5 done)
Blockers:    none  (or: active WU still open)
Uncommitted: 2 files modified (src/hooks/useAudio.ts, ...)
Recent log:
  2026-05-03 | phase-open  | PHASE_2 started — branch: feature/phase-2
  2026-05-04 | fix-open    | FIX_P2_device-r1 — 4 bugs
```
