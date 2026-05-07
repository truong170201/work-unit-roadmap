---
description: Client confirms phase complete — merge fix branches, cleanup worktrees, mark phase done.
argument-hint: ""
---

Close the active phase using the `wur-guidelines` skill.

This command may run only when the current user request explicitly invokes `/wur:done`.
If the agent merely believes the phase is ready, stop, report the readiness evidence, and ask the client to send `/wur:done`.
Do not infer closeout permission from passing tests, finished fixes, clean diffs, or a previous conversation.

1. Read `agents/roadmap/ALL.md` — extract the default branch (`$base`), confirm the active phase and its number `{n}`, and enforce the roadmap gate:
   - there must be an active phase
   - `Active Work Unit` must be `none`
   - otherwise stop — phase close is not allowed while a WU is still active
2. Read the active `agents/roadmap/PHASE_{n}.md` frontmatter and enforce the closeout gate:
   - allow `test_status: pass`
   - allow `test_status: waived` only if `test_waive_reason` is non-empty
   - otherwise stop — phase close is not allowed yet
3. Read `agents/roadmap/PHASE_{n}_FIX.md` if it exists. Legacy workspaces may also have `agents/roadmap/FIX_P{n}_*.md`; read them for compatibility but do not create new legacy files.
   For each open fix round in the fix ledger, verify its Fix Rounds row in `PHASE_{n}.md` is not `active`.
   If a `fix/phase-{n}-*` worktree has unmerged commits, merge it into the phase branch first:

   ```bash
   cd .worktrees/phase-{n}
   git merge --no-ff fix/phase-{n}-{slug} -m "WU-P{n}-fix: merge fix/phase-{n}-{slug}"
   ```

4. Merge the phase branch into the default branch. Main repo stays on `$base`; do not checkout feature branches there:

   ```bash
   # Resolve the main repo root from any worktree
   main_repo=$(git worktree list --porcelain \
               | awk '/^worktree / {p=$2} /^bare$/ {p=""} /^branch / && p!="" {print p; exit}' \
               || git rev-parse --path-format=absolute --git-common-dir | xargs -I{} dirname {})
   cd "$main_repo"
   git switch "$base" 2>/dev/null || git checkout "$base"
   git pull --ff-only origin "$base" 2>/dev/null || true
   git merge --no-ff "feature/phase-{n}" -m "Phase {n}: merge feature/phase-{n}"
   ```

   If running from inside `.worktrees/phase-{n}`, the `main_repo` resolver above returns the project root (the first non-worktree entry in `git worktree list`). Always confirm with `pwd` before merging.

5. Respect the recorded closeout test status:
   - if `test_status: pass`, run the tests again on the merged result; if they fail, stop and report — do NOT cleanup worktrees
   - if `test_status: waived`, do not fabricate a pass; keep the recorded waive reason and proceed with explicit trace
6. Clean up worktrees and local branches:

   ```bash
   git worktree remove .worktrees/fix-{n}-{slug} 2>/dev/null  # if it exists
   git worktree remove .worktrees/phase-{n}
   git branch -d feature/phase-{n}
   git branch -d fix/phase-{n}-* 2>/dev/null
   ```

7. Update `agents/roadmap/PHASE_{n}.md`:
   - Update frontmatter: `status: done`, `closed: {today}`
   - Move client-approved WUs to client-confirmed `done`.
   - For any WUs not yet `accepted` or `done`, mark them `deferred` with a brief reason or keep as `blocked` if unresolved. Do NOT mark unreviewed or unverified WUs as `done`.
   - Fill the exit gate verification log.
   - Update the corresponding line in `agents/index.md`: change `status: active` → `status: done`.
8. Update `agents/roadmap/ALL.md`: mark the phase row `done`, record the merge commit, clear active WU, set next phase as active if planned.
8a. If the Commit Index table in `agents/roadmap/ALL.md` exceeds 30 rows after this update, archive completed phase rows:
   - Create `agents/reports/commit-index-PHASE_{n}.md` with ALL rows for PHASE_{n} from the Commit Index
   - Replace those rows in ALL.md Commit Index with a single summary row:
     `| PHASE_{n} (archived) | {count} work units | see [[reports/commit-index-PHASE_{n}]] | all verified |`
   - This keeps ALL.md scannable without losing history.
   - Include the new report file in the step 10 commit.
9. Append to `agents/roadmap/log.md`:
   ```
   | {today} | phase-close | PHASE_{n} merged into {base} — commit: {hash} |
   ```
10. Commit roadmap updates on `$base`:
   ```bash
   git add agents/roadmap/ agents/index.md
   git commit -m "WU-P{n}-close: mark phase {n} done"
   ```
11. Report: phase closed, merge commit hash, test status (`pass` or `waived`), worktrees cleaned, fix rounds completed, what was accomplished, what phase is next.
