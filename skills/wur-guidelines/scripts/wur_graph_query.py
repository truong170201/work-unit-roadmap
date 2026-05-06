#!/usr/bin/env python3
"""
wur_graph_query.py — Query agents/ graph (graph.sqlite preferred, JSONL fallback).

Commands:
    neighbors  --node <slug>               All directly connected nodes (in + out)
    edges      --subject <slug>            Outgoing edges from subject, grouped by predicate
    path       --from <slug> --to <slug>   Shortest path between two nodes (BFS)
    facts      --about <slug>              Node info + all typed relationships
    status     --filter active|done|...   All pages with the given status value

Usage:
    python wur_graph_query.py <agents_dir> <command> [options] [--json]

Examples:
    python wur_graph_query.py agents/ facts --about roadmap/PHASE_2
    python wur_graph_query.py agents/ status --filter active
    python wur_graph_query.py agents/ path --from roadmap/PHASE_1 --to reports/phase1-verification
    python wur_graph_query.py agents/ neighbors --node roadmap/PHASE_2
    python wur_graph_query.py agents/ edges --subject roadmap/PHASE_2
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Backend: load graph data
# ---------------------------------------------------------------------------


def _load_sqlite(db_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load nodes and edges from graph.sqlite using the standard schema."""
    import sqlite3

    nodes: dict[str, Any] = {}
    edges: list[dict[str, Any]] = []

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute("SELECT * FROM nodes")
        for row in cur.fetchall():
            d = dict(row)
            nid = d.get("id") or d.get("slug", "")
            nodes[str(nid)] = d

        cur = con.execute("SELECT * FROM edges")
        for row in cur.fetchall():
            d = dict(row)
            edges.append(d)
    finally:
        con.close()

    return nodes, edges


