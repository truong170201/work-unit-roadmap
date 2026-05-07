#!/usr/bin/env python3
"""
wur_meta_consistency.py — local consistency checker for WUR docs/spec/script drift.

Usage:
    python wur_meta_consistency.py [repo_root] [--json]

Checks:
- forbidden stale phrases are absent
- schema-upgrade vs wiki-upgrade event names stay disambiguated
- `aborted` status exists everywhere it must
- script paths in docs use `skills/wur-guidelines/scripts/`
- graph page patterns stay identical across extract/lint/stats scripts
- README/commands/spec remain aligned on key conventions
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    level: str
    message: str
    path: str | None = None


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _contains(path: Path, needle: str) -> bool:
    return needle in _text(path)


def run_checks(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []

    readme = repo_root / "README.md"
    init_md = repo_root / "commands" / "init.md"
    test_md = repo_root / "commands" / "test.md"
    upgrade_md = repo_root / "commands" / "upgrade.md"
    wiki_add_md = repo_root / "commands" / "wiki" / "add.md"
    wiki_ima_md = repo_root / "commands" / "wiki" / "ima.md"
    wiki_graph_md = repo_root / "commands" / "wiki" / "graph.md"
    wiki_upgrade_md = repo_root / "commands" / "wiki" / "upgrade.md"
    skill_md = repo_root / "skills" / "wur-guidelines" / "SKILL.md"
    migrations_readme = (
        repo_root
        / "skills"
        / "wur-guidelines"
        / "references"
        / "migrations"
        / "README.md"
    )
    scripts_readme = repo_root / "skills" / "wur-guidelines" / "scripts" / "README.md"
    extract_py = (
        repo_root / "skills" / "wur-guidelines" / "scripts" / "wur_graph_extract.py"
    )
    lint_py = repo_root / "skills" / "wur-guidelines" / "scripts" / "wur_graph_lint.py"
    stats_py = repo_root / "skills" / "wur-guidelines" / "scripts" / "wur_wiki_stats.py"

    all_md_files = list(repo_root.rglob("*.md"))

    forbidden_phrases = {
        "under the phase's Fix Rounds": "FIX round entries must go under `## Roadmap` in agents/index.md",
        "path/to/skills/wur-guidelines/scripts": "script paths must use project-relative `skills/wur-guidelines/scripts/...`",
        "GRAPH_PAGES": "old extract constant name must not remain after standardizing on GRAPH_PAGE_PATTERNS",
        "| {date} |": "log placeholders must use `{today}`, not `{date}`",
    }
    for md_file in all_md_files:
        text = _text(md_file)
        rel = md_file.relative_to(repo_root).as_posix()
        for phrase, msg in forbidden_phrases.items():
            if phrase in text:
                findings.append(Finding("ERROR", f"{msg}: found `{phrase}`", rel))

    # Explicit scope split: schema-upgrade belongs to /wur:upgrade, wiki-upgrade to /wur:wiki:upgrade.
    if not _contains(upgrade_md, "schema-upgrade"):
        findings.append(
            Finding(
                "ERROR",
                "`/wur:upgrade` must log `schema-upgrade`",
                upgrade_md.relative_to(repo_root).as_posix(),
            )
        )
    if not _contains(wiki_upgrade_md, "wiki-upgrade"):
        findings.append(
            Finding(
                "ERROR",
                "`/wur:wiki:upgrade` must log `wiki-upgrade`",
                wiki_upgrade_md.relative_to(repo_root).as_posix(),
            )
        )
    if not _contains(migrations_readme, "schema-upgrade"):
        findings.append(
            Finding(
                "ERROR",
                "migration authoring guide must use `schema-upgrade`",
                migrations_readme.relative_to(repo_root).as_posix(),
            )
        )

    # `aborted` must exist in schema templates, ontology, lint, and scripts README.
    must_contain_aborted = [
        init_md,
        upgrade_md,
        wiki_upgrade_md,
        scripts_readme,
        lint_py,
        skill_md,
    ]
    for path in must_contain_aborted:
        if "aborted" not in _text(path):
            findings.append(
                Finding(
                    "ERROR",
                    "missing `aborted` status",
                    path.relative_to(repo_root).as_posix(),
                )
            )

    # Script paths in docs must be project-relative.
    script_path_docs = [readme, wiki_graph_md, scripts_readme]
    for path in script_path_docs:
        txt = _text(path)
        if "skills/wur-guidelines/scripts/" not in txt:
            findings.append(
                Finding(
                    "ERROR",
                    "missing canonical script path prefix `skills/wur-guidelines/scripts/`",
                    path.relative_to(repo_root).as_posix(),
                )
            )
        if "path/to/skills/wur-guidelines/scripts/" in txt:
            findings.append(
                Finding(
                    "ERROR",
                    "contains stale placeholder script path",
                    path.relative_to(repo_root).as_posix(),
                )
            )

    # Key command/docs conventions.
    if "under the `## Roadmap` section" not in _text(test_md):
        findings.append(
            Finding(
                "ERROR",
                "FIX round index update must target `## Roadmap`",
                test_md.relative_to(repo_root).as_posix(),
            )
        )
    if "| {today} | wiki-add |" not in _text(wiki_add_md):
        findings.append(
            Finding(
                "ERROR",
                "`/wur:wiki:add` must define a concrete `wiki-add` log entry",
                wiki_add_md.relative_to(repo_root).as_posix(),
            )
        )
    ima_text = _text(wiki_ima_md)
    for snippet in (
        "| {today} | wiki-ima |",
        "Only update roadmap files when the user intent calls for roadmap planning changes",
        "Do not require flags",
        "Do not mark any Work Unit `active`, `accepted`, or `done`",
    ):
        if snippet not in ima_text:
            findings.append(
                Finding(
                    "ERROR",
                    f"`/wur:wiki:ima` missing contract snippet `{snippet}`",
                    wiki_ima_md.relative_to(repo_root).as_posix(),
                )
            )
    if "WU-P{n}-fix:" not in _text(skill_md) or "WU-P{n}-abort:" not in _text(skill_md):
        findings.append(
            Finding(
                "ERROR",
                "SKILL.md commit format list must include fix and abort administrative commits",
                skill_md.relative_to(repo_root).as_posix(),
            )
        )

    # Graph patterns must match across scripts.
    extract = _load_module("wur_graph_extract", extract_py)
    lint = _load_module("wur_graph_lint", lint_py)
    stats = _load_module("wur_wiki_stats", stats_py)

    extract_patterns = list(getattr(extract, "GRAPH_PAGE_PATTERNS"))
    lint_patterns = list(getattr(lint, "GRAPH_PAGE_PATTERNS"))
    stats_patterns = list(getattr(stats, "GRAPH_PAGE_PATTERNS"))
    if extract_patterns != lint_patterns or extract_patterns != stats_patterns:
        findings.append(
            Finding(
                "ERROR", "GRAPH_PAGE_PATTERNS differ across extract/lint/stats scripts"
            )
        )

    # Lint valid statuses must include all ontology status_values.
    valid_statuses = set(getattr(lint, "VALID_STATUSES"))
    ontology_text = _text(wiki_upgrade_md)
    for required in ("planned", "active", "done", "blocked", "deferred", "aborted"):
        if required not in valid_statuses:
            findings.append(
                Finding(
                    "ERROR",
                    f"lint VALID_STATUSES missing `{required}`",
                    lint_py.relative_to(repo_root).as_posix(),
                )
            )
        if required not in ontology_text:
            findings.append(
                Finding(
                    "ERROR",
                    f"ontology template missing `{required}`",
                    wiki_upgrade_md.relative_to(repo_root).as_posix(),
                )
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check WUR docs/spec/script consistency."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root (default: auto-detect)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        message = f"target root does not exist: {repo_root}"
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "findings": [
                            {"level": "ERROR", "message": message, "path": None}
                        ],
                    },
                    indent=2,
                )
            )
        else:
            print(f"[FAIL] {message}")
        return 1

    try:
        findings = run_checks(repo_root)
    except FileNotFoundError as exc:
        message = f"required file missing: {exc.filename}"
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "findings": [
                            {"level": "ERROR", "message": message, "path": None}
                        ],
                    },
                    indent=2,
                )
            )
        else:
            print(f"[FAIL] {message}")
        return 1

    if args.json:
        print(
            json.dumps(
                {"ok": not findings, "findings": [asdict(f) for f in findings]},
                indent=2,
            )
        )
    else:
        if findings:
            for finding in findings:
                loc = f" [{finding.path}]" if finding.path else ""
                print(f"[{finding.level}] {finding.message}{loc}")
            print(f"[FAIL] {len(findings)} consistency issue(s) found")
        else:
            print("[OK] WUR docs/spec/scripts are consistent")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
