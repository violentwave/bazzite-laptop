"""Code intelligence store for LanceDB."""

import hashlib
import json
import logging
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
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

    def store_import_graph(self, graph_data: dict, replace: bool = True) -> None:
        """Store module-level import edges.

        Args:
            graph_data: Graph payload from ImportGraphBuilder.
            replace: If True, replace existing rows before inserting.
        """
        edges = graph_data.get("edges", [])
        circular_edges = {
            (edge.get("source", ""), edge.get("target", ""))
            for edge in graph_data.get("circular", [])
            if edge.get("source") and edge.get("target")
        }

        if replace:
            try:
                # Delete all rows (portable LanceDB predicate).
                self._import_graph.delete("source_module IS NOT NULL")
            except Exception as e:
                logger.debug("import_graph replace delete skipped: %s", e)

        records = []
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if not source or not target:
                continue
            records.append(
                {
                    "source_module": source,
                    "target_module": target,
                    "import_type": edge.get("import_type", "absolute"),
                    "is_circular": (source, target) in circular_edges,
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

    def query_impact(
        self, changed_files: list[str], max_depth: int = 3, include_tests: bool = True
    ) -> dict:
        """Analyze impact of file changes using structural, dependency, and history signals."""
        try:
            changed_files = [f for f in changed_files if f]
            blast_radius = self.query_blast_radius(changed_files, max_depth=max_depth)
            co_change = self._analyze_co_changes(changed_files, window_days=90)
            impacted_modules = [m.get("module", "") for m in blast_radius.get("modules", [])]

            suggested_tests: list[dict] = []
            if include_tests:
                suggested_tests = self.suggest_tests(
                    changed_files,
                    impacted_modules=[m for m in impacted_modules if m],
                )

            impact_score = self._compute_impact_score(
                blast_radius=blast_radius,
                co_change=co_change,
                suggested_tests=suggested_tests,
                include_tests=include_tests,
            )

            impact = {
                "changed_files": changed_files,
                "blast_radius": blast_radius,
                "direct_dependents": blast_radius.get("dependency_edges", []),
                "impacted_modules": impacted_modules,
                "co_change_analysis": co_change,
                "co_changed": co_change.get("files", []),
                "suggested_tests": suggested_tests,
                "impact_score": impact_score,
                "confidence": impact_score.get("signals", {}),
            }
            impact["impacted_modules"] = sorted(set(impact["impacted_modules"]))
            return impact
        except Exception as e:
            logger.warning(f"Failed to query impact: {e}")
            return {
                "changed_files": changed_files,
                "blast_radius": {"modules": [], "symbols": [], "max_depth": max_depth},
                "direct_dependents": [],
                "impacted_modules": [],
                "co_change_analysis": {"window_days": 90, "files": [], "commits_analyzed": 0},
                "co_changed": [],
                "suggested_tests": [],
                "impact_score": {"score": 0.0, "confidence": 0.0, "signals": {}},
                "confidence": {},
            }

    def query_blast_radius(self, changed_files: list[str], max_depth: int = 3) -> dict:
        """Compute blast radius from dependency and structural relationships."""
        modules = self._modules_for_files(changed_files)
        module_impacts: dict[str, int] = {}
        dependency_edges = []

        for module in modules:
            deps = self.query_dependency_graph(module, direction="up", max_depth=max_depth)
            for dep in deps.get("dependents", []):
                dependent = dep.get("module", "")
                depth = int(dep.get("depth", 1))
                if not dependent:
                    continue
                current = module_impacts.get(dependent)
                if current is None or depth < current:
                    module_impacts[dependent] = depth
                dependency_edges.append(
                    {
                        "source_id": dependent,
                        "target_id": module,
                        "rel_type": "imports",
                        "depth": depth,
                    }
                )

        symbol_impacts = self._collect_structural_impacts(changed_files, max_depth)

        return {
            "max_depth": max_depth,
            "changed_modules": modules,
            "modules": [
                {"module": module, "depth": depth}
                for module, depth in sorted(module_impacts.items(), key=lambda item: item[1])
            ],
            "symbols": symbol_impacts,
            "dependency_edges": dependency_edges,
        }

    def query_dependency_graph(
        self, module: str, direction: str = "both", max_depth: int = 3
    ) -> dict:
        """Return dependency graph information from the import graph table."""
        try:
            df = self._import_graph.to_pandas()
            if df.empty:
                return {
                    "module": module,
                    "direction": direction,
                    "dependencies": [],
                    "dependents": [],
                    "edges": [],
                    "circular": [],
                }

            adjacency: dict[str, set[str]] = {}
            reverse: dict[str, set[str]] = {}
            circular_edges: set[tuple[str, str]] = set()

            for _, row in df.iterrows():
                source = str(row.get("source_module", ""))
                target = str(row.get("target_module", ""))
                if not source or not target:
                    continue
                adjacency.setdefault(source, set()).add(target)
                reverse.setdefault(target, set()).add(source)
                if bool(row.get("is_circular", False)):
                    circular_edges.add((source, target))

            canonical = self._resolve_module(adjacency, reverse, module)
            if not canonical:
                return {
                    "module": module,
                    "direction": direction,
                    "dependencies": [],
                    "dependents": [],
                    "edges": [],
                    "circular": [],
                }

            dependencies = []
            dependents = []

            if direction in {"down", "both"}:
                dependencies = self._walk_graph(adjacency, canonical, max_depth)
            if direction in {"up", "both"}:
                dependents = self._walk_graph(reverse, canonical, max_depth)

            edge_set = set()
            for item in dependencies:
                edge_set.add((canonical, item["module"]))
            for item in dependents:
                edge_set.add((item["module"], canonical))

            edges = [
                {
                    "source": source,
                    "target": target,
                    "is_circular": (source, target) in circular_edges,
                }
                for source, target in sorted(edge_set)
            ]
            circular = [
                {"source": source, "target": target}
                for source, target in sorted(circular_edges)
                if source == canonical
                or target == canonical
                or (source, target) in edge_set
                or (target, source) in edge_set
            ]

            return {
                "module": canonical,
                "direction": direction,
                "dependencies": dependencies,
                "dependents": dependents,
                "edges": edges,
                "circular": circular,
            }
        except Exception as e:
            logger.warning("Failed to query dependency graph: %s", e)
            return {
                "module": module,
                "direction": direction,
                "dependencies": [],
                "dependents": [],
                "edges": [],
                "circular": [],
            }

    def map_code_chunk_to_nodes(
        self,
        relative_path: str,
        symbol_name: str,
        line_start: int,
        line_end: int,
        limit: int = 3,
    ) -> list[dict]:
        """Map a semantic code chunk to structural code nodes.

        This is the P74 fusion mapping layer between code_files and code_nodes.
        Matching priority: path + line overlap, then symbol fallback.
        """
        try:
            df = self._code_nodes.to_pandas()
            if df.empty:
                return []

            path_norm = self._normalize_rel_path(relative_path)
            if not path_norm:
                return []

            # Path-first match: code_nodes.file_path may be absolute or relative.
            path_matches = df[
                df["file_path"]
                .astype(str)
                .apply(lambda p: self._normalize_rel_path(str(p)) == path_norm)
            ]
            if path_matches.empty:
                return []

            # Overlap score: favor nodes closest to chunk line range.
            ranked = []
            for _, row in path_matches.iterrows():
                node_start = int(row.get("line_start", 0) or 0)
                node_end = int(row.get("line_end", 0) or 0)
                overlap = self._line_overlap_score(line_start, line_end, node_start, node_end)

                name = str(row.get("name", "") or "")
                qualified = str(row.get("qualified_name", "") or "")
                symbol_boost = 0.0
                if symbol_name and (symbol_name == name or symbol_name in qualified):
                    symbol_boost = 0.25

                score = overlap + symbol_boost
                ranked.append((score, row))

            ranked.sort(key=lambda item: item[0], reverse=True)

            # Fallback to symbol-only within file if overlap is poor.
            if ranked and ranked[0][0] <= 0.05 and symbol_name:
                by_symbol = path_matches[
                    path_matches["qualified_name"].str.contains(symbol_name, na=False, regex=False)
                    | (path_matches["name"] == symbol_name)
                ]
                if not by_symbol.empty:
                    ranked = [(0.5, row) for _, row in by_symbol.iterrows()]

            output = []
            for score, row in ranked[:limit]:
                qualified_name = str(row.get("qualified_name", "") or "")
                node_file = self._normalize_rel_path(str(row.get("file_path", "") or ""))
                node_start = int(row.get("line_start", 0) or 0)
                node_end = int(row.get("line_end", 0) or 0)
                stable_id = self._stable_fusion_id(
                    node_file,
                    qualified_name or str(row.get("name", "") or ""),
                    node_start,
                    node_end,
                )
                output.append(
                    {
                        "stable_id": stable_id,
                        "score": round(float(score), 4),
                        "node_id": str(row.get("node_id", "") or ""),
                        "node_type": str(row.get("node_type", "") or ""),
                        "name": str(row.get("name", "") or ""),
                        "qualified_name": qualified_name,
                        "file_path": node_file,
                        "line_start": node_start,
                        "line_end": node_end,
                    }
                )

            return output
        except Exception as e:
            logger.warning("Failed to map code chunk to nodes: %s", e)
            return []

    def get_node_relationship_neighbors(self, node_id: str, limit: int = 20) -> list[dict]:
        """Return structural relationships connected to a node."""
        try:
            if not node_id:
                return []
            df = self._relationships.to_pandas()
            if df.empty:
                return []

            matches = df[(df["source_id"] == node_id) | (df["target_id"] == node_id)]
            if matches.empty:
                return []

            out = []
            for _, row in matches.head(limit).iterrows():
                out.append(
                    {
                        "source_id": str(row.get("source_id", "") or ""),
                        "target_id": str(row.get("target_id", "") or ""),
                        "rel_type": str(row.get("rel_type", "") or ""),
                        "file_path": self._normalize_rel_path(str(row.get("file_path", "") or "")),
                        "line_number": int(row.get("line_number", 0) or 0),
                    }
                )
            return out
        except Exception as e:
            logger.warning("Failed to get node relationship neighbors: %s", e)
            return []

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

    def suggest_tests(
        self,
        changed_files: list[str],
        impacted_modules: list[str] | None = None,
    ) -> list[dict]:
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
            impacted_modules = impacted_modules or []

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

                if impacted_modules and test_name:
                    for module in impacted_modules:
                        module_tail = module.split(".")[-1]
                        if module_tail and module_tail in test_name:
                            covers.append(module)
                            confidence = min(1.0, confidence + 0.15)

                if covers:
                    covers = sorted(set(covers))
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

    def _collect_structural_impacts(self, changed_files: list[str], max_depth: int) -> list[dict]:
        """Collect impacted symbols by traversing reverse call/inherit/import edges."""
        try:
            nodes_df = self._code_nodes.to_pandas()
            rels_df = self._relationships.to_pandas()
            if nodes_df.empty or rels_df.empty:
                return []

            changed_nodes = set()
            for file_path in changed_files:
                matched = nodes_df[nodes_df["file_path"].str.contains(file_path, na=False)]
                for _, row in matched.iterrows():
                    node_id = str(row.get("node_id", ""))
                    if node_id:
                        changed_nodes.add(node_id)

            if not changed_nodes:
                return []

            reverse_edges: dict[str, list[dict]] = defaultdict(list)
            for _, row in rels_df.iterrows():
                src = str(row.get("source_id", ""))
                tgt = str(row.get("target_id", ""))
                rel_type = str(row.get("rel_type", ""))
                if src and tgt and rel_type in {"calls", "inherits", "imports"}:
                    reverse_edges[tgt].append(
                        {
                            "source_id": src,
                            "rel_type": rel_type,
                            "file_path": row.get("file_path", ""),
                            "line_number": int(row.get("line_number", 0) or 0),
                        }
                    )

            queue = deque((node_id, 0) for node_id in changed_nodes)
            visited = set(changed_nodes)
            impacted: dict[str, dict] = {}

            while queue:
                target, depth = queue.popleft()
                if depth >= max_depth:
                    continue
                for edge in reverse_edges.get(target, []):
                    source = edge["source_id"]
                    hop = depth + 1
                    existing = impacted.get(source)
                    if existing is None or hop < int(existing.get("depth", 99)):
                        impacted[source] = {
                            "symbol": source,
                            "depth": hop,
                            "rel_type": edge["rel_type"],
                            "file_path": edge.get("file_path", ""),
                            "line_number": edge.get("line_number", 0),
                        }
                    if source not in visited:
                        visited.add(source)
                        queue.append((source, hop))

            return sorted(impacted.values(), key=lambda item: int(item.get("depth", 0)))
        except Exception as e:
            logger.warning("Failed to collect structural impacts: %s", e)
            return []

    def _analyze_co_changes(self, changed_files: list[str], window_days: int = 90) -> dict:
        """Analyze historically co-changed files within a time window."""
        try:
            hist_df = self._change_history.to_pandas()
            if hist_df.empty:
                return {"window_days": window_days, "files": [], "commits_analyzed": 0}

            cutoff = datetime.now(tz=UTC) - timedelta(days=window_days)
            changed_set = set(changed_files)
            file_stats: dict[str, dict] = {}
            commits_seen = 0

            for _, row in hist_df.iterrows():
                timestamp_raw = str(row.get("timestamp", "") or "")
                try:
                    ts = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=UTC)
                except Exception:
                    continue

                if ts < cutoff:
                    continue

                try:
                    co_files = json.loads(row.get("co_changed_files", "[]") or "[]")
                except Exception:
                    co_files = []
                if not isinstance(co_files, list):
                    continue

                if not any(f in co_files for f in changed_files):
                    continue

                commits_seen += 1
                for file_path in co_files:
                    if not isinstance(file_path, str) or file_path in changed_set:
                        continue
                    stats = file_stats.setdefault(
                        file_path,
                        {"file": file_path, "count": 0, "last_seen": ts, "days_since_last": 9999},
                    )
                    stats["count"] += 1
                    if ts > stats["last_seen"]:
                        stats["last_seen"] = ts

            for stats in file_stats.values():
                delta = datetime.now(tz=UTC) - stats["last_seen"]
                stats["days_since_last"] = delta.days
                stats["last_seen"] = stats["last_seen"].date().isoformat()

            ranked = sorted(
                file_stats.values(),
                key=lambda item: (-int(item["count"]), int(item["days_since_last"])),
            )
            return {
                "window_days": window_days,
                "files": ranked[:20],
                "commits_analyzed": commits_seen,
            }
        except Exception as e:
            logger.warning("Failed co-change analysis: %s", e)
            return {"window_days": window_days, "files": [], "commits_analyzed": 0}

    def _compute_impact_score(
        self,
        *,
        blast_radius: dict,
        co_change: dict,
        suggested_tests: list[dict],
        include_tests: bool,
    ) -> dict:
        """Compute weighted impact score and confidence."""
        structural_count = len(blast_radius.get("symbols", []))
        dependency_count = len(blast_radius.get("modules", []))
        historical_count = len(co_change.get("files", []))
        avg_test_conf = 0.0
        if suggested_tests:
            avg_test_conf = sum(float(t.get("confidence", 0.0)) for t in suggested_tests) / len(
                suggested_tests
            )

        structural_signal = min(1.0, structural_count / 20.0)
        dependency_signal = min(1.0, dependency_count / 20.0)
        historical_signal = min(1.0, historical_count / 20.0)
        test_signal = avg_test_conf if include_tests else 0.0

        score = (
            0.35 * structural_signal
            + 0.30 * dependency_signal
            + 0.20 * historical_signal
            + 0.15 * test_signal
        )

        confidence_parts = [
            1.0 if structural_count else 0.0,
            1.0 if dependency_count else 0.0,
            1.0 if co_change.get("commits_analyzed", 0) else 0.0,
            (1.0 if suggested_tests else 0.0) if include_tests else 1.0,
        ]
        confidence = sum(confidence_parts) / len(confidence_parts)

        return {
            "score": round(score, 4),
            "confidence": round(confidence, 4),
            "signals": {
                "structural": round(structural_signal, 4),
                "dependency": round(dependency_signal, 4),
                "historical": round(historical_signal, 4),
                "tests": round(test_signal, 4),
            },
        }

    def _normalize_rel_path(self, path: str) -> str:
        """Normalize a path to repo-relative form for fusion matching."""
        if not path:
            return ""
        p = path.replace("\\", "/")
        marker = "/bazzite-laptop/"
        if marker in p:
            p = p.split(marker, 1)[1]
        p = p.lstrip("./")
        return p

    def _line_overlap_score(
        self,
        a_start: int,
        a_end: int,
        b_start: int,
        b_end: int,
    ) -> float:
        """Return normalized overlap score between two line ranges."""
        if a_start <= 0 or a_end <= 0 or b_start <= 0 or b_end <= 0:
            return 0.0
        left = max(a_start, b_start)
        right = min(a_end, b_end)
        overlap = max(0, right - left + 1)
        if overlap == 0:
            return 0.0
        a_len = max(1, a_end - a_start + 1)
        b_len = max(1, b_end - b_start + 1)
        return overlap / float(max(a_len, b_len))

    def _stable_fusion_id(self, path: str, symbol: str, line_start: int, line_end: int) -> str:
        """Build deterministic stable identifier for semantic/structural linking."""
        payload = f"{path}|{symbol}|{line_start}|{line_end}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

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

    def _modules_for_files(self, changed_files: list[str]) -> list[str]:
        """Resolve changed file paths to module IDs."""
        try:
            nodes_df = self._code_nodes.to_pandas()
        except Exception:
            nodes_df = None

        modules: set[str] = set()
        for file_path in changed_files:
            if nodes_df is not None and not nodes_df.empty:
                module_rows = nodes_df[
                    (nodes_df["node_type"] == "module")
                    & (nodes_df["file_path"].str.contains(file_path, na=False, regex=False))
                ]
                for _, row in module_rows.iterrows():
                    module_name = str(row.get("qualified_name", ""))
                    if module_name:
                        modules.add(module_name)

            path = Path(file_path)
            if path.suffix == ".py":
                parts = list(path.parts)
                if "ai" in parts:
                    idx = parts.index("ai")
                    rel_parts = parts[idx:]
                    rel_parts[-1] = rel_parts[-1].replace(".py", "")
                    if rel_parts[-1] == "__init__":
                        rel_parts = rel_parts[:-1]
                    if rel_parts:
                        modules.add(".".join(rel_parts))

        return sorted(modules)

    def _resolve_module(
        self, adjacency: dict[str, set[str]], reverse: dict[str, set[str]], module: str
    ) -> str | None:
        """Resolve a module name against graph keys with ai/non-ai compatibility."""
        all_modules = set(adjacency) | set(reverse)
        for targets in adjacency.values():
            all_modules.update(targets)

        candidates = [module]
        if module.startswith("ai."):
            candidates.append(module.removeprefix("ai."))
        else:
            candidates.append(f"ai.{module}")

        for candidate in candidates:
            if candidate in all_modules:
                return candidate

        # fallback suffix match for older indexes where ai prefix differs
        for candidate in candidates:
            for entry in all_modules:
                if entry.endswith(f".{candidate}") or entry.endswith(
                    f".{candidate.removeprefix('ai.')}"
                ):
                    return entry
        return None

    def _walk_graph(
        self, graph: dict[str, set[str]], start: str, max_depth: int
    ) -> list[dict[str, int | str]]:
        """BFS traversal returning module-depth pairs."""
        queue: list[tuple[str, int]] = [(start, 0)]
        visited = {start}
        results: list[dict[str, int | str]] = []

        while queue:
            module, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for nxt in sorted(graph.get(module, set())):
                if nxt in visited:
                    continue
                visited.add(nxt)
                next_depth = depth + 1
                results.append({"module": nxt, "depth": next_depth})
                queue.append((nxt, next_depth))

        return results


_store_instance: CodeIntelStore | None = None


def get_code_store() -> CodeIntelStore:
    """Get singleton CodeIntelStore instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = CodeIntelStore()
    return _store_instance
