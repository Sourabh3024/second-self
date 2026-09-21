#!/usr/bin/env python3
"""Build data/graph.json from classified wiki notes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secondself.graph import build_and_write_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a knowledge graph from wiki notes.")
    parser.add_argument("--wiki-dir", help="Wiki directory. Defaults to the configured wiki directory.")
    parser.add_argument("--output", help="Output JSON path. Defaults to data/graph.json.")
    args = parser.parse_args()

    graph, output_path = build_and_write_graph(args.wiki_dir, args.output)
    print(f"Wrote graph to {output_path}")
    print(f"Nodes: {graph['metadata']['node_count']}")
    print(f"Edges: {graph['metadata']['edge_count']}")


if __name__ == "__main__":
    main()
