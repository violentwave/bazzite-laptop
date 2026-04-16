"""P121 tests for Security Autopilot UI tool aggregation."""

from __future__ import annotations

import json

from ai.security_autopilot import ui_service


def _mock_overview() -> dict:
    return {
        "system_status": "warning",
        "scan_status": "clean",
        "last_scan_time": "2026-04-16T21:00:00+00:00",
    }


def _mock_alerts(*_args, **_kwargs) -> list[dict]:
    return [
        {
            "id": "a-1",
            "title": "Critical malware found",
            "description": "Detected in quarantine folder",
            "severity": "critical",
            "category": "threat",
            "source": "security.alert_summary",
            "timestamp": "2026-04-16T20:59:00+00:00",
            "acknowledged": False,
        }
    ]


def _mock_findings(*_args, **_kwargs) -> list[dict]:
    return [
        {
            "id": "scan-1",
            "scan_type": "quick",
            "status": "infected",
            "threats_found": 2,
            "files_scanned": 120,
            "timestamp": "2026-04-16T20:58:00+00:00",
            "details": "2 suspicious files",
        }
    ]


def _mock_provider_issues() -> list[dict]:
    return [
        {
            "provider": "openai",
            "issue_type": "auth_failed",
            "description": "token invalid",
            "timestamp": "2026-04-16T20:57:00+00:00",
            "consecutive_failures": 4,
            "auth_broken": True,
        }
    ]


def test_autopilot_overview_contains_expected_counts(monkeypatch) -> None:
    monkeypatch.setattr(ui_service, "get_overview", _mock_overview)
    monkeypatch.setattr(ui_service, "get_alerts", _mock_alerts)
    monkeypatch.setattr(ui_service, "get_findings", _mock_findings)
    monkeypatch.setattr(ui_service, "get_provider_health_issues", _mock_provider_issues)

    overview = ui_service.get_autopilot_overview()

    assert overview["system_status"] == "warning"
    assert overview["finding_count"] >= 3
    assert overview["incident_count"] >= 1
    assert overview["remediation_queue_count"] >= 1
    assert overview["severity_counts"]["critical"] >= 1


def test_autopilot_remediation_queue_is_plan_only(monkeypatch) -> None:
    monkeypatch.setattr(ui_service, "get_alerts", _mock_alerts)
    monkeypatch.setattr(ui_service, "get_findings", _mock_findings)
    monkeypatch.setattr(ui_service, "get_provider_health_issues", _mock_provider_issues)

    queue = ui_service.get_autopilot_remediation_queue(limit=5)

    assert queue
    first = queue[0]
    assert first["execution_mode"] == "plan-only"
    assert first["action_count"] >= 1
    assert isinstance(first["requires_approval"], bool)


def test_autopilot_evidence_bundles_are_redacted(monkeypatch) -> None:
    def _alerts_with_secret(*_args, **_kwargs) -> list[dict]:
        return [
            {
                "id": "a-2",
                "title": "Suspicious credential",
                "description": "token=SUPERSECRET",
                "severity": "high",
                "category": "threat",
                "source": "security.alert_summary",
                "timestamp": "2026-04-16T20:56:00+00:00",
                "acknowledged": False,
            }
        ]

    monkeypatch.setattr(ui_service, "get_alerts", _alerts_with_secret)
    monkeypatch.setattr(ui_service, "get_findings", _mock_findings)
    monkeypatch.setattr(ui_service, "get_provider_health_issues", _mock_provider_issues)

    bundles = ui_service.get_autopilot_evidence(limit=3)

    assert bundles
    blob = json.dumps(bundles)
    assert "SUPERSECRET" not in blob
    assert "persisted" in bundles[0]
    assert bundles[0]["persisted"] is False
