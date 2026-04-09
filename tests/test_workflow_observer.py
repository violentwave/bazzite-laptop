"""Comprehensive tests for WorkflowObserver persistence and summaries."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from ai.orchestration.observer import WorkflowObserver
from ai.workflows.runner import WorkflowRunner


class _DateTimeProxy:
    UTC = UTC

    @staticmethod
    def now(tz=None):
        return datetime.now(tz)

    @staticmethod
    def fromisoformat(value: str):
        return datetime.fromisoformat(value)


@pytest.fixture(autouse=True)
def _patch_observer_datetime():
    with patch("ai.orchestration.observer.datetime", _DateTimeProxy):
        yield


class _FakeTable:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, rows: list[dict]) -> None:
        self.rows.extend(dict(row) for row in rows)

    def to_pandas(self):
        return pd.DataFrame(self.rows)

    def delete(self, expression: str) -> None:
        step_id = expression.split("'")[1]
        self.rows = [row for row in self.rows if row.get("step_id") != step_id]


@pytest.fixture(autouse=True)
def _patch_observer_table():
    def fake_get_table(self):
        if not hasattr(self, "_fake_table"):
            self._fake_table = _FakeTable()
        return self._fake_table

    with patch.object(WorkflowObserver, "_get_table", fake_get_table):
        yield


def test_record_step_start_creates_row(tmp_path):
    """call record_step_start and verify row exists with running status."""
    observer = WorkflowObserver(db_path=tmp_path)

    step_id = observer.record_step_start(
        run_id="run-1",
        workflow_name="wf",
        step_name="step-a",
        tool_called="tool.a",
        agent_name="agent-a",
    )

    steps = observer.get_run_steps("run-1")
    assert len(steps) == 1
    assert steps[0]["step_id"] == step_id
    assert steps[0]["status"] == "running"


def test_record_step_end_updates_row(tmp_path):
    """start then end a step; verify status and non-zero duration."""
    observer = WorkflowObserver(db_path=tmp_path)
    step_id = observer.record_step_start(
        run_id="run-2",
        workflow_name="wf",
        step_name="step-a",
        tool_called="tool.a",
        agent_name="agent-a",
    )

    observer.record_step_end(step_id=step_id, status="success", output="ok")
    step = observer.get_run_steps("run-2")[0]

    assert step["status"] == "success"
    assert step["duration_ms"] > 0
    assert step["output_preview"] == "ok"


def test_record_step_end_failure(tmp_path):
    """end a step with error and verify failed fields are persisted."""
    observer = WorkflowObserver(db_path=tmp_path)
    step_id = observer.record_step_start(
        run_id="run-3",
        workflow_name="wf",
        step_name="step-a",
        tool_called="tool.a",
        agent_name="agent-a",
    )

    observer.record_step_end(step_id=step_id, status="failed", error="boom")
    step = observer.get_run_steps("run-3")[0]

    assert step["status"] == "failed"
    assert step["error"] == "boom"


def test_get_run_steps_returns_all(tmp_path):
    """record 3 steps in one run and verify all are returned."""
    observer = WorkflowObserver(db_path=tmp_path)

    for idx in range(3):
        step_id = observer.record_step_start(
            run_id="run-4",
            workflow_name="wf",
            step_name=f"step-{idx}",
            tool_called="tool.a",
            agent_name="agent-a",
        )
        observer.record_step_end(step_id=step_id, status="success", output=f"ok-{idx}")

    steps = observer.get_run_steps("run-4")
    assert len(steps) == 3


def test_get_run_summary_success(tmp_path):
    """3 successful steps should yield success run summary."""
    observer = WorkflowObserver(db_path=tmp_path)

    for idx in range(3):
        step_id = observer.record_step_start(
            run_id="run-5",
            workflow_name="wf",
            step_name=f"step-{idx}",
            tool_called="tool.a",
            agent_name="agent-a",
        )
        observer.record_step_end(step_id=step_id, status="success")

    summary = observer.get_run_summary("run-5")
    assert summary["status"] == "success"
    assert summary["completed"] == 3
    assert summary["failed"] == 0


def test_get_run_summary_partial_failure(tmp_path):
    """2 success + 1 failed step should yield failed run summary."""
    observer = WorkflowObserver(db_path=tmp_path)

    for _ in range(2):
        step_id = observer.record_step_start(
            run_id="run-6",
            workflow_name="wf",
            step_name="ok-step",
            tool_called="tool.a",
            agent_name="agent-a",
        )
        observer.record_step_end(step_id=step_id, status="success")

    failed_step_id = observer.record_step_start(
        run_id="run-6",
        workflow_name="wf",
        step_name="bad-step",
        tool_called="tool.b",
        agent_name="agent-b",
    )
    observer.record_step_end(step_id=failed_step_id, status="failed", error="bad")

    summary = observer.get_run_summary("run-6")
    assert summary["status"] == "failed"
    assert summary["completed"] == 2
    assert summary["failed"] == 1


def test_cancel_run_updates_pending(tmp_path):
    """pending steps for a run become cancelled after cancel_run."""
    observer = WorkflowObserver(db_path=tmp_path)
    table = observer._get_table()
    started_at = datetime.now(UTC).isoformat()

    table.add(
        [
            {
                "run_id": "run-7",
                "step_id": "pending-1",
                "workflow_name": "wf",
                "step_name": "p1",
                "tool_called": "tool.a",
                "agent_name": "agent-a",
                "started_at": started_at,
                "finished_at": "",
                "duration_ms": 0.0,
                "status": "pending",
                "error": "",
                "retry_count": 0,
                "output_preview": "",
            },
            {
                "run_id": "run-7",
                "step_id": "pending-2",
                "workflow_name": "wf",
                "step_name": "p2",
                "tool_called": "tool.b",
                "agent_name": "agent-b",
                "started_at": started_at,
                "finished_at": "",
                "duration_ms": 0.0,
                "status": "pending",
                "error": "",
                "retry_count": 0,
                "output_preview": "",
            },
        ]
    )

    cancelled = observer.cancel_run("run-7")
    steps = observer.get_run_steps("run-7")

    assert cancelled == 2
    assert len(steps) == 2
    assert all(step["status"] == "cancelled" for step in steps)


def test_get_recent_runs_limit(tmp_path):
    """create 5 runs and verify get_recent_runs(3) returns 3."""
    observer = WorkflowObserver(db_path=tmp_path)

    for idx in range(5):
        step_id = observer.record_step_start(
            run_id=f"run-{idx}",
            workflow_name="wf",
            step_name="step",
            tool_called="tool.a",
            agent_name="agent-a",
        )
        observer.record_step_end(step_id=step_id, status="success")

    recent = observer.get_recent_runs(limit=3)
    assert len(recent) == 3


def test_observer_does_not_crash_workflow(tmp_path):
    """if observer raises, workflow execution still completes."""
    runner = WorkflowRunner()
    runner._execute_tool = AsyncMock(return_value="ok")

    plan = [{"id": "step_1", "tool": "tool.a", "args": {}}]
    broken_observer = MagicMock()
    broken_observer.record_step_start.side_effect = RuntimeError("observer down")

    with patch("ai.orchestration.observer.get_observer", return_value=broken_observer):
        result = asyncio.run(runner.run_plan(plan, workflow_name="wf", run_id="run-8"))

    assert result["status"] == "complete"
    assert result["steps"]["step_1"]["status"] == "complete"


def test_output_preview_truncation(tmp_path):
    """long output preview should be truncated to 200 chars."""
    observer = WorkflowObserver(db_path=tmp_path)
    step_id = observer.record_step_start(
        run_id="run-9",
        workflow_name="wf",
        step_name="step-a",
        tool_called="tool.a",
        agent_name="agent-a",
    )

    observer.record_step_end(step_id=step_id, status="success", output=("x" * 300))
    step = observer.get_run_steps("run-9")[0]

    assert len(step["output_preview"]) == 200
    assert step["output_preview"] == "x" * 200
