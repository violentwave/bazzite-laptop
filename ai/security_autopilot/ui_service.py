"""Read-only Security Autopilot UI aggregation helpers (P121).

This module exposes plan-only, non-destructive view models for the
Unified Control Console security autopilot panel.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.security_autopilot.audit import EvidenceManager
from ai.security_autopilot.models import IncidentStatus, SecurityFinding, SecurityIncident, Severity
from ai.security_autopilot.planner import RemediationPlanner
from ai.security_autopilot.policy import PolicyMode, SecurityAutopilotPolicy, load_policy_config
from ai.security_service import (
    SECURITY_DIR,
    get_alerts,
    get_findings,
    get_overview,
    get_provider_health_issues,
)

_AUDIT_PATH = SECURITY_DIR / "autopilot-audit.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _severity_rank(value: str) -> int:
    order = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "info": 0,
    }
    return order.get(value.lower(), 0)


def _to_severity(value: str) -> Severity:
    lowered = value.lower().strip()
    if lowered == "critical":
        return Severity.CRITICAL
    if lowered == "high":
        return Severity.HIGH
    if lowered == "medium":
        return Severity.MEDIUM
    if lowered == "low":
        return Severity.LOW
    return Severity.INFO


def _normalize_findings(limit: int = 100) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for alert in get_alerts(limit=limit):
        findings.append(
            {
                "finding_id": f"alert-{alert.get('id', 'unknown')}",
                "title": alert.get("title", "Security alert"),
                "description": alert.get("description", ""),
                "severity": alert.get("severity", "medium"),
                "category": alert.get("category", "alerts"),
                "source": alert.get("source", "security.alert_summary"),
                "detected_at": alert.get("timestamp") or _utc_now_iso(),
                "confidence": 0.95,
                "metadata": {"acknowledged": bool(alert.get("acknowledged", False))},
            }
        )

    for finding in get_findings(limit=limit):
        status = str(finding.get("status", "unknown"))
        threats = int(finding.get("threats_found", 0) or 0)
        severity = "low"
        if status == "infected" or threats > 0:
            severity = "critical"
        elif status == "error":
            severity = "medium"

        findings.append(
            {
                "finding_id": f"scan-{finding.get('id', 'unknown')}",
                "title": f"{finding.get('scan_type', 'unknown')} scan result",
                "description": finding.get("details") or f"status={status}, threats={threats}",
                "severity": severity,
                "category": "scan",
                "source": "security.last_scan",
                "detected_at": finding.get("timestamp") or _utc_now_iso(),
                "confidence": 0.85,
                "metadata": {
                    "scan_status": status,
                    "files_scanned": int(finding.get("files_scanned", 0) or 0),
                    "threats_found": threats,
                },
            }
        )

    for issue in get_provider_health_issues():
        auth_broken = bool(issue.get("auth_broken", False))
        findings.append(
            {
                "finding_id": f"provider-{issue.get('provider', 'unknown')}",
                "title": f"Provider issue: {issue.get('provider', 'unknown')}",
                "description": issue.get("description", "Provider health degraded"),
                "severity": "high" if auth_broken else "medium",
                "category": "provider",
                "source": "system.provider_status",
                "detected_at": issue.get("timestamp") or _utc_now_iso(),
                "confidence": 0.8,
                "metadata": {
                    "issue_type": issue.get("issue_type", "degraded"),
                    "consecutive_failures": int(issue.get("consecutive_failures", 0) or 0),
                    "auth_broken": auth_broken,
                },
            }
        )

    findings.sort(key=lambda item: item.get("detected_at", ""), reverse=True)
    return findings[:limit]


def _group_incidents(findings: list[dict[str, Any]]) -> list[SecurityIncident]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        grouped[str(finding.get("category", "uncategorized"))].append(finding)

    incidents: list[SecurityIncident] = []
    for category, grouped_findings in grouped.items():
        if not grouped_findings:
            continue

        max_sev = max(
            (str(item.get("severity", "info")) for item in grouped_findings),
            key=_severity_rank,
        )

        incident_findings = [
            SecurityFinding(
                finding_id=str(item.get("finding_id", "finding-unknown")),
                title=str(item.get("title", "Security finding")),
                description=str(item.get("description", "")),
                severity=_to_severity(str(item.get("severity", "info"))),
                category=category,
                source=str(item.get("source", "unknown")),
                detected_at=str(item.get("detected_at", _utc_now_iso())),
                confidence=float(item.get("confidence", 0.5) or 0.5),
                metadata=item.get("metadata", {}),
            )
            for item in grouped_findings
        ]

        incidents.append(
            SecurityIncident(
                incident_id=f"incident-{category}",
                title=f"Security incident: {category}",
                severity=_to_severity(max_sev),
                status=IncidentStatus.TRIAGE,
                findings=incident_findings,
                summary=f"{len(grouped_findings)} finding(s) in category '{category}'",
                tags=[category, max_sev],
            )
        )

    incidents.sort(
        key=lambda incident: _severity_rank(incident.severity.value),
        reverse=True,
    )
    return incidents


def get_autopilot_findings(limit: int = 50) -> list[dict[str, Any]]:
    """Return normalized autopilot findings for UI display."""

    return _normalize_findings(limit=limit)


def get_autopilot_incidents(limit: int = 25) -> list[dict[str, Any]]:
    """Return grouped incidents derived from current findings."""

    findings = _normalize_findings(limit=200)
    incidents = _group_incidents(findings)
    payload: list[dict[str, Any]] = []

    for incident in incidents[:limit]:
        payload.append(
            {
                "incident_id": incident.incident_id,
                "title": incident.title,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "summary": incident.summary,
                "finding_count": len(incident.findings),
                "tags": incident.tags,
                "created_at": incident.created_at,
                "updated_at": incident.updated_at,
            }
        )
    return payload


def get_autopilot_remediation_queue(limit: int = 25) -> list[dict[str, Any]]:
    """Return plan-only remediation queue for current incidents."""

    incidents = _group_incidents(_normalize_findings(limit=200))
    planner = RemediationPlanner()
    policy = SecurityAutopilotPolicy()
    mode = PolicyMode.RECOMMEND_ONLY
    queue: list[dict[str, Any]] = []

    for incident in incidents[:limit]:
        plan = planner.build_plan(incident)
        decision = planner.build_decision(incident, plan)
        policy_checks = [
            policy.evaluate_remediation_action(action, mode=mode) for action in plan.actions
        ]

        blocked_count = sum(1 for check in policy_checks if check.decision.value == "blocked")
        approval_count = sum(
            1 for check in policy_checks if check.decision.value == "approval_required"
        )
        auto_allowed_count = sum(
            1 for check in policy_checks if check.decision.value == "auto_allowed"
        )

        queue.append(
            {
                "plan_id": plan.plan_id,
                "incident_id": incident.incident_id,
                "incident_title": incident.title,
                "priority": plan.priority.value,
                "execution_mode": plan.execution_mode,
                "summary": plan.summary,
                "action_count": len(plan.actions),
                "requires_approval": approval_count > 0
                or decision.outcome.value == "manual-review",
                "blocked_actions": blocked_count,
                "approval_required_actions": approval_count,
                "auto_allowed_actions": auto_allowed_count,
                "decision": decision.outcome.value,
                "safety_constraints": plan.safety_constraints,
                "generated_at": plan.generated_at,
            }
        )

    queue.sort(key=lambda item: _severity_rank(str(item.get("priority", "info"))), reverse=True)
    return queue


def get_autopilot_policy_status() -> dict[str, Any]:
    """Return active policy mode and mode matrix metadata."""

    config = load_policy_config()
    mode_names = sorted(mode.value for mode in config.mode_rules)

    return {
        "policy_version": config.policy_version,
        "default_mode": config.default_mode.value,
        "blocked_always": sorted(category.value for category in config.blocked_always),
        "destructive_actions": sorted(category.value for category in config.destructive_actions),
        "mode_names": mode_names,
        "allowed_path_prefixes": config.allowed_path_prefixes,
    }


def get_autopilot_audit_events(limit: int = 50, path: Path | None = None) -> list[dict[str, Any]]:
    """Return recent append-only audit events from JSONL ledger."""

    target_path = path or _AUDIT_PATH
    if not target_path.exists():
        return []

    events: list[dict[str, Any]] = []
    with target_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(parsed)

    events.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return events[:limit]


def get_autopilot_evidence(limit: int = 25) -> list[dict[str, Any]]:
    """Return redacted, ephemeral evidence bundles for incident triage."""

    manager = EvidenceManager()
    incidents = _group_incidents(_normalize_findings(limit=200))
    bundles: list[dict[str, Any]] = []

    for incident in incidents[:limit]:
        raw_items = {
            "incident_id": incident.incident_id,
            "incident_title": incident.title,
            "incident_summary": incident.summary,
            "finding_count": len(incident.findings),
            "top_findings": [
                {
                    "finding_id": finding.finding_id,
                    "title": finding.title,
                    "severity": finding.severity.value,
                    "source": finding.source,
                }
                for finding in incident.findings[:3]
            ],
        }
        bundle = manager.create_bundle(source="autopilot.derived", raw_items=raw_items)
        payload = asdict(bundle)
        payload["persisted"] = False
        bundles.append(payload)

    return bundles[:limit]


def get_autopilot_overview() -> dict[str, Any]:
    """Return top-level autopilot summary for dashboard overview."""

    security_overview = get_overview()
    findings = _normalize_findings(limit=200)
    incidents = _group_incidents(findings)
    queue = get_autopilot_remediation_queue(limit=200)
    policy_status = get_autopilot_policy_status()
    audit_count = len(get_autopilot_audit_events(limit=500))

    severity_counts = {
        "critical": sum(1 for item in findings if item.get("severity") == "critical"),
        "high": sum(1 for item in findings if item.get("severity") == "high"),
        "medium": sum(1 for item in findings if item.get("severity") == "medium"),
        "low": sum(1 for item in findings if item.get("severity") == "low"),
        "info": sum(1 for item in findings if item.get("severity") == "info"),
    }

    category_counts: dict[str, int] = {}
    for item in findings:
        category = str(item.get("category", "uncategorized"))
        category_counts[category] = category_counts.get(category, 0) + 1

    top_categories = [
        {"category": category, "count": count}
        for category, count in sorted(
            category_counts.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )[:5]
    ]

    return {
        "generated_at": _utc_now_iso(),
        "system_status": security_overview.get("system_status", "unknown"),
        "scan_status": security_overview.get("scan_status", "unknown"),
        "last_scan_time": security_overview.get("last_scan_time"),
        "default_mode": policy_status["default_mode"],
        "policy_version": policy_status["policy_version"],
        "finding_count": len(findings),
        "incident_count": len(incidents),
        "open_incident_count": len(incidents),
        "remediation_queue_count": len(queue),
        "requires_approval_count": sum(1 for item in queue if item.get("requires_approval")),
        "blocked_action_count": sum(int(item.get("blocked_actions", 0) or 0) for item in queue),
        "audit_event_count": audit_count,
        "severity_counts": severity_counts,
        "top_categories": top_categories,
    }
