---
description: Ingest a source into the agents/ wiki.
argument-hint: "<source-path-or-description>"
---

Ingest the source into the `agents/` wiki using the `wur-guidelines` skill.

Source: $ARGUMENTS

1. Read `agents/SCHEMA.md` first if you haven't this session — it may define custom conventions.
2. Place the raw source in `agents/raw/` if it isn't already there. Use a slugified filename.
3. Read the source. Chunk-read if large — never load the whole thing if it would consume > 25% of context.
4. Briefly discuss key takeaways before writing — what stands out, what connects to existing pages.
5. Survey `agents/` to identify which existing pages this source touches; read each candidate to confirm.
6. Write the source-summary page in `agents/research/` with frontmatter:

   ```markdown
   ---
   type: research
   status: done
   tags: []
   source: {original-file-or-url}
   added: {YYYY-MM-DD}
   ---

   # {Source Title}

   > [[roadmap/ALL]] · [[index]]
   ```

   Surgically update touched pages with `str_replace`. Create new concept/entity pages in `agents/docs/` (each with at least one inbound `[[wikilink]]`) using frontmatter like:

   ```markdown
   ---
   type: note
   status: done
   tags: []
   informs: []
   ---
   ```

   Update `agents/index.md`:
   - add the research page under `## Research`
   - add any new docs page under `## Docs`

   Append one line to `agents/roadmap/log.md`:
   ```
   | {today} | wiki-add | {source slug} ingested into research/docs |
   ```

7. If `agents/graph/ontology.yaml` exists, mention that the derived graph is now stale and suggest running `/wur:wiki:graph extract`.

8. Tell me what you did: pages touched, pages created, contradictions flagged, follow-ups worth investigating.

If `agents/` does not exist, suggest running `/wur:init` first.
If `agents/` exists but the graph layer is missing, suggest `/wur:wiki:upgrade` when graph-aware querying or stats are desired.
