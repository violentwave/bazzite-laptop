"""Opt-in conversation memory stored in LanceDB.

Stores summaries of LLM interactions and retrieves relevant past context.
Disabled by default — enable with ENABLE_CONVERSATION_MEMORY=true in keys.env.

Table: conversations
    id:               UUID string
    query:            user message (truncated to 500 chars)
    response_summary: first 200 chars of the assistant response
    task_type:        LLM task type (fast, reason, batch, code)
    timestamp:        ISO-8601 UTC string
    vector:           768-dim embedding of the query
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ai.config import APP_NAME, VECTOR_DB_DIR
from ai.rag.constants import EMBEDDING_DIM
from ai.rag.embedder import embed_texts

logger = logging.getLogger(APP_NAME)

_TABLE_NAME = "conversations"
_MAX_ROWS = 1000
_CLEANUP_COUNT = 100


def is_enabled() -> bool:
    """Return True if conversation memory is opted in via environment variable."""
    return os.environ.get("ENABLE_CONVERSATION_MEMORY", "").lower() == "true"


def _get_schema():
    """Lazy-load pyarrow schema to avoid Flatpak sandbox segfault."""
    import pyarrow as pa  # noqa: PLC0415

    return pa.schema([
        pa.field("id", pa.utf8()),
        pa.field("query", pa.utf8()),
        pa.field("response_summary", pa.utf8()),
        pa.field("task_type", pa.utf8()),
        pa.field("timestamp", pa.utf8()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])


def _get_table(db_path: Path | None = None):
    """Open or create the conversations table. Connects to LanceDB lazily."""
    import lancedb  # noqa: PLC0415

    path = db_path or VECTOR_DB_DIR
    path.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(path))
    schema = _get_schema()
    if _TABLE_NAME in db.table_names():
        return db.open_table(_TABLE_NAME)
    return db.create_table(_TABLE_NAME, schema=schema)


def _cleanup_if_needed(table) -> None:
    """Delete oldest _CLEANUP_COUNT rows when the table exceeds _MAX_ROWS."""
    try:
        count = table.count_rows()
        if count <= _MAX_ROWS:
            return
        rows = table.to_arrow(columns=["id", "timestamp"]).to_pydict()
        pairs = sorted(zip(rows.get("timestamp", []), rows.get("id", []), strict=False))
        oldest_ids = [pair[1] for pair in pairs[:_CLEANUP_COUNT]]
        if oldest_ids:
            ids_clause = ", ".join(f"'{i}'" for i in oldest_ids)
            table.delete(f"id IN ({ids_clause})")
            logger.info(
                "Conversation memory cleanup: removed %d entries (total was %d)",
                _CLEANUP_COUNT,
                count,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Conversation memory cleanup failed")


def store_interaction(
    query: str,
    response_summary: str,
    task_type: str,
    db_path: Path | None = None,
) -> bool:
    """Store a conversation interaction in LanceDB.

    No-op and returns False if ENABLE_CONVERSATION_MEMORY is not true.

    Args:
        query: The user's message (truncated to 500 chars before embedding).
        response_summary: Summary of the response (truncated to 200 chars).
        task_type: LLM task type used (fast, reason, etc.).
        db_path: Override LanceDB path (used in tests).

    Returns:
        True on success, False if disabled or on any error.
    """
    if not is_enabled():
        return False
    try:
        vectors = embed_texts([query[:500]], input_type="search_document")
        if not vectors:
            return False
        table = _get_table(db_path)
        row = {
            "id": str(uuid4()),
            "query": query[:500],
            "response_summary": response_summary[:200],
            "task_type": task_type,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "vector": vectors[0],
        }
        table.add([row])
        _cleanup_if_needed(table)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to store conversation interaction")
        return False


def retrieve_relevant_context(
    query: str,
    limit: int = 3,
    db_path: Path | None = None,
) -> list[str]:
    """Return relevant past response summaries for a query.

    No-op and returns [] if ENABLE_CONVERSATION_MEMORY is not true.

    Args:
        query: The current user message to find past context for.
        limit: Maximum number of past interactions to return.
        db_path: Override LanceDB path (used in tests).

    Returns:
        List of response_summary strings from past interactions, or [].
    """
    if not is_enabled():
        return []
    try:
        vectors = embed_texts([query], input_type="search_query")
        if not vectors:
            return []
        table = _get_table(db_path)
        results = table.search(vectors[0]).limit(limit).to_list()
        return [r["response_summary"] for r in results if r.get("response_summary")]
    except Exception:  # noqa: BLE001
        logger.debug("Conversation memory retrieval failed (table may not exist yet)")
        return []
