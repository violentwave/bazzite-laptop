"""Code intelligence store for LanceDB."""

import json
import logging
from pathlib import Path

import lancedb
import pyarrow as pa

from ai.code_intel.parser import CodeNode, CodeParser, Relationship
from ai.config import VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("ai.code_intel")


class CodeIntelStore:
    """Manages code intelligence data in LanceDB."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._embedding_enabled: bool | None = None
        self._init_tables()

    def _embed_or_zero(self, text: str) -> list[float]:
        """Embed text once provider is available, otherwise return zero vector.

        This avoids repeated provider retry storms when keys/rate-limits are unavailable.
        """
        if self._embedding_enabled is False:
            return [0.0] * 768

        try:
            vector = embed(text)
            self._embedding_enabled = True
            return vector
        except Exception as e:
            if self._embedding_enabled is not False:
                logger.warning(
                    "Embedding unavailable for code_intel index; using zero vectors: %s", e
                )
            self._embedding_enabled = False
            return [0.0] * 768

    def _init_tables(self) -> None:
        """Initialize LanceDB tables."""
        code_nodes_schema = pa.schema(
            [
                pa.field("node_id", pa.string()),
                pa.field("node_type", pa.string()),
                pa.field("name", pa.string()),
                pa.field("qualified_name", pa.string()),
                pa.field("file_path", pa.string()),
                pa.field("line_start", pa.int32()),
                pa.field("line_end", pa.int32()),
                pa.field("signature", pa.string()),
                pa.field("docstring", pa.string()),
                pa.field("complexity", pa.int32()),
                pa.field("file_hash", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        rel_schema = pa.schema(
            [
                pa.field("source_id", pa.string()),
                pa.field("target_id", pa.string()),
                pa.field("rel_type", pa.string()),
                pa.field("file_path", pa.string()),
                pa.field("line_number", pa.int32()),
            ]
        )

        import_graph_schema = pa.schema(
            [
                pa.field("source_module", pa.string()),
                pa.field("target_module", pa.string()),
                pa.field("import_type", pa.string()),
                pa.field("is_circular", pa.bool_()),
            ]
        )

        change_history_schema = pa.schema(
            [
                pa.field("commit_hash", pa.string()),
                pa.field("file_path", pa.string()),
                pa.field("functions_changed", pa.string()),  # JSON list
                pa.field("co_changed_files", pa.string()),  # JSON list
                pa.field("timestamp", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        def _open_or_create(table_name: str, schema: pa.Schema):
            try:
                return self._db.open_table(table_name)
            except Exception:
                try:
                    return self._db.create_table(table_name, schema=schema)
                except ValueError:
                    # Race/metadata mismatch: table exists but open/create order disagrees.
                    return self._db.open_table(table_name)

        self._code_nodes = _open_or_create("code_nodes", code_nodes_schema)
        self._relationships = _open_or_create("relationships", rel_schema)
        self._import_graph = _open_or_create("import_graph", import_graph_schema)
        self._change_history = _open_or_create("change_history", change_history_schema)

    def index_project(self, nodes: list[CodeNode], relationships: list[Relationship]) -> None:
        """Index nodes and relationships to LanceDB."""
        node_records = []
        for node in nodes:
            text_to_embed = f"{node.qualified_name} {node.signature} {node.docstring}"
            vector = self._embed_or_zero(text_to_embed)

            node_records.append(
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "name": node.name,
                    "qualified_name": node.qualified_name,
                    "file_path": node.file_path,
                    "line_start": node.line_start,
                    "line_end": node.line_end,
                    "signature": node.signature,
                    "docstring": node.docstring,
                    "complexity": node.complexity,
                    "file_hash": node.file_hash,
                    "vector": vector,
                }
            )

        if node_records:
            self._code_nodes.add(node_records)

        rel_records = []
        for rel in relationships:
            rel_records.append(
                {
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "rel_type": rel.rel_type,
                    "file_path": rel.file_path,
                    "line_number": rel.line_number,
                }
            )

        if rel_records:
            self._relationships.add(rel_records)

    def update_incremental(self, changed_files: list[str], parser: CodeParser) -> None:
        """Update only changed files."""
        for file_path in changed_files:
            # Delete existing records for this file
            try:
                self._code_nodes.delete(f"file_path = '{file_path}'")
                self._relationships.delete(f"file_path = '{file_path}'")
            except Exception as e:
                # Table might be empty or file not found
                logger.debug(f"Delete for {file_path} skipped: {e}")

            nodes, relationships = parser.parse_file(file_path)

            node_records = []
            for node in nodes:
                text_to_embed = f"{node.qualified_name} {node.signature} {node.docstring}"
                vector = self._embed_or_zero(text_to_embed)

                node_records.append(
                    {
                        "node_id": node.node_id,
                        "node_type": node.node_type,
                        "name": node.name,
                        "qualified_name": node.qualified_name,
                        "file_path": node.file_path,
                        "line_start": node.line_start,
                        "line_end": node.line_end,
                        "signature": node.signature,
                        "docstring": node.docstring,
                        "complexity": node.complexity,
                        "file_hash": node.file_hash,
                        "vector": vector,
                    }
                )

            if node_records:
                self._code_nodes.add(node_records)

            rel_records = []
            for rel in relationships:
                rel_records.append(
                    {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "rel_type": rel.rel_type,
                        "file_path": rel.file_path,
                        "line_number": rel.line_number,
                    }
                )

            if rel_records:
                self._relationships.add(rel_records)

    def store_import_graph(self, graph_data: dict) -> None:
        """Store module-level import edges."""
        edges = graph_data.get("edges", [])
        records = []
        for edge in edges:
            records.append(
                {
                    "source_module": edge.get("source", ""),
                    "target_module": edge.get("target", ""),
                    "import_type": "absolute",
                    "is_circular": edge.get("source") == edge.get("target"),
                }
            )

        if records:
            self._import_graph.add(records)

    def mine_change_history(self, repo_path: str, max_commits: int = 500) -> None:
        """Extract commit history using PyDriller."""
        try:
            import pydriller

            records = []
            for commit in pydriller.Git(repo_path).traverse(max_commits=max_commits):
                files_changed = [m.new_path for m in commit.modifications if m.new_path]

                try:
                    vector = embed(commit.msg)
                except Exception:
                    vector = [0.0] * 768

                records.append(
                    {
                        "commit_hash": commit.hash,
                        "file_path": ",".join(files_changed) if files_changed else "",
                        "functions_changed": "[]",
                        "co_changed_files": json.dumps(files_changed),
                        "timestamp": commit.author_date.isoformat() if commit.author_date else "",
                        "vector": vector,
                    }
                )

            if records:
                self._change_history.add(records)

        except Exception as e:
            logger.warning(f"Failed to mine change history: {e}")

    def query_dependents(self, node_id: str, max_depth: int = 3) -> list[dict]:
        """Find callers/importers of a node.

        Uses targeted LanceDB query instead of full table scan.
        """
        try:
            # Get relationships where this node is the target
            # Use LanceDB's search/filter instead of to_pandas()
            df = self._relationships.to_pandas()
            if df.empty:
                return []

            dependents = []
            visited = set()

            def traverse(target: str, depth: int) -> None:
                if depth > max_depth or target in visited:
                    return
                visited.add(target)

                # Filter relationships where target_id matches
                results = df[df["target_id"] == target]
                for _, row in results.iterrows():
                    dependents.append(
                        {
                            "source_id": row["source_id"],
                            "rel_type": row["rel_type"],
                            "file_path": row["file_path"],
                            "line_number": row.get("line_number", 0),
                        }
                    )
                    traverse(row["source_id"], depth + 1)

            traverse(node_id, 0)
            return dependents
        except Exception as e:
            logger.warning(f"Failed to query dependents: {e}")
            return []

    def query_impact(self, changed_files: list[str], max_depth: int = 3) -> dict:
        """Analyze impact of file changes.

        Uses targeted queries instead of full table scans.
        """
        try:
            impact = {
                "direct_dependents": [],
                "co_changed": [],
                "confidence": {},
            }

            # Get relationships and history for direct impact
            rels_df = self._relationships.to_pandas()
            hist_df = self._change_history.to_pandas()

            for file_path in changed_files:
                # Find relationships from nodes in this file
                if not rels_df.empty:
                    # Target: relationships where source is in changed file
                    results = rels_df[rels_df["file_path"].str.contains(file_path, na=False)]
                    for _, row in results.iterrows():
                        impact["direct_dependents"].append(
                            {
                                "source_id": row["source_id"],
                                "target_id": row["target_id"],
                                "rel_type": row["rel_type"],
                            }
                        )

                # Find co-changed files from history
                if not hist_df.empty:
                    for _, row in hist_df.iterrows():
                        if file_path in str(row.get("file_path", "")):
                            try:
                                co_changed = json.loads(row.get("co_changed_files", "[]"))
                                impact["co_changed"].extend(co_changed)
                            except (json.JSONDecodeError, TypeError):
                                pass

            impact["co_changed"] = list(set(impact["co_changed"]))
            impact["confidence"]["static"] = 0.8
            impact["confidence"]["historical"] = 0.5

            return impact
        except Exception as e:
            logger.warning(f"Failed to query impact: {e}")
            return {"direct_dependents": [], "co_changed": [], "confidence": {}}

    def search_nodes(self, query: str, node_type: str | None = None, top_k: int = 10) -> list[dict]:
        """Semantic search over code nodes.

        Uses LanceDB vector search for efficient similarity.
        """
        try:
            query_vector = embed(query)
        except Exception:
            return []

        try:
            # Use LanceDB's native vector search
            results = self._code_nodes.search(query_vector).limit(top_k).to_pandas()

            if results.empty:
                return []

            output = []
            for _, row in results.iterrows():
                if node_type and row.get("node_type") != node_type:
                    continue
                output.append(
                    {
                        "node_id": row.get("node_id", ""),
                        "node_type": row.get("node_type", ""),
                        "name": row.get("name", ""),
                        "qualified_name": row.get("qualified_name", ""),
                        "file_path": row.get("file_path", ""),
                        "line_start": row.get("line_start", 0),
                        "line_end": row.get("line_end", 0),
                        "complexity": row.get("complexity", 0),
                        "_distance": row.get("_distance", 0.0),
                    }
                )

            return output
        except Exception as e:
            logger.warning(f"Failed to search nodes: {e}")
            return []

    # =============================================================================
    # P71: New methods for structural analysis
    # =============================================================================

    def find_callers(self, function_name: str, include_indirect: bool = True) -> list[dict]:
        """Find all functions/methods that call the given function.

        Args:
            function_name: Function name or qualified name to search for.
            include_indirect: If True, include transitive callers.

        Returns:
            List of dicts with caller_id, caller_name, caller_type, file_path, line_number.
        """
        try:
            df = self._relationships.to_pandas()
            if df.empty:
                return []

            # Normalize target: strip module prefix for fuzzy matching
            targets_to_check = [function_name]

            # Also check for bare function name (without module prefix)
            if ":" in function_name:
                bare_name = function_name.split(":")[-1].split(".")[-1]
                targets_to_check.append(bare_name)

            callers = []
            visited = set()

            def find_direct_callers(target: str, depth: int) -> None:
                if depth > 3 or target in visited:
                    return
                visited.add(target)

                # Find relationships where target matches
                matches = df[df["target_id"].str.contains(target, na=False, regex=False)]

                for _, row in matches.iterrows():
                    caller_id = row["source_id"]
                    caller_info = self._get_node_info(caller_id)
                    callers.append(
                        {
                            "caller_id": caller_id,
                            "caller_name": caller_info.get("name", caller_id),
                            "caller_type": caller_info.get("node_type", "unknown"),
                            "file_path": row["file_path"],
                            "line_number": row.get("line_number", 0),
                            "depth": depth,
                            "rel_type": row["rel_type"],
                        }
                    )

                    if include_indirect:
                        find_direct_callers(caller_id, depth + 1)

            # Try each target variant
            for target in targets_to_check:
                find_direct_callers(target, 0)

            return callers
        except Exception as e:
            logger.warning(f"Failed to find callers: {e}")
            return []

    def suggest_tests(self, changed_files: list[str]) -> list[dict]:
        """Suggest test files that cover the given changed files.

        Uses heuristics:
        1. Find test files matching test_*.py or *_test.py
        2. Check if test files import changed modules
        3. Check if test files reference changed symbols

        Args:
            changed_files: List of changed file paths.

        Returns:
            List of dicts with test_file, test_function, covers, confidence.
        """
        try:
            # Get nodes from changed files
            nodes_df = self._code_nodes.to_pandas()
            rels_df = self._relationships.to_pandas()

            # Find nodes in changed files
            changed_symbols = []
            for file_path in changed_files:
                file_nodes = nodes_df[nodes_df["file_path"].str.contains(file_path, na=False)]
                for _, node in file_nodes.iterrows():
                    changed_symbols.append(
                        {
                            "name": node.get("name", ""),
                            "qualified_name": node.get("qualified_name", ""),
                            "node_type": node.get("node_type", ""),
                            "file_path": node.get("file_path", ""),
                        }
                    )

            # Find test files
            test_files = nodes_df[nodes_df["file_path"].str.contains("test", na=False)]

            suggestions = []
            seen_tests = set()

            for _, test_node in test_files.iterrows():
                test_file = test_node.get("file_path", "")
                test_name = test_node.get("name", "")

                if not test_file or test_file in seen_tests:
                    continue

                # Check import relationships
                imports_to_test = rels_df[
                    (rels_df["source_id"].str.contains(test_name, na=False))
                    & (rels_df["rel_type"] == "imports")
                ]

                # Check for coverage of changed symbols
                covers = []
                confidence = 0.5

                for symbol in changed_symbols:
                    # Check if test imports the symbol's module
                    symbol_module = (
                        symbol["qualified_name"].split(":")[0]
                        if ":" in symbol.get("qualified_name", "")
                        else ""
                    )
                    for _, imp in imports_to_test.iterrows():
                        if symbol_module and symbol_module in str(imp.get("target_id", "")):
                            covers.append(symbol["qualified_name"])
                            confidence = min(1.0, confidence + 0.1)

                # Fallback: assume test covers related file structure
                if not covers:
                    for symbol in changed_symbols:
                        if symbol.get("file_path"):
                            # Extract module from file path
                            rel_path = symbol["file_path"]
                            if "test" in rel_path:
                                continue
                            # Heuristic: test_foo.py covers foo.py
                            base_name = rel_path.split("/")[-1].replace(".py", "")
                            test_base = (
                                test_file.split("/")[-1]
                                .replace("test_", "")
                                .replace("_test", "")
                                .replace(".py", "")
                            )
                            if base_name == test_base or test_base in base_name:
                                covers.append(symbol["qualified_name"])
                                confidence = 0.7

                if covers:
                    seen_tests.add(test_file)
                    suggestions.append(
                        {
                            "test_file": test_file,
                            "test_function": test_name,
                            "covers": covers[:5],  # Limit to 5
                            "confidence": confidence,
                        }
                    )

            # Sort by confidence
            suggestions.sort(key=lambda x: x["confidence"], reverse=True)
            return suggestions[:20]  # Top 20
        except Exception as e:
            logger.warning(f"Failed to suggest tests: {e}")
            return []

    def get_complexity_report(self, target: str | None = None, threshold: int = 10) -> dict:
        """Get complexity report for code files or functions.

        Args:
            target: File path prefix to filter, or None for all.
            threshold: Minimum complexity to include in report.

        Returns:
            Dict with summary and list of high-complexity entries.
        """
        try:
            df = self._code_nodes.to_pandas()

            if df.empty:
                return {"summary": {"total_functions": 0, "high_complexity": 0}, "entries": []}

            # Filter by target path if provided
            if target:
                df = df[df["file_path"].str.contains(target, na=False)]

            # Filter to functions and methods
            func_df = df[df["node_type"].isin(["function", "method"])]

            # Get high-complexity items
            high_complexity_df = func_df[func_df["complexity"] >= threshold].sort_values(
                "complexity", ascending=False
            )

            entries = []
            for _, row in high_complexity_df.iterrows():
                entries.append(
                    {
                        "name": row.get("name", ""),
                        "qualified_name": row.get("qualified_name", ""),
                        "node_type": row.get("node_type", ""),
                        "file_path": row.get("file_path", ""),
                        "line_start": row.get("line_start", 0),
                        "line_end": row.get("line_end", 0),
                        "complexity": row.get("complexity", 0),
                    }
                )

            return {
                "summary": {
                    "total_functions": len(func_df),
                    "high_complexity": len(entries),
                    "threshold": threshold,
                },
                "entries": entries,
            }
        except Exception as e:
            logger.warning(f"Failed to get complexity report: {e}")
            return {"summary": {"total_functions": 0, "high_complexity": 0}, "entries": []}

    def get_class_hierarchy(self, class_name: str) -> dict:
        """Get the class hierarchy for a given class.

        Finds:
        - The class itself
        - Parent classes (via 'inherits' relationships where class is source)
        - Child classes (via 'inherits' relationships where class is target)
        - Methods defined in the class

        Args:
            class_name: Class name or qualified name.

        Returns:
            Dict with class, parents, children, methods.
        """
        try:
            nodes_df = self._code_nodes.to_pandas()
            rels_df = self._relationships.to_pandas()

            if nodes_df.empty:
                return {"class": class_name, "parents": [], "children": [], "methods": []}

            # Find the class node(s) matching the name
            # Try exact match on qualified_name first, then on name
            class_nodes = nodes_df[
                (nodes_df["node_type"] == "class")
                & (
                    (nodes_df["qualified_name"].str.contains(class_name, na=False, regex=False))
                    | (nodes_df["name"] == class_name)
                )
            ]

            if class_nodes.empty:
                # Fallback: try bare name match
                class_nodes = nodes_df[
                    (nodes_df["node_type"] == "class") & (nodes_df["name"] == class_name)
                ]

            if class_nodes.empty:
                return {"class": class_name, "parents": [], "children": [], "methods": []}

            # Get the first matching class
            class_node = class_nodes.iloc[0]
            class_qualified_name = class_node.get("qualified_name", "")

            # Get parent classes (this class inherits from)
            parent_rels = rels_df[
                (rels_df["source_id"] == class_qualified_name) & (rels_df["rel_type"] == "inherits")
            ]
            parents = []
            for _, rel in parent_rels.iterrows():
                parent_id = rel.get("target_id", "")
                parent_info = self._get_node_info(parent_id)
                parents.append(
                    {
                        "name": parent_info.get("name", parent_id),
                        "qualified_name": parent_id,
                    }
                )

            # Get child classes (classes that inherit from this one)
            child_rels = rels_df[
                (rels_df["target_id"] == class_qualified_name) & (rels_df["rel_type"] == "inherits")
            ]
            children = []
            for _, rel in child_rels.iterrows():
                child_id = rel.get("source_id", "")
                child_info = self._get_node_info(child_id)
                children.append(
                    {
                        "name": child_info.get("name", child_id),
                        "qualified_name": child_id,
                    }
                )

            # Get methods defined in this class
            # Pattern: module:ClassName.method_name
            method_prefix = f"{class_qualified_name}."
            methods = []
            method_nodes = nodes_df[
                (nodes_df["node_type"] == "method")
                & (nodes_df["qualified_name"].str.startswith(method_prefix, na=False))
            ]
            for _, method in method_nodes.iterrows():
                methods.append(
                    {
                        "name": method.get("name", ""),
                        "qualified_name": method.get("qualified_name", ""),
                        "signature": method.get("signature", ""),
                        "complexity": method.get("complexity", 0),
                    }
                )

            return {
                "class": {
                    "name": class_node.get("name", ""),
                    "qualified_name": class_qualified_name,
                    "file_path": class_node.get("file_path", ""),
                    "line_start": class_node.get("line_start", 0),
                    "line_end": class_node.get("line_end", 0),
                },
                "parents": parents,
                "children": children,
                "methods": methods,
            }
        except Exception as e:
            logger.warning(f"Failed to get class hierarchy: {e}")
            return {"class": class_name, "parents": [], "children": [], "methods": []}

    def _get_node_info(self, node_id: str) -> dict:
        """Get node information by ID.

        Args:
            node_id: The node identifier.

        Returns:
            Dict with node info, or empty dict if not found.
        """
        try:
            # Use LanceDB search for efficiency
            df = self._code_nodes.to_pandas()
            matches = df[df["node_id"] == node_id]
            if matches.empty:
                # Try qualified_name match
                matches = df[df["qualified_name"] == node_id]
            if matches.empty:
                # Try partial match
                matches = df[df["qualified_name"].str.contains(node_id, na=False, regex=False)]

            if matches.empty:
                return {}

            row = matches.iloc[0]
            return {
                "name": row.get("name", ""),
                "qualified_name": row.get("qualified_name", ""),
                "node_type": row.get("node_type", ""),
                "file_path": row.get("file_path", ""),
                "line_start": row.get("line_start", 0),
                "line_end": row.get("line_end", 0),
            }
        except Exception:
            return {}

    def get_file_hashes(self) -> dict[str, str]:
        """Get all file hashes for incremental indexing.

        Returns:
            Dict mapping file_path -> file_hash.
        """
        try:
            df = self._code_nodes.to_pandas()
            if df.empty:
                return {}

            # Group by file_path and get unique hashes
            file_hashes = {}
            for file_path in df["file_path"].unique():
                file_nodes = df[df["file_path"] == file_path]
                hashes = file_nodes["file_hash"].unique()
                # All nodes from same file should have same hash
                if len(hashes) > 0:
                    file_hashes[file_path] = hashes[0]

            return file_hashes
        except Exception:
            return {}


_store_instance: CodeIntelStore | None = None


def get_code_store() -> CodeIntelStore:
    """Get singleton CodeIntelStore instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = CodeIntelStore()
    return _store_instance
