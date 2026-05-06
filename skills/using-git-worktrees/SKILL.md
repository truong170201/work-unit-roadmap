---
name: using-git-worktrees
description: Use when starting feature work that needs isolation — creates isolated git worktrees under .worktrees/ with safety verification and clean baseline
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching or stashing.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Scope:** Used only for phase implementation (`.worktrees/phase-{n}`) and bug-fix branches (`.worktrees/fix-{n}-*`). Wiki operations (`/wur:wiki:*`) and workspace setup (`/wur:init`) run from the main repo — no worktree is created or needed for them.

**Git log guarantee:** Every WU commit made inside the worktree lands on `feature/phase-{n}`. When `/wur:done` runs `git merge --no-ff`, all WU commits appear in the default branch log as a named group under one merge commit. This preserves full cherry-pick, revert, and bisect capability per WU. The main repo stays on the default branch throughout — no branch switching, no stashing, no history tangling.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Directory Selection

Always use `.worktrees/` at the project root — `/wur:init` adds it to `.gitignore` by default.

1. Verify `.worktrees/` is gitignored: `git check-ignore -q .worktrees/`
2. If not ignored: add `.worktrees/` to `.gitignore` and commit before creating the worktree.

## Creation Steps

### 1. Detect Base Branch

```bash
# Detect default branch (main, master, or develop)
base=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
base=${base:-$(git rev-parse --verify main 2>/dev/null && echo main || \
              git rev-parse --verify master 2>/dev/null && echo master || \
              git rev-parse --verify develop 2>/dev/null && echo develop)}
```

### 2. Create Worktree

**Phase worktree** (from base branch):

```bash
git fetch origin "$base" 2>/dev/null || true
git worktree add .worktrees/phase-{n} -b feature/phase-{n} "$base"
cd .worktrees/phase-{n}
```

**Fix worktree** (from the phase branch):

```bash
git worktree add .worktrees/fix-{n}-{slug} -b fix/phase-{n}-{slug} feature/phase-{n}
cd .worktrees/fix-{n}-{slug}
```

Naming conventions (match `/wur:*` commands):

| Kind | Worktree path | Branch |
|------|---------------|--------|
| Phase | `.worktrees/phase-{n}` | `feature/phase-{n}` |
| Fix | `.worktrees/fix-{n}-{slug}` | `fix/phase-{n}-{slug}` |

### 3. Run Project Setup

Auto-detect and run appropriate setup:

```bash
# Node.js
[ -f package.json ] && npm install

# Python
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f pyproject.toml ] && poetry install

# Rust
[ -f Cargo.toml ] && cargo build

# Go
[ -f go.mod ] && go mod download
```

### 4. Verify Clean Baseline

Run tests to ensure worktree starts clean. If tests fail, report and ask before proceeding.

### 5. Report Location

```
Worktree ready at .worktrees/<name>
Tests passing (N tests, 0 failures)
Ready to implement <feature>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify gitignored) |
| `.worktrees/` missing | Create it, add to .gitignore |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask |
| No package.json/etc | Skip dependency install |

## Red Flags

**Never:**
- Create worktree without verifying it's gitignored
- Skip baseline test verification
- Proceed with failing tests without asking
- Use `git checkout` to switch branches when a worktree exists

**Always:**
- Verify `.worktrees/` is gitignored
- Auto-detect and run project setup
- Verify clean test baseline
- Clean up with `git worktree remove` when done

## Integration

**Called by:**
- `/wur:start` — REQUIRED before phase implementation
- `/wur:test` — REQUIRED for fix branches
- Any task needing isolated workspace

**Cleaned up by:**
- `/wur:done` — removes phase + fix worktrees after phase closeout
