#!/usr/bin/env python3
"""
wur_graph_extract.py
====================
Extract a typed graph from an agents/ WUR workspace.

Usage
-----
    python wur_graph_extract.py <agents_dir> [--out <dir>] [--formats jsonl,sqlite,graphml]

Outputs (written to <agents_dir>/graph/ by default, or --out)
------
    nodes.jsonl        one node per line  (git-tracked)
    edges.jsonl        one edge per line  (git-tracked)
    graph.sqlite       relational DB      (gitignored — binary)
    graph.graphml      Gephi/yEd export   (gitignored — large)
    summary.md         human-readable stats
    last_extracted.md  timestamp + counts

Node types
----------
    phase       roadmap/PHASE_*.md
    fix-round   roadmap/FIX_*.md
    research    research/*.md
    decision    docs/*.md   (frontmatter type: decision)
    note        docs/*.md   (frontmatter type: note, or default for docs/)
    report      reports/*.md

Edge predicates (frontmatter, top-level)
-----------------------------------------
    depends_on   any node     → target node(s)
    verifies     report       → target phase/fix node
    informs      research/note/decision → target node(s)
    parent       fix-round    → parent phase node
    mentions     (body [[wikilinks]]) — low-confidence navigation links
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    print(
        "ERROR: PyYAML is required but not installed.\n"
        "       Run:  pip install pyyaml\n"
        "       Then re-run this script.",
        file=sys.stderr,
    )
    sys.exit(2)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAPH_PAGE_PATTERNS: list[tuple[str, str]] = [
    # (glob_pattern relative to agents_dir, default node_type)
    ("roadmap/PHASE_*.md", "phase"),
    ("roadmap/FIX_*.md", "fix-round"),
    ("research/*.md", "research"),
    ("docs/*.md", "note"),  # refined per-file by frontmatter type:
    ("reports/*.md", "report"),
]

# Files/dirs to never include, relative to agents_dir root
SKIP_FILES = {
    "SCHEMA.md",
    "index.md",
    "log.md",
    "README.md",
    "ALL.md",
}
SKIP_DIRS = {
    "graph",
    "references",
    "raw",
    "project",
}

# Frontmatter fields that carry typed edge targets
EDGE_FIELDS: dict[str, str] = {
    "depends_on": "depends_on",
    "verifies": "verifies",
    "informs": "informs",
    "parent": "parent",
}

# Regex that matches [[any/path/here]] wikilinks
WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+?)(?:[|#][^\[\]]*)?\]\]")

# Regex for the first markdown heading
HEADING_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def edge_id(subject: str, predicate: str, obj: str) -> str:
    """Deterministic 24-char hex ID for an edge triple."""
    raw = f"{subject}\x00{predicate}\x00{obj}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """
    Split a markdown file into (frontmatter_dict, body_text).
    Returns ({}, text) when no frontmatter block is present.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, body


def extract_title(body: str, slug: str) -> str:
    """Return first H1 heading from body, or fall back to slug basename."""
    m = HEADING_RE.search(body)
    if m:
        return m.group(1).strip()
    return Path(slug).name


def resolve_wikilink(raw_target: str, agents_dir: Path) -> str:
    """
    Normalise a raw wikilink target to a canonical node ID.

    Input examples
    --------------
        [[roadmap/PHASE_1]]          → roadmap/PHASE_1
        roadmap/PHASE_1              → roadmap/PHASE_1
        [[research/nosmar-analysis]] → research/nosmar-analysis
    """
    target = raw_target.strip().strip("[]")
    # Remove .md extension if present
    if target.endswith(".md"):
        target = target[:-3]
    # Remove leading agents/ prefix if someone included it
    if target.startswith("agents/"):
        target = target[len("agents/") :]
    return target


def parse_edge_field(value: Any) -> list[str]:
    """
    Accept a frontmatter edge field value that can be:
      - a single string   "[[roadmap/PHASE_1]]"
      - a list            ["[[roadmap/PHASE_1]]", "[[roadmap/PHASE_2]]"]
    Returns a flat list of raw target strings (without [[ ]]).
    """
    if isinstance(value, str):
        items: list[str] = [value]
    elif isinstance(value, list):
        items = [str(v) for v in value]
    else:
        return []
    result: list[str] = []
    for item in items:
        # Strip outer [[ ]] if present
        inner = item.strip()
        if inner.startswith("[[") and inner.endswith("]]"):
            inner = inner[2:-2]
        # Handle pipe aliases  [[path|alias]]
        inner = inner.split("|")[0].split("#")[0].strip()
        if inner:
            result.append(inner)
    return result


