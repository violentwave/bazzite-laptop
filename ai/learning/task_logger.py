"""LanceDB logger for task patterns (Phase 22: Task Pattern Learning).

Table: task_patterns

Schema fields:
    id               -- UUID primary key
    description      -- Task description text
    approach         -- Implementation approach taken
    outcome          -- Result/outcome of the task
    files_touched    -- Comma-separated file paths
    tools_used       -- Comma-separated tool names
    tests_added      -- Number of tests added
    phase            -- Phase identifier (e.g., P22)
    agent            -- Agent name (default: claude-code)
    success          -- Always True for logged tasks
    duration_minutes -- Estimated duration in minutes
    token_estimate   -- Estimated token count
    timestamp        -- ISO8601 timestamp (UTC)
    vector           -- 768-dim embedding of "{description} {approach}"
"""

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

TABLE_NAME = "task_patterns"

SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("description", pa.string()),
        pa.field("approach", pa.string()),
        pa.field("outcome", pa.string()),
        pa.field("files_touched", pa.string()),
        pa.field("tools_used", pa.string()),
        pa.field("tests_added", pa.int32()),
        pa.field("phase", pa.string()),
        pa.field("agent", pa.string()),
        pa.field("success", pa.bool_()),
        pa.field("duration_minutes", pa.int32()),
        pa.field("token_estimate", pa.int32()),
        pa.field("timestamp", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ]
)


class TaskLogger:
    """Log task patterns to LanceDB for future retrieval."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize TaskLogger.

        Args:
            db_path: Path to LanceDB directory. Defaults to VECTOR_DB_DIR.
        """
        self._db_path = Path(db_path) if db_path else VECTOR_DB_DIR
        self._db = None
        self._table = None

    def _connect(self):
        """Get or create LanceDB connection."""
        if self._db is not None:
            return self._db
        try:
            self._db_path.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self._db_path))
        except (OSError, PermissionError) as e:
            logger.error("Failed to connect to LanceDB at %s: %s", self._db_path, e)
            raise
        return self._db

    def _get_or_create_table(self):
        """Open task_patterns table, creating it with schema if needed."""
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

    def log_success(
        self,
        description: str,
        approach: str,
        outcome: str,
        files_touched: list[str] | None = None,
        tools_used: list[str] | None = None,
        tests_added: int = 0,
        phase: str | None = None,
        agent: str = "claude-code",
        duration_minutes: int = 0,
        token_estimate: int = 0,
    ) -> str:
        """Log a successful task pattern to LanceDB.

        Args:
            description: Task description.
            approach: Implementation approach taken.
            outcome: Result/outcome of the task.
            files_touched: List of file paths modified.
            tools_used: List of tool names used.
            tests_added: Number of tests added.
            phase: Phase identifier (e.g., P22).
            agent: Agent name (default: claude-code).
            duration_minutes: Estimated duration in minutes.
            token_estimate: Estimated token count.

        Returns:
            The UUID of the newly created row.
        """
        embedding = embed_single(f"{description} {approach}")

        files_str = ",".join(files_touched) if files_touched else ""
        tools_str = ",".join(tools_used) if tools_used else ""

        entry = {
            "id": str(uuid4()),
            "description": description,
            "approach": approach,
            "outcome": outcome,
            "files_touched": files_str,
            "tools_used": tools_str,
            "tests_added": tests_added,
            "phase": phase or "",
            "agent": agent,
            "success": True,
            "duration_minutes": duration_minutes,
            "token_estimate": token_estimate,
            "timestamp": datetime.now(UTC).isoformat(),
            "vector": embedding,
        }

        table = self._get_or_create_table()
        table.add([entry])

        logger.info("Logged task pattern %s to %s", entry["id"], TABLE_NAME)
        return entry["id"]
