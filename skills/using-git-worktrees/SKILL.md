---
name: using-git-worktrees
description: Use when a WUR contract has executable project work that requires editing project files in a sparse worktree excluding agents/ and contracts/.
---

# Sparse Worktrees For Contract Execution

WUR does not create a worktree just because `/wur:start` created a contract. The executor first reads the contract.

Use this skill only when the active contract contains executable project work and implementing it requires editing project files.

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

- Do not create a worktree when the contract has no executable project work.
- If there is no implementation task, report blocked/no-op/clarification-needed in the contract ledger.
- If implementation requires editing project files, create or reuse a sparse worktree before editing those files.
- Do not copy `agents/` into the execution worktree.
- Do not copy `contracts/` into the execution worktree.
- Do not use sparse worktree setup as a substitute for WUR receive.
- The executor returns evidence; WUR updates `agents/`.

## When To Use

| Situation | Use sparse worktree? |
|---|---|
| Contract has no executable project work | No; report blocked/no-op/clarification-needed |
| Report-only or clarification-only round | No |
| Implementation edits project files | Yes |
| User explicitly asks for isolated execution | Yes, if there is executable work |
| Git sparse checkout errors or permission problems | Prefer manual execution from contract |
