---
description: Upgrade an existing agents/ workspace to the schema this WUR plugin expects. Treat current state as raw input — never clobber.
argument-hint: ""
---

Upgrade the `agents/` workspace using the `wur-guidelines` skill.

This is the **schema migration** path. It is distinct from `/wur:wiki:upgrade` (which only adds the optional graph layer to an existing schema).

## Contract

| Detected state | Action |
|---|---|
| `agents/` does not exist | Stop. Run `/wur:init` first. |
| `agents/SCHEMA.md` missing or no `schema_version` frontmatter | Backfill `schema_version: 1`, then run structural + content migration. |
| `schema_version` matches plugin's latest | Run structural + content migration. No-op if already compliant. |
| `schema_version` is older than plugin's latest | Plan migrations stepwise (1→2, 2→3, …). Confirm with user. Run. Commit each step as a Tiny WU. |
| `schema_version` is newer than plugin's latest | Refuse. Plugin is too old for this workspace. |

The plugin's **latest schema** for this version of WUR is **`1`** (the original `wiki` layout — `agents/{project,roadmap,docs,research,reports,references,raw,graph}` with the conventions in `agents/SCHEMA.md`).

## Invariants (must hold across every migration)

A migration is **only** valid if it preserves the validity of existing state. These are non-negotiable:

1. **All existing phases keep working.** Every `agents/roadmap/PHASE_*.md` (`status: active`, `done`, `aborted`, `blocked`, `deferred`) must remain readable, and references from `ALL.md` and `index.md` must still resolve.
2. **All existing Work Unit IDs remain valid.** `WU-P{n}-{unit}`, `WU-TW-{k}`, `WU-P{n}-(close|fix|abort)` strings already in commit history are forever — a migration cannot rename or invalidate them.
3. **Activity log is append-only.** `agents/roadmap/log.md` is never rewritten; the migration only appends.
4. **Git history is preserved.** No filter-branch, no `git rebase --root`, no force-push by the migration. Rollback is `git revert` of the migration commits.
5. **No data loss.** A page may be moved or transformed, never deleted. If a target schema removes a concept, leave a stub at the old path with a `> moved to [[new/path]]` line for one schema generation.
6. **Status values cannot regress.** A phase that was `done` cannot become `planned` after migration, nor can `aborted` become `active`.

If any step would break one of these, abort the migration and surface a `## Manual steps` section in the migration page so the user resolves it deliberately.

`/wur:upgrade` is **not** an escape hatch. It cannot be used to "reset" a misbehaving project — that is what `/wur:abort` (per phase) and a cold human decision are for.

## Procedure

1. If `agents/` does not exist, stop and instruct the user to run `/wur:init`.

2. Refuse to run from inside a worktree — migrations belong on the default branch only:

   ```bash
   if git rev-parse --git-dir | grep -q '/worktrees/'; then
     echo "WUR: /wur:upgrade must run from the main repo, not a worktree"
     exit 1
   fi
   ```

3. Refuse if any phase is active (migrations could conflict with phase work). Read `agents/roadmap/ALL.md`:

   ```bash
   active=$(awk '
     BEGIN { IGNORECASE=1 }
     {
       sub(/^[[:space:]]*[-*][[:space:]]*/, "")
       if (tolower($0) ~ /^active phase:/) {
         sub(/^[^:]*:[[:space:]]*/, "")
         gsub(/[[:space:]]+$/, "")
         print; exit
       }
     }
   ' agents/roadmap/ALL.md)
   if [ -n "$active" ] && [ "$active" != "none" ]; then
     echo "WUR: cannot upgrade while phase $active is active. Run /wur:done or /wur:abort first."
     exit 1
   fi
   ```

4. Verify clean working tree (no uncommitted changes that could conflict with the migration):

   ```bash
   if [ -n "$(git status --porcelain)" ]; then
     echo "WUR: working tree dirty — commit or stash before /wur:upgrade"
     exit 1
   fi
   ```

5. Detect current schema version. Read the YAML frontmatter at the top of `agents/SCHEMA.md`:

   ```bash
   current_schema=$(awk '
     /^---$/ { if (++n == 1) next; else exit }
     n == 1 && /^schema_version:[[:space:]]*[0-9]+[[:space:]]*$/ {
       sub(/^schema_version:[[:space:]]*/, "")
       gsub(/[[:space:]]+$/, "")
       print
       exit
     }
   ' agents/SCHEMA.md 2>/dev/null)
   ```

   `schema_version` must be an unquoted integer. Trailing whitespace is allowed; quotes, lists, or expressions are not. If `agents/SCHEMA.md` is missing entirely, treat as `legacy` (pre-versioning).

