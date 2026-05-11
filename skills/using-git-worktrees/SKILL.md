---
name: using-git-worktrees
description: Use only when a WUR contract explicitly asks for isolated execution with a sparse worktree that excludes agents/ and contracts/.
---

# Optional Sparse Worktrees

WUR no longer requires worktrees for normal `/wur:start` flow. The default execution boundary is `contracts/PHASE_{n}_CONTRACT.md`.

Use this skill only when the contract or user explicitly asks for isolation.

## Principle

A worktree used by an external executor should not carry WUR state. `agents/` is the source-of-truth wiki and `contracts/` is the contract/report boundary. The executor works from the contract brief and must not edit those folders.

## Recommended Sparse Worktree

```bash
git worktree add .worktrees/P{n}_contract -b work/P{n}_contract main
cd .worktrees/P{n}_contract
git sparse-checkout init --no-cone
git sparse-checkout set "/*" "!/agents/" "!/contracts/"
```

Verify:

```bash
git status --short
Test-Path agents
Test-Path contracts
```

`agents/` and `contracts/` should not be present in the execution worktree. If the Git version does not support the exclude patterns reliably, do not force automation; copy the contract instructions manually and keep execution out of `agents/`.

## Rules

- Do not create phase/fix worktrees by default.
- Do not copy `agents/` into the execution worktree.
- Do not copy `contracts/` into the execution worktree.
- Do not use sparse worktree setup as a substitute for WUR receive.
- The executor returns evidence; WUR updates `agents/`.

## When To Use

| Situation | Use sparse worktree? |
|---|---|
| Small docs/wiki update | No |
| Executor can safely work in normal repo without touching `agents/` | Optional |
| Large/risky code change | Yes |
| User explicitly asks for isolated execution | Yes |
| Git sparse checkout errors or permission problems | Prefer manual execution from contract |