def infer_node_type(fm: dict[str, Any], default_type: str) -> str:
    """
    Use frontmatter `type:` field to refine the node type.
    For docs/ pages the default_type is 'note'; frontmatter may override
    it to 'decision'.
    """
    fm_type = str(fm.get("type", "")).strip().lower()
    if fm_type in {"phase", "fix-round", "research", "decision", "note", "report"}:
        return fm_type
    return default_type


def safe_int(value: Any) -> int | None:
    """Convert value to int, return None on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def file_rel_slug(agents_dir: Path, file_path: Path) -> str:
    """
    Return canonical node ID / slug for a file path.
    e.g.  <agents_dir>/roadmap/PHASE_1.md  →  roadmap/PHASE_1
    """
    rel = file_path.relative_to(agents_dir)
    parts = list(rel.parts)
    # Strip .md extension from last component
    parts[-1] = Path(parts[-1]).stem
    return "/".join(parts)


# ---------------------------------------------------------------------------
# File walking
# ---------------------------------------------------------------------------


def collect_files(agents_dir: Path) -> list[tuple[Path, str]]:
    """
    Walk GRAPH_PAGE_PATTERNS and return (file_path, default_node_type) pairs.
    Skips files/dirs listed in SKIP_FILES / SKIP_DIRS.
    """
    import glob as _glob

    results: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    for pattern, default_type in GRAPH_PAGE_PATTERNS:
        matched = sorted(agents_dir.glob(pattern))
        for path in matched:
            # Normalise to absolute resolved path
            path = path.resolve()
            if path in seen:
                continue
            # Skip if any ancestor dir is in SKIP_DIRS
            rel = path.relative_to(agents_dir.resolve())
            if rel.parts[0] in SKIP_DIRS:
                continue
            if path.name in SKIP_FILES:
                continue
            seen.add(path)
            results.append((path, default_type))

    return results


# ---------------------------------------------------------------------------
# Node extraction
# ---------------------------------------------------------------------------


def build_node(
    agents_dir: Path,
    file_path: Path,
    default_type: str,
) -> dict[str, Any]:
    """Parse one markdown file and return a node dict."""
    text = file_path.read_text(encoding="utf-8-sig", errors="replace")
    fm, body = parse_frontmatter(text)

    slug = file_rel_slug(agents_dir, file_path)
    node_type = infer_node_type(fm, default_type)
    title = extract_title(body, slug)

    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = []

    # Collect remaining frontmatter as metadata (exclude well-known cols)
    well_known = {
        "type",
        "status",
        "tags",
        "phase",
        "opened",
        "closed",
        "test_status",
        "depends_on",
        "verifies",
        "informs",
        "parent",
        "title",
    }
    metadata = {k: v for k, v in fm.items() if k not in well_known}

    return {
        "id": slug,
        "slug": slug,
        "title": str(fm.get("title", title)),
        "page_type": str(fm.get("type", default_type)),
        "node_type": node_type,
        "path": str(file_path.relative_to(agents_dir)).replace("\\", "/"),
        "status": str(fm.get("status", "")) or None,
        "phase_num": safe_int(fm.get("phase")),
        "opened": str(fm.get("opened", "")) or None,
        "closed": str(fm.get("closed", "")) or None,
        "test_status": str(fm.get("test_status", "")) or None,
        "tags_json": json.dumps(tags),
        "metadata_json": json.dumps(metadata),
        # Keep raw frontmatter for edge extraction (not written to SQLite directly)
        "_fm": fm,
        "_body": body,
    }


# ---------------------------------------------------------------------------
# Edge extraction
# ---------------------------------------------------------------------------


def build_edges(
    node: dict[str, Any],
    agents_dir: Path,
    known_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract all edges for a single node."""
    edges: list[dict[str, Any]] = []
    subject = node["id"]
    fm: dict[str, Any] = node["_fm"]
    body: str = node["_body"]
    page = node["path"]

    # --- Frontmatter typed edges ---
    for fm_field, predicate in EDGE_FIELDS.items():
        raw_value = fm.get(fm_field)
        if raw_value is None:
            continue
        for raw_target in parse_edge_field(raw_value):
            obj = resolve_wikilink(raw_target, agents_dir)
            if not obj or obj == subject:
                continue
            edges.append(
                {
                    "id": edge_id(subject, predicate, obj),
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "extraction_method": "frontmatter",
                    "page": page,
                }
            )

    # --- Body wikilink mentions ---
    seen_mention_targets: set[str] = set()
    for m in WIKILINK_RE.finditer(body):
        raw_target = m.group(1).strip()
        obj = resolve_wikilink(raw_target, agents_dir)
        if not obj or obj == subject:
            continue
        # Only create mentions edge to known graph nodes
        if known_ids is not None and obj not in known_ids:
            continue
        if obj in seen_mention_targets:
            continue
        # Skip if already covered by a typed edge
        already_typed = any(
            e["object"] == obj and e["extraction_method"] == "frontmatter"
            for e in edges
        )
        if already_typed:
            continue
        seen_mention_targets.add(obj)
        edges.append(
            {
                "id": edge_id(subject, "mentions", obj),
                "subject": subject,
                "predicate": "mentions",
                "object": obj,
                "extraction_method": "wikilink",
                "page": page,
            }
        )

    return edges


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def write_jsonl(
    records: list[dict[str, Any]],
    out_path: Path,
    *,
    exclude_keys: set[str] | None = None,
) -> None:
    """Write records to a .jsonl file, optionally excluding internal keys."""
    exclude = exclude_keys or set()
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            clean = {k: v for k, v in rec.items() if k not in exclude}
            fh.write(json.dumps(clean, ensure_ascii=False) + "\n")


