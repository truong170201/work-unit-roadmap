---
description: Health check on the wiki — structural + semantic, propose fixes, never silent-edit.
argument-hint: ""
---

Lint the wiki using the `wur-guidelines` skill.

> **Script mode (preferred):** When `wur_graph_lint.py` is available, run it directly for deterministic results:
> ```bash
> python skills/wur-guidelines/scripts/wur_graph_lint.py agents/ [--json]
> ```
> Exit code 0 = no errors. Exit code 1 = errors found. LLM-executed steps below are the fallback when the script cannot run.

1. Read `agents/SCHEMA.md` — it may declare additional lint rules.
2. Structural pass on `agents/` — check for:
   - Orphan graph pages (no inbound `[[wikilinks]]`)
   - Broken wikilinks (pointing to nonexistent pages)
   - Graph pages missing required frontmatter (`type`, `status`, `tags`)
   - Oversized pages (> 800-line hard cap, > 400-line soft cap)
   - Stale pages (status `active` but no commits touching them in the last 30 days)
   - **Tag violations** (errors):
     - `tags:` field missing on a graph page
     - `tags:` field is a scalar instead of a list
     - Any tag does not match `^[a-z][a-z0-9-]*$` (uppercase, spaces, or special chars)
   - **Tag warnings** (not blocking):
     - Unknown tags not found in the predefined vocabulary (`api`, `auth`, `data`, `infra`, `ui`, `security`, `performance`, `breaking-change`, `migration`, `risky`, `spike`, `research`, `external`, `archived`) and not declared in `agents/SCHEMA.md` under `## Project Tags`
   - **Phase file size**:
     - warn if any `PHASE_*.md` or `FIX_*.md` exceeds 400 lines
     - error if exceeds 800 lines — propose moving the Completion Log section to `agents/reports/PHASE_{n}-completion-log.md` and replacing it with a single link
   - **index.md coverage gaps** — for every graph page not listed in `agents/index.md`:
     - auto-generate the missing entry (do not ask; add directly to proposal)
     - group by section: PHASE_*/FIX_* → `## Roadmap`, research/ → `## Research`, docs/ → `## Docs`, reports/ → `## Reports`
     - present as a single consolidated diff for user approval
3. Semantic pass — read recently-updated pages and highly-linked hubs:
   - Contradictions between pages
   - Claims superseded by newer sources
   - Concepts mentioned but lacking their own page
   - Cross-references that should exist but don't
4. If `agents/graph/ontology.yaml` exists, also run graph-aware checks:
   - `nodes.jsonl` and `edges.jsonl` present (tracked — missing means extract has never run)
   - `summary.md` and `last_extracted.md` present (tracked — used for staleness check)
   - `graph.sqlite` present (binary, gitignored — note if absent but do not require)
   - graph artifacts stale: compare `last_extracted.md` timestamp against most recent change in `agents/`
   - unknown node types or edge types relative to the ontology
   - invalid `parent`, `depends_on`, `verifies`, or `informs` relationships
5. Present findings grouped by severity:
   - **Errors** (require fix before next WU): broken wikilinks, missing required frontmatter, invalid type/status/tags format
   - **Warnings** (fix soon): orphan pages, stale graph, unknown tags, oversized pages approaching limit
   - **Auto-repairs** (ready to apply with one approval): index.md missing entries, Completion Log split when over 600 lines
   Never apply silently — present the full diff and wait for user approval.
6. Append one line to `agents/roadmap/log.md`: `| {today} | wiki-lint | {N} structural, {M} semantic |`

Run on a cadence: structural after every ~5 ingests, semantic weekly or after ~20 ingests. When the graph layer exists, re-run `/wur:wiki:graph extract` after approved fixes that affect graph pages.
