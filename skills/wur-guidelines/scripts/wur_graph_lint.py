#!/usr/bin/env python3
"""
wur_graph_lint.py — Validate agents/ graph pages and graph artifacts.

Checks:
  1. Missing frontmatter fields (type, status, tags)
  2. Invalid type value
  3. Invalid status value
  4. Tag format (^[a-z][a-z0-9-]*$, must be a list)
  5. Broken wikilinks ([[target]] must resolve to a real file)
  6. Orphan pages (no inbound wikilinks) — warning
  7. Stale graph artifacts (last_extracted.md vs latest mtime) — warning
  8. Edge integrity (every edge subject/object must be a known node ID)
  9. Missing test_status in PHASE_*.md phase files
 10. Oversized pages (>400 lines warn, >800 lines error)

Usage:
    python wur_graph_lint.py <agents_dir> [--json]

Exit codes:
    0 — no errors (warnings may exist)
    1 — one or more errors found
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TYPES = {"phase", "fix-round", "research", "decision", "note", "report"}
VALID_STATUSES = {"planned", "active", "done", "blocked", "deferred", "aborted"}
TAG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]")

GRAPH_PAGE_PATTERNS: list[tuple[str, str]] = [
    ("roadmap/PHASE_*_FIX.md", "fix-round"),
    ("roadmap/PHASE_*.md", "phase"),
    ("roadmap/FIX_*.md", "fix-round"),  # legacy compatibility
    ("research/*.md", "research"),
    ("docs/*.md", "note"),
    ("reports/*.md", "report"),
]

# ---------------------------------------------------------------------------
# Diagnostic helpers
# ---------------------------------------------------------------------------


class Diagnostic:
    __slots__ = ("level", "file", "message")

    def __init__(self, level: str, file: str | None, message: str) -> None:
        self.level = level  # "ERROR" | "WARN"
        self.file = file
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "file": self.file, "message": self.message}

    def __str__(self) -> str:
        tag = f"[{self.level}]"
        pad = " " * (7 - len(tag))
        loc = f"{self.file}: " if self.file else ""
        return f"{tag}{pad}{loc}{self.message}"


class Linter:
    def __init__(self, agents_dir: Path) -> None:
        self.agents_dir = agents_dir.resolve()
        self.diagnostics: list[Diagnostic] = []

    def error(self, file: str | None, msg: str) -> None:
        self.diagnostics.append(Diagnostic("ERROR", file, msg))

    def warn(self, file: str | None, msg: str) -> None:
        self.diagnostics.append(Diagnostic("WARN", file, msg))

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.level == "ERROR")

    @property
    def warn_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.level == "WARN")


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def collect_graph_pages(agents_dir: Path) -> list[Path]:
    """Return only graph pages (excludes system pages like ALL.md, log.md, SCHEMA.md)."""
    seen: set[Path] = set()
    pages: list[Path] = []
    for pattern, _default_type in GRAPH_PAGE_PATTERNS:
        for path in sorted(agents_dir.glob(pattern)):
            path = path.resolve()
            if path not in seen:
                seen.add(path)
                pages.append(path)
    return pages


def relative(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Split YAML frontmatter from body. Returns (fm_dict | None, body)."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    yaml_src = text[3:end].strip()
    body = text[end + 4 :]
    try:
        fm = yaml.safe_load(yaml_src) or {}
    except yaml.YAMLError:
        fm = None
    return fm, body


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_frontmatter(linter: Linter, rel: str, fm: dict[str, Any] | None) -> None:
    """Checks 1–4: required fields, valid type/status, tag format."""
    if fm is None:
        linter.error(rel, "cannot parse frontmatter (invalid YAML)")
        return

    required = ("type", "status", "tags")
    for field in required:
        if field not in fm:
            linter.error(rel, f"missing frontmatter field '{field}'")

    if "type" in fm and fm["type"] not in VALID_TYPES:
        linter.error(
            rel,
            f"invalid type '{fm['type']}' — must be one of: {', '.join(sorted(VALID_TYPES))}",
        )

    if "status" in fm and fm["status"] not in VALID_STATUSES:
        linter.error(
            rel,
            f"invalid status '{fm['status']}' — must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    if "tags" in fm:
        tags = fm["tags"]
        if not isinstance(tags, list):
            linter.error(rel, "frontmatter 'tags' must be a YAML list, not a scalar")
        else:
            for tag in tags:
                if not isinstance(tag, str) or not TAG_RE.match(tag):
                    linter.error(rel, f"tag '{tag}' does not match ^[a-z][a-z0-9-]*$")


def check_test_status(
    linter: Linter, rel: str, path: Path, fm: dict[str, Any] | None
) -> None:
    """Check 9: PHASE_*.md must have test_status field."""
    if not path.name.startswith("PHASE_") or path.name.endswith("_FIX.md"):
        return
    if fm is None or "test_status" not in fm:
        linter.error(rel, "PHASE file missing frontmatter field 'test_status'")


def check_size(linter: Linter, rel: str, lines: int) -> None:
    """Check 10: >400 lines warn, >800 lines error."""
    if lines > 800:
        linter.error(rel, f"oversized page — {lines} lines (hard cap 800)")
    elif lines > 400:
        linter.warn(rel, f"large page — {lines} lines (soft cap 400)")


def check_wikilinks(
    linter: Linter,
    rel: str,
    body: str,
    slug_to_path: dict[str, Path],
    agents_dir: Path,
) -> list[str]:
    """Check 5: broken wikilinks. Returns list of referenced slugs (for orphan analysis)."""
    referenced_slugs: list[str] = []
    for match in WIKILINK_RE.finditer(body):
        raw = match.group(1).strip()
        # Normalise: strip leading/trailing slashes, lowercase for lookup
        slug = raw.strip("/")
        referenced_slugs.append(slug)
        # Try direct path resolution first
        candidate = agents_dir / (slug + ".md")
        if candidate.exists():
            continue
        candidate2 = agents_dir / slug
        if candidate2.exists():
            continue
        # Fallback: slug lookup (case-insensitive basename)
        slug_lower = slug.lower()
        if slug_lower not in slug_to_path:
            linter.error(rel, f"broken wikilink [[{raw}]] — no matching file found")
    return referenced_slugs


# ---------------------------------------------------------------------------
# Build slug → path index
# ---------------------------------------------------------------------------


def build_slug_index(pages: list[Path], agents_dir: Path) -> dict[str, Path]:
    """Map lowercase relative path (without .md) → absolute Path."""
    index: dict[str, Path] = {}
    for p in pages:
        rel = p.relative_to(agents_dir)
        # Key 1: full relative path without extension, e.g. "roadmap/PHASE_1"
        key = str(rel.with_suffix("")).lower().replace("\\", "/")
        index[key] = p
        # Key 2: basename without extension, e.g. "phase_1"
        index[rel.stem.lower()] = p
    return index


# ---------------------------------------------------------------------------
# Orphan check
# ---------------------------------------------------------------------------


def check_orphans(
    linter: Linter,
    pages: list[Path],
    inbound: dict[str, int],
    agents_dir: Path,
) -> None:
    """Check 6: warn on graph pages with no inbound wikilinks."""
    for page in pages:
        rel = relative(page, agents_dir).replace("\\", "/")
        slug = (
            str(page.relative_to(agents_dir).with_suffix("")).lower().replace("\\", "/")
        )
        # Skip top-level special files
        if "/" not in rel:
            continue
        if inbound.get(slug, 0) == 0 and inbound.get(page.stem.lower(), 0) == 0:
            linter.warn(rel, "orphan page (no inbound wikilinks)")


# ---------------------------------------------------------------------------
# Stale graph check
# ---------------------------------------------------------------------------


def check_stale_graph(linter: Linter, agents_dir: Path) -> None:
    """Check 7: compare last_extracted.md timestamp vs latest mtime in agents/."""
    last_extracted = agents_dir / "graph" / "last_extracted.md"
    if not last_extracted.exists():
        return

    text = last_extracted.read_text(encoding="utf-8-sig").strip()
    # Look for an ISO date in the file content, e.g. "2026-04-01" or RFC-3339
    date_match = re.search(r"(\d{4}-\d{2}-\d{2}(?:T[\d:+Z.-]*)?)", text)
    if not date_match:
        linter.warn(
            None, "graph/last_extracted.md exists but contains no parseable timestamp"
        )
        return

    try:
        extracted_dt = datetime.fromisoformat(date_match.group(1).rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        linter.warn(
            None,
            f"graph/last_extracted.md timestamp '{date_match.group(1)}' could not be parsed",
        )
        return

    latest_mtime: float = 0.0
    latest_path: Path | None = None
    for md_file in agents_dir.rglob("*.md"):
        # Skip the artifacts themselves
        if md_file.is_relative_to(agents_dir / "graph"):
            continue
        mtime = md_file.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_path = md_file

    if latest_path is None:
        return

    latest_dt = datetime.fromtimestamp(latest_mtime, tz=timezone.utc)
    # last_extracted.md stores second-level precision; allow a 1-second grace
    # window so a fresh extract is not marked stale due to filesystem mtime
    # fractions or write-order timing on Windows/macOS/Linux.
    if latest_dt > extracted_dt + timedelta(seconds=1):
        extracted_str = extracted_dt.strftime("%Y-%m-%d")
        latest_str = latest_dt.strftime("%Y-%m-%d")
        linter.warn(
            None,
            f"graph artifacts stale — last extracted {extracted_str}, "
            f"latest change {latest_str} ({relative(latest_path, agents_dir)})",
        )


# ---------------------------------------------------------------------------
# Edge integrity check
# ---------------------------------------------------------------------------


def check_edge_integrity(linter: Linter, agents_dir: Path) -> None:
    """Check 8: every edge subject/object must reference a valid node ID."""
    graph_dir = agents_dir / "graph"
    nodes_file = graph_dir / "nodes.jsonl"
    edges_file = graph_dir / "edges.jsonl"

    if not nodes_file.exists() or not edges_file.exists():
        return  # graph layer not extracted yet — skip silently

    node_ids: set[str] = set()
    try:
        for line in nodes_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            node = json.loads(line)
            nid = node.get("id") or node.get("slug")
            if nid:
                node_ids.add(str(nid))
    except (json.JSONDecodeError, OSError) as exc:
        linter.error("graph/nodes.jsonl", f"cannot parse nodes file: {exc}")
        return

    try:
        for lineno, line in enumerate(
            edges_file.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            line = line.strip()
            if not line:
                continue
            edge = json.loads(line)
            subj = str(edge.get("subject", edge.get("from", "")))
            obj = str(edge.get("object", edge.get("to", "")))
            if subj and subj not in node_ids:
                linter.error(
                    "graph/edges.jsonl",
                    f"line {lineno}: edge subject '{subj}' does not match any node ID",
                )
            if obj and obj not in node_ids:
                linter.error(
                    "graph/edges.jsonl",
                    f"line {lineno}: edge object '{obj}' does not match any node ID",
                )
    except (json.JSONDecodeError, OSError) as exc:
        linter.error("graph/edges.jsonl", f"cannot parse edges file: {exc}")


# ---------------------------------------------------------------------------
# Main lint runner
# ---------------------------------------------------------------------------


def run_lint(agents_dir: Path) -> Linter:
    agents_dir = agents_dir.resolve()
    linter = Linter(agents_dir)

    if not agents_dir.is_dir():
        linter.error(
            None, f"agents_dir '{agents_dir}' does not exist or is not a directory"
        )
        return linter

    pages = collect_graph_pages(agents_dir)
    slug_to_path = build_slug_index(pages, agents_dir)

    # Inbound link counter: slug (lowercase, no ext) → count
    inbound: dict[str, int] = {
        str(p.relative_to(agents_dir).with_suffix("")).lower().replace("\\", "/"): 0
        for p in pages
    }

    # Per-page checks
    for page in pages:
        rel = relative(page, agents_dir).replace("\\", "/")
        try:
            text = page.read_text(encoding="utf-8-sig")
        except OSError as exc:
            linter.error(rel, f"cannot read file: {exc}")
            continue

        lines = text.splitlines()
        check_size(linter, rel, len(lines))

        fm, body = parse_frontmatter(text)

        check_frontmatter(linter, rel, fm)
        if fm is not None:
            check_test_status(linter, rel, page, fm)

        # Wikilink checks for all pages
        referenced = check_wikilinks(linter, rel, body, slug_to_path, agents_dir)

        # Accumulate inbound counts
        for slug in referenced:
            key = slug.lower()
            if key in inbound:
                inbound[key] += 1
            # Also try basename key
            basename_key = Path(slug).stem.lower()
            if basename_key in inbound:
                inbound[basename_key] += 1

    # Orphan check (after all pages processed)
    check_orphans(linter, pages, inbound, agents_dir)

    # Stale graph check
    check_stale_graph(linter, agents_dir)

    # Edge integrity check
    check_edge_integrity(linter, agents_dir)

    return linter


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint agents/ graph pages and graph artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("agents_dir", help="Path to the agents/ directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON array")
    args = parser.parse_args(argv)

    agents_dir = Path(args.agents_dir)
    linter = run_lint(agents_dir)

    pages_checked = len(collect_graph_pages(agents_dir)) if agents_dir.is_dir() else 0

    if args.json:
        result = {
            "pages_checked": pages_checked,
            "errors": linter.error_count,
            "warnings": linter.warn_count,
            "diagnostics": [d.to_dict() for d in linter.diagnostics],
        }
        print(json.dumps(result, indent=2))
    else:
        for d in linter.diagnostics:
            print(d)
        status = "OK" if linter.error_count == 0 else "FAIL"
        print(
            f"[{status}]    {pages_checked} pages checked, "
            f"{linter.error_count} errors, {linter.warn_count} warnings"
        )

    return 1 if linter.error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
