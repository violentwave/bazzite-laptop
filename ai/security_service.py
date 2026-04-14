"""Security Ops Center service for aggregating security and ops signals.

This service provides a unified view of security alerts, scan findings,
CVE data, provider health issues, and timer/workflow anomalies.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Paths
SECURITY_DIR = Path.home() / "security"
STATUS_FILE = SECURITY_DIR / ".status"
ALERTS_FILE = SECURITY_DIR / "alerts.json"
LLM_STATUS_FILE = SECURITY_DIR / "llm-status.json"

# Logs
HEALTH_LOG_DIR = Path("/var/log/system-health")
CLAMAV_LOG_DIR = Path("/var/log/clamav-scans")


@dataclass
class SecurityAlert:
    """Security alert data structure."""

    id: str
    severity: str  # critical, high, medium, low, info
    category: str  # scan, cve, provider, timer, system
    title: str
    description: str
    timestamp: str
    source: str
    acknowledged: bool = False
    related_action: str | None = None


@dataclass
class ScanFinding:
    """Scan finding data structure."""

    id: str
    scan_type: str
    status: str  # clean, infected, error, pending
    threats_found: int
    files_scanned: int
    timestamp: str
    details: str | None = None


@dataclass
class CVERisk:
    """CVE risk data structure."""

    id: str
    package: str
    severity: str
    cve_id: str
    description: str
    fixed_version: str | None
    timestamp: str


@dataclass
class ProviderHealthIssue:
    """Provider health issue data structure."""

    provider: str
    issue_type: str  # auth_failed, timeout, error, degraded
    description: str
    timestamp: str
    consecutive_failures: int
    auth_broken: bool = False


@dataclass
class TimerAnomaly:
    """Timer/workflow anomaly data structure."""

    timer_name: str
    expected_interval: str
    last_run: str
    status: str  # healthy, stale, failed
    severity: str


@dataclass
class SecurityOverview:
    """Complete security overview."""

    # Summary counts
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # System status
    system_status: str = "unknown"  # secure, warning, critical
    last_scan_time: str | None = None
    scan_status: str = "unknown"

    # Provider status
    healthy_providers: int = 0
    degraded_providers: int = 0
    failed_providers: int = 0

    # Recent activity
    recent_alerts: list[SecurityAlert] = field(default_factory=list)
    recent_findings: list[ScanFinding] = field(default_factory=list)
    cve_risks: list[CVERisk] = field(default_factory=list)
    provider_issues: list[ProviderHealthIssue] = field(default_factory=list)
    timer_anomalies: list[TimerAnomaly] = field(default_factory=list)

    # Metadata
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SecurityService:
    """Service for aggregating security and ops data."""

    def __init__(self) -> None:
        """Initialize the security service."""
        self._cache: dict[str, Any] = {}
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(seconds=30)

    def _read_status_file(self) -> dict:
        """Read the security status file."""
        try:
            if STATUS_FILE.exists():
                return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read status file: {e}")
        return {}

    def _read_alerts_file(self) -> list[dict]:
        """Read the alerts file."""
        try:
            if ALERTS_FILE.exists():
                data = json.loads(ALERTS_FILE.read_text())
                return data.get("alerts", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read alerts file: {e}")
        return []

    def _read_llm_status(self) -> dict:
        """Read LLM provider status."""
        try:
            if LLM_STATUS_FILE.exists():
                return json.loads(LLM_STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read LLM status: {e}")
        return {}

    def _read_health_logs(self) -> list[str]:
        """Read recent health log entries."""
        logs = []
        try:
            if HEALTH_LOG_DIR.exists():
                # Get latest log file
                log_files = sorted(
                    HEALTH_LOG_DIR.glob("health-*.log"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if log_files:
                    lines = log_files[0].read_text().splitlines()
                    logs = lines[-20:]  # Last 20 lines
        except OSError as e:
            logger.warning(f"Failed to read health logs: {e}")
        return logs

    def _read_clamav_logs(self) -> list[str]:
        """Read recent ClamAV log entries."""
        logs = []
        try:
            if CLAMAV_LOG_DIR.exists():
                log_files = sorted(
                    CLAMAV_LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True
                )
                if log_files:
                    lines = log_files[0].read_text().splitlines()
                    logs = lines[-20:]
        except OSError as e:
            logger.warning(f"Failed to read ClamAV logs: {e}")
        return logs

    def _parse_alerts(self, raw_alerts: list[dict]) -> list[SecurityAlert]:
        """Parse raw alert data into SecurityAlert objects."""
        alerts = []
        for raw in raw_alerts:
            alert = SecurityAlert(
                id=raw.get("id", "unknown"),
                severity=raw.get("severity", "info"),
                category=raw.get("category", "system"),
                title=raw.get("title", "Unknown Alert"),
                description=raw.get("description", ""),
                timestamp=raw.get("timestamp", datetime.now().isoformat()),
                source=raw.get("source", "system"),
                acknowledged=raw.get("acknowledged", False),
                related_action=raw.get("related_action"),
            )
            alerts.append(alert)
        return alerts

    def _get_provider_issues(self, llm_status: dict) -> list[ProviderHealthIssue]:
        """Extract provider health issues from LLM status."""
        issues = []
        providers = llm_status.get("providers", {})

        for provider_name, info in providers.items():
            if not isinstance(info, dict):
                continue

            health_score = info.get("score", 100)
            auth_broken = info.get("auth_broken", False)
            failures = info.get("consecutive_failures", 0)

            if auth_broken or failures >= 3 or health_score < 50:
                issue = ProviderHealthIssue(
                    provider=provider_name,
                    issue_type="auth_failed" if auth_broken else "degraded",
                    description=f"Health score: {health_score}, failures: {failures}",
                    timestamp=llm_status.get("generated_at", datetime.now().isoformat()),
                    consecutive_failures=failures,
                    auth_broken=auth_broken,
                )
                issues.append(issue)

        return issues

    def _get_scan_findings(self, status: dict) -> list[ScanFinding]:
        """Extract scan findings from status."""
        findings = []

        # Current scan status
        scan_type = status.get("scan_type", "unknown")
        scan_result = status.get("result", "unknown")
        last_scan = status.get("last_scan_time")

        if last_scan:
            finding = ScanFinding(
                id=f"scan-{last_scan}",
                scan_type=scan_type,
                status="clean" if scan_result == "clean" else scan_result,
                threats_found=1 if scan_result == "infected" else 0,
                files_scanned=0,  # Not tracked in current status
                timestamp=last_scan,
                details=None,
            )
            findings.append(finding)

        return findings

    def _calculate_overview(self) -> SecurityOverview:
        """Calculate complete security overview."""
        status = self._read_status_file()
        raw_alerts = self._read_alerts_file()
        llm_status = self._read_llm_status()

        alerts = self._parse_alerts(raw_alerts)
        provider_issues = self._get_provider_issues(llm_status)
        scan_findings = self._get_scan_findings(status)

        # Count severity levels
        critical_count = sum(1 for a in alerts if a.severity == "critical")
        high_count = sum(1 for a in alerts if a.severity == "high")
        medium_count = sum(1 for a in alerts if a.severity == "medium")
        low_count = sum(1 for a in alerts if a.severity == "low")

        # Determine system status
        if critical_count > 0 or any(p.auth_broken for p in provider_issues):
            system_status = "critical"
        elif high_count > 0 or len(provider_issues) > 0:
            system_status = "warning"
        else:
            system_status = "secure"

        # Provider counts
        providers = llm_status.get("providers", {})
        healthy = sum(
            1 for p in providers.values() if isinstance(p, dict) and p.get("score", 0) >= 80
        )
        degraded = sum(
            1 for p in providers.values() if isinstance(p, dict) and 50 <= p.get("score", 0) < 80
        )
        failed = sum(
            1 for p in providers.values() if isinstance(p, dict) and p.get("score", 100) < 50
        )

        # Get recent alerts (last 10)
        recent_alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:10]

        return SecurityOverview(
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            system_status=system_status,
            last_scan_time=status.get("last_scan_time"),
            scan_status=status.get("result", "unknown"),
            healthy_providers=healthy,
            degraded_providers=degraded,
            failed_providers=failed,
            recent_alerts=recent_alerts,
            recent_findings=scan_findings,
            cve_risks=[],  # Populated by CVE scanner
            provider_issues=provider_issues,
            timer_anomalies=[],  # Populated by timer health
        )

    def get_overview(self) -> SecurityOverview:
        """Get security overview (with caching)."""
        now = datetime.now()
        if self._cache_time and (now - self._cache_time) < self._cache_ttl:
            return self._cache.get("overview", SecurityOverview())

        overview = self._calculate_overview()
        self._cache["overview"] = overview
        self._cache_time = now
        return overview

    def get_alerts(self, severity: str | None = None, limit: int = 50) -> list[SecurityAlert]:
        """Get security alerts with optional filtering."""
        raw_alerts = self._read_alerts_file()
        alerts = self._parse_alerts(raw_alerts)

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_findings(self, limit: int = 20) -> list[ScanFinding]:
        """Get recent scan findings."""
        status = self._read_status_file()
        return self._get_scan_findings(status)[:limit]

    def get_provider_health(self) -> list[ProviderHealthIssue]:
        """Get provider health issues."""
        llm_status = self._read_llm_status()
        return self._get_provider_issues(llm_status)

    def get_system_health(self) -> dict:
        """Get system health snapshot."""
        status = self._read_status_file()
        return {
            "state": status.get("state", "unknown"),
            "health_status": status.get("health_status", "unknown"),
            "health_issues": status.get("health_issues", []),
            "last_scan": status.get("last_scan_time"),
            "scan_result": status.get("result"),
        }

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a security alert."""
        try:
            if not ALERTS_FILE.exists():
                return False

            data = json.loads(ALERTS_FILE.read_text())
            alerts = data.get("alerts", [])

            for alert in alerts:
                if alert.get("id") == alert_id:
                    alert["acknowledged"] = True
                    alert["acknowledged_at"] = datetime.now().isoformat()
                    break

            data["alerts"] = alerts
            ALERTS_FILE.write_text(json.dumps(data, indent=2))
            self._cache.clear()  # Invalidate cache
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False


