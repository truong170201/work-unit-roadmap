# WUR Git Hook Enforcement

Use these hooks to attach WUR rules to real git behavior in the managed project.

Install them at the **project root** (not under `agents/`):

```text
.githooks/
  commit-msg
  pre-commit
  pre-push
```

Then configure:

```bash
touch .githooks/.wur-managed
git config core.hooksPath .githooks

# Linux / macOS — set executable bit:
chmod +x .githooks/commit-msg .githooks/pre-commit .githooks/pre-push

# Windows — chmod is a no-op but Git for Windows runs hooks via its
# bundled sh.exe regardless of file permissions. No extra step needed.
# Hooks fire correctly from PowerShell, cmd, or Git Bash.
```

These hooks are intentionally minimal:
- no planning
- no AI inference
- only allow / block / require trace

## `commit-msg`

Reject commit messages that do not start with a recognized WUR prefix.

Allowed shapes:

| Shape | Example | Used by |
|---|---|---|
| `WU-P{n}-{unit}: …` | `WU-P01-003: add login validation` | implementation WUs (3 digits, optional letter suffix) |
| `WU-P{n}-close: …` | `WU-P01-close: mark phase 1 done` | `/wur:done` final commit |
| `WU-P{n}-fix: …` | `WU-P01-fix: merge fix/phase-1-empty-input` | `/wur:done` fix-round merge |
| `WU-P{n}-abort: …` | `WU-P01-abort: abandon phase 1` | `/wur:abort` |
| `WU-TW-{k}: …` | `WU-TW-001: bootstrap workspace` | Tiny WUs |
| `Phase {n}: merge …` | `Phase 1: merge feature/phase-1` | `/wur:done` phase merge |

```sh
#!/bin/sh
set -eu

msg_file="$1"
first_line=$(head -n 1 "$msg_file")

if printf '%s\n' "$first_line" | grep -Eq '^(WU-(P[0-9]+-([0-9]{3}[a-z]?|close|fix|abort)|TW-[0-9]+): .+|Phase [0-9]+: merge .+)$'; then
  exit 0
fi

cat >&2 <<'MSG'
WUR: commit message must match one of:
  WU-P{n}-{unit}: <description>     (e.g. WU-P01-003: add login validation)
  WU-P{n}-(close|fix|abort): <…>    (administrative phase commits)
  WU-TW-{k}: <description>          (Tiny WU)
  Phase {n}: merge <branch>         (phase merge by /wur:done)
MSG
exit 1
```

## `pre-commit`

Block implementation changes on the default branch. Also block implementation changes that do not stage roadmap updates together.

```sh
#!/bin/sh
set -eu

# Skip pre-commit for merge commits — git fires us only when conflicts were
# resolved and the user runs `git commit`. The merge commit's tree contains
# everything from the source branch, including roadmap updates, and must be
# allowed even on the default branch.
if git rev-parse --verify MERGE_HEAD >/dev/null 2>&1 \
   || git rev-parse --verify CHERRY_PICK_HEAD >/dev/null 2>&1 \
   || git rev-parse --verify REVERT_HEAD >/dev/null 2>&1; then
  exit 0
fi

staged=$(git diff --cached --name-only)
[ -z "$staged" ] && exit 0

# Tolerant ALL.md readers — accept "- Default branch: main" / "Default branch: main" / leading whitespace.
read_field() {
  field="$1"
  awk -v f="$field" '
    BEGIN { IGNORECASE=1 }
    {
      # strip leading list marker and whitespace
      sub(/^[[:space:]]*[-*][[:space:]]*/, "")
      if (tolower($0) ~ "^"tolower(f)":") {
        sub(/^[^:]*:[[:space:]]*/, "")
        # strip trailing decoration like " — name (active)"
        gsub(/[[:space:]]+$/, "")
        print
        exit
      }
    }
  ' agents/roadmap/ALL.md 2>/dev/null || true
}

default_branch=$(read_field "Default branch")
active_phase=$(read_field "Active phase")
current_branch=$(git branch --show-current)

project_files=$(printf '%s\n' "$staged" | grep -Ev '^(agents/|\.gitignore$|\.githooks/)' || true)
roadmap_files=$(printf '%s\n' "$staged" | grep '^agents/roadmap/' || true)

if [ -n "$project_files" ] && [ -n "$default_branch" ] && [ "$current_branch" = "$default_branch" ]; then
  echo "WUR: implementation changes cannot be committed from the default branch ($default_branch)." >&2
  exit 1
fi

if [ -n "$project_files" ] && [ -z "$roadmap_files" ]; then
  echo "WUR: implementation commits must stage agents/roadmap/ updates in the same commit." >&2
  exit 1
fi

if [ -n "$project_files" ] && [ -n "$active_phase" ] && [ "$active_phase" != "none" ]; then
  # tolerate "PHASE_2", "PHASE_2 — Local Study", "phase 2", or "2"
  phase_num=$(printf '%s' "$active_phase" | sed -n 's/.*[Pp][Hh][Aa][Ss][Ee]_\?[[:space:]]*\([0-9][0-9]*\).*/\1/p')
  [ -z "$phase_num" ] && phase_num=$(printf '%s' "$active_phase" | sed -n 's/^\([0-9][0-9]*\).*/\1/p')
  if [ -z "$phase_num" ]; then
    echo "WUR: cannot parse phase number from 'Active phase: $active_phase' in agents/roadmap/ALL.md." >&2
    exit 1
  fi
  case "$current_branch" in
    feature/phase-"$phase_num"|fix/phase-"$phase_num"-*) : ;;
    *)
      echo "WUR: implementation changes must be committed from feature/phase-$phase_num or fix/phase-$phase_num-*" >&2
      exit 1
      ;;
  esac
fi
```

## `pre-push`

Block pushing the default branch while the roadmap still shows an active phase or active WU.

```sh
#!/bin/sh
set -eu

read_field() {
  field="$1"
  awk -v f="$field" '
    BEGIN { IGNORECASE=1 }
    {
      sub(/^[[:space:]]*[-*][[:space:]]*/, "")
      if (tolower($0) ~ "^"tolower(f)":") {
        sub(/^[^:]*:[[:space:]]*/, "")
        gsub(/[[:space:]]+$/, "")
        print
        exit
      }
    }
  ' agents/roadmap/ALL.md 2>/dev/null || true
}

default_branch=$(read_field "Default branch")
active_phase=$(read_field "Active phase")
active_wu=$(read_field "Active Work Unit")
current_branch=$(git branch --show-current)

[ -z "$default_branch" ] && exit 0
[ "$current_branch" != "$default_branch" ] && exit 0

if [ -n "$active_phase" ] && [ "$active_phase" != "none" ]; then
  echo "WUR: cannot push default branch while Active phase is $active_phase." >&2
  exit 1
fi

if [ -n "$active_wu" ] && [ "$active_wu" != "none" ]; then
  echo "WUR: cannot push default branch while Active Work Unit is $active_wu." >&2
  exit 1
fi
```

## Waives

Hooks should not invent waives. Waives must already be present in the canonical WUR state:
- `test_status: waived`
- `test_waive_reason: ...`
- roadmap/log entries that explain the exception

If a project needs deeper enforcement later, add external automation on top of these hooks rather than replacing them.