def _load_jsonl(
    nodes_file: Path, edges_file: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load nodes and edges from JSONL files."""
    nodes: dict[str, Any] = {}
    edges: list[dict[str, Any]] = []

    if nodes_file.exists():
        for line in nodes_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                node = json.loads(line)
                nid = str(node.get("id") or node.get("slug", ""))
                if nid:
                    nodes[nid] = node
            except json.JSONDecodeError:
                pass

    if edges_file.exists():
        for line in edges_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                edges.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return nodes, edges


class GraphBackend:
    """Unified graph data accessor: sqlite preferred, JSONL fallback."""

    def __init__(self, agents_dir: Path) -> None:
        self.agents_dir = agents_dir.resolve()
        graph_dir = self.agents_dir / "graph"
        db_path = graph_dir / "graph.sqlite"
        nodes_file = graph_dir / "nodes.jsonl"
        edges_file = graph_dir / "edges.jsonl"

        if db_path.exists():
            try:
                self.nodes, self.edges = _load_sqlite(db_path)
                self._source = "sqlite"
                return
            except Exception:
                pass  # fall through to JSONL

        if nodes_file.exists() or edges_file.exists():
            self.nodes, self.edges = _load_jsonl(nodes_file, edges_file)
            self._source = "jsonl"
        else:
            self.nodes = {}
            self.edges = []
            self._source = "none"

    def available(self) -> bool:
        return bool(self.nodes or self.edges)

    def source(self) -> str:
        return self._source

    # ------------------------------------------------------------------
    # Graph helpers
    # ------------------------------------------------------------------

    def _edge_subject(self, edge: dict) -> str:
        return str(edge.get("subject", edge.get("from", "")))

    def _edge_object(self, edge: dict) -> str:
        return str(edge.get("object", edge.get("to", "")))

    def _edge_predicate(self, edge: dict) -> str:
        return str(edge.get("predicate", edge.get("type", edge.get("kind", "related"))))

    def outgoing(self, node_id: str) -> list[dict]:
        return [e for e in self.edges if self._edge_subject(e) == node_id]

    def incoming(self, node_id: str) -> list[dict]:
        return [e for e in self.edges if self._edge_object(e) == node_id]

    def adjacency(self) -> dict[str, set[str]]:
        """Undirected adjacency map (for BFS path finding)."""
        adj: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            s = self._edge_subject(edge)
            o = self._edge_object(edge)
            if s and o:
                adj[s].add(o)
                adj[o].add(s)
        return dict(adj)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_neighbors(backend: GraphBackend, node: str, as_json: bool) -> int:
    """All directly connected nodes (in + out edges)."""
    if node not in backend.nodes:
        _die(f"node '{node}' not found in graph")

    out_edges = backend.outgoing(node)
    in_edges = backend.incoming(node)

    connected: dict[str, list[str]] = defaultdict(list)
    for e in out_edges:
        obj = backend._edge_object(e)
        pred = backend._edge_predicate(e)
        connected[obj].append(f"→{pred}")
    for e in in_edges:
        subj = backend._edge_subject(e)
        pred = backend._edge_predicate(e)
        connected[subj].append(f"←{pred}")

    if as_json:
        print(
            json.dumps(
                {
                    "node": node,
                    "neighbors": [
                        {"id": nid, "via": via} for nid, via in connected.items()
                    ],
                },
                indent=2,
            )
        )
    else:
        print(f"{node} — {len(connected)} neighbor(s)")
        for nid, via in sorted(connected.items()):
            via_str = ", ".join(via)
            label = _node_label(backend.nodes.get(nid, {}))
            print(f"  {nid}{label}  [{via_str}]")
    return 0


def cmd_edges(backend: GraphBackend, subject: str, as_json: bool) -> int:
    """All outgoing edges from subject, grouped by predicate."""
    if subject not in backend.nodes:
        _die(f"node '{subject}' not found in graph")

    out = backend.outgoing(subject)
    if not out:
        msg = f"{subject}: no outgoing edges"
        if as_json:
            print(json.dumps({"subject": subject, "edges": {}}))
        else:
            print(msg)
        return 0

    grouped: dict[str, list[str]] = defaultdict(list)
    for e in out:
        grouped[backend._edge_predicate(e)].append(backend._edge_object(e))

    if as_json:
        print(json.dumps({"subject": subject, "edges": dict(grouped)}, indent=2))
    else:
        print(f"{subject}")
        for pred, targets in sorted(grouped.items()):
            for t in sorted(targets):
                label = _node_label(backend.nodes.get(t, {}))
                print(f"  {pred}: {t}{label}")
    return 0


def cmd_path(backend: GraphBackend, src: str, dst: str, as_json: bool) -> int:
    """Shortest path between two nodes (BFS on undirected graph)."""
    for nid in (src, dst):
        if nid not in backend.nodes:
            _die(f"node '{nid}' not found in graph")

    adj = backend.adjacency()
    # BFS
    queue: deque[list[str]] = deque([[src]])
    visited: set[str] = {src}

    while queue:
        path = queue.popleft()
        current = path[-1]
        if current == dst:
            if as_json:
                print(
                    json.dumps(
                        {"from": src, "to": dst, "path": path, "hops": len(path) - 1}
                    )
                )
            else:
                arrow = " → ".join(path)
                print(f"Path ({len(path) - 1} hops): {arrow}")
            return 0
        for neighbor in sorted(adj.get(current, [])):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    if as_json:
        print(json.dumps({"from": src, "to": dst, "path": None, "hops": -1}))
    else:
        print(f"No path found between '{src}' and '{dst}'")
    return 0


def cmd_facts(backend: GraphBackend, about: str, as_json: bool) -> int:
    """Node info + all typed relationships."""
    # Try exact match first, then suffix match
    node_data = backend.nodes.get(about)
    if node_data is None:
        # Partial / suffix match
        for nid in backend.nodes:
            if nid.endswith(about) or about.endswith(nid):
                node_data = backend.nodes[nid]
                about = nid
                break
    if node_data is None:
        _die(f"node '{about}' not found in graph")

    out_edges = backend.outgoing(about)
    in_edges = backend.incoming(about)

    # Group outgoing by predicate
    out_grouped: dict[str, list[str]] = defaultdict(list)
    for e in out_edges:
        out_grouped[backend._edge_predicate(e)].append(backend._edge_object(e))

    # Group incoming by predicate (show as reverse)
    in_grouped: dict[str, list[str]] = defaultdict(list)
    for e in in_edges:
        in_grouped[backend._edge_predicate(e)].append(backend._edge_subject(e))

    if as_json:
        print(
            json.dumps(
                {
                    "id": about,
                    "node": node_data,
                    "outgoing": dict(out_grouped),
                    "incoming": {f"{pred}←": vals for pred, vals in in_grouped.items()},
                },
                indent=2,
            )
        )
        return 0

    # Human-readable output matching the spec example
    node_type = node_data.get("type", "?")
    node_status = node_data.get("status", "?")
    print(f"{about} [{node_type} | {node_status}]")

    for pred, targets in sorted(out_grouped.items()):
        for t in sorted(targets):
            print(f"  {pred}: {t}")

    for pred, sources in sorted(in_grouped.items()):
        for s in sorted(sources):
            print(f"  {pred}←: {s}")
    return 0


def cmd_status(backend: GraphBackend, status_filter: str, as_json: bool) -> int:
    """All nodes with the given status value."""
    matches = [
        (nid, data)
        for nid, data in backend.nodes.items()
        if str(data.get("status", "")).lower() == status_filter.lower()
    ]

    if as_json:
        print(
            json.dumps(
                {
                    "filter": status_filter,
                    "count": len(matches),
                    "nodes": [{"id": nid, **data} for nid, data in matches],
                },
                indent=2,
            )
        )
    else:
        print(f"Status '{status_filter}' — {len(matches)} page(s)")
        for nid, data in sorted(matches, key=lambda x: x[0]):
            node_type = data.get("type", "?")
            print(f"  {nid} [{node_type}]")
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node_label(data: dict) -> str:
    if not data:
        return ""
    parts = []
    if "type" in data:
        parts.append(data["type"])
    if "status" in data:
        parts.append(data["status"])
    return f" [{' | '.join(parts)}]" if parts else ""


def _die(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query the agents/ graph (graph.sqlite preferred, JSONL fallback).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("agents_dir", help="Path to the agents/ directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    sub = parser.add_subparsers(dest="command", required=True)

    # neighbors
    p_nb = sub.add_parser("neighbors", help="All directly connected nodes")
    p_nb.add_argument("--node", required=True, metavar="SLUG", help="Node slug/ID")

    # edges
    p_ed = sub.add_parser("edges", help="Outgoing edges from subject")
    p_ed.add_argument(
        "--subject", required=True, metavar="SLUG", help="Subject node slug/ID"
    )

    # path
    p_pa = sub.add_parser("path", help="Shortest path between two nodes")
    p_pa.add_argument("--from", dest="from_node", required=True, metavar="SLUG")
    p_pa.add_argument("--to", dest="to_node", required=True, metavar="SLUG")

    # facts
    p_fa = sub.add_parser("facts", help="Node info + all typed relationships")
    p_fa.add_argument("--about", required=True, metavar="SLUG", help="Node slug/ID")

    # status
    p_st = sub.add_parser("status", help="All pages with a given status")
    p_st.add_argument(
        "--filter",
        required=True,
        metavar="STATUS",
        help="Status value: active, done, blocked, planned, deferred, aborted",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    agents_dir = Path(args.agents_dir)
    if not agents_dir.is_dir():
        _die(f"agents_dir '{agents_dir}' does not exist or is not a directory")

    backend = GraphBackend(agents_dir)
    if not backend.available():
        _die(
            "no graph data found — run wur_graph_extract.py first "
            "(expected agents/graph/graph.sqlite or agents/graph/nodes.jsonl)"
        )

    as_json = args.json

    if args.command == "neighbors":
        return cmd_neighbors(backend, args.node, as_json)
    elif args.command == "edges":
        return cmd_edges(backend, args.subject, as_json)
    elif args.command == "path":
        return cmd_path(backend, args.from_node, args.to_node, as_json)
    elif args.command == "facts":
        return cmd_facts(backend, args.about, as_json)
    elif args.command == "status":
        return cmd_status(backend, args.filter, as_json)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
