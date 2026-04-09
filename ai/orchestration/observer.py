"""Workflow step recording for per-step run tracking.

Provides WorkflowObserver class for recording workflow execution steps
to LanceDB 'workflow_steps' table.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger(__name__)

WORKFLOW_STEPS_SCHEMA = pa.schema(
    [
        pa.field("run_id", pa.utf8()),
        pa.field("step_id", pa.utf8()),
        pa.field("workflow_name", pa.utf8()),
        pa.field("step_name", pa.utf8()),
        pa.field("tool_called", pa.utf8()),
        pa.field("agent_name", pa.utf8()),
        pa.field("started_at", pa.utf8()),
        pa.field("finished_at", pa.utf8()),
        pa.field("duration_ms", pa.float64()),
        pa.field("status", pa.utf8()),
        pa.field("error", pa.utf8()),
        pa.field("retry_count", pa.int32()),
        pa.field("output_preview", pa.utf8()),
    ]
)


class WorkflowObserver:
    """Records workflow execution steps to LanceDB."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialize the observer with LanceDB connection.

        Args:
            db_path: Optional path to LanceDB. Defaults to VECTOR_DB_DIR.
        """
        self._db_path = Path(db_path) if db_path else VECTOR_DB_DIR
        self._db: lancedb.LanceDB | None = None
        self._table = None

    def _get_table(self) -> lancedb.table.LanceTable:
        """Get or create the workflow_steps table."""
        if self._db is None:
            self._db = lancedb.connect(str(self._db_path))

        try:
            table = self._db.open_table("workflow_steps")
            self._table = table
            return table
        except lancedb.io.LanceDBError:
            table = self._db.create_table("workflow_steps", schema=WORKFLOW_STEPS_SCHEMA)
            self._table = table
            return table

    def record_step_start(
        self,
        run_id: str,
        workflow_name: str,
        step_name: str,
        tool_called: str,
        agent_name: str,
    ) -> str:
        """Record the start of a workflow step.

        Args:
            run_id: The workflow run ID.
            workflow_name: Name of the workflow.
            step_name: Name of the step.
            tool_called: Tool that was invoked.
            agent_name: Agent handling the step.

        Returns:
            The step_id (UUID) for the new step.
        """
        step_id = str(uuid.uuid4())
        started_at = datetime.now(datetime.UTC).isoformat()

        row = {
            "run_id": run_id,
            "step_id": step_id,
            "workflow_name": workflow_name,
            "step_name": step_name,
            "tool_called": tool_called,
            "agent_name": agent_name,
            "started_at": started_at,
            "finished_at": "",
            "duration_ms": 0.0,
            "status": "running",
            "error": "",
            "retry_count": 0,
            "output_preview": "",
        }

        table = self._get_table()
        table.add([row])
        logger.debug(
            "Recorded step start: run_id=%s, step_id=%s, step_name=%s", run_id, step_id, step_name
        )

        return step_id

    def record_step_end(
        self,
        step_id: str,
        status: str,
        output: Any | None = None,
        error: str | None = None,
        retry_count: int = 0,
    ) -> None:
        """Record the end of a workflow step (atomic update).

        Uses delete-then-insert pattern for LanceDB update.

        Args:
            step_id: The step ID from record_step_start.
            status: One of: success, failed, cancelled.
            output: Optional output from the step.
            error: Optional error message.
            retry_count: Number of retries attempted.
        """
        table = self._get_table()

        existing = table.to_pandas()
        step_rows = existing[existing["step_id"] == step_id]

        if step_rows.empty:
            logger.warning("Step not found for update: step_id=%s", step_id)
            return

        original_row = step_rows.iloc[0].to_dict()
        started_at_str = original_row["started_at"]
        started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
        finished_at = datetime.now(datetime.UTC)
        duration_ms = (finished_at - started_at).total_seconds() * 1000.0

        output_preview = ""
        if output is not None:
            preview = str(output)[:200].replace("\n", " ").strip()
            output_preview = preview

        error_str = error if error else ""

        updated_row = {
            "run_id": original_row["run_id"],
            "step_id": step_id,
            "workflow_name": original_row["workflow_name"],
            "step_name": original_row["step_name"],
            "tool_called": original_row["tool_called"],
            "agent_name": original_row["agent_name"],
            "started_at": started_at_str,
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "status": status,
            "error": error_str,
            "retry_count": retry_count,
            "output_preview": output_preview,
        }

        table.delete(f"step_id == '{step_id}'")
        table.add([updated_row])
        logger.debug(
            "Recorded step end: step_id=%s, status=%s, duration_ms=%.2f",
            step_id,
            status,
            duration_ms,
        )

    def get_run_steps(self, run_id: str) -> list[dict]:
        """Get all steps for a run, sorted by started_at.

        Args:
            run_id: The workflow run ID.

        Returns:
            List of step dictionaries sorted by started_at.
        """
        table = self._get_table()
        df = table.to_pandas()
        run_steps = df[df["run_id"] == run_id].sort_values("started_at")
        return run_steps.to_dict(orient="records")

    def get_run_summary(self, run_id: str) -> dict:
        """Get summary for a workflow run.

        Args:
            run_id: The workflow run ID.

        Returns:
            Dictionary with run summary including status, counts, and timing.
        """
        steps = self.get_run_steps(run_id)

        if not steps:
            return {
                "run_id": run_id,
                "workflow_name": "",
                "total_steps": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "total_duration_ms": 0.0,
                "started_at": "",
                "finished_at": "",
                "status": "not_found",
            }

        workflow_name = steps[0].get("workflow_name", "")
        total_steps = len(steps)
        completed = sum(1 for s in steps if s.get("status") == "success")
        failed = sum(1 for s in steps if s.get("status") == "failed")
        cancelled = sum(1 for s in steps if s.get("status") == "cancelled")

        started_times = [s.get("started_at", "") for s in steps if s.get("started_at")]
        finished_times = [s.get("finished_at", "") for s in steps if s.get("finished_at")]

        started_at = min(started_times) if started_times else ""
        finished_at = max(finished_times) if finished_times else ""

        total_duration_ms = sum(s.get("duration_ms", 0.0) for s in steps)

        has_running = any(s.get("status") == "running" for s in steps)
        if has_running:
            status = "running"
        elif failed > 0:
            status = "failed"
        elif cancelled > 0:
            status = "cancelled"
        else:
            status = "success"

        return {
            "run_id": run_id,
            "workflow_name": workflow_name,
            "total_steps": total_steps,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "total_duration_ms": total_duration_ms,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
        }

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        """Get recent workflow runs with summaries.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            List of run summaries sorted by started_at descending.
        """
        table = self._get_table()
        df = table.to_pandas()

        if df.empty:
            return []

        run_ids = df["run_id"].unique()[:limit]
        summaries = []

        for run_id in run_ids:
            summary = self.get_run_summary(run_id)
            if summary["status"] != "not_found":
                summaries.append(summary)

        summaries.sort(key=lambda x: x["started_at"], reverse=True)
        return summaries[:limit]

    def cancel_run(self, run_id: str) -> int:
        """Cancel a workflow run by marking pending/running steps as cancelled.

        Args:
            run_id: The workflow run ID.

        Returns:
            Number of rows updated.
        """
        table = self._get_table()
        df = table.to_pandas()

        run_steps = df[df["run_id"] == run_id]
        to_cancel = run_steps[run_steps["status"].isin(["pending", "running"])]

        if to_cancel.empty:
            return 0

        cancelled_count = 0
        for _, row in to_cancel.iterrows():
            step_id = row["step_id"]
            self.record_step_end(step_id, status="cancelled")
            cancelled_count += 1

        logger.info("Cancelled run %s: %d steps marked cancelled", run_id, cancelled_count)
        return cancelled_count


_observer: WorkflowObserver | None = None


def get_observer() -> WorkflowObserver:
    """Get the singleton WorkflowObserver instance.

    Returns:
        The singleton WorkflowObserver.
    """
    global _observer
    if _observer is None:
        _observer = WorkflowObserver()
    return _observer
