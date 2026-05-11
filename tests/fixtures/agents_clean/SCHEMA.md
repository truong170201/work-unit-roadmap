---
schema_version: 1
---

# agents/ Wiki Schema

## Status Values
`planned` · `active` · `done` · `blocked` · `deferred` · `aborted`

## Required Frontmatter (graph pages)
- `type`
- `status`
- `tags`

## Contract Boundary
- `agents/` is the source-of-truth wiki.
- `contracts/rule.md` stores shared execution rules outside `agents/`.
- `contracts/PHASE_{n}_CONTRACT.md` stores phase task brief, Allowed Read References, and executor report ledger.
- Executor handoff reports stay in the active phase contract.
- `agents/reports/` stores durable WUR reports and summaries, not executor handoff ledgers.
- If a worktree is used, exclude `agents/` and `contracts/`; keep WUR state in the main project root only.
