"""Semantic cache with LanceDB backend (Phase 23: Semantic Caching).

Table: semantic_cache

Schema fields:
    id          -- UUID primary key
    query       -- Original query text
    response    -- JSON-encoded LLM response
    task_type   -- "fast" | "reason" | "batch" | "code"
    cached_at   -- ISO8601 UTC timestamp
    hit_count   -- How many times this was served (unused, kept for schema)
    vector      -- 768-dim embedding of query
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.constants import EMBEDDING_DIM
from ai.rag.embedder import embed_single

logger = logging.getLogger(__name__)

TABLE_NAME = "semantic_cache"

_TTL_MAP: dict[str, int] = {
    "fast": 30 * 60,
    "reason": 2 * 60 * 60,
    "batch": 24 * 60 * 60,
    "code": 60 * 60,
}
_DEFAULT_TTL = 3600

VALID_TASK_TYPES: frozenset[str] = frozenset({"fast", "reason", "batch", "code"})

SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("query", pa.string()),
        pa.field("response", pa.string()),
        pa.field("task_type", pa.string()),
        pa.field("cached_at", pa.string()),
        pa.field("hit_count", pa.int32()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ]
)


class SemanticCache:
    """Semantic cache for LLM responses using LanceDB vector search."""

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        db_path: str | None = None,
    ) -> None:
        """Initialize SemanticCache.

        Args:
            similarity_threshold: Minimum cosine similarity for a cache hit.
            db_path: Path to LanceDB directory. Defaults to VECTOR_DB_DIR.
        """
        self._db_path = Path(db_path) if db_path else VECTOR_DB_DIR
        self._db = None
        self._table = None
        self._similarity_threshold = similarity_threshold

    def _connect(self):
        """Get or create LanceDB connection."""
        if self._db is not None:
            return self._db
        try:
            self._db_path.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self._db_path))
        except (OSError, PermissionError) as e:
            logger.debug("Failed to connect to LanceDB at %s: %s", self._db_path, e)
            raise
        return self._db

    def _get_or_create_table(self):
        """Open semantic_cache table, creating it with schema if needed."""
        if self._table is not None:
            return self._table

        db = self._connect()
        try:
            tables = db.list_tables()
            existing = tables.tables if hasattr(tables, "tables") else list(tables)
            if TABLE_NAME in existing:
                self._table = db.open_table(TABLE_NAME)
                return self._table
        except Exception as e:
            logger.debug("Error checking existing tables: %s", e)

        try:
            self._table = db.create_table(TABLE_NAME, schema=SCHEMA)
        except Exception as e:
            if "already exists" in str(e).lower():
                self._table = db.open_table(TABLE_NAME)
            else:
                raise

        return self._table

    def get(self, query: str, task_type: str = "fast") -> dict | None:
        """Find semantically similar cached response.

        Args:
            query: Query text to search for.
            task_type: Task type filter ("fast" | "reason" | "batch" | "code").

        Returns:
            Parsed response dict if cache hit and TTL valid, else None.

        Raises:
            ValueError: If task_type is not one of the known valid values.
        """
        if task_type not in VALID_TASK_TYPES:
            raise ValueError(
                f"Invalid task_type {task_type!r}. Must be one of {sorted(VALID_TASK_TYPES)}"
            )

        try:
            vector = embed_single(query)
        except Exception as e:
            logger.debug("Failed to embed query: %s", e)
            return None

        try:
            table = self._get_or_create_table()
            results = table.search(vector).where(f"task_type = '{task_type}'").limit(1).to_list()
        except Exception as e:
            logger.debug("Search failed: %s", e)
            return None

        if not results:
            return None

        result = results[0]
        distance_threshold = 1.0 - self._similarity_threshold
        distance = result.get("_distance", 1.0)

        if distance >= distance_threshold:
            return None

        try:
            cached_at = datetime.fromisoformat(result["cached_at"])
        except Exception:
            return None

        ttl = _TTL_MAP.get(task_type, _DEFAULT_TTL)
        age = (datetime.now(UTC) - cached_at).total_seconds()

        if age >= ttl:
            return None

        try:
            return json.loads(result["response"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("Failed to parse cached response: %s", e)
            return None

    def put(self, query: str, response: dict, task_type: str = "fast") -> None:
        """Store a query+response pair.

        Args:
            query: Query text.
            response: Response dict to cache (will be JSON-encoded).
            task_type: Task type ("fast" | "reason" | "batch" | "code").
        """
        try:
            vector = embed_single(query)
        except Exception as e:
            logger.error("Failed to embed query for cache put: %s", e)
            return

        entry = {
            "id": str(uuid4()),
            "query": query,
            "response": json.dumps(response),
            "task_type": task_type,
            "cached_at": datetime.now(UTC).isoformat(),
            "hit_count": 0,
            "vector": vector,
        }

        try:
            table = self._get_or_create_table()
            table.add([entry])
        except Exception as e:
            logger.debug("Failed to add cache entry: %s", e)

    def evict_expired(self) -> int:
        """Delete all rows where cached_at age exceeds TTL for their task_type.

        Returns:
            Count of evicted rows.
        """
        try:
            table = self._get_or_create_table()
        except Exception:
            return 0

        try:
            all_rows = table.to_list()
        except Exception:
            return 0

        if not all_rows:
            return 0

        now = datetime.now(UTC)
        to_delete = []

        for row in all_rows:
            row_id = row.get("id")
            if not row_id:
                continue

            cached_at_str = row.get("cached_at")
            if not cached_at_str:
                continue

            try:
                cached_at = datetime.fromisoformat(cached_at_str)
            except ValueError:
                continue

            task_type = row.get("task_type", "fast")
            ttl = _TTL_MAP.get(task_type, _DEFAULT_TTL)
            age = (now - cached_at).total_seconds()
            if age >= ttl:
                to_delete.append(row_id)

        if not to_delete:
            return 0

        try:
            table.delete(f"id IN ({','.join(repr(x) for x in to_delete)})")
        except Exception as e:
            logger.debug("Failed to delete expired entries: %s", e)
            return 0

        return len(to_delete)
