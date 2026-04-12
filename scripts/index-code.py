#!/usr/bin/env python3
"""Rebuild the code intelligence index.

Supports:
  --incremental: Only re-index changed files (hash-based detection)
  --force: Force full re-index even if hashes match
  --file: Re-index a single file
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.code_intel.parser import CodeParser, ImportGraphBuilder
from ai.code_intel.store import get_code_store

PROJECT_ROOT = Path("/var/home/lch/projects/bazzite-laptop")


def main():
    parser = argparse.ArgumentParser(description="Rebuild code intelligence index")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only re-index changed files (hash-based detection)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full re-index (ignore incremental)",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Re-index a single file",
    )
    args = parser.parse_args()

    code_parser = CodeParser(project_root=Path(__file__).parent.parent)
    store = get_code_store()

    # Single file mode
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / args.file

        print(f"Indexing single file: {file_path}")
        nodes, rels = code_parser.parse_file(str(file_path))
        print(f"Found {len(nodes)} nodes, {len(rels)} relationships")

        store.update_incremental([str(file_path)], code_parser)
        print(f"Indexed {len(nodes)} nodes, {len(rels)} relationships")
        return

    # Force full reindex
    if args.force or not args.incremental:
        print("Full re-index (use --incremental for faster updates)...")
        nodes, rels = code_parser.parse_project()
        print(f"Found {len(nodes)} nodes, {len(rels)} relationships")

        print("Indexing to LanceDB...")
        store.index_project(nodes, rels)

        print("Building import graph...")
        graph = ImportGraphBuilder().build()
        store.store_import_graph(graph)

        print("Mining change history...")
        store.mine_change_history(str(PROJECT_ROOT))

        print(f"Indexed {len(nodes)} nodes, {len(rels)} relationships")
        return

    # Incremental mode
    print("Incremental index (detecting changes)...")

    # Get current file hashes from store
    stored_hashes = store.get_file_hashes()
    print(f"Stored hashes: {len(stored_hashes)} files")

    # Get current project files and their hashes
    changed_files = []
    all_py_files = list(code_parser.project_root.rglob("*.py"))
    all_py_files = [
        f
        for f in all_py_files
        if not any(skip in str(f) for skip in ["__pycache__", ".venv", "node_modules", ".git"])
    ]

    for py_file in all_py_files:
        file_str = str(py_file)
        current_hash = code_parser.get_file_hash(file_str)
        stored_hash = stored_hashes.get(file_str)

        if stored_hash != current_hash:
            changed_files.append(file_str)

    if not changed_files:
        print("No changes detected. Index is up to date.")
        return

    print(f"Changed files: {len(changed_files)}")
    for f in changed_files[:10]:  # Show first 10
        print(f"  - {f}")
    if len(changed_files) > 10:
        print(f"  ... and {len(changed_files) - 10} more")

    print("Updating index...")
    store.update_incremental(changed_files, code_parser)

    # Also update import graph for changed modules
    print("Updating import graph...")
    graph = ImportGraphBuilder().build()
    # Note: This adds new edges, doesn't replace. Full rebuild needed for import changes.
    store.store_import_graph(graph)

    print(f"Indexed {len(changed_files)} changed files")


if __name__ == "__main__":
    main()
