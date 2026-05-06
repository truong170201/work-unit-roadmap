---
description: Query the agents/ wiki — index-first navigation, synthesize answer with citations.
argument-hint: "<question>"
---

Answer the question from the `agents/` wiki using the `wur-guidelines` skill.

Question: $ARGUMENTS

1. Read `agents/SCHEMA.md` if you haven't this session.
2. Read `agents/index.md` — identify candidate pages from one-line summaries.
3. Read candidate pages. Follow promising `[[wikilinks]]`. Don't recursively chase every link.
4. If `agents/graph/nodes.jsonl` and `edges.jsonl` exist and the question is relational (dependencies, parent/child, verification coverage, what links to what), use the graph artifacts to shortlist relevant pages faster.
5. If needed, find backlinks: `grep -rl "\[\[<slug>\]\]" agents/`.
6. Synthesize the answer with `[[wikilink]]` citations to canonical agents/ pages you used. Use graph files only for navigation, never as the final citation target.
7. If the answer represents new connection-making, offer to file it back into `agents/docs/` as a synthesis note.
8. If `agents/` has no relevant content, say so plainly — don't confabulate. Suggest sources to ingest via `/wur:wiki:add`. If graph artifacts are missing but would help, suggest `/wur:wiki:upgrade` then `/wur:wiki:graph extract`.
