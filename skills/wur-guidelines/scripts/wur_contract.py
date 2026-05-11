#!/usr/bin/env python3
"""Create and update one-file WUR execution contracts.

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
            "Notes For WUR:\n"
            "- {roadmap/status update suggestion}\n"
            "```\n"
        )
    return existing[existing.index(REPORT_MARKER) :].rstrip() + "\n"


def render_contract(
    *,
    phase: str,
    title: str,
    criteria: list[str],
    units: list[WorkUnit],
    work_unit: str | None,
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
        "",
        "## WUR Contract Rules",
        "",
        "- This contract is the execution boundary for an external agent.",
        "- `agents/` remains the canonical wiki and must be read-only to the executor.",
        "- Do not modify `agents/`.",
        "- Do not modify `contracts/` except this contract report section.",
        "- Do not mark Work Units accepted, done, or close a phase.",
        "- Do not merge branches or run `/wur:done`.",
        "- Implement only pending work listed in this file.",
        "- Run verification before claiming success.",
        "- If blocked, add a blocked report instead of guessing.",
        "- Keep output concise; WUR coordinator performs final acceptance.",
        "",
        "## Optional Sparse Worktree",
        "",
        "If isolation is needed, create a worktree that excludes WUR state:",
        "",
        "```bash",
        "git worktree add .worktrees/P{phase}_contract -b work/P{phase}_contract main",
        "cd .worktrees/P{phase}_contract",
        "git sparse-checkout init --no-cone",
        "git sparse-checkout set \"/*\" \"!/agents/\" \"!/contracts/\"",
        "```",
        "",
        "The executor should use this contract as its task brief and must not carry "
        "`agents/` or `contracts/` into the execution worktree.",
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
            "## Receive Rules",
            "",
            "- WUR accepts a report only after checking commit hash, changed files, and verification evidence.",
            "- WUR updates `agents/` after receive; external executors do not update roadmap files directly.",
            "- Failed work becomes another execution round in this same contract, not a separate Phase Fix file.",
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
    existing = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(
        render_contract(
            phase=phase,
            title=title,
            criteria=criteria,
            units=selected,
            work_unit=work_unit,
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
