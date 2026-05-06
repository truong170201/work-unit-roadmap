# WUR Graph Scripts

Real Python implementations for `agents/` graph operations.
Require: Python 3.10+ and PyYAML (`pip install pyyaml`).

## Scripts

| Script | Purpose |
|---|---|
| `wur_graph_extract.py` | Compile agents/ into nodes.jsonl, edges.jsonl, graph.sqlite |
| `wur_graph_lint.py` | Validate frontmatter, wikilinks, edge integrity, tag format |
| `wur_graph_query.py` | Query graph — neighbors, edges, path, facts, status filter |
| `wur_wiki_stats.py` | Dashboard: page counts, status, broken links, graph freshness |
| `wur_meta_consistency.py` | Local consistency checker for docs/spec/script drift |

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

# End-to-end script tests
python -m unittest discover -s tests -v
```

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
| 9 | Missing `test_status` field in PHASE_*.md | ERROR |
| 10 | Oversized pages (>400 lines warn, >800 lines error) | WARN/ERROR |

## Query commands (wur_graph_query.py)

```
neighbors  --node <slug>             All directly connected nodes (in + out)
edges      --subject <slug>          Outgoing edges grouped by predicate
path       --from <slug> --to <slug> Shortest path between two nodes (BFS)
facts      --about <slug>            Node info + all typed relationships
status     --filter <value>          All pages with the given status
```

All commands accept `--json` for machine-readable output.

## Valid frontmatter values

**type:** `phase` · `fix-round` · `research` · `decision` · `note` · `report`

**status:** `planned` · `active` · `done` · `blocked` · `deferred` · `aborted`

**test_status** (PHASE files only): `pass` · `waived` · `fail` · `not-run`

## Stats output (wur_wiki_stats.py)

Shows: page counts by type/status, broken links, orphan pages, missing frontmatter, graph layer health (nodes/edges count, sqlite presence, freshness). Exit code always 0 (read-only).

## Meta consistency output (wur_meta_consistency.py)

Checks: stale phrases, event-name drift (`schema-upgrade` vs `wiki-upgrade`), missing `aborted` status, inconsistent script paths, and graph-pattern drift across extract/lint/stats scripts. Exit code 0 = no drift. Exit code 1 = one or more release-blocking inconsistencies.
