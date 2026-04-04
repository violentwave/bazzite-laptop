"""Shared context module for agent collaboration."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("ai.collab")


class SharedContext:
    """LanceDB-backed shared context for agent decisions and findings."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize shared_context table."""
        schema = pa.schema(
            [
                pa.field("context_id", pa.string()),
                pa.field(
                    "context_type", pa.string()
                ),  # decision, finding, blocker, active_edit, pattern, warning
                pa.field("agent", pa.string()),
                pa.field("content", pa.string()),
                pa.field("files_involved", pa.string()),  # JSON list
                pa.field("priority", pa.int32()),
                pa.field("created_at", pa.string()),
                pa.field("expires_at", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        table_names = self._db.list_tables()
        if "shared_context" in table_names:
            self._table = self._db.open_table("shared_context")
        else:
            self._table = self._db.create_table("shared_context", schema=schema)

    def add_context(
        self,
        context_type: str,
        content: str,
        agent: str,
        files: list[str] | None = None,
        priority: int = 3,
        ttl_hours: int | None = None,
    ) -> str:
        """Add a context entry."""
        import uuid

        context_id = str(uuid.uuid4())

        timestamp = datetime.now(UTC).isoformat()
        expires_at = None
        if ttl_hours:
            from datetime import timedelta

            expires_at = (datetime.now(UTC) + timedelta(hours=ttl_hours)).isoformat()

        try:
            vector = embed(content)
        except Exception:
            vector = [0.0] * 768

        self._table.add(
            [
                {
                    "context_id": context_id,
                    "context_type": context_type,
                    "agent": agent,
                    "content": content,
                    "files_involved": "[]" if not files else str(files),
                    "priority": priority,
                    "created_at": timestamp,
                    "expires_at": expires_at or "",
                    "vector": vector,
                }
            ]
        )

        return context_id

    def query_relevant(
        self, query: str, context_type: str | None = None, top_k: int = 5
    ) -> list[dict]:
        """Semantic search for relevant context."""
        try:
            query_vector = embed(query)
            df = self._table.to_pandas()

            if df.empty:
                return []

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
                if context_type and row["context_type"] != context_type:
                    continue
                results.append(
                    {
                        "context_id": row["context_id"],
                        "context_type": row["context_type"],
                        "agent": row["agent"],
                        "content": row["content"],
                        "files_involved": row["files_involved"],
                        "created_at": row["created_at"],
                    }
                )

            return results
        except Exception as e:
            logger.warning(f"Failed to query context: {e}")
            return []

    def get_active_edits(self, agent: str | None = None) -> list[dict]:
        """Get active edit entries."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return []

            results = []
            for _, row in df.iterrows():
                if row["context_type"] == "active_edit":
                    if agent is None or row["agent"] == agent:
                        results.append(
                            {
                                "context_id": row["context_id"],
                                "content": row["content"],
                                "files_involved": row["files_involved"],
                                "agent": row["agent"],
                            }
                        )

            return results
        except Exception as e:
            logger.warning(f"Failed to get active edits: {e}")
            return []

    def cleanup_expired(self) -> None:
        """Delete expired context entries."""
        try:
            now = datetime.now(UTC).isoformat()
            df = self._table.to_pandas()

            if df.empty:
                return

            for _, row in df.iterrows():
                if row["expires_at"] and row["expires_at"] < now:
                    self._table.delete(f"context_id = '{row['context_id']}'")
        except Exception as e:
            logger.warning(f"Failed to cleanup expired: {e}")


_context_instance: SharedContext | None = None


def get_shared_context() -> SharedContext:
    """Get singleton SharedContext instance."""
    global _context_instance
    if _context_instance is None:
        _context_instance = SharedContext()
    return _context_instance
