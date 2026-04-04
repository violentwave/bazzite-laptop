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
        self._init_tables()

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

        table_names = self._db.list_tables()

        if "code_nodes" in table_names:
            self._code_nodes = self._db.open_table("code_nodes")
        else:
            self._code_nodes = self._db.create_table("code_nodes", schema=code_nodes_schema)

        if "relationships" in table_names:
            self._relationships = self._db.open_table("relationships")
        else:
            self._relationships = self._db.create_table("relationships", schema=rel_schema)

        if "import_graph" in table_names:
            self._import_graph = self._db.open_table("import_graph")
        else:
            self._import_graph = self._db.create_table("import_graph", schema=import_graph_schema)

        if "change_history" in table_names:
            self._change_history = self._db.open_table("change_history")
        else:
            self._change_history = self._db.create_table(
                "change_history", schema=change_history_schema
            )

    def index_project(self, nodes: list[CodeNode], relationships: list[Relationship]) -> None:
        """Index nodes and relationships to LanceDB."""
        node_records = []
        for node in nodes:
            text_to_embed = f"{node.qualified_name} {node.signature} {node.docstring}"
            try:
                vector = embed(text_to_embed)
            except Exception:
                vector = [0.0] * 768

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
            self._code_nodes.delete(f"file_path = '{file_path}'")
            self._relationships.delete(f"file_path = '{file_path}'")

            nodes, relationships = parser.parse_file(file_path)

            node_records = []
            for node in nodes:
                text_to_embed = f"{node.qualified_name} {node.signature} {node.docstring}"
                try:
                    vector = embed(text_to_embed)
                except Exception:
                    vector = [0.0] * 768

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
        """Find callers/importers of a node."""
        try:
            df = self._relationships.to_pandas()
            if df.empty:
                return []

            dependents = []
            visited = set()

            def traverse(target: str, depth: int) -> None:
                if depth > max_depth or target in visited:
                    return
                visited.add(target)

                results = df[df["target_id"] == target]
                for _, row in results.iterrows():
                    dependents.append(
                        {
                            "source_id": row["source_id"],
                            "rel_type": row["rel_type"],
                            "file_path": row["file_path"],
                        }
                    )
                    traverse(row["source_id"], depth + 1)

            traverse(node_id, 0)
            return dependents
        except Exception as e:
            logger.warning(f"Failed to query dependents: {e}")
            return []

    def query_impact(self, changed_files: list[str]) -> dict:
        """Analyze impact of file changes."""
        try:
            rel_df = self._relationships.to_pandas()
            hist_df = self._change_history.to_pandas()

            impact = {
                "direct_dependents": [],
                "co_changed": [],
                "confidence": {},
            }

            for file_path in changed_files:
                if not rel_df.empty:
                    results = rel_df[rel_df["file_path"] == file_path]
                    for _, row in results.iterrows():
                        impact["direct_dependents"].append(
                            {
                                "source_id": row["source_id"],
                                "rel_type": row["rel_type"],
                            }
                        )

                if not hist_df.empty:
                    for _, row in hist_df.iterrows():
                        if file_path in row["file_path"]:
                            impact["co_changed"].extend(json.loads(row["co_changed_files"]))

            impact["co_changed"] = list(set(impact["co_changed"]))
            impact["confidence"]["static"] = 0.8
            impact["confidence"]["historical"] = 0.5

            return impact
        except Exception as e:
            logger.warning(f"Failed to query impact: {e}")
            return {"direct_dependents": [], "co_changed": [], "confidence": {}}

    def search_nodes(self, query: str, node_type: str | None = None, top_k: int = 10) -> list[dict]:
        """Semantic search over code nodes."""
        try:
            df = self._code_nodes.to_pandas()
            if df.empty:
                return []

            query_vector = embed(query)

            import numpy as np

            vectors = np.array(df["vector"].tolist())
            query_vec = np.array(query_vector).reshape(1, -1)

            vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
            query_vec = query_vec / np.linalg.norm(query_vec, keepdims=True)

            similarities = vectors @ query_vec.T.flatten()
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            results = []
            for idx in top_indices:
                row = df.iloc[idx]
                if node_type and row["node_type"] != node_type:
                    continue
                results.append(
                    {
                        "node_id": row["node_id"],
                        "node_type": row["node_type"],
                        "name": row["name"],
                        "qualified_name": row["qualified_name"],
                        "file_path": row["file_path"],
                        "complexity": row["complexity"],
                    }
                )

            return results
        except Exception as e:
            logger.warning(f"Failed to search nodes: {e}")
            return []


_store_instance: CodeIntelStore | None = None


def get_code_store() -> CodeIntelStore:
    """Get singleton CodeIntelStore instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = CodeIntelStore()
    return _store_instance
