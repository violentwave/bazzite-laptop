"""Task queue for agent coordination."""

import json
import logging
import sqlite3
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger("ai.collab")

_TASK_DB_PATH = Path.home() / ".config" / "bazzite-ai" / "task-queue.db"


class TaskStatus(Enum):
    """Task status values."""

    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class TaskType(Enum):
    """Task type values."""

    IMPLEMENT_FEATURE = "implement_feature"
    IMPLEMENT_MCP_TOOL = "implement_mcp_tool"
    REFACTOR_MODULE = "refactor_module"
    WRITE_TESTS = "write_tests"
    FIX_BUG = "fix_bug"
    AUDIT_CODE = "audit_code"
    REVIEW_PR = "review_pr"
    UPDATE_DOCS = "update_docs"
    SECURITY_AUDIT = "security_audit"


AGENT_ROUTING = {
    TaskType.IMPLEMENT_FEATURE: "claude_code",
    TaskType.IMPLEMENT_MCP_TOOL: "claude_code",
    TaskType.REFACTOR_MODULE: "claude_code",
    TaskType.WRITE_TESTS: "claude_code",
    TaskType.FIX_BUG: "opencode",
    TaskType.AUDIT_CODE: "opencode",
    TaskType.REVIEW_PR: "opencode",
    TaskType.UPDATE_DOCS: "opencode",
    TaskType.SECURITY_AUDIT: "opencode",
}


def _ensure_db_dir() -> None:
    """Ensure config directory exists."""
    _TASK_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class TaskQueue:
    """SQLite-backed task queue for agent coordination."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or _TASK_DB_PATH
        _ensure_db_dir()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                task_type TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 3,
                status TEXT DEFAULT 'pending',
                agent_affinity TEXT,
                parent_id TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                files_touched TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                task_id TEXT PRIMARY KEY,
                result TEXT,
                files_touched TEXT,
                completed_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT NOT NULL,
                depends_on TEXT NOT NULL,
                PRIMARY KEY (task_id, depends_on)
            )
        """)

        conn.commit()
        conn.close()

    def add_task(
        self,
        title: str,
        task_type: TaskType,
        description: str = "",
        priority: int = 3,
        agent_affinity: str | None = None,
        dependencies: list[str] | None = None,
        parent_id: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Create a new task."""
        import uuid

        task_id = str(uuid.uuid4())

        if agent_affinity is None:
            agent_affinity = AGENT_ROUTING.get(task_type, "opencode")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.now(UTC).isoformat()
        cursor.execute(
            """INSERT INTO tasks (task_id, title, task_type, description, priority,
                                  status, agent_affinity, parent_id, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                title,
                task_type.value,
                description,
                priority,
                TaskStatus.PENDING.value,
                agent_affinity,
                parent_id,
                timestamp,
                json.dumps(metadata) if metadata else None,
            ),
        )

        if dependencies:
            for dep in dependencies:
                cursor.execute(
                    "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on) VALUES (?, ?)",
                    (task_id, dep),
                )

        conn.commit()
        conn.close()
        return task_id

    def claim_task(self, agent_name: str, task_types: list[TaskType] | None = None) -> dict | None:
        """Claim a task for an agent."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = """
            SELECT task_id, title, task_type, description, priority, agent_affinity
            FROM tasks
            WHERE status = 'pending'
        """
        if task_types:
            type_values = ",".join(f"'{t.value}'" for t in task_types)
            query += f" AND task_type IN ({type_values})"
        query += " ORDER BY priority ASC LIMIT 1"

        cursor.execute(query)
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        task_id = row[0]
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE task_id = ?",
            (TaskStatus.CLAIMED.value, task_id),
        )
        conn.commit()
        conn.close()

        return {
            "task_id": row[0],
            "title": row[1],
            "task_type": row[2],
            "description": row[3],
            "priority": row[4],
            "agent_affinity": row[5],
        }

    def start_task(self, task_id: str, agent_name: str) -> None:
        """Mark task as in progress."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.now(UTC).isoformat()
        cursor.execute(
            "UPDATE tasks SET status = ?, started_at = ? WHERE task_id = ?",
            (TaskStatus.IN_PROGRESS.value, timestamp, task_id),
        )
        conn.commit()
        conn.close()

    def complete_task(
        self, task_id: str, result: str = "", files_touched: list[str] | None = None
    ) -> None:
        """Mark task as done."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.now(UTC).isoformat()
        cursor.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, result = ?, files_touched = ? "
            "WHERE task_id = ?",
            (TaskStatus.DONE.value, timestamp, result, json.dumps(files_touched), task_id),
        )

        cursor.execute(
            "INSERT OR REPLACE INTO task_results "
            "(task_id, result, files_touched, completed_at) VALUES (?, ?, ?, ?)",
            (task_id, result, json.dumps(files_touched), timestamp),
        )

        conn.commit()
        conn.close()

    def fail_task(self, task_id: str, error: str = "") -> None:
        """Mark task as failed."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
            (TaskStatus.FAILED.value, error, task_id),
        )
        conn.commit()
        conn.close()

    def get_ready_tasks(self, agent_name: str | None = None) -> list[dict]:
        """Get tasks whose dependencies are all done."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.task_id, t.title, t.task_type, t.description, t.priority, t.agent_affinity
            FROM tasks t
            WHERE t.status = 'pending'
            AND NOT EXISTS (
                SELECT 1 FROM task_dependencies td
                WHERE td.task_id = t.task_id
                AND td.depends_on NOT IN (
                    SELECT task_id FROM tasks WHERE status = 'done'
                )
            )
            ORDER BY t.priority ASC
        """)

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "task_id": row[0],
                    "title": row[1],
                    "task_type": row[2],
                    "description": row[3],
                    "priority": row[4],
                    "agent_affinity": row[5],
                }
            )

        conn.close()
        return results

    def decompose_task(self, parent_id: str, subtasks: list[dict]) -> list[str]:
        """Create subtasks with dependencies."""
        task_ids = []
        prev_id = None

        for i, subtask in enumerate(subtasks):
            deps = [parent_id]
            if prev_id:
                deps.append(prev_id)

            task_id = self.add_task(
                title=subtask.get("title", f"Subtask {i}"),
                task_type=TaskType(subtask.get("task_type", "implement_feature")),
                description=subtask.get("description", ""),
                priority=subtask.get("priority", 3),
                dependencies=deps,
            )
            task_ids.append(task_id)
            prev_id = task_id

        return task_ids

    def get_queue_status(self) -> dict:
        """Get queue status summary."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) FROM tasks GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT agent_affinity, COUNT(*) FROM tasks
            WHERE status IN ('pending', 'claimed', 'in_progress')
            GROUP BY agent_affinity
        """)
        agent_counts = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()
        return {
            "by_status": status_counts,
            "by_agent": agent_counts,
            "total": sum(status_counts.values()),
        }


_queue_instance: TaskQueue | None = None


def get_queue() -> TaskQueue:
    """Get singleton TaskQueue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = TaskQueue()
    return _queue_instance