6. Compare against plugin's latest (`1`) and branch:

   - **`current_schema` is empty / `legacy`** — workspace was created before schema versioning. Backfill:
     - Insert YAML frontmatter `---\nschema_version: 1\n---` at the top of `agents/SCHEMA.md` (create the file if missing, using the SCHEMA.md template from `/wur:init`).
     - Append to `agents/roadmap/log.md`:
       `| {today} | schema-upgrade | backfilled schema_version: 1 |`
     - Commit on the default branch (worktrees are blocked by step 2):
       `git commit -am "WU-TW-{k}: backfill schema_version to 1"`
     - Continue to step 7.

   - **`current_schema == 1`** — already on the latest schema this plugin knows about. Continue to step 7 (structural + content migration still runs).

   - **`current_schema < 1`** — impossible given `1` is the floor. Refuse and report a corrupted SCHEMA.md.

   - **`current_schema > 1`** — workspace was upgraded by a newer plugin. Refuse:

     ```text
     WUR: agents/ uses schema_version {current_schema}, but this plugin only knows up to 1.
     Upgrade the plugin (or downgrade the workspace deliberately via your migration history).
     ```

   - **`current_schema` between 1 and plugin-latest exclusive** — N/A while latest = 1. Reserved for future plugin versions, which will list per-step migration scripts under `skills/wur-guidelines/references/migrations/v{from}-to-v{to}.md`. Each step:
     1. Snapshot is unnecessary — git is the snapshot. Clean working tree was already verified in step 4.
     2. Read the migration page at `skills/wur-guidelines/references/migrations/v{from}-to-v{to}.md`.
     3. Treat the **current** state of `agents/` as raw input. Read each old-shape page, transform to the new shape, write the new page. Never overwrite without first reading.
     4. Update `agents/SCHEMA.md` frontmatter to `schema_version: {to}`.
     5. Append to `agents/roadmap/log.md`:
        `| {today} | schema-upgrade | migrated schema {from} → {to} |`
     6. Commit as one Tiny WU per migration step:
        `git commit -am "WU-TW-{k}: migrate agents/ schema {from} → {to}"`

     Repeat until `current_schema == plugin-latest`.

7. **Create backup tag** — before making any structural or content changes, tag the current HEAD as a safety net:

   ```bash
   backup_tag="wur-pre-upgrade-$(date +%Y%m%d-%H%M%S)"
   git tag "$backup_tag"
   echo "WUR: backup tag created → $backup_tag"
   echo "WUR: to restore: git checkout $backup_tag -- agents/"
   ```

   The backup tag is a pointer to the current clean commit. It costs nothing and allows instant rollback. It is deleted in step 11 only after verification passes.