def write_sqlite(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    out_path: Path,
) -> None:
    """Write nodes and edges to a SQLite database."""
    import sqlite3

    if out_path.exists():
        out_path.unlink()

    con = sqlite3.connect(str(out_path))
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE nodes (
            id            TEXT PRIMARY KEY,
            slug          TEXT NOT NULL,
            title         TEXT NOT NULL,
            page_type     TEXT NOT NULL,
            node_type     TEXT NOT NULL,
            path          TEXT NOT NULL,
            status        TEXT,
            phase_num     INTEGER,
            opened        TEXT,
            closed        TEXT,
            test_status   TEXT,
            tags_json     TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );
        CREATE INDEX idx_nodes_type   ON nodes(node_type);
        CREATE INDEX idx_nodes_status ON nodes(status);

        CREATE TABLE edges (
            id                TEXT PRIMARY KEY,
            subject           TEXT NOT NULL,
            predicate         TEXT NOT NULL,
            object            TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            page              TEXT NOT NULL
        );
        CREATE INDEX idx_edges_subject   ON edges(subject);
        CREATE INDEX idx_edges_object    ON edges(object);
        CREATE INDEX idx_edges_predicate ON edges(predicate);
    """)

    for n in nodes:
        cur.execute(
            """
            INSERT OR REPLACE INTO nodes
              (id, slug, title, page_type, node_type, path,
               status, phase_num, opened, closed, test_status,
               tags_json, metadata_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                n["id"],
                n["slug"],
                n["title"],
                n["page_type"],
                n["node_type"],
                n["path"],
                n["status"],
                n["phase_num"],
                n["opened"],
                n["closed"],
                n["test_status"],
                n["tags_json"],
                n["metadata_json"],
            ),
        )

    for e in edges:
        cur.execute(
            """
            INSERT OR REPLACE INTO edges
              (id, subject, predicate, object, extraction_method, page)
            VALUES (?,?,?,?,?,?)
            """,
            (
                e["id"],
                e["subject"],
                e["predicate"],
                e["object"],
                e["extraction_method"],
                e["page"],
            ),
        )

    con.commit()
    con.close()


