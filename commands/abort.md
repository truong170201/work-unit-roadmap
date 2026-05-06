---
description: Abort an active phase — discard or preserve worktree, delete feature/fix branches, mark phase aborted in roadmap.
argument-hint: "<phase-number> [--soft] [-- reason]"
---

Abort phase `$ARGUMENTS` using the `wur-guidelines` skill.

Use this when a phase was started by mistake or is being intentionally abandoned. All commits made on `feature/phase-{n}` and any `fix/phase-{n}-*` branches will be discarded — they never reach the default branch.

If the phase has commits worth keeping, do **not** abort. Use `/wur:done` (with `/wur:test waive: ...` if needed) instead so the merge preserves history.

## State semantics

`/wur:abort` recognizes three states. Pick exactly one:

| State | Trigger | What happens to worktree | What happens to branches | Roadmap entry |
|---|---|---|---|---|
| **hard** (default) | `/wur:abort {n}` or `/wur:abort {n} -- <reason>` | force-removed | deleted | `status: aborted`, reason recorded if given |
| **soft** | `/wur:abort {n} --soft [-- <reason>]` | **preserved** for later inspection | preserved (not deleted) | `status: aborted`, soft note + reason |
| **waived** | `/wur:abort {n} -- <reason>` where `<reason>` is non-empty | force-removed | deleted | `status: aborted`, reason marked as `waive_reason` for audit |

Rules:

- A reason is **required** for waived. The waived state is just hard-abort with an explicit, audit-grade trace — equivalent to `/wur:test waive: ...` for closeout.
- Soft is the only mode that leaves recoverable artifacts. It must still mark the phase `aborted` so `/wur:start {n}` is allowed again only after the soft worktree is cleaned up manually.
- All three states forbid the merged commits from ever reaching the default branch automatically. If you want history preserved on `$base`, use `/wur:done`, not `/wur:abort`.

1. Read `agents/roadmap/ALL.md` — extract default branch (`$base`), confirm `PHASE_{n}` exists and is `active`. If not active, stop and report.

2. Refuse to abort if any commits on `feature/phase-{n}` are not also reachable from `$base`, **unless** the user explicitly confirms loss. Detect with:

   ```bash
   git fetch . "feature/phase-{n}:feature/phase-{n}" 2>/dev/null || true
   unmerged=$(git rev-list --count "$base..feature/phase-{n}")
   if [ "$unmerged" -gt 0 ]; then
     echo "WUR: feature/phase-{n} has $unmerged commits not in $base — abort will discard them."
     # require explicit user confirmation before continuing
   fi
   ```

3. Determine the abort mode from `$ARGUMENTS`:
   - if the args contain `--soft` (anywhere before the optional `-- <reason>` separator) → **soft**
   - else if `-- <reason>` is non-empty → **waived**
   - else → **hard**

4. **Soft mode only:** leave `.worktrees/phase-{n}` and `.worktrees/fix-{n}-*` in place; skip both the worktree-remove and branch-delete steps. Continue at step 6.

5. **Hard / waived mode:** force-remove worktrees and delete branches:

   ```bash
   git worktree remove --force .worktrees/fix-{n}-{slug} 2>/dev/null
   git worktree remove --force .worktrees/phase-{n} 2>/dev/null
   git branch -D feature/phase-{n} 2>/dev/null
   for b in $(git branch --list "fix/phase-{n}-*" --format '%(refname:short)'); do
     git branch -D "$b"
   done
   ```

6. Update `agents/roadmap/PHASE_{n}.md` frontmatter:
   - `status: aborted`
   - `closed: {today}`
   - For **soft**: add `abort_mode: soft` and a section `## Abort Reason (soft)` with the reason or "no reason given". Note that the worktree and branch are still on disk pending manual cleanup.
   - For **waived**: add `abort_mode: waived`, `waive_reason: "<reason>"`, and a section `## Abort Reason (waived)` with the same text.
   - For **hard**: add `abort_mode: hard` and a section `## Abort Reason` with the reason or "no reason given".

7. Update `agents/roadmap/ALL.md`:
   - mark the phase row as `aborted` (suffix `(soft)` if soft)
   - clear `Active phase` (set to `none` if no other phase is active)
   - clear `Active Work Unit` (set to `none`)

8. Update `agents/index.md`: change phase entry `status: active` → `status: aborted`.

9. For every `agents/roadmap/FIX_P{n}_*.md`, set frontmatter `status: aborted` and `closed: {today}`. Update their entries in `agents/index.md` similarly.

10. Append to `agents/roadmap/log.md`:

    ```text
    | {today} | phase-abort | PHASE_{n} aborted ({mode}) — reason: {reason} |
    ```

11. Commit roadmap updates on `$base` (resolve main repo root the same way `/wur:done` does):

    ```bash
    main_repo=$(git worktree list --porcelain \
                | awk '/^worktree / {p=$2} /^bare$/ {p=""} /^branch / && p!="" {print p; exit}' \
                || git rev-parse --path-format=absolute --git-common-dir | xargs -I{} dirname {})
    cd "$main_repo"
    git switch "$base" 2>/dev/null || git checkout "$base"
    git add agents/roadmap/ agents/index.md
    git commit -m "WU-P{n}-abort: abandon phase {n} ({mode})"
    ```

12. Report: phase aborted in `{mode}` mode, branches deleted (or preserved for soft), worktrees removed (or preserved for soft), reason recorded, what (if anything) was lost, what phase is next.

   For soft aborts, also print the reminder: "`.worktrees/phase-{n}` is preserved. Inspect, then delete manually with `git worktree remove --force` + `git branch -D feature/phase-{n}` once you no longer need it."
