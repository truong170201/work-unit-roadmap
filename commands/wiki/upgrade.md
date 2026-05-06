---
description: Upgrade the agents/ wiki with graph-layer files and conventions.
argument-hint: ""
---

Upgrade the existing `agents/` wiki with graph-layer support.

The `agents/` folder already exists after `/wur:init`. This command does **not** create a second wiki. It adds optional graph-aware files and normalizes conventions so `/wur:wiki:add`, `/wur:wiki:ask`, `/wur:wiki:lint`, `/wur:wiki:stats`, and `/wur:wiki:graph` can work coherently.

If `agents/` does not exist, stop — run `/wur:init` first.

1. Ensure these files exist and do not overwrite user content blindly:
   - `agents/SCHEMA.md`
   - `agents/index.md`
   - `agents/graph/ontology.yaml`
   - `agents/graph/README.md`
   - `agents/graph/.gitignore`

2. If `agents/SCHEMA.md` is missing graph sections, merge them in manually (do not replace the whole file). Check for each section and append if absent:

   - `## Graph Scope`
   - `## Canonical Wikilink Syntax`
   - `## Typed Graph Relationships`
   - `## Tag Conventions` — if absent, append the full tag conventions block from the SCHEMA.md template in `/wur:init`

   ```markdown
   ## Graph Scope

   Graph pages (must have frontmatter):
   - `agents/roadmap/PHASE_*.md`
   - `agents/roadmap/FIX_*.md`
   - `agents/research/*.md`
   - `agents/docs/*.md`
   - `agents/reports/*.md`

   System pages (may omit frontmatter):
   - `agents/project/PHILOSOPHY.md`
   - `agents/project/USAGE.md`
   - `agents/roadmap/ALL.md`
   - `agents/roadmap/log.md`
   - `agents/SCHEMA.md`
   - `agents/index.md`
   - `agents/references/*`
   - `agents/raw/*`

   ## Canonical Wikilink Syntax
   Use path-style wikilinks rooted at `agents/`, for example:
   - `[[roadmap/PHASE_1]]`
   - `[[roadmap/FIX_P1_device-r1]]`
   - `[[project/PHILOSOPHY]]`
   - `[[docs/ADR_001]]`

   Do not use basename-only links like `[[PHASE_1]]`.

   ## Typed Graph Relationships
   - `depends_on` — one phase depends on another
   - `parent` — a fix round belongs to a phase
   - `verifies` — a report verifies a phase or fix round
   - `informs` — research or docs inform a phase, decision, or report
   ```

3. Write `agents/graph/ontology.yaml` if missing:

   ```yaml
   version: 1

   # How page `type` maps to a graph node_type.
   # Explicit override: set `graph.node_type` in page frontmatter.
   node_types:
     phase:
       maps_from:
         type: phase
     fix-round:
       maps_from:
         type: fix-round
     research:
       maps_from:
         type: research
     decision:
       maps_from:
         type: decision
     note:
       maps_from:
         type: note
     report:
       maps_from:
         type: report

   # Predicates allowed in typed edges.
   # Implicit predicates are emitted by the extractor automatically.
   # Add domain-specific predicates in your project under # --- Project predicates ---
   predicates:

     # --- Implicit predicates (emitted automatically, no frontmatter needed) ---
     mentions:
       subject_types: ["*"]
       object_types: ["*"]
       requires_evidence: false
       description: "Low-specificity edge from body [[wikilinks]]. Navigation only."

     # --- Typed structural predicates ---
     depends_on:
       subject_types: [phase, fix-round, research, note]
       object_types: [phase]
       requires_evidence: false
       description: "Phase depends on another phase being done first."
     parent:
       subject_types: [fix-round]
       object_types: [phase]
       requires_evidence: false
       description: "Fix-round belongs to a phase."
     verifies:
       subject_types: [report]
       object_types: [phase, fix-round]
       requires_evidence: false
       description: "Report verifies a phase or fix round."
     informs:
       subject_types: [research, note, decision]
       object_types: [phase, decision, report, note]
       requires_evidence: false
       description: "Research, notes, or decisions inform another graph page."

     # --- Project predicates (add domain-specific ones here) ---
     # example:
     # introduces:
     #   subject_types: [phase]
     #   object_types: [note]
     #   requires_evidence: true
     #   description: "Phase introduces a new concept or decision."

   status_values:
     - planned
     - active
     - done
     - blocked
     - deferred
     - aborted

   predefined_tags:
     scope:
       - api
       - auth
       - data
       - infra
       - ui
       - security
       - performance
     risk:
       - breaking-change
       - migration
       - risky
     process:
       - spike
       - research
     source:
       - external
       - archived

   tag_rules:
     format: "^[a-z][a-z0-9-]*$"
     type: list
     unknown_tags: warning
     custom_tags_section: "## Project Tags"
   ```

4. Write `agents/graph/README.md` if missing:

   ```markdown
   # agents/graph

   Derived graph layer for the canonical `agents/` wiki.

   Canonical source of truth:
   - markdown pages under `agents/`

   Derived artifacts:
   | File | Tracked? | Description |
   |---|---|---|
   | `nodes.jsonl` | ✅ yes | One node per line — enables graph diffs in PRs |
   | `edges.jsonl` | ✅ yes | One edge per line — enables graph diffs in PRs |
   | `graph.sqlite` | ❌ gitignored | Relational DB for fast typed-edge queries |
   | `graph.graphml` | ❌ gitignored | For Gephi / yEd visualisation |
   | `summary.md` | ✅ yes | Human-readable extract summary |
   | `last_extracted.md` | ✅ yes | Timestamp + source file count |

   Build or refresh with:
   - `/wur:wiki:graph extract`

   Validate with:
   - `/wur:wiki:graph lint`
   - `/wur:wiki:lint`
   ```

5. Write `agents/graph/.gitignore` if missing:

   ```text
   # Binary / large generated artifacts — rebuild with wiki:graph extract
   graph.sqlite
   graph.graphml
   ```

   `nodes.jsonl` and `edges.jsonl` are intentionally tracked — they enable graph diffs in PRs and let agents query the graph without running an extract first.

6. Ensure `agents/index.md` has a `## Graph` section:

   ```markdown
   ## Graph
   - [[graph/README]] — derived graph layer for agents/
   ```

7. Append one line to `agents/roadmap/log.md`:

   ```
   | {today} | wiki-upgrade | graph layer enabled for agents/ |
   ```

8. Do not run graph extraction automatically. Mention the next step explicitly:
   - Run `/wur:wiki:graph extract` when you want derived graph artifacts.
   - Run `/wur:wiki:stats` for wiki and graph health.
   - Run `/wur:wiki:lint` for structural/semantic checks, with graph-aware checks when the graph layer exists.
