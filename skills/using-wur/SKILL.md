---
name: using-wur
description: Use when starting any conversation — establishes how to find and use WUR skills, requiring this bootstrap before any response or action.
---

<SUBAGENT-STOP>
If you were dispatched as an external executor for a `contracts/PHASE_{n}_CONTRACT.md` file, follow that contract instead of this bootstrap.
</SUBAGENT-STOP>

# Using WUR Skills

## Rule

Invoke relevant or requested WUR skills before any response or action. Start here, then use `wur-guidelines` for roadmap, wiki, contract, receive, status, and closeout work.

## WUR Shape

WUR uses three local skills:

1. **`using-wur`** — this bootstrap.
2. **`wur-guidelines`** — core workflow: `agents/` wiki, Work Units, shared contract rules, phase contracts, verification, receive, and client-confirmed closeout.
3. **`using-git-worktrees`** — optional isolation guidance only when a contract explicitly recommends a sparse worktree.

Everything else is driven by slash commands in `commands/` and `commands/wiki/`.

## Current Model

```text
agents/ = source-of-truth wiki
contracts/rule.md = shared execution rules
contracts/PHASE_{n}_CONTRACT.md = phase execution contract + report ledger
```

`/wur:start {n}` creates or refreshes the shared rule file and phase contract. It does not make the WUR coordinator execute code by itself.

External executors may implement from the contract, but they must not edit `agents/`. WUR receives their report and updates `agents/` after verification.

## Command Map

- "initialize WUR" → `wur-guidelines` → `/wur:init`
- "create/start phase 2" → `wur-guidelines` → `/wur:start 2`
- "record failed tests" → `wur-guidelines` → `/wur:test fail: ...`
- "close phase" → `wur-guidelines` → `/wur:done` only when the current user request explicitly asks for it
- "ingest/add to wiki" → `wur-guidelines` → `/wur:wiki:add`
- "turn idea into MVP context" → `wur-guidelines` → `/wur:wiki:ima`

## Red Flags

| Thought | Reality |
|---|---|
| "This is just a simple question" | Questions are tasks. Check WUR first. |
| "I'll update agents/ after execution" | External executors do not edit `agents/`; WUR receives reports. |
| "I'll make a new report file" | Keep reports in the same phase contract file unless the command says otherwise. |
| "Tests passed, so I can run `/wur:done`" | Only the current client request can authorize `/wur:done`. |
| "I'll skip verification" | Evidence before claims. |
| "I'll create Phase Fix files" | New work uses contract rounds, not Phase Fix ledgers. |

## User Instructions

Instructions say what to accomplish, not how to bypass WUR. Keep the workflow small, explicit, and verifiable.
