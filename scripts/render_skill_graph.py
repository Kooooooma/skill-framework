#!/usr/bin/env python3
"""Render node.graph.json as a DOT graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import Report, topo_sort  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a skill node graph to DOT.")
    parser.add_argument("skill_path")
    parser.add_argument("--graph", default=None, help="Graph id. Defaults to the first graph.")
    parser.add_argument("-o", "--output", help="Write DOT to this file instead of stdout.")
    args = parser.parse_args()

    root = Path(args.skill_path).expanduser().resolve()
    graph_file = root / "node.graph.json"
    if not graph_file.exists():
        raise SystemExit(f"Missing node graph: {graph_file}")

    graph = json.loads(graph_file.read_text(encoding="utf-8"))
    graphs = graph.get("graphs", {})
    graph_id = args.graph or next(iter(graphs), None)
    if not graph_id or graph_id not in graphs:
        raise SystemExit("No matching graph found in node.graph.json")

    nodes = graphs[graph_id].get("nodes", {})
    report = Report()
    topo_sort(nodes, report, graph_id)
    if report.errors:
        for error in report.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    lines = ["digraph skill_graph {", "  rankdir=LR;"]
    for node in nodes:
        lines.append(f'  "{node}";')
    for node, spec in nodes.items():
        for dep in spec.get("depends_on", []):
            lines.append(f'  "{dep}" -> "{node}";')
    lines.append("}")
    dot = "\n".join(lines) + "\n"

    if args.output:
        Path(args.output).expanduser().resolve().write_text(dot, encoding="utf-8")
    else:
        print(dot, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
