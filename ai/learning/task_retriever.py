"""Task retrieval by semantic similarity (Phase 22: Task Pattern Learning).

Provides retrieve_similar_tasks() to find similar past successful tasks
from the task_patterns LanceDB table.
"""

import logging
from pathlib import Path

import lancedb

from ai.config import VECTOR_DB_DIR
from ai.learning.task_logger import TABLE_NAME
from ai.rag.embedder import embed_single

logger = logging.getLogger(__name__)


def retrieve_similar_tasks(
    query: str,
    top_k: int = 3,
    min_similarity: float = 0.75,
    db_path: str | None = None,
) -> list[dict]:
    """Find similar past successful tasks by semantic similarity.

    Args:
        query: Query text to search for.
        top_k: Maximum number of results to return.
        min_similarity: Minimum similarity threshold (0-1).
        db_path: Path to LanceDB directory. Defaults to VECTOR_DB_DIR.

    Returns:
        List of dicts with keys: id, description, approach, outcome,
        files_touched, tools_used, phase, agent, timestamp.
        Empty list if table doesn't exist or no matching results.
    """
    db_path = Path(db_path) if db_path else VECTOR_DB_DIR

    try:
        db_path.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(db_path))
    except (OSError, PermissionError) as e:
        logger.error("Failed to connect to LanceDB at %s: %s", db_path, e)
        return []

    try:
        tables = db.list_tables()
        existing = tables.tables if hasattr(tables, "tables") else list(tables)
        if TABLE_NAME not in existing:
            logger.debug("Table %s does not exist yet", TABLE_NAME)
            return []
    except Exception as e:
        logger.debug("Error checking existing tables: %s", e)
        return []

    try:
        table = db.open_table(TABLE_NAME)
    except Exception:
        logger.debug("Could not open table %s", TABLE_NAME)
        return []

    try:
        vector = embed_single(query)
    except Exception as e:
        logger.error("Failed to embed query: %s", e)
        return []

    try:
        results = table.search(vector).where("success = true").limit(top_k).to_list()
    except Exception as e:
        logger.error("Search failed: %s", e)
        return []

    distance_threshold = 1.0 - min_similarity

    cleaned = []
    for row in results:
        distance = row.get("_distance", 1.0)
        if distance >= distance_threshold:
            continue

        cleaned.append(
            {
                "id": row.get("id", ""),
                "description": row.get("description", ""),
                "approach": row.get("approach", ""),
                "outcome": row.get("outcome", ""),
                "files_touched": row.get("files_touched", ""),
                "tools_used": row.get("tools_used", ""),
                "phase": row.get("phase", ""),
                "agent": row.get("agent", ""),
                "timestamp": row.get("timestamp", ""),
            }
        )

    return cleaned
