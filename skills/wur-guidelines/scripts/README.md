# WUR Scripts

Real Python implementations for deterministic WUR wiki, graph, and contract operations.
Require: Python 3.10+ and PyYAML (`pip install pyyaml`).

## Scripts

| Script | Purpose |
|---|---|
| `wur_graph_extract.py` | Compile agents/ into nodes.jsonl, edges.jsonl, graph.sqlite |
| `wur_graph_lint.py` | Validate frontmatter, wikilinks, edge integrity, tag format |
| `wur_graph_query.py` | Query graph — neighbors, edges, path, facts, status filter |
| `wur_wiki_stats.py` | Dashboard: page counts, status, broken links, graph freshness |
| `wur_meta_consistency.py` | Local consistency checker for docs/spec/script drift |
| `wur_contract.py` | Create or refresh shared rule files and phase execution contracts, then append returned reports to the same contract file |

## Quick start

```bash
cd your-project/
pip install pyyaml

# Validate wiki before extract
python skills/wur-guidelines/scripts/wur_graph_lint.py agents/

# Compile graph
python skills/wur-guidelines/scripts/wur_graph_extract.py agents/

# Query
python skills/wur-guidelines/scripts/wur_graph_query.py agents/ status --filter active
python skills/wur-guidelines/scripts/wur_graph_query.py agents/ facts --about roadmap/PHASE_1

# Wiki stats dashboard
python skills/wur-guidelines/scripts/wur_wiki_stats.py agents/

# Local consistency check
python skills/wur-guidelines/scripts/wur_meta_consistency.py .

# Create or refresh shared rules and a phase contract
python skills/wur-guidelines/scripts/wur_contract.py create --phase 1

# Create or refresh a single-WU contract inside the same phase file
python skills/wur-guidelines/scripts/wur_contract.py create --phase 1 --wu WU003

# Append returned report to the same contract file
python skills/wur-guidelines/scripts/wur_contract.py receive --phase 1 --report-file report.md

# End-to-end script tests
python -m unittest discover -s tests -v
```

## Contract files (wur_contract.py)

Use contracts when execution should happen outside the WUR wiki state. The contract
file is the boundary between WUR and an executor.

- `agents/` is the source-of-truth wiki.
- `contracts/rule.md` is the shared execution rule contract.
- `contracts/PHASE_{n}_CONTRACT.md` is the phase execution contract.
- Phase contracts contain task instructions, pending Work Units, explicit Allowed Read References, and returned execution reports.
- Do not create `contracts/outbox/` or `contracts/inbox/`.
- Do not create Phase Fix ledgers for new work; failed execution becomes another round inside the same contract.

`create` writes `contracts/rule.md`, reads `agents/roadmap/PHASE_{n}.md`, skips
WUs already `accepted` or `done`, and refreshes the phase task section while
preserving `## Execution Rounds And Reports`. Re-running it is safe.

The generated contract lists explicit Allowed Read References selected from
`agents/project/`, `agents/departments/`, and `agents/specialists/` when present.
Executors use only those listed paths to infer useful specialist lenses for the
work. They must not scan all of `agents/` or modify `agents/`.

`receive` appends a report to `## Execution Rounds And Reports` in the same
contract file. WUR then validates the report before updating `agents/`.

Executors working from the contract add or update Fix Round sections directly
inside `## Execution Rounds And Reports` when verification fails. This avoids a
second WUR helper command and keeps the contract as the single handoff ledger.

## Integration with /wur:wiki:graph

When these scripts are present in the project or on PATH, `/wur:wiki:graph extract` and
`/wur:wiki:graph lint` will invoke them directly instead of using LLM-executed instructions.
This ensures deterministic, reproducible results.

## Artifacts

| File | Location | Tracked? |
|---|---|---|
| nodes.jsonl | agents/graph/ | yes |
| edges.jsonl | agents/graph/ | yes |
| graph.sqlite | agents/graph/ | no — gitignored |
| graph.graphml | agents/graph/ | no — gitignored |
| summary.md | agents/graph/ | yes |
| last_extracted.md | agents/graph/ | yes |

## Lint checks (wur_graph_lint.py)

| # | Check | Level |
|---|---|---|
| 1 | Missing frontmatter field (`type`, `status`, `tags`) | ERROR |
| 2 | Invalid `type` value | ERROR |
| 3 | Invalid `status` value | ERROR |
| 4 | Tag format — must match `^[a-z][a-z0-9-]*$`, must be a list | ERROR |
| 5 | Broken wikilinks (`[[target]]` not resolved to a real file) | ERROR |
| 6 | Orphan pages (no inbound wikilinks) | WARN |
| 7 | Stale graph artifacts (`last_extracted.md` older than latest change) | WARN |
| 8 | Edge integrity — every edge subject/object must be a known node ID | ERROR |
| 9 | Missing `test_status` field in PHASE_*.md phase files | ERROR |
| 10 | Oversized pages (>400 lines warn, >800 lines error) | WARN/ERROR |

## Query commands (wur_graph_query.py)

```text
neighbors  --node <slug>             All directly connected nodes (in + out)
edges      --subject <slug>          Outgoing edges grouped by predicate
path       --from <slug> --to <slug> Shortest path between two nodes (BFS)
facts      --about <slug>            Node info + all typed relationships
status     --filter <value>          All pages with the given status
```

All commands accept `--json` for machine-readable output.

## Valid frontmatter values

**type:** `phase` · `fix-round` · `research` · `decision` · `note` · `report` · `department` · `specialist`

**status:** `planned` · `active` · `done` · `blocked` · `deferred` · `aborted`

**test_status** (PHASE files only): `pass` · `waived` · `fail` · `not-run`

## Stats output (wur_wiki_stats.py)

Shows: page counts by type/status, broken links, orphan pages, missing frontmatter, graph layer health (nodes/edges count, sqlite presence, freshness). Exit code always 0 (read-only).

## Meta consistency output (wur_meta_consistency.py)

Checks: stale phrases, event-name drift (`schema-upgrade` vs `wiki-upgrade`), missing `aborted` status, inconsistent script paths, and graph-pattern drift across extract/lint/stats scripts. Exit code 0 = no drift. Exit code 1 = one or more release-blocking inconsistencies.
