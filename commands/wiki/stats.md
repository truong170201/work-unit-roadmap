---
description: Show size, status, and graph health for the agents/ wiki.
argument-hint: ""
---

Report operational stats for the `agents/` wiki.

> **Script mode (preferred):** When `wur_wiki_stats.py` is available, run it directly:
> ```bash
> python skills/wur-guidelines/scripts/wur_wiki_stats.py agents/ [--json]
> ```
> This script produces a deterministic dashboard from actual file counts and timestamps. LLM-executed steps below are the fallback.

If `agents/` does not exist, stop — run `/wur:init` first.

1. Count pages by category:
   - phases (`agents/roadmap/PHASE_*.md`)
   - fix rounds (`agents/roadmap/FIX_*.md`)
   - research pages
   - docs pages (`decision` and `note`)
   - reports
2. Count statuses across graph pages:
   - `planned`
   - `active`
   - `done`
   - `blocked`
   - `deferred`
3. Report navigation health:
   - total `[[wikilinks]]`
   - orphan pages
   - pages missing required frontmatter (`type`, `status`, `tags`) — graph pages only
4. If `agents/graph/ontology.yaml` exists, also report graph-layer health:
   - whether `nodes.jsonl` and `edges.jsonl` exist (tracked)
   - whether `graph.sqlite` exists (binary, not tracked — rebuild with `/wur:wiki:graph extract`)
   - whether `summary.md` and `last_extracted.md` exist (tracked)
   - last extraction timestamp from `agents/graph/last_extracted.md`
   - whether the graph appears stale relative to recent changes in `agents/`
5. Present the result compactly, for example:

```text
agents/ wiki stats
- Phases: 3 (active: 1, done: 2)
- Fix rounds: 4 (active: 1, done: 3)
- Research: 6
- Docs/notes: 5
- Reports: 4
- Broken links: 0
- Orphans: 2
- Graph layer: enabled
- Last graph extract: 2026-05-08
- Graph freshness: stale (run /wur:wiki:graph extract)
```

This command is read-only. Do not mutate pages or graph artifacts.