def write_graphml(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    out_path: Path,
) -> None:
    """Write a GraphML file compatible with Gephi / yEd."""
    # Namespace
    NS = "http://graphml.graphdrawing.org/graphml"
    ET.register_namespace("", NS)

    root = ET.Element(f"{{{NS}}}graphml")

    # Attribute keys for nodes
    node_attr_defs = [
        ("d_title", "title", "node", "string"),
        ("d_node_type", "node_type", "node", "string"),
        ("d_status", "status", "node", "string"),
        ("d_phase_num", "phase_num", "node", "int"),
        ("d_opened", "opened", "node", "string"),
        ("d_closed", "closed", "node", "string"),
        ("d_test_status", "test_status", "node", "string"),
        ("d_path", "path", "node", "string"),
    ]
    for key_id, attr_name, for_, type_ in node_attr_defs:
        key_el = ET.SubElement(
            root,
            f"{{{NS}}}key",
            id=key_id,
            attrib={"for": for_, "attr.name": attr_name, "attr.type": type_},
        )

    # Attribute keys for edges
    edge_attr_defs = [
        ("d_predicate", "predicate", "edge", "string"),
        ("d_extraction_method", "extraction_method", "edge", "string"),
        ("d_page", "page", "edge", "string"),
    ]
    for key_id, attr_name, for_, type_ in edge_attr_defs:
        ET.SubElement(
            root,
            f"{{{NS}}}key",
            id=key_id,
            attrib={"for": for_, "attr.name": attr_name, "attr.type": type_},
        )

    graph_el = ET.SubElement(root, f"{{{NS}}}graph", id="G", edgedefault="directed")

    def data_el(parent: ET.Element, key: str, value: Any) -> None:
        if value is None:
            return
        d = ET.SubElement(parent, f"{{{NS}}}data", key=key)
        d.text = str(value)

    for n in nodes:
        node_el = ET.SubElement(graph_el, f"{{{NS}}}node", id=n["id"])
        data_el(node_el, "d_title", n["title"])
        data_el(node_el, "d_node_type", n["node_type"])
        data_el(node_el, "d_status", n["status"])
        data_el(node_el, "d_phase_num", n["phase_num"])
        data_el(node_el, "d_opened", n["opened"])
        data_el(node_el, "d_closed", n["closed"])
        data_el(node_el, "d_test_status", n["test_status"])
        data_el(node_el, "d_path", n["path"])

    for e in edges:
        edge_el = ET.SubElement(
            graph_el,
            f"{{{NS}}}edge",
            id=e["id"],
            source=e["subject"],
            target=e["object"],
        )
        data_el(edge_el, "d_predicate", e["predicate"])
        data_el(edge_el, "d_extraction_method", e["extraction_method"])
        data_el(edge_el, "d_page", e["page"])

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(out_path), encoding="unicode", xml_declaration=True)


