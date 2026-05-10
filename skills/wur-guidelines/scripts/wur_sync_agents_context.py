#!/usr/bin/env python3
"""Selective `agents/` context sync for active WUR phase worktrees.

Copies only new, safe context files from the default branch into the current
phase branch. It deliberately avoids git merge and never overwrites roadmap
execution files such as PHASE_N.md, ALL.md, or log.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


SAFE_PREFIXES = (
    "agents/docs/",
    "agents/research/",
    "agents/raw/",
    "agents/references/",
    "agents/specialists/",
    "agents/departments/",
    "agents/reports/",
)

FORBIDDEN_PREFIXES = (
    "agents/roadmap/",
    "agents/graph/",
)

FORBIDDEN_FILES = {
    "agents/index.md",
    "agents/SCHEMA.md",
}


class SyncError(RuntimeError):
    """Raised for expected sync failures."""


@dataclass(frozen=True)
class SyncPlan:
    base: str
    branch: str
    files: list[str]
    skipped_existing: int
    skipped_unsafe: int


def run_git(args: list[str], *, cwd: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise SyncError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def current_branch(cwd: str) -> str:
    return run_git(["branch", "--show-current"], cwd=cwd)


def default_branch(cwd: str) -> str:
    try:
        value = run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=cwd)
        if value.startswith("origin/"):
            return value.removeprefix("origin/")
    except SyncError:
        pass

    for name in ("main", "master", "develop"):
        try:
            run_git(["rev-parse", "--verify", name], cwd=cwd)
            return name
        except SyncError:
            pass
    return "main"


def normalize(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/")))


def list_tree(branch: str, cwd: str) -> set[str]:
    output = run_git(["ls-tree", "-r", "--name-only", branch, "--", "agents"], cwd=cwd)
    return {normalize(line) for line in output.splitlines() if line.strip()}


def is_safe_new_context(path: str) -> bool:
    path = normalize(path)
    if path in FORBIDDEN_FILES:
        return False
    if any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return False
    return any(path.startswith(prefix) for prefix in SAFE_PREFIXES)


def build_plan(base: str, cwd: str) -> SyncPlan:
    branch = current_branch(cwd)
    if branch == base:
        raise SyncError(f"refusing to sync on default branch '{base}'")
    if not branch.startswith("feature/phase-") and not branch.startswith("fix/phase-"):
        raise SyncError(
            "refusing to sync outside a WUR phase/fix branch "
            "(expected feature/phase-* or fix/phase-*)"
        )

    status = run_git(["status", "--short"], cwd=cwd)
    if status:
        raise SyncError("working tree must be clean before selective agents sync")

    base_files = list_tree(base, cwd)
    branch_files = list_tree("HEAD", cwd)

    new_files = sorted(base_files - branch_files)
    safe_files = [path for path in new_files if is_safe_new_context(path)]
    skipped_unsafe = len(new_files) - len(safe_files)

    return SyncPlan(
        base=base,
        branch=branch,
        files=safe_files,
        skipped_existing=len(base_files & branch_files),
        skipped_unsafe=skipped_unsafe,
    )


def checkout_files(plan: SyncPlan, cwd: str) -> None:
    if not plan.files:
        return
    run_git(["checkout", plan.base, "--", *plan.files], cwd=cwd)


def commit_files(plan: SyncPlan, cwd: str, message: str) -> str | None:
    if not plan.files:
        return None
    run_git(["add", *plan.files], cwd=cwd)
    run_git(["commit", "-m", message], cwd=cwd)
    return run_git(["rev-parse", "--short", "HEAD"], cwd=cwd)


def plan_to_dict(plan: SyncPlan, *, commit: str | None = None) -> dict[str, object]:
    return {
        "base": plan.base,
        "branch": plan.branch,
        "files": plan.files,
        "count": len(plan.files),
        "skipped_existing": plan.skipped_existing,
        "skipped_unsafe": plan.skipped_unsafe,
        "commit": commit,
    }


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import only new safe agents/ context files from the default branch.",
    )
    parser.add_argument("--cwd", default=".", help="Phase/fix worktree path.")
    parser.add_argument("--base", default=None, help="Default branch override.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument(
        "--message",
        default="sync: import new agents context from default branch",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        base = args.base or default_branch(args.cwd)
        plan = build_plan(base, args.cwd)
        commit = None
        if not args.dry_run:
            checkout_files(plan, args.cwd)
            if not args.no_commit:
                commit = commit_files(plan, args.cwd, args.message)
        payload = plan_to_dict(plan, commit=commit)
    except SyncError as exc:
        payload = {"ok": False, "error": str(exc)}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"[FAIL] {exc}")
        return 1

    payload["ok"] = True
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"[OK] {payload['count']} new context file(s) from {payload['base']}")
        for path in plan.files:
            print(path)
        if commit:
            print(f"commit: {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
