"""Workflow definitions storage."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("ai.workflows")


class WorkflowStore:
    """LanceDB-backed workflow storage."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize workflows table."""
        schema = pa.schema(
            [
                pa.field("workflow_id", pa.string()),
                pa.field("name", pa.string()),
                pa.field("description", pa.string()),
                pa.field("schedule", pa.string()),  # cron
                pa.field("steps", pa.string()),  # JSON list
                pa.field("trigger_type", pa.string()),  # manual, schedule, file_change, event
                pa.field("trigger_config", pa.string()),  # JSON
                pa.field("enabled", pa.bool_()),
                pa.field("created_at", pa.string()),
                pa.field("last_run", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        table_names = self._db.list_tables()
        if "workflows" in table_names:
            self._table = self._db.open_table("workflows")
        else:
            self._table = self._db.create_table("workflows", schema=schema)

    def save_workflow(
        self,
        name: str,
        description: str,
        steps: list[dict],
        schedule: str | None = None,
        trigger_type: str = "manual",
        trigger_config: dict | None = None,
    ) -> str:
        """Save a workflow."""
        import uuid

        workflow_id = str(uuid.uuid4())

        timestamp = datetime.now(UTC).isoformat()

        try:
            vector = embed(f"{name} {description}")
        except Exception:
            vector = [0.0] * 768

        self._table.add(
            [
                {
                    "workflow_id": workflow_id,
                    "name": name,
                    "description": description,
                    "schedule": schedule or "",
                    "steps": json.dumps(steps),
                    "trigger_type": trigger_type,
                    "trigger_config": json.dumps(trigger_config) if trigger_config else "{}",
                    "enabled": True,
                    "created_at": timestamp,
                    "last_run": "",
                    "vector": vector,
                }
            ]
        )

        return workflow_id

    def get_workflow(self, workflow_id: str) -> dict | None:
        """Get a workflow by ID."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return None

            row = df[df["workflow_id"] == workflow_id]
            if row.empty:
                return None

            row = row.iloc[0]
            return {
                "workflow_id": row["workflow_id"],
                "name": row["name"],
                "description": row["description"],
                "schedule": row["schedule"],
                "steps": json.loads(row["steps"]),
                "trigger_type": row["trigger_type"],
                "trigger_config": json.loads(row["trigger_config"]),
                "enabled": row["enabled"],
                "created_at": row["created_at"],
                "last_run": row["last_run"],
            }
        except Exception as e:
            logger.warning(f"Failed to get workflow: {e}")
            return None

    def list_workflows(self, enabled_only: bool = True) -> list[dict]:
        """List all workflows."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return []

            if enabled_only:
                df = df[df["enabled"]]

            results = []
            for _, row in df.iterrows():
                results.append(
                    {
                        "workflow_id": row["workflow_id"],
                        "name": row["name"],
                        "description": row["description"],
                        "trigger_type": row["trigger_type"],
                        "enabled": row["enabled"],
                    }
                )

            return results
        except Exception as e:
            logger.warning(f"Failed to list workflows: {e}")
            return []

    def search_workflows(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search for workflows."""
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
                results.append(
                    {
                        "workflow_id": row["workflow_id"],
                        "name": row["name"],
                        "description": row["description"],
                    }
                )

            return results
        except Exception as e:
            logger.warning(f"Failed to search workflows: {e}")
            return []

    def disable_workflow(self, workflow_id: str) -> None:
        """Disable a workflow."""
        try:
            self._table.update(f"workflow_id = '{workflow_id}'", {"enabled": False})
        except Exception as e:
            logger.warning(f"Failed to disable workflow: {e}")

    def enable_workflow(self, workflow_id: str) -> None:
        """Enable a workflow."""
        try:
            self._table.update(f"workflow_id = '{workflow_id}'", {"enabled": True})
        except Exception as e:
            logger.warning(f"Failed to enable workflow: {e}")


_store_instance: WorkflowStore | None = None


def get_workflow_store() -> WorkflowStore:
    """Get singleton WorkflowStore."""
    global _store_instance
    if _store_instance is None:
        _store_instance = WorkflowStore()
    return _store_instance


SECURITY_DEEP_SCAN = {
    "name": "security_deep_scan",
    "description": "Chained security: AV scan → ingest → CVE check → threat/alert → audit",
    "steps": [
        {"id": "av_scan", "tool": "security.run_scan", "args": {"scan_type": "quick"}},
        {
            "id": "log_ingest",
            "tool": "security.run_ingest",
            "args": {},
        },
        {
            "id": "cve_check",
            "tool": "security.cve_check",
            "args": {},
            "depends_on": ["log_ingest"],
        },
        {
            "id": "threat_summary",
            "tool": "security.threat_summary",
            "args": {},
            "depends_on": ["log_ingest"],
        },
        {
            "id": "alert_summary",
            "tool": "security.alert_summary",
            "args": {},
            "depends_on": ["log_ingest"],
        },
        {
            "id": "full_audit",
            "agent": "security",
            "task_type": "run_audit",
            "args": {},
            "depends_on": ["cve_check", "threat_summary", "alert_summary"],
        },
    ],
}

CODE_HEALTH_CHECK = {
    "name": "code_health_check",
    "description": "Lint check → performance profile on changed files → store tuning insight",
    "steps": [
        {"id": "lint", "agent": "code_quality", "task_type": "lint_check", "args": {}},
        {
            "id": "profile",
            "agent": "performance",
            "task_type": "profile_tool",
            "payload_from": "lint",
            "args": {},
            "depends_on": ["lint"],
        },
        {
            "id": "store",
            "agent": "knowledge",
            "task_type": "store_insight",
            "payload_from": "profile",
            "args": {"category": "performance_insight"},
            "depends_on": ["profile"],
        },
    ],
}

MORNING_BRIEFING_ENRICHED = {
    "name": "morning_briefing_enriched",
    "description": "Memory search → parallel agent execution → summarize results",
    "steps": [
        {
            "id": "memory_context",
            "tool": "memory.search",
            "args": {"query": "recent security incidents system health"},
        },
        {"id": "security", "agent": "security", "task_type": "run_audit", "args": {}},
        {"id": "code", "agent": "code_quality", "task_type": "lint_check", "args": {}},
        {"id": "perf", "agent": "performance", "task_type": "detect_regression", "args": {}},
        {"id": "timers", "agent": "timer_sentinel", "task_type": "check_timers", "args": {}},
        {
            "id": "collect",
            "agent": "knowledge",
            "task_type": "summarize_session",
            "args": {"context_keys": ["memory_context", "security", "code", "perf", "timers"]},
            "depends_on": ["memory_context", "security", "code", "perf", "timers"],
        },
    ],
}

WORKFLOW_REGISTRY = {
    "security_deep_scan": SECURITY_DEEP_SCAN,
    "code_health_check": CODE_HEALTH_CHECK,
    "morning_briefing_enriched": MORNING_BRIEFING_ENRICHED,
}