def write_summary(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    out_path: Path,
    agents_dir: Path,
    elapsed_s: float,
) -> None:
    """Write a human-readable summary.md."""
    from collections import Counter

    type_counts: Counter[str] = Counter(n["node_type"] for n in nodes)
    pred_counts: Counter[str] = Counter(e["predicate"] for e in edges)
    method_counts: Counter[str] = Counter(e["extraction_method"] for e in edges)

    lines = [
        "# WUR Graph Extract Summary",
        "",
        f"**Source:** `{agents_dir.as_posix()}`  ",
        f"**Extracted:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ",
        f"**Duration:** {elapsed_s:.2f}s",
        "",
        "## Node Counts",
        "",
        "| Type | Count |",
        "|------|-------|",
    ]
    for nt in sorted(type_counts):
        lines.append(f"| {nt} | {type_counts[nt]} |")
    lines += [
        "",
        f"**Total nodes:** {len(nodes)}",
        "",
        "## Edge Counts",
        "",
        "| Predicate | Count |",
        "|-----------|-------|",
    ]
    for pred in sorted(pred_counts):
        lines.append(f"| {pred} | {pred_counts[pred]} |")
    lines += [
        "",
        "| Extraction method | Count |",
        "|-------------------|-------|",
    ]
    for meth in sorted(method_counts):
        lines.append(f"| {meth} | {method_counts[meth]} |")
    lines += [
        "",
        f"**Total edges:** {len(edges)}",
        "",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_last_extracted(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    out_path: Path,
) -> None:
    """Write last_extracted.md — lightweight stamp used by lint staleness check."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = f"timestamp: {ts}\nnode_count: {len(nodes)}\nedge_count: {len(edges)}\n"
    out_path.write_text(content, encoding="utf-8")


def append_log_entry(
    agents_dir: Path,
    node_count: int,
    edge_count: int,
) -> None:
    """Append one line to agents/roadmap/log.md (if it exists)."""
    log_path = agents_dir / "roadmap" / "log.md"
    if not log_path.exists():
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = (
        f"| {today} | wiki-graph-extract | {node_count} nodes, {edge_count} edges |\n"
    )
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a typed graph from an agents/ WUR workspace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "agents_dir",
        help="Path to the agents/ directory (e.g. path/to/project/agents)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory (default: <agents_dir>/graph/)",
    )
    parser.add_argument(
        "--formats",
        default="jsonl,sqlite,graphml",
        help="Comma-separated list of output formats: jsonl, sqlite, graphml (default: all)",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Skip appending to agents/roadmap/log.md",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import time

    args = parse_args(argv)
    agents_dir = Path(args.agents_dir).resolve()

    if not agents_dir.is_dir():
        print(f"ERROR: agents_dir not found: {agents_dir}", file=sys.stderr)
        return 1

    out_dir = Path(args.out).resolve() if args.out else agents_dir / "graph"
    out_dir.mkdir(parents=True, exist_ok=True)

    formats = {f.strip().lower() for f in args.formats.split(",")}
    valid_formats = {"jsonl", "sqlite", "graphml"}
    unknown = formats - valid_formats
    if unknown:
        print(
            f"ERROR: Unknown format(s): {', '.join(sorted(unknown))}. "
            f"Valid: {', '.join(sorted(valid_formats))}",
            file=sys.stderr,
        )
        return 1

    print(f"[wur_graph_extract] agents_dir : {agents_dir}")
    print(f"[wur_graph_extract] output dir : {out_dir}")
    print(f"[wur_graph_extract] formats    : {', '.join(sorted(formats))}")

    start = time.monotonic()

    # --- Collect files ---
    files = collect_files(agents_dir)
    print(f"[wur_graph_extract] found {len(files)} graph page(s)")

    # --- Build nodes ---
    raw_nodes: list[dict[str, Any]] = []
    for file_path, default_type in files:
        try:
            node = build_node(agents_dir, file_path, default_type)
            raw_nodes.append(node)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN: skipping {file_path.name}: {exc}", file=sys.stderr)

    # --- Build edges (only to known graph nodes) ---
    known_ids: set[str] = {n["id"] for n in raw_nodes}
    raw_edges: list[dict[str, Any]] = []
    for node in raw_nodes:
        try:
            raw_edges.extend(build_edges(node, agents_dir, known_ids))
        except Exception as exc:  # noqa: BLE001
            print(
                f"  WARN: edge extraction failed for {node['id']}: {exc}",
                file=sys.stderr,
            )

    # Deduplicate edges by ID
    seen_edge_ids: set[str] = set()
    edges: list[dict[str, Any]] = []
    for e in raw_edges:
        if e["id"] not in seen_edge_ids:
            seen_edge_ids.add(e["id"])
            edges.append(e)

    # Strip internal keys from node dicts before writing
    INTERNAL_KEYS = {"_fm", "_body"}
    nodes = [{k: v for k, v in n.items() if k not in INTERNAL_KEYS} for n in raw_nodes]

    elapsed = time.monotonic() - start
    print(
        f"[wur_graph_extract] {len(nodes)} node(s), {len(edges)} edge(s) in {elapsed:.2f}s"
    )

    # --- Write outputs ---
    if "jsonl" in formats:
        nodes_path = out_dir / "nodes.jsonl"
        edges_path = out_dir / "edges.jsonl"
        write_jsonl(nodes, nodes_path)
        write_jsonl(edges, edges_path)
        print(f"[wur_graph_extract] wrote {nodes_path.name}, {edges_path.name}")

    if "sqlite" in formats:
        sqlite_path = out_dir / "graph.sqlite"
        write_sqlite(raw_nodes, edges, sqlite_path)
        print(f"[wur_graph_extract] wrote {sqlite_path.name}")

    if "graphml" in formats:
        graphml_path = out_dir / "graph.graphml"
        write_graphml(nodes, edges, graphml_path)
        print(f"[wur_graph_extract] wrote {graphml_path.name}")

    # Always write summary. Write last_extracted.md *after* appending to log.md so
    # a fresh extract is not immediately marked stale by the log entry itself.
    summary_path = out_dir / "summary.md"
    last_path = out_dir / "last_extracted.md"
    write_summary(nodes, edges, summary_path, agents_dir, elapsed)

    # Append to log.md before stamping last_extracted.md.
    if not args.no_log:
        append_log_entry(agents_dir, len(nodes), len(edges))

    write_last_extracted(nodes, edges, last_path)
    print(f"[wur_graph_extract] wrote {summary_path.name}, {last_path.name}")

    print("[wur_graph_extract] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
