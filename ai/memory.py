"""Cross-session conversation memory with semantic retrieval.

Stores important facts from conversations for retrieval in future sessions.
Uses LanceDB with 768-dim embeddings (Gemini Embedding 001).
"""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.constants import EMBEDDING_DIM
from ai.rag.embedder import embed_single

logger = logging.getLogger(__name__)

MEMORY_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("ts", pa.string()),
        pa.field("role", pa.string()),
        pa.field("summary", pa.string()),
        pa.field("importance", pa.int32()),
        pa.field("source", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ]
)


class ConversationMemory:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or VECTOR_DB_DIR
        self._db = None
        self._table = None
        self._ensure_table()

    def _ensure_table(self) -> None:
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        if self._table is None:
            try:
                self._table = self._db.open_table("conversation_memory")
            except Exception:
                self._table = self._db.create_table("conversation_memory", schema=MEMORY_SCHEMA)

    def store_memory(
        self,
        summary: str,
        role: str = "system",
        importance: int = 3,
        source: str = "newelle",
    ) -> str:
        if importance < 1 or importance > 5:
            raise ValueError("importance must be between 1 and 5")

        redacted_summary = self._redact_secrets(summary)

        try:
            vector = embed_single(redacted_summary)
        except Exception as e:
            logger.warning("Failed to embed memory: %s", e)
            return ""

        record = {
            "id": str(uuid.uuid4()),
            "ts": datetime.now(UTC).isoformat(),
            "role": role,
            "summary": redacted_summary,
            "importance": importance,
            "source": source,
            "vector": vector,
        }

        try:
            self._ensure_table()
            self._table.add([record])
            return record["id"]
        except Exception as e:
            logger.error("Failed to store memory: %s", e)
            return ""

    def _redact_secrets(self, text: str) -> str:
        try:
            from ai.security.inputvalidator import InputValidator

            validator = InputValidator()
            redacted = validator.redact_secrets(text)
            return redacted
        except Exception:
            return text

    def retrieve_memories(
        self, query: str, top_k: int = 5, min_importance: int = 1
    ) -> list[dict[str, Any]]:
        try:
            vector = embed_single(query)
        except Exception as e:
            logger.warning("Failed to embed query: %s", e)
            return []

        try:
            self._ensure_table()
            results = (
                self._table.search(vector)
                .where(f"importance >= {min_importance}")
                .limit(top_k)
                .to_list()
            )
        except Exception as e:
            logger.error("Failed to search memories: %s", e)
            return []

        memories = []
        for r in results:
            memories.append(
                {
                    "id": r.get("id"),
                    "ts": r.get("ts"),
                    "role": r.get("role"),
                    "summary": r.get("summary"),
                    "importance": r.get("importance"),
                    "source": r.get("source"),
                }
            )
        return memories

    def search_memories(self, query: str, top_k: int = 5) -> str:
        memories = self.retrieve_memories(query, top_k=top_k)
        return json.dumps(memories)

    def prune_memories(self, max_age_days: int = 90, min_importance: int = 1) -> int:
        self._ensure_table()
        df = self._table.to_pandas()
        if df.empty:
            return 0

        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        to_delete = df[
            (df["ts"] < cutoff) & (df["importance"] <= min_importance) & (df["importance"] < 4)
        ]

        if to_delete.empty:
            return 0

        ids_to_delete = to_delete["id"].tolist()
        try:
            self._table.delete(f"id IN ({','.join(repr(i) for i in ids_to_delete)})")
            return len(ids_to_delete)
        except Exception as e:
            logger.error("Failed to prune memories: %s", e)
            return 0

    def get_recent(self, n: int = 10) -> list[dict[str, Any]]:
        try:
            self._ensure_table()
            df = self._table.to_pandas()
            if df.empty:
                return []
            df = df.sort_values("ts", ascending=False).head(n)
            return df.to_dict("records")
        except Exception as e:
            logger.error("Failed to get recent memories: %s", e)
            return []


_memory: ConversationMemory | None = None
_memory_lock = None


def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        import threading

        global _memory_lock
        if _memory_lock is None:
            _memory_lock = threading.Lock()
        with _memory_lock:
            if _memory is None:
                _memory = ConversationMemory()
    return _memory


def summarize_session(messages: list[dict], source: str = "newelle") -> list[str]:
    """Extract important facts from a conversation using simple heuristics.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        source: Source identifier for the memories.

    Returns:
        List of summary strings to be stored as memories.
    """
    summaries = []
    seen_contents: set[str] = set()

    preference_patterns = [
        "i prefer",
        "i like",
        "i hate",
        "always do",
        "never do",
        "please use",
        "i want",
    ]
    security_patterns = [
        "cve",
        "threat",
        "alert",
        "quarantine",
        "virus",
        "malware",
    ]
    decision_patterns = [
        "decided",
        "chose",
        "going with",
        "switched to",
        "use",
        "instead",
    ]

    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        content_lower = content.lower()

        if any(p in content_lower for p in preference_patterns):
            if content not in seen_contents:
                summaries.append(content)
                seen_contents.add(content)

        if any(p in content_lower for p in security_patterns):
            if content not in seen_contents:
                summaries.append(content)
                seen_contents.add(content)

        if any(p in content_lower for p in decision_patterns):
            if content not in seen_contents:
                summaries.append(content)
                seen_contents.add(content)

    return summaries[:3]