# Singleton instance
_security_service: SecurityService | None = None


def get_security_service() -> SecurityService:
    """Get the singleton security service instance."""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service


def get_overview() -> dict:
    """Get security overview as dict (for MCP)."""
    service = get_security_service()
    overview = service.get_overview()

    return {
        "critical_count": overview.critical_count,
        "high_count": overview.high_count,
        "medium_count": overview.medium_count,
        "low_count": overview.low_count,
        "system_status": overview.system_status,
        "last_scan_time": overview.last_scan_time,
        "scan_status": overview.scan_status,
        "healthy_providers": overview.healthy_providers,
        "degraded_providers": overview.degraded_providers,
        "failed_providers": overview.failed_providers,
        "generated_at": overview.generated_at,
    }


def get_alerts(severity: str | None = None, limit: int = 50) -> list[dict]:
    """Get alerts as dict list (for MCP)."""
    service = get_security_service()
    alerts = service.get_alerts(severity=severity, limit=limit)

    return [
        {
            "id": a.id,
            "severity": a.severity,
            "category": a.category,
            "title": a.title,
            "description": a.description,
            "timestamp": a.timestamp,
            "source": a.source,
            "acknowledged": a.acknowledged,
            "related_action": a.related_action,
        }
        for a in alerts
    ]


