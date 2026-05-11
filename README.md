# Work Unit Roadmap — a Claude Code Plugin

Turn a coding agent workflow into a disciplined project wiki and execution contract system: atomic Work Units, verification evidence, client-confirmed closeout, and a recoverable project memory.

```text
Small task, verify, report, receive. Repeat.
```

## What is this?

Most AI coding sessions fail because the agent mixes planning, execution, status updates, and self-approval in one context window. WUR separates those concerns.

`agents/` is the project second brain: roadmap, research, decisions, design, tech stack, specialist registry, reports, and graph state. It is the source of truth.

`contracts/rule.md` stores shared WUR execution rules. `contracts/PHASE_{n}_CONTRACT.md` is one phase contract per phase: task brief, pending Work Units, explicit Allowed Read References, and the report ledger. The executor reads only the listed `agents/` paths when deeper context is needed, follows `contracts/rule.md`, returns evidence in the phase contract, and WUR receives the report before updating `agents/`.

There is no Codex App Server integration, no MCP runtime coordinator, and no required subagent platform. WUR is a wiki + contract + receive workflow.

Software projects should also keep `agents/project/DESIGN.md` and `agents/project/TECH_STACK.md`. `DESIGN.md` is the AI-readable Design Contract. `TECH_STACK.md` records stack choices and verification commands. Defaults are recommendations, not mandates: common web apps prefer Vite/React/TypeScript/Tailwind/shadcn; SEO sites prefer Next.js App Router; mobile prefers Expo + TypeScript + NativeWind; browser games prefer Vite + TypeScript with Phaser or Three.js.

## Scope boundary

Canonical scope contract lives in `skills/wur-guidelines/SKILL.md` (`## Scope Boundary`). This README is package/user documentation; runtime agent behavior is defined by the `skills/` and `commands/` files.

Short form:
- **Wiki = plan**
- **Contracts = execution boundary**
- **Checks = deterministic local scripts**
- No hosted CI/CD, deployment pipelines, cloud services, or platform-specific runtime orchestration inside WUR.

## Why use it

WUR prevents common AI drift:

- editing roadmap state directly during execution
- creating many noisy executor handoff/fix files
- marking Work Units done without client review
- losing project context when the agent hits context limits
- making the executor ask too many questions because the task lacks a clear contract

The contract keeps the executor focused. The wiki stays clean.

## Control model

1. `/wur:init` creates `agents/` once.
2. `/wur:wiki:*` enriches and queries the wiki.
3. `/wur:start {n}` creates or refreshes `contracts/rule.md` and `contracts/PHASE_{n}_CONTRACT.md`.
4. The executor follows that contract. It must not edit `agents/`.
5. Reports are appended to the same contract file.
6. `/wur:test` records pass/waive/fail state. Failed work stays in the same contract ledger; the executor may add or update a fix round there, not a Phase Fix file.
7. `/wur:done` closes a phase only when the current client request explicitly invokes it.

## Installation

### Claude Code — marketplace (recommended)

```text
/plugin marketplace add truong170201/work-unit-roadmap
/plugin install wur@work-unit-roadmap
/reload-plugins
```

### Claude Code — local clone

```bash
git clone https://github.com/truong170201/work-unit-roadmap.git
```

```text
/plugin install .
/reload-plugins
```

## Quick start

### 1. Bootstrap the project wiki

```text
/wur:init "Build an internal inventory app for warehouse operators."
```

This creates:

- `agents/project/PHILOSOPHY.md`, `USAGE.md`, plus `DESIGN.md` / `TECH_STACK.md` for software projects
- `agents/roadmap/ALL.md` and `agents/roadmap/log.md`
- `agents/SCHEMA.md` and `agents/index.md`
- `agents/raw/`, `research/`, `docs/`, `reports/`, `references/`
- optional `agents/departments/` and `agents/specialists/` when project context is clear

### 2. Optional graph layer

```text
/wur:wiki:upgrade
/wur:wiki:graph extract
```

Markdown under `agents/` remains canonical. Derived graph artifacts can be rebuilt.

### 3. Enrich wiki from an idea

```text
/wur:wiki:ima "Older warehouse operators need a faster picking flow with fewer screen taps."
```

IMA writes durable knowledge into `agents/` and may update roadmap planning when the user's natural language calls for it. It never starts execution, marks WUs done, closes phases, or touches application code.

### 4. Create the phase contract

```text
/wur:start 1
```

This creates or refreshes:

```text
contracts/rule.md
contracts/PHASE_1_CONTRACT.md
```

