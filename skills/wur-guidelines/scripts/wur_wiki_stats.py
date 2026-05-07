#!/usr/bin/env python3
"""
wur_wiki_stats.py — Stats summary for an agents/ WUR wiki workspace.

Usage:
    python wur_wiki_stats.py <agents_dir> [--json]

Output:
    Human-readable report (or --json for machine-readable).
    Counts graph pages by type/status, checks navigation health
    (broken wikilinks, orphans, missing frontmatter), and reports
    graph layer artifact presence and freshness.

Exit code: 0 always (read-only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional PyYAML — graceful fallback to regex parser if missing
# ---------------------------------------------------------------------------

try:
    import yaml as _yaml  # type: ignore

    _HAVE_YAML = True
except ImportError:
    _HAVE_YAML = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Same glob patterns as wur_graph_extract.py / wur_graph_lint.py
GRAPH_PAGE_PATTERNS: list[tuple[str, str]] = [
    ("roadmap/PHASE_*_FIX.md", "fix-round"),
    ("roadmap/PHASE_*.md", "phase"),
    ("roadmap/FIX_*.md", "fix-round"),  # legacy compatibility
    ("research/*.md", "research"),
    ("docs/*.md", "note"),  # may be overridden to "decision" by frontmatter
    ("reports/*.md", "report"),
]

WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+?)(?:[|#][^\[\]]*)?\]\]")

SEP = "\u2500" * 33  # ─────────────────────────────────

# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def _parse_yaml_fallback(yaml_src: str) -> dict[str, Any]:
    """Minimal key: value regex parser used when PyYAML is absent."""
    result: dict[str, Any] = {}
    for line in yaml_src.splitlines():
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)", line.strip())
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            if val:
                result[key] = val
    return result


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """
    Split YAML frontmatter from markdown body.
    Returns (fm_dict | None, body_text).
    Always normalises CRLF → LF first.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    yaml_src = text[3:end].strip()
    body = text[end + 4 :]
    if _HAVE_YAML:
        try:
            fm = _yaml.safe_load(yaml_src) or {}
        except Exception:
            fm = None
    else:
        fm = _parse_yaml_fallback(yaml_src)
    if not isinstance(fm, dict):
        fm = None
    return fm, body


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def collect_graph_pages(agents_dir: Path) -> list[tuple[Path, str]]:
    """Return (path, default_type) for every file matching GRAPH_PAGE_PATTERNS."""
    seen: set[Path] = set()
    pages: list[tuple[Path, str]] = []
    for pattern, default_type in GRAPH_PAGE_PATTERNS:
        for path in sorted(agents_dir.glob(pattern)):
            if path not in seen:
                seen.add(path)
                pages.append((path, default_type))
    return pages


def collect_all_md(agents_dir: Path) -> list[Path]:
    """Return all .md files recursively under agents_dir."""
    return sorted(agents_dir.rglob("*.md"))


