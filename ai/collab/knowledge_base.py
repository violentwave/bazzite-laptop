"""Agent knowledge base for cross-agent learning."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("ai.collab")


class AgentKnowledge:
    """LanceDB-backed knowledge store for agent learning."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize agent_knowledge table."""
        schema = pa.schema(
            [
                pa.field("knowledge_id", pa.string()),
                pa.field(
                    "knowledge_type", pa.string()
                ),  # pattern, quirk, solution, convention, api_usage
                pa.field("title", pa.string()),
                pa.field("content", pa.string()),
                pa.field("source_agent", pa.string()),
                pa.field("tags", pa.string()),  # JSON list
                pa.field("confidence", pa.float32()),
                pa.field("use_count", pa.int32()),
                pa.field("version", pa.int32()),
                pa.field("created_at", pa.string()),
                pa.field("updated_at", pa.string()),
                pa.field("related_files", pa.string()),  # JSON list
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        table_names = self._db.list_tables()
        if "agent_knowledge" in table_names:
            self._table = self._db.open_table("agent_knowledge")
        else:
            self._table = self._db.create_table("agent_knowledge", schema=schema)

    def store_knowledge(
        self,
        knowledge_type: str,
        title: str,
        content: str,
        source_agent: str,
        tags: list[str] | None = None,
        related_files: list[str] | None = None,
        confidence: float = 0.8,
    ) -> str:
        """Store a knowledge entry."""
        import uuid

        knowledge_id = str(uuid.uuid4())

        timestamp = datetime.now(UTC).isoformat()

        try:
            vector = embed(f"{title} {content}")
        except Exception:
            vector = [0.0] * 768

        self._table.add(
            [
                {
                    "knowledge_id": knowledge_id,
                    "knowledge_type": knowledge_type,
                    "title": title,
                    "content": content,
                    "source_agent": source_agent,
                    "tags": "[]" if not tags else str(tags),
                    "confidence": confidence,
                    "use_count": 0,
                    "version": 1,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "related_files": "[]" if not related_files else str(related_files),
                    "vector": vector,
                }
            ]
        )

        return knowledge_id

    def query_knowledge(
        self,
        query: str,
        knowledge_type: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Semantic search and increment use_count."""
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
                if knowledge_type and row["knowledge_type"] != knowledge_type:
                    continue

                results.append(
                    {
                        "knowledge_id": row["knowledge_id"],
                        "knowledge_type": row["knowledge_type"],
                        "title": row["title"],
                        "content": row["content"],
                        "source_agent": row["source_agent"],
                        "tags": row["tags"],
                        "confidence": row["confidence"],
                        "use_count": row["use_count"],
                    }
                )

                # Increment use_count
                try:
                    new_count = row["use_count"] + 1
                    self._table.update(
                        f"knowledge_id = '{row['knowledge_id']}'",
                        {
                            "use_count": new_count,
                            "updated_at": datetime.now(UTC).isoformat(),
                        },
                    )
                except Exception as e:
                    logger.debug(f"Use count update skipped: {e}")

            return results
        except Exception as e:
            logger.warning(f"Failed to query knowledge: {e}")
            return []

    def decay_confidence(self, days_unused: int = 30, decay_rate: float = 0.05) -> None:
        """Reduce confidence of unused entries."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return

            cutoff = datetime.now(UTC) - timedelta(days=days_unused)
            cutoff_str = cutoff.isoformat()

            for _, row in df.iterrows():
                if row["updated_at"] < cutoff_str:
                    new_confidence = max(0.0, row["confidence"] - decay_rate)
                    self._table.update(
                        f"knowledge_id = '{row['knowledge_id']}'",
                        {"confidence": new_confidence},
                    )
        except Exception as e:
            logger.warning(f"Failed to decay confidence: {e}")

    def get_stale(self, min_age_days: int = 60, max_confidence: float = 0.3) -> list[dict]:
        """Get low-confidence old entries for review."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return []

            cutoff = datetime.now(UTC) - timedelta(days=min_age_days)
            cutoff_str = cutoff.isoformat()

            results = []
            for _, row in df.iterrows():
                if row["updated_at"] < cutoff_str and row["confidence"] <= max_confidence:
                    results.append(
                        {
                            "knowledge_id": row["knowledge_id"],
                            "title": row["title"],
                            "knowledge_type": row["knowledge_type"],
                            "confidence": row["confidence"],
                            "updated_at": row["updated_at"],
                        }
                    )

            return results
        except Exception as e:
            logger.warning(f"Failed to get stale: {e}")
            return []


_knowledge_instance: AgentKnowledge | None = None


def get_agent_knowledge() -> AgentKnowledge:
    """Get singleton AgentKnowledge instance."""
    global _knowledge_instance
    if _knowledge_instance is None:
        _knowledge_instance = AgentKnowledge()
    return _knowledge_instance
