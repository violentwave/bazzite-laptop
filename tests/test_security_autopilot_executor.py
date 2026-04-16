"""P122 tests for Safe Remediation Runner."""

from __future__ import annotations

import json

from ai.security_autopilot.audit import AuditLedger, EvidenceManager
from ai.security_autopilot.executor import (
    ExecutionApproval,
    RemediationExecutionRequest,
    SafeRemediationExecutor,
)
from ai.security_autopilot.policy import PolicyMode, SecurityAutopilotPolicy


def _build_executor(tmp_path, calls: list[tuple[str, dict]]):
    def _runner(tool_name: str, args: dict):
        calls.append((tool_name, args))
        return {"success": True, "tool": tool_name, "args": args}

    return SafeRemediationExecutor(
        policy=SecurityAutopilotPolicy(),
        audit_ledger=AuditLedger(path=tmp_path / "audit.jsonl"),
        evidence_manager=EvidenceManager(),
        tool_runner=_runner,
    )


def _read_audit(tmp_path):
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_safe_allowlisted_action_execution_generates_audit_and_evidence(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(
        RemediationExecutionRequest(
            action_id="run_health_snapshot",
            payload={"reason": "routine check"},
            mode=PolicyMode.SAFE_AUTO,
        )
    )

    assert result.status == "executed"
    assert result.executed is True
    assert result.evidence_bundle_id
    assert result.audit_event_id
    assert calls == [("security.run_health", {})]

    audit = _read_audit(tmp_path)
    assert len(audit) == 1
    assert audit[0]["event_type"] == "remediation.executed"


def test_unknown_action_rejected(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(RemediationExecutionRequest(action_id="unknown_action", payload={}))

    assert result.status == "rejected"
    assert "Unknown remediation action" in result.reason
    assert calls == []


def test_arbitrary_shell_rejected(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(
        RemediationExecutionRequest(
            action_id="notify_operator",
            payload={"message": "bash -lc 'rm -rf /'"},
        )
    )

    assert result.status == "rejected"
    assert "shell-like" in result.reason
    assert calls == []


def test_sudo_rejected(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(
        RemediationExecutionRequest(
            action_id="notify_operator",
            payload={"message": "sudo systemctl stop service"},
        )
    )

    assert result.status == "rejected"
    assert "shell-like" in result.reason
    assert calls == []


def test_secret_and_path_sanitization_rejection(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(
        RemediationExecutionRequest(
            action_id="notify_operator",
            payload={"message": "api_key=ABC123"},
            target="/usr/bin/tool",
        )
    )

    assert result.status == "rejected"
    assert "Unsafe target path" in result.reason
    audit = _read_audit(tmp_path)
    serialized = json.dumps(audit)
    assert "ABC123" not in serialized


def test_approval_required_rejected_when_missing(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(
        RemediationExecutionRequest(
            action_id="prepare_quarantine_request",
            payload={"artifact": "/tmp/suspicious.bin", "reason": "manual triage"},
            mode=PolicyMode.APPROVAL_REQUIRED,
        )
    )

    assert result.status == "rejected"
    assert result.approval_required is True
    assert "Approval required" in result.reason
    assert result.executed is False


def test_policy_blocked_rejection(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    result = executor.execute(
        RemediationExecutionRequest(
            action_id="run_log_ingest",
            payload={"reason": "maintenance"},
            mode=PolicyMode.LOCKDOWN,
        )
    )

    assert result.status == "rejected"
    assert result.policy_decision == "blocked"
    assert result.executed is False
    assert calls == []


def test_rollback_metadata_presence_and_absence(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    prepared = executor.execute(
        RemediationExecutionRequest(
            action_id="prepare_secret_rotation_request",
            payload={"secret_name": "OPENAI_API_KEY", "reason": "rotation drill"},
            approval=ExecutionApproval(approved=True, approver="secops"),
            mode=PolicyMode.APPROVAL_REQUIRED,
        )
    )
    executed = executor.execute(
        RemediationExecutionRequest(
            action_id="notify_operator",
            payload={"message": "rotation request prepared", "channel": "secops"},
            mode=PolicyMode.SAFE_AUTO,
        )
    )

    assert prepared.status == "prepared"
    assert prepared.rollback.rollback_possible is True
    assert prepared.rollback.rollback_action == "cancel_secret_rotation_request"

    assert executed.status == "executed"
    assert executed.rollback.rollback_possible is False


def test_malformed_input_rejected(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []
    executor = _build_executor(tmp_path, calls)

    bad_request = RemediationExecutionRequest(action_id="notify_operator")
    bad_request.payload = "not-a-dict"  # type: ignore[assignment]
    result = executor.execute(bad_request)

    assert result.status == "rejected"
    assert "Malformed payload" in result.reason