The contract skips WUs already `accepted` or `done`. Re-running `/wur:start 1` updates the task section but keeps existing reports.

### 5. Execute outside WUR state

Give `contracts/rule.md` and the phase contract file to another agent or human executor. The executor may read only the project docs, departments, and specialists listed under `Allowed Read References` to infer useful specialist lenses, and must not edit `agents/`. It may implement code, run tests, and commit code. If a worktree is used, it must use the sparse-checkout instructions in `contracts/rule.md` so `agents/` and `contracts/` are not carried into the execution worktree.

### 6. Receive reports and close

The executor writes the result into the contract's `## Execution Rounds And Reports` section. WUR validates the report and updates `agents/`.

```text
/wur:test pass
/wur:done
```

`/wur:done` is client-confirmed closeout only.

## Commands

| Command | Run from | Purpose |
|---|---|---|
| `/wur:init` | main repo | Create the `agents/` project wiki |
| `/wur:upgrade` | main repo | Migrate an existing `agents/` workspace |
| `/wur:start {n}` | main repo | Create or refresh `contracts/rule.md` and `contracts/PHASE_{n}_CONTRACT.md` |
| `/wur:test pass` | main repo | Record phase test pass |
| `/wur:test waive: <reason>` | main repo | Record traceable verification waive |
| `/wur:test fail: <description>` | main repo | Record failing status and keep follow-up in the same contract ledger |
| `/wur:done` | main repo | Client-confirmed phase closeout |
| `/wur:abort {n}` | main repo | Abandon phase with trace |
| `/wur:status` | main repo | Show active phase, contract, WU, reports, blockers |
| `/wur:wiki:*` | main repo | Wiki ingest, IMA, ask, lint, stats, graph |

## Scripts

```bash
python skills/wur-guidelines/scripts/wur_contract.py create --phase 1
python skills/wur-guidelines/scripts/wur_contract.py create --phase 1 --wu WU003
python skills/wur-guidelines/scripts/wur_contract.py receive --phase 1 --report-file report.md
python skills/wur-guidelines/scripts/wur_graph_lint.py agents/
python skills/wur-guidelines/scripts/wur_graph_extract.py agents/
python skills/wur-guidelines/scripts/wur_wiki_stats.py agents/
python skills/wur-guidelines/scripts/wur_meta_consistency.py .
```

## Repository structure

```text
work-unit-roadmap/
  README.md
  CLAUDE.md / AGENTS.md
  .claude-plugin/
  skills/
    using-wur/SKILL.md
    wur-guidelines/SKILL.md
    wur-guidelines/scripts/
      wur_contract.py
      wur_graph_extract.py
      wur_graph_lint.py
      wur_graph_query.py
      wur_wiki_stats.py
      wur_meta_consistency.py
    using-git-worktrees/SKILL.md
  commands/
    init.md upgrade.md start.md done.md abort.md test.md status.md
    wiki/
      upgrade.md add.md ima.md ask.md lint.md stats.md graph.md
  tests/
```

## Readiness checklist

- [ ] `agents/` exists and is coherent
- [ ] `agents/project/DESIGN.md` exists for software/dev projects
- [ ] `agents/project/TECH_STACK.md` records material stack choices
- [ ] `agents/roadmap/ALL.md` and phase files are current
- [ ] `contracts/rule.md` exists for shared execution rules
- [ ] `contracts/PHASE_{n}_CONTRACT.md` exists for active execution
- [ ] executor handoff reports live in the same phase contract file, not scattered files
- [ ] `agents/reports/` stores durable WUR reports and summaries: research synthesis, verification, audits, receive summaries, completion reports, archives, and other long-lived project reports
- [ ] `python skills/wur-guidelines/scripts/wur_meta_consistency.py .` returns OK
- [ ] `python -m unittest discover -s tests -v` passes locally

## Other platforms

Claude Code is the only bundled first-class plugin target in this repo. Other platforms are not bundled as first-class plugin targets: there is no Codex manifest, no Cursor package, and no Windsurf package.

The skills use the standard agentskills.io format. For another agent client, copy `skills/` and `commands/` into that client's supported configuration shape, then create a bootstrap file that invokes `using-wur` first.

Claude Code exposes the commands as `/wur:*` and `/wur:wiki:*`. Other clients may reuse the same `commands/` files only if they have their own command mechanism; otherwise invoke the same intent in natural language, such as "create the WUR contract for phase 2", "record a failed contract round", or "lint the wiki".

## License

MIT
