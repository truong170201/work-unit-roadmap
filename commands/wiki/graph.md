---
description: Compile, lint, or query the agents/ typed graph layer.
argument-hint: "extract | lint | neighbors --node <slug> | edges --subject <slug> | path --from <slug> --to <slug> | facts --about <slug>"
---

> **Recommended:** Use the bundled Python scripts for deterministic results:
> ```bash
> python skills/wur-guidelines/scripts/wur_graph_lint.py    agents/   # validate first
> python skills/wur-guidelines/scripts/wur_graph_extract.py agents/   # then extract
> python skills/wur-guidelines/scripts/wur_graph_query.py   agents/ facts --about roadmap/PHASE_1
> ```
> Requires: Python 3.10+ and `pip install pyyaml`. When scripts are available, prefer them over LLM-executed extraction — scripts are deterministic and produce real `graph.sqlite`.
> Fall back to LLM-executed instructions below only when scripts cannot be run.

Operate on the `agents/graph/` layer for the `agents/` wiki.

If `agents/` does not exist, stop — run `/wur:init` first.
If `agents/graph/ontology.yaml` does not exist, suggest `/wur:wiki:upgrade` first.

Markdown under `agents/` remains canonical. The graph is a derived layer for navigation, relational queries, and validation. If the graph files are stale or missing, rebuild them from the canonical pages.

Supported actions:

- `extract`
- `lint`
- `neighbors --node <slug>`
- `edges --subject <slug>`
- `path --from <slug> --to <slug>`
- `facts --about <slug>`

## `extract`

1. Read `agents/SCHEMA.md`, `agents/index.md`, and `agents/graph/ontology.yaml`.
2. Walk graph pages under `agents/`:
   - `agents/roadmap/PHASE_*.md`
   - `agents/roadmap/FIX_*.md`
   - `agents/research/*.md`
   - `agents/docs/*.md`
   - `agents/reports/*.md`
3. For each page, derive one node with:
   - `id` — canonical path-like slug such as `roadmap/PHASE_1`
   - `type`
   - `status`
   - `title`
   - `tags`
   - key metadata (`phase`, `opened`, `closed`, etc. when present)
4. Derive edges from:
   - frontmatter relationships like `depends_on`, `parent`, `verifies`, `informs`
   - canonical `[[wikilinks]]` inside page bodies
5. Write derived artifacts under `agents/graph/`:
   - `nodes.jsonl` — one node per line (tracked in git for graph diffs)
   - `edges.jsonl` — one edge per line (tracked in git for graph diffs)
   - `graph.sqlite` — relational database for fast typed-edge queries (gitignored — binary)
   - `graph.graphml` — for Gephi / yEd visualisation (gitignored — large)
   - `summary.md` — human-readable extract summary
   - `last_extracted.md` — timestamp + source file count
6. Do not rewrite canonical pages during extract.
7. Append one line to `agents/roadmap/log.md`:
   ```
   | {today} | wiki-graph-extract | {node_count} nodes, {edge_count} edges |
   ```

## `lint`

1. Read `agents/graph/ontology.yaml`, `nodes.jsonl`, `edges.jsonl`, `graph.sqlite` (if present), and `last_extracted.md` if present.
   > Staleness is determined by comparing the timestamp recorded in `last_extracted.md` against the most recent modification time of any file under `agents/`.
2. Validate:
   - every edge points to existing nodes
   - every node type is allowed by the ontology
   - every edge type is allowed by the ontology
   - `parent` edges point from `fix-round` → `phase`
   - `depends_on` edges connect valid graph page IDs
   - every `tags` value on each node matches the `tag_rules.format` regex from the ontology
   - `tags` field is a list, not a scalar (per `tag_rules.type`)
   - graph artifacts are not older than the most recent relevant change in `agents/`
3. Present findings as proposed fixes. Never silently rewrite canonical pages.
4. If graph artifacts are stale, recommend re-running `/wur:wiki:graph extract`.

## `neighbors --node <slug>`

Return directly connected nodes for the given canonical slug.

## `edges --subject <slug>`

Return outgoing edges for the given canonical slug, grouped by edge type.

## `path --from <slug> --to <slug>`

Return the shortest meaningful path between two canonical slugs if one exists.

## `facts --about <slug>`

Return the node summary plus its typed relationships. Cite the canonical `agents/` pages used to derive the answer.

When answering any graph query, use graph files for navigation but cite canonical pages from `agents/`, not the derived JSONL/GraphML files.