def get_findings(limit: int = 20) -> list[dict]:
    """Get scan findings as dict list (for MCP)."""
    service = get_security_service()
    findings = service.get_findings(limit=limit)

    return [
        {
            "id": f.id,
            "scan_type": f.scan_type,
            "status": f.status,
            "threats_found": f.threats_found,
            "files_scanned": f.files_scanned,
            "timestamp": f.timestamp,
            "details": f.details,
        }
        for f in findings
    ]


def get_provider_health_issues() -> list[dict]:
    """Get provider health issues as dict list (for MCP)."""
    service = get_security_service()
    issues = service.get_provider_health()

    return [
        {
            "provider": i.provider,
            "issue_type": i.issue_type,
            "description": i.description,
            "timestamp": i.timestamp,
            "consecutive_failures": i.consecutive_failures,
            "auth_broken": i.auth_broken,
        }
        for i in issues
    ]


def get_system_health() -> dict:
    """Get system health (for MCP)."""
    service = get_security_service()
    return service.get_system_health()


def acknowledge_alert(alert_id: str) -> dict:
    """Acknowledge an alert (for MCP)."""
    service = get_security_service()
    success = service.acknowledge_alert(alert_id)

    return {
        "success": success,
        "alert_id": alert_id,
        "timestamp": datetime.now().isoformat(),
    }
