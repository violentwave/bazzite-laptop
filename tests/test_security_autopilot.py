"""P119 tests for Security Autopilot core."""

from __future__ import annotations

import json

import pytest

from ai.security_autopilot.audit import AuditLedger, EvidenceManager
from ai.security_autopilot.classifier import FindingClassifier
from ai.security_autopilot.models import (
    AuditEvent,
    IncidentStatus,
    RemediationAction,
    SecurityFinding,
    SecurityIncident,
    Severity,
    next_id,
)
from ai.security_autopilot.planner import RemediationPlanner
from ai.security_autopilot.sensors import BazziteSensorAdapter, SensorSnapshot


def test_remediation_action_rejects_destructive_flag() -> None:
    with pytest.raises(ValueError, match="destructive remediation"):
        RemediationAction(
            action_id=next_id("action"),
            title="Delete compromised artifact",
            description="Would remove file from disk",
            destructive=True,
        )


def test_sensor_adapter_collects_and_handles_errors() -> None:
    def _fetcher(tool: str, _params: dict) -> dict:
        if tool == "security.status":
            return {"status": "ok"}
        raise RuntimeError("tool unavailable")

    adapter = BazziteSensorAdapter(fetcher=_fetcher)
    good = adapter.collect("security.status")
    bad = adapter.collect("logs.anomalies")

    assert good.status == "ok"
    assert good.payload["status"] == "ok"
    assert bad.status == "error"
    assert "unavailable" in bad.error


def test_classifier_creates_findings_and_groups_incidents() -> None:
    classifier = FindingClassifier()
    snapshots = [
        SensorSnapshot(
            sensor="security.alert_summary",
            status="ok",
            payload={"critical": 1, "high": 2},
        ),
        SensorSnapshot(
            sensor="logs.anomalies",
            status="ok",
            payload={
                "anomalies": [
                    {
                        "category": "threat",
                        "severity": "critical",
                        "message": "malware indicator observed",
                    }
                ]
            },
        ),
    ]

    findings = classifier.classify_snapshots(snapshots)
    incidents = classifier.group_incidents(findings)

    assert len(findings) >= 3
    assert any(f.category == "threat" for f in findings)
    assert incidents
    assert any(i.severity == Severity.CRITICAL for i in incidents)


def test_evidence_manager_redacts_sensitive_fields() -> None:
    manager = EvidenceManager()
    bundle = manager.create_bundle(
        source="security.status",
        raw_items={
            "raw": "api_key=SECRET-12345 user=alice@example.com",
            "nested": {"token": "token: abcdefgh"},
        },
    )

    serialized = json.dumps([item.value for item in bundle.items])
    assert bundle.redaction_count >= 2
    assert "SECRET-12345" not in serialized
    assert "alice@example.com" not in serialized
    assert "[REDACTED]" in serialized


def test_planner_generates_plan_only_non_destructive_actions() -> None:
    planner = RemediationPlanner()
    incident = SecurityIncident(
        incident_id=next_id("incident"),
        title="Incident: vulnerability",
        severity=Severity.HIGH,
        status=IncidentStatus.TRIAGE,
        findings=[
            SecurityFinding(
                finding_id=next_id("finding"),
                title="Vulnerability identified",
                description="high severity CVE found",
                severity=Severity.HIGH,
                category="vulnerability",
                source="security.cve_check",
            )
        ],
        summary="single vulnerable package",
    )

    plan = planner.build_plan(incident)
    decision = planner.build_decision(incident, plan)

    assert plan.execution_mode == "plan-only"
    assert plan.actions
    assert all(not action.destructive for action in plan.actions)
    assert decision.outcome.value == "manual-review"


def test_audit_ledger_appends_hash_chained_records(tmp_path) -> None:
    ledger = AuditLedger(path=tmp_path / "audit.jsonl")

    e1 = AuditEvent(
        event_id=next_id("event"),
        event_type="incident.created",
        actor="security_autopilot",
        payload={"incident_id": "i-1"},
    )
    e2 = AuditEvent(
        event_id=next_id("event"),
        event_type="plan.generated",
        actor="security_autopilot",
        payload={"incident_id": "i-1", "plan_id": "p-1"},
    )

    stored_1 = ledger.append_event(e1)
    stored_2 = ledger.append_event(e2)

    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert stored_1.event_hash
    assert stored_2.event_hash
    assert stored_2.prev_hash == stored_1.event_hash