def _is_relative_to(path: Path, base: Path) -> bool:
    """Python 3.8-compatible Path.is_relative_to()."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Slug index  (same logic as wur_graph_lint.py::build_slug_index)
# ---------------------------------------------------------------------------


def build_slug_index(all_md: list[Path], agents_dir: Path) -> dict[str, Path]:
    """
    Map lowercase relative path (without .md) → absolute Path.
    Two keys per file:
      - full relative stem:  "roadmap/PHASE_1"
      - basename stem:       "phase_1"
    """
    index: dict[str, Path] = {}
    for p in all_md:
        try:
            rel = p.relative_to(agents_dir)
        except ValueError:
            continue
        key = str(rel.with_suffix("")).lower().replace("\\", "/")
        index[key] = p
        index[rel.stem.lower()] = p
    return index


# ---------------------------------------------------------------------------
# Stats collection
# ---------------------------------------------------------------------------


def collect_stats(agents_dir: Path) -> dict[str, Any]:  # noqa: C901
    agents_dir = agents_dir.resolve()
    graph_dir = agents_dir / "graph"

    # ------------------------------------------------------------------ #
    # 1. Graph pages — type & status counts, missing-frontmatter count    #
    # ------------------------------------------------------------------ #
    graph_page_tuples = collect_graph_pages(agents_dir)
    graph_pages: list[Path] = [p for p, _ in graph_page_tuples]
    graph_page_set: set[Path] = set(graph_pages)

    type_counts: Counter[str] = Counter()
    status_by_type: dict[str, Counter[str]] = {}
    missing_fm_count = 0

    # Cache fm per graph page (needed later for orphan scan)
    graph_fm: dict[Path, dict[str, Any] | None] = {}

    for path, default_type in graph_page_tuples:
        try:
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            graph_fm[path] = None
            missing_fm_count += 1
            type_counts[default_type] += 1
            if default_type not in status_by_type:
                status_by_type[default_type] = Counter()
            continue

        fm, _ = parse_frontmatter(raw)
        graph_fm[path] = fm

        # Effective type — use frontmatter value, fall back to pattern default
        page_type = str(fm["type"]) if (fm and "type" in fm) else default_type
        type_counts[page_type] += 1

        if page_type not in status_by_type:
            status_by_type[page_type] = Counter()

        status_val = str((fm or {}).get("status", "") or "").strip()
        if status_val:
            status_by_type[page_type][status_val] += 1

        # Missing frontmatter: fm absent OR any required key missing
        if fm is None or not all(k in fm for k in ("type", "status", "tags")):
            missing_fm_count += 1

    # ------------------------------------------------------------------ #
    # 2. Wikilink scan                                                    #
    #    - broken links:  scan ALL .md files                             #
    #    - orphan inbound: count only links originating in graph pages   #
    # ------------------------------------------------------------------ #
    all_md = collect_all_md(agents_dir)
    slug_index = build_slug_index(all_md, agents_dir)

    # Build slug → path map for graph pages (both full-rel and stem keys)
    graph_slug_map: dict[str, Path] = {}
    for p in graph_pages:
        try:
            rel_stem = (
                str(p.relative_to(agents_dir).with_suffix(""))
                .lower()
                .replace("\\", "/")
            )
            graph_slug_map[rel_stem] = p
            graph_slug_map[p.stem.lower()] = p
        except ValueError:
            pass

    inbound: dict[str, int] = {slug: 0 for slug in graph_slug_map}

    total_wikilinks = 0
    broken_links = 0
    broken_examples: list[str] = []

    for md_file in all_md:
        try:
            text = md_file.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue

        is_graph_source = md_file in graph_page_set

        for match in WIKILINK_RE.finditer(text):
            raw = match.group(1).strip()
            total_wikilinks += 1
            slug = raw.strip("/")

            # Broken link resolution (three-way: exact path, bare path, slug index)
            if (agents_dir / (slug + ".md")).exists() or (agents_dir / slug).exists():
                resolved = True
            else:
                resolved = slug.lower() in slug_index

            if not resolved:
                broken_links += 1
                if len(broken_examples) < 5:
                    try:
                        loc = str(md_file.relative_to(agents_dir)).replace("\\", "/")
                    except ValueError:
                        loc = str(md_file)
                    broken_examples.append(f"[[{raw}]] in {loc}")

            # Inbound accumulation (graph-page sources only, for orphan detection)
            if is_graph_source:
                key = slug.lower()
                if key in inbound:
                    inbound[key] += 1
                bk = Path(slug).stem.lower()
                if bk in inbound:
                    inbound[bk] += 1

    # Orphan pages: graph pages with zero inbound from other graph pages
    orphan_pages: list[str] = []
    for path in graph_pages:
        try:
            rel_str = str(path.relative_to(agents_dir)).replace("\\", "/")
            rel_stem = (
                str(path.relative_to(agents_dir).with_suffix(""))
                .lower()
                .replace("\\", "/")
            )
        except ValueError:
            continue
        if "/" not in rel_str:
            continue  # skip any top-level files
        count = inbound.get(rel_stem, 0) + inbound.get(path.stem.lower(), 0)
        if count == 0:
            orphan_pages.append(rel_str)

    # ------------------------------------------------------------------ #
    # 3. Graph layer artifact checks                                      #
    # ------------------------------------------------------------------ #
    graph_enabled = graph_dir.is_dir()

    def _count_jsonl_lines(p: Path) -> int:
        if not p.exists():
            return 0
        count = 0
        try:
            for line in p.read_text(
                encoding="utf-8-sig", errors="replace"
            ).splitlines():
                if line.strip():
                    count += 1
        except OSError:
            pass
        return count

    nodes_present = (graph_dir / "nodes.jsonl").exists()
    edges_present = (graph_dir / "edges.jsonl").exists()
    sqlite_present = (graph_dir / "graph.sqlite").exists()
    ontology_present = (graph_dir / "ontology.yaml").exists()
    le_present = (graph_dir / "last_extracted.md").exists()

    nodes_count = _count_jsonl_lines(graph_dir / "nodes.jsonl") if nodes_present else 0
    edges_count = _count_jsonl_lines(graph_dir / "edges.jsonl") if edges_present else 0

    last_extracted_str = ""
    freshness = "unknown"

    if le_present:
        try:
            le_text = (
                (graph_dir / "last_extracted.md")
                .read_text(encoding="utf-8-sig")
                .strip()
            )
            dm = re.search(r"(\d{4}-\d{2}-\d{2}(?:T[\d:+Z.-]*)?)", le_text)
            if dm:
                last_extracted_str = dm.group(1)[:10]
                extracted_dt = datetime.fromisoformat(dm.group(1).rstrip("Z")).replace(
                    tzinfo=timezone.utc
                )

                latest_mtime = 0.0
                for md_file in agents_dir.rglob("*.md"):
                    if _is_relative_to(md_file, graph_dir):
                        continue
                    mt = md_file.stat().st_mtime
                    if mt > latest_mtime:
                        latest_mtime = mt

                if latest_mtime:
                    latest_dt = datetime.fromtimestamp(latest_mtime, tz=timezone.utc)
                    freshness = (
                        "OK"
                        if latest_dt <= extracted_dt + timedelta(seconds=1)
                        else "STALE"
                    )
                else:
                    freshness = "OK"
        except Exception:
            freshness = "unknown"

    # ------------------------------------------------------------------ #
    # 4. Totals                                                           #
    # ------------------------------------------------------------------ #
    total_warnings = len(orphan_pages) + (1 if freshness == "STALE" else 0)
    total_errors = broken_links

    return {
        "agents_dir": str(agents_dir),
        "total_graph_pages": len(graph_pages),
        "type_counts": dict(type_counts),
        "status_by_type": {k: dict(v) for k, v in status_by_type.items()},
        "wikilinks": {
            "total": total_wikilinks,
            "broken": broken_links,
            "broken_examples": broken_examples,
        },
        "orphan_pages": orphan_pages,
        "missing_frontmatter": missing_fm_count,
        "graph_layer": {
            "enabled": graph_enabled,
            "ontology_yaml": ontology_present,
            "nodes_jsonl": {"present": nodes_present, "count": nodes_count},
            "edges_jsonl": {"present": edges_present, "count": edges_count},
            "graph_sqlite": sqlite_present,
            "last_extracted": last_extracted_str,
            "freshness": freshness,
        },
        "errors": total_errors,
        "warnings": total_warnings,
    }


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

# Display order and friendly labels for known page types
_TYPE_DISPLAY: list[tuple[str, str]] = [
    ("phase", "phases"),
    ("fix-round", "fix-rounds"),
    ("research", "research"),
    ("note", "docs/notes"),
    ("decision", "decisions"),
    ("report", "reports"),
]
_KNOWN_TYPES: set[str] = {t for t, _ in _TYPE_DISPLAY}


def _row(label: str, value: str, *, width: int = 18) -> str:
    """Left-align label+colon in a fixed-width column."""
    return f"  {(label + ':'):<{width}}{value}"


def render_text(stats: dict[str, Any]) -> str:
    out: list[str] = []

    out.append("agents/ wiki stats")
    out.append(SEP)

    # ---- Pages by type -------------------------------------------------
    out.append("Pages by type:")
    type_counts = stats["type_counts"]
    status_by_type = stats["status_by_type"]

    for type_key, label in _TYPE_DISPLAY:
        count = type_counts.get(type_key, 0)
        if count == 0:
            continue
        statuses = status_by_type.get(type_key, {})
        if type_key == "phase":
            a = statuses.get("active", 0)
            d = statuses.get("done", 0)
            b = statuses.get("blocked", 0)
            suffix = f"  (active: {a}, done: {d}, blocked: {b})"
        elif type_key == "fix-round":
            a = statuses.get("active", 0)
            d = statuses.get("done", 0)
            suffix = f"  (active: {a}, done: {d})"
        else:
            suffix = ""
        out.append(f"  {(label + ':'):<13s}{count}{suffix}")

    # Any unexpected types found in the workspace
    for type_key in sorted(type_counts):
        if type_key not in _KNOWN_TYPES:
            out.append(f"  {(type_key + ':'):<13s}{type_counts[type_key]}")

    out.append("")

    # ---- Navigation health ---------------------------------------------
    wl = stats["wikilinks"]
    orphans = stats["orphan_pages"]
    out.append("Navigation health:")
    out.append(_row("total wikilinks", str(wl["total"])))
    out.append(_row("broken links", str(wl["broken"])))

    orphan_suffix = ""
    if orphans:
        shown = orphans[:3]
        extra = "..." if len(orphans) > 3 else ""
        orphan_suffix = f"  ({', '.join(shown)}{extra})"
    out.append(_row("orphan pages", str(len(orphans))) + orphan_suffix)
    out.append(f"  missing frontmatter: {stats['missing_frontmatter']}")

    out.append("")

    # ---- Graph layer ---------------------------------------------------
    gl = stats["graph_layer"]
    out.append("Graph layer:")
    status_str = "enabled" if gl["enabled"] else "disabled (no agents/graph/ dir)"
    out.append(_row("status", status_str))

    nj = gl["nodes_jsonl"]
    ej = gl["edges_jsonl"]
    nodes_val = f"present ({nj['count']} nodes)" if nj["present"] else "absent"
    edges_val = f"present ({ej['count']} edges)" if ej["present"] else "absent"
    out.append(_row("nodes.jsonl", nodes_val))
    out.append(_row("edges.jsonl", edges_val))
    out.append(_row("graph.sqlite", "present" if gl["graph_sqlite"] else "absent"))
    out.append(_row("last extracted", gl["last_extracted"] or "\u2014"))

    freshness = gl["freshness"]
    fresh_str = (
        "STALE \u2014 run /wur:wiki:graph extract"
        if freshness == "STALE"
        else freshness
    )
    out.append(_row("freshness", fresh_str))

    out.append(SEP)
    out.append(
        f"Total graph pages: {stats['total_graph_pages']}"
        f"  |  Errors: {stats['errors']}"
        f"  |  Warnings: {stats['warnings']}"
    )

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="wur_wiki_stats.py",
        description="Show stats for an agents/ WUR wiki workspace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python wur_wiki_stats.py agents/\n"
            "  python wur_wiki_stats.py agents/ --json\n\n"
            "Exit code is always 0 (read-only operation)."
        ),
    )
    p.add_argument("agents_dir", help="Path to the agents/ directory")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    agents_dir = Path(args.agents_dir)

    if not agents_dir.is_dir():
        print(f"ERROR: '{agents_dir}' is not a directory.", file=sys.stderr)
        sys.exit(0)

    stats = collect_stats(agents_dir)

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print(render_text(stats))

    sys.exit(0)


if __name__ == "__main__":
    main()