8. **Structural completeness** — create missing folders and files. Never overwrite anything that already exists.

   Required folders (create if absent, leave empty):
   ```text
   agents/docs/
   agents/research/
   agents/reports/
   agents/references/
   agents/raw/
   agents/project/
   agents/roadmap/
   ```

   Required files — create only if the file does not yet exist:

   | File | Template source |
   |---|---|
   | `agents/SCHEMA.md` | Full schema-1 template (see below) |
   | `agents/index.md` | Index template (see below) |
   | `agents/roadmap/log.md` | Log template (see below) |
   | `agents/roadmap/ALL.md` | Template from `/wur:init` step 11 |
   | `agents/project/PHILOSOPHY.md` | Template from `/wur:init` step 9 |
   | `agents/project/USAGE.md` | Template from `/wur:init` step 10 |

   **`agents/SCHEMA.md`** template (use if file is absent):
   ```markdown
   ---
   schema_version: 1
   ---

   # agents/ Wiki Schema

   > Schema version: **1** (the `wiki` layout). When the WUR plugin ships a newer
   > schema, run `/wur:upgrade` to migrate. Never hand-edit `schema_version`.

   ## Page Types
   | Type | Location | Description |
   |---|---|---|
   | `phase` | `agents/roadmap/PHASE_*.md` | One execution phase |
   | `fix-round` | `agents/roadmap/PHASE_*_FIX.md` | Consolidated fix ledger for a phase |
   | `fix-round` | `agents/roadmap/FIX_*.md` | Legacy bug fix batch file, readable but not preferred for new work |
   | `research` | `agents/research/*.md` | Ingested external source or analysis |
   | `decision` | `agents/docs/*.md` | Architectural decision record |
   | `note` | `agents/docs/*.md` | Durable note, synthesis, or concept page |
   | `report` | `agents/reports/*.md` | Verification or completion report |

   ## Status Values
   `planned` · `active` · `done` · `blocked` · `deferred` · `aborted`

   ## Work Unit Status Lifecycle
   `planned -> active -> ready-for-review -> accepted -> done`

   Agents may set `planned`, `active`, `ready-for-review`, `blocked`, and `deferred`.
   Only the client may set `accepted` or `done`.

   ## Graph Scope
   Graph pages (must have frontmatter):
   - `agents/roadmap/PHASE_*.md`
   - `agents/roadmap/PHASE_*_FIX.md`
   - `agents/roadmap/FIX_*.md` (legacy)
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

   ## Required Frontmatter (graph pages)
   - `type` — one of the page types above
   - `status` — one of the status values above
   - `tags` — YAML list of lowercase kebab-case strings, even if empty (`tags: []`)

   ## Graph Conventions
   - `depends_on: ["[[roadmap/PHASE_1]]"]` — dependency on another phase (also valid from fix-round, research, note)
   - `parent: "[[roadmap/PHASE_1]]"` — fix-round belongs to a phase
   - `verifies: ["[[roadmap/PHASE_1]]"]` — report verifies a phase or fix round
   - `informs: ["[[roadmap/PHASE_1]]"]` — research or docs inform another graph page
   - Use path-style wikilinks like `[[roadmap/PHASE_1]]`, not `[[PHASE_1]]`
   - Every `[[wikilink]]` creates an edge in Obsidian graph view

   ## Tag Conventions

   `tags:` is a YAML list of lowercase kebab-case strings. Always a list, even when empty (`tags: []`). Never a string.

   ### Format rule
   ```yaml
   tags: [auth, breaking-change, spike]   # correct
   tags: [Auth, Breaking Change]            # wrong — uppercase, spaces
   tags: auth                              # wrong — must be a list
   ```

   ### Predefined vocabulary

   Use these names before inventing new ones. Consistent names make graph filtering useful.

   **Scope** — what area of the system this touches:
   | Tag | Meaning |
   |---|---|
   | `api` | External API contract or boundary |
   | `auth` | Authentication or authorization |
   | `data` | Data model, schema, or migration |
   | `infra` | Infrastructure, environment, or deployment |
   | `ui` | User interface |
   | `security` | Security-sensitive change |
   | `performance` | Performance impact |

   **Risk** — signal extra caution:
   | Tag | Meaning |
   |---|---|
   | `breaking-change` | Introduces a breaking change |
   | `migration` | Data or structural migration |
   | `risky` | High-risk, needs extra review |

   **Process** — how the work was done:
   | Tag | Meaning |
   |---|---|
   | `spike` | Exploratory phase — waived tests acceptable |
   | `research` | Knowledge-gathering, no production code |

   **Source** — for `research/` pages only:
   | Tag | Meaning |
   |---|---|
   | `external` | Ingested from external URL or file |
   | `archived` | Source is no longer maintained |

   Custom project-specific tags are allowed. They must be lowercase kebab-case and documented in this file under a `## Project Tags` section.

   ### Lint rules (checked by `/wur:wiki:lint`)
   - Every tag must match `^[a-z][a-z0-9-]*$`
   - `tags:` must be a list, not a scalar
   - Unknown tags (not in predefined vocabulary and not in `## Project Tags`) are flagged as warnings, not errors

   Run `/wur:wiki:upgrade` to add `agents/graph/ontology.yaml`, `agents/graph/README.md`, and the full graph layer.
   ```

   **`agents/index.md`** template (use if file is absent):
   ```markdown
   # agents/ Index

   > One line per page. Update when adding or closing pages.

   ## Project
   - [[project/PHILOSOPHY]] — project mission, principles, non-goals
   - [[project/USAGE]] — how to run, test, build, verify

   ## Roadmap
   - [[roadmap/ALL]] — master dashboard: phases, status, commit index
   - [[roadmap/log]] — append-only activity journal
   ```

   **`agents/roadmap/log.md`** template (use if file is absent):
   ```markdown
   # Activity Log

   Append-only. One line per event. Never edit past entries.

   | Date | Event | Detail |
   |---|---|---|
   | {today} | workspace-init | created by /wur:upgrade structural check |
   ```

9. **Content migration** — for each existing file that already existed before this run, read its current content and upgrade it to schema compliance. Never delete content; only add what is missing.

   ### `agents/SCHEMA.md` (if it already existed)

   Check for each required section. Append any section that is missing:

   | Required section | Append if absent |
   |---|---|
   | `## Page Types` | Full table with all 6 types |
   | `## Status Values` | Status values line |
   | `## Graph Scope` | Graph/system pages lists |
   | `## Required Frontmatter (graph pages)` | type + status + tags description |
   | `## Graph Conventions` | Wikilink syntax + typed edge list |
   | `## Tag Conventions` | Format rule + predefined vocabulary + lint rules |

   If `schema_version` frontmatter is present but missing the closing `---`, fix the frontmatter block. Never remove existing content.

   ### `agents/roadmap/ALL.md` (if it already existed)

   Check for each required section. Append any section that is missing, with an empty-row template:

   | Required section | Append if absent |
   |---|---|
   | `## Objective` | `{Concrete project objective — fill in before first phase.}` |
   | `## 80/20 Focus` | Three bullet placeholders |
   | `## Current Status` | Five fields: Default branch, Active phase, Active Work Unit, Latest completed unit, Blockers |
   | `## Phases` | Table header only |
   | `## Commit Index` | Table header only |
   | `## Operating Rules` | Four canonical rules |

   Do not modify any section that already exists — append only.

   ### `agents/index.md` (if it already existed)

   - Ensure `## Project` section exists with entries for `PHILOSOPHY` and `USAGE`.
   - Ensure `## Roadmap` section exists with entries for `ALL` and `log`.
   - For every graph page found under `agents/` (`PHASE_*.md`, `PHASE_*_FIX.md`, legacy `FIX_*.md`, `research/*.md`, `docs/*.md`, `reports/*.md`), check if it appears in `index.md`. If not, append it under the correct section:
     - `PHASE_*.md` / `PHASE_*_FIX.md` / legacy `FIX_*.md` → `## Roadmap`
     - `research/*.md` → `## Research` (create section if absent)
     - `docs/*.md` → `## Docs` (create section if absent)
     - `reports/*.md` → `## Reports` (create section if absent)

   ### Graph pages: `PHASE_*.md`, `PHASE_*_FIX.md`, legacy `FIX_*.md`, `research/*.md`, `docs/*.md`, `reports/*.md`

   For each graph page, read the file and check for YAML frontmatter (file must start with `---`).

   **If no frontmatter exists** — prepend a minimal frontmatter block. Infer values from path:

   | Path pattern | `type` | `status` default |
   |---|---|---|
   | `roadmap/PHASE_*_FIX.md` | `fix-round` | read from file body or `active` |
   | `roadmap/PHASE_*.md` | `phase` | read from file body (`Status:` field) or `planned` |
   | `roadmap/FIX_*.md` | `fix-round` | legacy; read from file body or `active` |
   | `research/*.md` | `research` | `done` |
   | `docs/*.md` | `note` | `done` |
   | `reports/*.md` | `report` | `done` |

   Prepend — use the appropriate template for the path:

   For `roadmap/PHASE_*.md`:
   ```markdown
   ---
   type: phase
   status: {inferred}
   tags: []
   test_status: not-run
   test_waive_reason: null
   ---
   ```

   For all other graph pages:
   ```markdown
   ---
   type: {inferred}
   status: {inferred}
   tags: []
   ---
   ```

   **If frontmatter exists but is missing `type`** — add `type: {inferred}` inside the existing frontmatter block.

   **If frontmatter exists but is missing `status`** — add `status: {inferred}` inside the existing frontmatter block.

   **If frontmatter exists but is missing `tags`** — add `tags: []` inside the existing frontmatter block.

   **If frontmatter exists but is missing `test_status` (PHASE files only)** — add `test_status: not-run` and `test_waive_reason: null` inside the existing frontmatter block.

   **Never change a `type` or `status` value that already exists.** Only add what is absent.

   ### `agents/roadmap/log.md` (if it already existed)

   Append-only — never rewrite or remove existing entries. Do not append any entry here — logging happens only at step 11 (completion).

   ### `agents/project/PHILOSOPHY.md` and `agents/project/USAGE.md`

   Do not modify these files if they already exist and have content. They are human-authored. If a file exists but is empty (0 bytes or whitespace only), fill it with the template from `/wur:init` steps 9–10.

10. **Verification** — after all structural and content changes, verify the migrated workspace before committing.

    Run each check and collect failures into a list:

    **Link integrity** — for every `[[wikilink]]` found in any file under `agents/`:
    - Resolve the path relative to `agents/` (e.g. `[[roadmap/PHASE_1]]` → `agents/roadmap/PHASE_1.md`)
    - Check the file exists on disk
    - Collect every broken link: `{source file} → [[{link}]] (not found)`

    **Frontmatter completeness** — for every graph page:
    - Check `type` is present and is one of the 6 valid types
    - Check `status` is present and is one of the 5 valid values
    - Check `tags` is present and is a list (not a scalar)
    - Collect every violation: `{file}: missing {field}` or `{file}: invalid {field} value '{value}'`

    **Index coverage** — for every graph page under `agents/`:
    - Check it appears in `agents/index.md`
    - Collect every missing entry: `{file} not listed in index.md`

    **Tag validation** — for every graph page with a `tags:` field:
    - Check `tags:` is a list, not a scalar
    - Check every tag matches `^[a-z][a-z0-9-]*$`
    - Collect format errors: `{file}: tags must be a list` or `{file}: invalid tag '{tag}' (must be lowercase kebab-case)`
    - Collect unknown-tag warnings: `{file}: unknown tag '{tag}' — add to ## Project Tags in SCHEMA.md or use a predefined tag`

    **Required sections** — for `agents/SCHEMA.md` and `agents/roadmap/ALL.md`:
    - Check each required `##` section heading is present
    - Collect every missing section: `{file}: missing section '{heading}'`

    **Decision**:
    - If zero failures → proceed to step 11.
    - If any failures remain → **do not commit**. Report the full failure list. Instruct the user which items require manual attention. Do not delete the backup tag — leave it so the user can restore if needed:
      ```
      WUR: verification failed. Backup preserved at tag: {backup_tag}
      To restore: git checkout {backup_tag} -- agents/
      Manual fixes required (see list above). Re-run /wur:upgrade after fixing.
      ```

11. **Commit and cleanup** — only reached when verification passes.

    Commit all changes made in steps 8–9 as a single Tiny WU:
    ```bash
    git add agents/
    git commit -m "WU-TW-{k}: upgrade agents/ workspace to schema-1 compliance"
    ```

    Append to `agents/roadmap/log.md` (include in the same commit above — stage before committing):
    ```
    | {today} | schema-upgrade | schema-1 compliance verified — structural + content migration complete |
    ```

    After the commit succeeds, delete the backup tag:
    ```bash
    git tag -d "$backup_tag"
    echo "WUR: backup tag removed — upgrade complete"
    ```

    If nothing changed in steps 8–9 (workspace was already fully compliant), skip the commit but still delete the backup tag and report: no-op.

12. Run `/wur:wiki:lint` and report findings (broken wikilinks are highest priority). If `agents/graph/` exists, remind the user that `/wur:wiki:graph extract` is needed because derived artifacts may now be stale.

## Why "treat current as raw"

The first published architecture (the `wiki` layout, schema `1`) is the canonical raw form for **every** future migration. A new plugin version never assumes the workspace is already in its target shape — it always reads the old shape and transforms it. This means:

- An old `agents/` is never lost, only transformed.
- Migration scripts are unidirectional (`{from}→{to}`); rollback is via `git revert`.
- `schema_version` is the only authoritative marker. File layout, page count, or naming conventions cannot be inferred — they must be derived from the schema map for that version.

This is also why **`/wur:init` refuses to run on an existing `agents/`**: only `/wur:upgrade` is allowed to touch a populated workspace.

## Relationship to `/wur:wiki:upgrade`

| Command | Scope | Mutates schema? |
|---|---|---|
| `/wur:upgrade` | Whole `agents/` workspace, between WUR plugin versions | Yes, bumps `schema_version` |
| `/wur:wiki:upgrade` | Adds the graph layer (`agents/graph/ontology.yaml`, conventions) on top of any schema | No, additive only |

If both are needed, run `/wur:upgrade` first, then `/wur:wiki:upgrade`.
