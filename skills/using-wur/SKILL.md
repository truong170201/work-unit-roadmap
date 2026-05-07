---
name: using-wur
description: Use when starting any conversation — establishes how to find and use WUR skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

WUR skills define **how** to accomplish what the user asks. They do not block user goals — they enforce quality while achieving them.

1. **User's goals** — what to build, fix, or investigate. Always respected.
2. **WUR workflow** — how to do it: in a Work Unit, with verification, one commit at a time.
3. **Default system prompt** — overridden where WUR is more specific.

"Just fix it quickly" still means: fix it correctly, in a WU, verified. Speed comes from keeping WUs small — not from skipping the workflow.

## How to Access Skills

Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you — follow it directly. Never use the Read tool on skill files.

# Using WUR Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

## Red Flags

These thoughts mean STOP — you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |
| "I'll just fix this bug real quick" | Bugs need `/wur:test` → fix WU + fix worktree. |
| "One more WU won't hurt" | Scope creep destroys roadmaps. Follow the phase plan. |
| "The roadmap is out of date anyway" | Update it. That's part of the workflow. |

## Available Skills

This plugin provides exactly three skills:

1. **`using-wur`** (this skill) — bootstrap. Teaches discovery + Red Flags.
2. **`wur-guidelines`** — core workflow. Phases, Work Units, verification, commits.
3. **`using-git-worktrees`** — creates `.worktrees/<name>` for isolated implementation.

Any other skill name you may have seen in external docs (brainstorming, writing-plans, test-driven-development, etc.) is NOT part of this plugin. Do not invoke skills that do not exist.

## Skill Priority

When multiple skills apply, use this order:

1. **`wur-guidelines`** — always first. Determines WHAT task you are actually on and HOW to track it.
2. **`using-git-worktrees`** — before any implementation. Ensures isolated workspace.

Everything else (creating phase files, running commands, wiki operations) is driven by slash commands in `commands/` (phase lifecycle) and `commands/wiki/` (knowledge management), registered under the plugin namespace `wur`, not standalone skills.

"Start phase 2" → `wur-guidelines` → `/wur:start 2` → `using-git-worktrees`.
"Fix a bug" → `wur-guidelines` → `/wur:test` → `using-git-worktrees` for fix branch.
"Ingest a paper" → `wur-guidelines` → `/wur:wiki:add`.
"Turn this idea into MVP context" → `wur-guidelines` → `/wur:wiki:ima`.

## Skill Types

All three skills in this plugin are **prescriptive** — follow their steps in order. They exist because discipline beats ad-hoc choice. Some steps include a user confirmation (e.g., confirming baseline test results), but the overall flow does not vary by situation or perceived simplicity.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
