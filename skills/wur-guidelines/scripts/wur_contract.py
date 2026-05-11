#!/usr/bin/env python3
"""Create and update WUR execution contract files.

Contracts keep execution instructions and returned reports outside `agents/`
while preserving `agents/` as the canonical project wiki.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REPORT_MARKER = "## Execution Rounds And Reports"
DONE_STATUSES = {"accepted", "done"}
RULE_FILE = "rule.md"
PROJECT_CONTEXT_FILES = (
    "agents/project/PHILOSOPHY.md",
    "agents/project/USAGE.md",
    "agents/project/DESIGN.md",
    "agents/project/TECH_STACK.md",
)
COORDINATION_DIRS = (
    "agents/departments",
    "agents/specialists",
)


@dataclass(frozen=True)
class WorkUnit:
    work_id: str
    goal: str
    acceptance: str
    scope: str
    dependencies: str
    verification: str
    status: str
    commit: str


class ContractError(RuntimeError):
    pass


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def read_phase(path: Path) -> tuple[str, list[str], list[WorkUnit]]:
    if not path.exists():
        raise ContractError(f"phase file does not exist: {path}")

    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    criteria: list[str] = []
    criteria_match = re.search(
        r"^## Success Criteria\s*\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if criteria_match:
        for line in criteria_match.group("body").splitlines():
            clean = line.strip()
            if clean.startswith("- "):
                criteria.append(clean[2:].strip())

    units: list[WorkUnit] = []
    in_table = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("| ID | Goal | Acceptance Criteria |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if units:
                break
            continue
        if re.match(r"^\|\s*-+", line):
            continue
        cells = split_row(line)
        if len(cells) < 8:
            continue
        units.append(WorkUnit(*cells[:8]))

    return title, criteria, units


def pending_units(units: list[WorkUnit], work_unit: str | None) -> list[WorkUnit]:
    filtered = [unit for unit in units if unit.status.strip().lower() not in DONE_STATUSES]
    if work_unit:
        filtered = [unit for unit in filtered if unit.work_id == work_unit]
    return filtered


def report_tail(existing: str | None) -> str:
    if not existing or REPORT_MARKER not in existing:
        return (
            f"{REPORT_MARKER}\n\n"
            "Keep all execution reports in this same contract file. Do not create "
            "`contracts/inbox/` or `contracts/outbox/` files.\n\n"
            "### Report Template\n\n"
            "```markdown\n"
            "### Received Report - {round or WU}\n"
            "Result: pass | failed | blocked | partial\n"
            "Commit: {hash or none}\n"
            "Verification: {commands and results}\n"
            "Changed Files:\n"
            "- {path}\n"
            "Contract Section Edited: `## Execution Rounds And Reports` only\n"
            "Work Unit State Updates:\n"
            "- {WU id}: {before status} -> {suggested status: active | ready-for-review | blocked | deferred}; reason: {evidence}\n"
            "Notes For WUR:\n"
            "- {roadmap/status update suggestion}\n"
            "```\n"
        )
    return existing[existing.index(REPORT_MARKER) :].rstrip() + "\n"


def coordination_context_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for rel_path in PROJECT_CONTEXT_FILES:
        if (root / rel_path).exists():
            paths.append(rel_path)
    for rel_dir in COORDINATION_DIRS:
        folder = root / rel_dir
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            paths.append(path.relative_to(root).as_posix())
    return paths


def render_rule_file() -> str:
    return "\n".join(
        [
            "# WUR Contract Rules",
            "",
            "This file is the shared rule contract for every `contracts/PHASE_*_CONTRACT.md` handoff.",
            "Phase contracts contain phase-specific work and reports; this file contains reusable rules.",
            "",
            "## Execution Boundary",
            "",
            "- `agents/` is the source-of-truth wiki.",
            "- Do not modify `agents/`.",
            "- You may edit only the active phase contract's `## Execution Rounds And Reports` section.",
            "- Do not edit the phase contract header, Goal, Success Criteria, Pending Work table, or Allowed Read References.",
            "- Do not edit any other `contracts/` file.",
            "- Do not create `contracts/inbox/` or `contracts/outbox/`.",
            "- Do not create Phase Fix files for new work.",
            "- Never mark Work Units `accepted`, `done`, or close a phase; WUR coordinator applies `accepted` or `done` only after client confirmation.",
            "- Do not merge branches or run `/wur:done`.",
            "- Implement only pending work listed in the active phase contract.",
            "",
            "## Allowed Reads",
            "",
            "- Read only the `agents/` paths listed in the active phase contract's `Allowed Read References` section.",
            "- Do not scan all of `agents/`.",
            "- Do not read unlisted `agents/` files unless the client or WUR contract explicitly adds them.",
            "- Infer useful specialist lenses from the listed references and WU scope.",
            "",
            "## Work, Fix, Report",
            "",
            "- Run verification before claiming success.",
            "- If blocked, add a blocked report instead of guessing.",
            "- If verification fails, add or update a `### Fix Round R{n} - {scope}` section in the active phase contract.",
            "- Do not wait for WUR to generate a separate fix file or run another helper command.",
            "- Use one contract ledger for task brief, fix rounds, and reports.",
            "- Record lifecycle evidence for every touched Work Unit: before status, suggested after status, result, commit, verification, blockers, and coverage gaps.",
            "- Allowed executor status suggestions: `active`, `ready-for-review`, `blocked`, or `deferred`.",
            "- Report changed files, commit hash, verification evidence, specialist lenses applied, and any material coverage gaps.",
            "- Keep output concise; WUR coordinator performs final acceptance.",
            "",
            "## Isolated Worktree",
            "",
            "If you create a worktree, you MUST use sparse checkout and exclude `agents/` and `contracts/`.",
            "Do not copy, checkout, or sync `agents/` or `contracts/` into the execution worktree.",
            "Keep WUR state in the main project root only; the worktree is for implementation files.",
            "",
            "Recommended setup:",
            "",
            "```bash",
            "git worktree add .worktrees/P{phase}_contract -b work/P{phase}_contract main",
            "cd .worktrees/P{phase}_contract",
            "git sparse-checkout init --no-cone",
            "git sparse-checkout set \"/*\" \"!/agents/\" \"!/contracts/\"",
            "```",
            "",
            "Use the active phase contract as the task brief. Do not carry `agents/` or `contracts/` into the execution worktree.",
            "",
        ]
    )


def ensure_rule_file(root: Path) -> Path:
    target = root / "contracts" / RULE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_rule_file(), encoding="utf-8")
    return target


def render_contract(
    *,
    phase: str,
    title: str,
    criteria: list[str],
    units: list[WorkUnit],
    work_unit: str | None,
    context_paths: list[str],
    existing: str | None,
) -> str:
    today = date.today().isoformat()
    scope_mode = work_unit or f"PHASE_{phase}"
    lines = [
        f"# WUR Contract: PHASE_{phase}",
        "",
        f"Generated: {today}",
        f"Scope mode: `{scope_mode}`",
        f"Source: `agents/roadmap/PHASE_{phase}.md`",
        f"Required shared rules: `contracts/{RULE_FILE}` — read before execution.",
        "Task brief: use this file's Goal, Success Criteria, Pending Work, and Allowed Read References.",
        "Execution setup: read `contracts/rule.md` before creating a worktree.",
        "",
        "## Goal",
        "",
        title,
        "",
        "## Success Criteria",
        "",
    ]
    if criteria:
        lines.extend(f"- {item}" for item in criteria)
    else:
        lines.append("- Use the phase acceptance criteria from the roadmap.")
    lines.extend(
        [
            "",
            "## Pending Work",
            "",
            "| ID | Goal | Acceptance Criteria | Scope | Dependencies | Verification | Status | Commit |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if units:
        for unit in units:
            lines.append(
                "| "
                + " | ".join(
                    [
                        unit.work_id,
                        unit.goal,
                        unit.acceptance,
                        unit.scope,
                        unit.dependencies,
                        unit.verification,
                        unit.status,
                        unit.commit,
                    ]
                )
                + " |"
            )
    else:
        lines.append("| none | No pending work found | n/a | n/a | n/a | n/a | done | n/a |")
    lines.extend(
        [
            "",
            "## Allowed Read References",
            "",
            "Only read the listed paths when deeper context is needed. Do not scan all of `agents/`.",
            "Do not read unlisted `agents/` files unless the client or WUR contract explicitly adds them.",
            "",
        ]
    )
    if context_paths:
        lines.extend(f"- `{path}`" for path in context_paths)
    else:
        lines.append("- No project/personnel references were selected.")
    lines.extend(
        [
            "",
            "Specialist coordination:",
            "- Infer useful specialist lenses from the listed references and WU scope.",
            "- Do not require WUR to assign one person per WU.",
            "- Report which specialist lenses were applied.",
            "",
        ]
    )
    lines.append(report_tail(existing))
    return "\n".join(lines).rstrip() + "\n"


def contract_path(root: Path, phase: str) -> Path:
    return root / "contracts" / f"PHASE_{phase}_CONTRACT.md"


def create_contract(root: Path, phase: str, work_unit: str | None) -> Path:
    phase_file = root / "agents" / "roadmap" / f"PHASE_{phase}.md"
    title, criteria, units = read_phase(phase_file)
    selected = pending_units(units, work_unit)
    target = contract_path(root, phase)
    target.parent.mkdir(parents=True, exist_ok=True)
    ensure_rule_file(root)
    existing = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(
        render_contract(
            phase=phase,
            title=title,
            criteria=criteria,
            units=selected,
            work_unit=work_unit,
            context_paths=coordination_context_paths(root),
            existing=existing,
        ),
        encoding="utf-8",
    )
    return target


def receive_report(root: Path, phase: str, report_file: Path) -> Path:
    target = contract_path(root, phase)
    if not target.exists():
        raise ContractError(f"contract does not exist: {target}")
    if not report_file.exists():
        raise ContractError(f"report file does not exist: {report_file}")

    text = target.read_text(encoding="utf-8").rstrip()
    report = report_file.read_text(encoding="utf-8").strip()
    if REPORT_MARKER not in text:
        text += "\n\n" + report_tail(None).rstrip()
    entry = (
        f"\n\n### Received Report - {date.today().isoformat()}\n\n"
        f"{report}\n"
    )
    target.write_text(text + entry, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create or refresh one phase contract.")
    create.add_argument("--root", default=".", help="Project root.")
    create.add_argument("--phase", required=True, help="Phase number.")
    create.add_argument("--wu", default=None, help="Optional Work Unit ID filter.")
    create.add_argument("--json", action="store_true")

    receive = subparsers.add_parser("receive", help="Append a report to the same contract file.")
    receive.add_argument("--root", default=".", help="Project root.")
    receive.add_argument("--phase", required=True, help="Phase number.")
    receive.add_argument("--report-file", required=True, help="Report markdown to append.")
    receive.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "create":
            path = create_contract(root, args.phase, args.wu)
            payload = {"ok": True, "path": str(path)}
        elif args.command == "receive":
            path = receive_report(root, args.phase, Path(args.report_file).resolve())
            payload = {"ok": True, "path": str(path)}
        else:
            raise ContractError(f"unknown command: {args.command}")
    except ContractError as exc:
        payload = {"ok": False, "error": str(exc)}
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2))
        else:
            print(f"[FAIL] {exc}")
        return 1

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(f"[OK] {payload['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
