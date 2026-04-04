#!/usr/bin/env python3
"""Rebuild the code intelligence index."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.code_intel.parser import CodeParser, ImportGraphBuilder
from ai.code_intel.store import get_code_store


def main():
    parser = CodeParser()
    print("Parsing project...")
    nodes, rels = parser.parse_project()
    print(f"Found {len(nodes)} nodes, {len(rels)} relationships")

    store = get_code_store()
    print("Indexing to LanceDB...")
    store.index_project(nodes, rels)

    print("Building import graph...")
    graph = ImportGraphBuilder()
    graph_data = graph.build()
    store.store_import_graph(graph_data)

    repo_path = "/var/home/lch/projects/bazzite-laptop"
    print("Mining change history...")
    store.mine_change_history(repo_path)

    print(f"Indexed {len(nodes)} nodes, {len(rels)} relationships")


if __name__ == "__main__":
    main()
