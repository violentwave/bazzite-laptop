"""Classification and incident grouping for Security Autopilot."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ai.security_autopilot.models import (
    IncidentStatus,
    SecurityFinding,
    SecurityIncident,
    Severity,
    next_id,
)
from ai.security_autopilot.sensors import SensorSnapshot


def _severity_from_text(value: str) -> Severity:
    lowered = value.lower().strip()
    if lowered in {"critical", "crit", "sev0"}:
        return Severity.CRITICAL
    if lowered in {"high", "sev1", "issues"}:
        return Severity.HIGH
    if lowered in {"medium", "med", "warning", "warn"}:
        return Severity.MEDIUM
    if lowered in {"low", "info", "ok", "clean"}:
        return Severity.LOW
    return Severity.INFO


def _max_severity(levels: list[Severity]) -> Severity:
    order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    return max(levels, key=order.index)


class FindingClassifier:
    """Turn sensor snapshots into normalized findings and incidents."""

    def classify_snapshots(self, snapshots: list[SensorSnapshot]) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []

        for snapshot in snapshots:
            if snapshot.status != "ok":
                findings.append(
                    SecurityFinding(
                        finding_id=next_id("finding"),
                        title=f"Sensor unavailable: {snapshot.sensor}",
                        description=snapshot.error or "sensor read failed",
                        severity=Severity.MEDIUM,
                        category="sensor",
                        source=snapshot.sensor,
                        confidence=1.0,
                        metadata={"status": snapshot.status},
                    )
                )
                continue

            findings.extend(self._extract_findings(snapshot))

        return findings

    def _extract_findings(self, snapshot: SensorSnapshot) -> list[SecurityFinding]:
        payload = snapshot.payload
        findings: list[SecurityFinding] = []

        if snapshot.sensor == "security.alert_summary":
            critical = int(payload.get("critical", 0) or 0)
            high = int(payload.get("high", 0) or 0)
            if critical > 0:
                findings.append(
                    self._build(
                        snapshot,
                        title="Critical security alerts detected",
                        description=f"{critical} critical alerts in summary",
                        severity=Severity.CRITICAL,
                        category="alerts",
                    )
                )
            if high > 0:
                findings.append(
                    self._build(
                        snapshot,
                        title="High-severity security alerts detected",
                        description=f"{high} high-severity alerts in summary",
                        severity=Severity.HIGH,
                        category="alerts",
                    )
                )

        if snapshot.sensor == "logs.anomalies":
            for anomaly in payload.get("anomalies", []):
                findings.append(
                    self._build(
                        snapshot,
                        title=f"Anomaly: {anomaly.get('category', 'unknown')}",
                        description=anomaly.get("message", "anomaly detected"),
                        severity=_severity_from_text(str(anomaly.get("severity", "medium"))),
                        category=str(anomaly.get("category", "anomaly")),
                        metadata={"anomaly": anomaly},
                    )
                )

        if snapshot.sensor == "security.cve_check":
            total = int(payload.get("total_cves", 0) or 0)
            high = int(payload.get("high_severity", 0) or 0)
            kev = int(payload.get("kev_cves", 0) or 0)
            if total > 0:
                sev = (
                    Severity.CRITICAL if kev > 0 else Severity.HIGH if high > 0 else Severity.MEDIUM
                )
                findings.append(
                    self._build(
                        snapshot,
                        title="Vulnerabilities identified",
                        description=(
                            f"total={total}, high={high}, kev={kev} from dependency CVE scan"
                        ),
                        severity=sev,
                        category="vulnerability",
                    )
                )

        if snapshot.sensor == "agents.timer_health":
            overall = str(payload.get("overall", payload.get("status", ""))).lower()
            stale = payload.get("stale_count", 0)
            if overall in {"warning", "critical"} or stale:
                findings.append(
                    self._build(
                        snapshot,
                        title="Security timers unhealthy",
                        description=f"overall={overall or 'unknown'}, stale_count={stale}",
                        severity=Severity.HIGH if overall == "critical" else Severity.MEDIUM,
                        category="operations",
                    )
                )

        if snapshot.sensor == "system.service_status":
            failed = int(payload.get("failed_services", 0) or 0)
            if failed > 0:
                findings.append(
                    self._build(
                        snapshot,
                        title="Security services degraded",
                        description=f"{failed} monitored services are not healthy",
                        severity=Severity.HIGH,
                        category="operations",
                    )
                )

        if not findings:
            status = str(payload.get("status", ""))
            if status:
                sev = _severity_from_text(status)
                if sev in {Severity.HIGH, Severity.CRITICAL, Severity.MEDIUM}:
                    findings.append(
                        self._build(
                            snapshot,
                            title=f"Status requires review: {snapshot.sensor}",
                            description=f"reported status '{status}'",
                            severity=sev,
                            category="status",
                        )
                    )

        return findings

    def _build(
        self,
        snapshot: SensorSnapshot,
        title: str,
        description: str,
        severity: Severity,
        category: str,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityFinding:
        merged = {"sensor": snapshot.sensor}
        if metadata:
            merged.update(metadata)
        return SecurityFinding(
            finding_id=next_id("finding"),
            title=title,
            description=description,
            severity=severity,
            category=category,
            source=snapshot.sensor,
            confidence=0.9,
            metadata=merged,
        )

    def group_incidents(self, findings: list[SecurityFinding]) -> list[SecurityIncident]:
        """Group findings into incidents by category."""

        grouped: dict[str, list[SecurityFinding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.category].append(finding)

        incidents: list[SecurityIncident] = []
        for category, grouped_findings in grouped.items():
            if not grouped_findings:
                continue
            sev = _max_severity([f.severity for f in grouped_findings])
            incidents.append(
                SecurityIncident(
                    incident_id=next_id("incident"),
                    title=f"Security incident: {category}",
                    severity=sev,
                    status=IncidentStatus.TRIAGE,
                    findings=grouped_findings,
                    summary=f"{len(grouped_findings)} finding(s) in category '{category}'",
                    tags=[category, sev.value],
                )
            )

        return incidents
