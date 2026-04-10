"""Lease behavior tests for P55 phase sync backend."""

from datetime import UTC, datetime, timedelta

from ai.phase_control.models import PhaseRow, PhaseStatus
from ai.phase_control.notion_sync import InMemoryPhaseSync


def test_claim_lease_prevents_duplicate_owners():
    phase = PhaseRow(
        phase_name="P55",
        phase_number=55,
        status=PhaseStatus.READY,
        execution_prompt="do it",
        validation_commands=["python -V"],
        done_criteria=["ok"],
    )
    sync = InMemoryPhaseSync([phase])

    first = sync.claim_lease(
        55,
        run_id="run-a",
        runner_host="host-a",
        lease_seconds=300,
        slack_channel="C1",
        slack_thread_ts="1.2",
    )
    second = sync.claim_lease(
        55,
        run_id="run-b",
        runner_host="host-b",
        lease_seconds=300,
        slack_channel="C1",
        slack_thread_ts="1.2",
    )
    assert first is True
    assert second is False


def test_expired_lease_can_be_reclaimed():
    phase = PhaseRow(
        phase_name="P55",
        phase_number=55,
        status=PhaseStatus.READY,
        execution_prompt="do it",
        validation_commands=["python -V"],
        done_criteria=["ok"],
        run_id="run-a",
        lease_expires_at=datetime.now(tz=UTC) - timedelta(seconds=1),
    )
    sync = InMemoryPhaseSync([phase])
    claimed = sync.claim_lease(
        55,
        run_id="run-b",
        runner_host="host-b",
        lease_seconds=300,
        slack_channel="C1",
        slack_thread_ts="1.2",
    )
    assert claimed is True
