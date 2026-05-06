# Schema Migrations

Each `agents/` workspace declares its layout via `schema_version` in the YAML frontmatter of `agents/SCHEMA.md`. When the WUR plugin ships a new schema, this directory holds the migration scripts.

## Naming

```text
v{from}-to-v{to}.md
```

Examples:

- `v1-to-v2.md` — migrate from schema 1 to schema 2
- `v2-to-v3.md` — migrate from schema 2 to schema 3

`/wur:upgrade` chains them: to go from `1 → 3` it runs `v1-to-v2.md` then `v2-to-v3.md`, committing one Tiny WU per step.

## Authoring rules

1. **Idempotent** — re-running on an already-migrated workspace is a safe no-op. Detect target shape and exit cleanly.
2. **Treat current as raw** — read each old-shape page, transform it, write the new page. Never overwrite without first reading.
3. **Per-step `schema_version` bump** — the last action of the script must update `agents/SCHEMA.md` frontmatter to `schema_version: {to}`.
4. **Log entry** — append `| {today} | schema-upgrade | migrated schema {from} → {to} |` to `agents/roadmap/log.md`.
5. **One commit per step** — `WU-TW-{k}: migrate agents/ schema {from} → {to}`.
6. **No silent renames** — if a page moves or is renamed, leave a stub at the old path with a `> moved to [[new/path]]` line, valid for one schema generation, removed in the next migration.
7. **Document conflicts** — if a step cannot be applied automatically, list the manual actions in a `## Manual steps` section in the migration page. The agent must surface them to the user before continuing.

## Current state

- Schema floor: `1` (the original `wiki` layout)
- Plugin latest: `1`
- Migrations available: none (no schema bump has happened yet)

When schema `2` is introduced, add `v1-to-v2.md` here and update `commands/upgrade.md` to advertise the new latest.
