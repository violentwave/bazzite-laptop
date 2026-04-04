"""Security alert evaluation for proactive threat detection.

Evaluates CVE results, scan freshness, and release alerts to generate
actionable security alerts with deduplication.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ai.config import SECURITY_DIR

logger = logging.getLogger("bazzite-ai.security_alerts")

ALERTS_FILE = SECURITY_DIR / "alerts.json"
DEDUP_FILE = SECURITY_DIR / ".alert-dedup.json"


class SecurityAlertEvaluator:
    def __init__(self, security_dir: Path | None = None) -> None:
        self.security_dir = security_dir or SECURITY_DIR
        self.dedup_state = self._load_dedup_state()

    def _load_dedup_state(self) -> dict[str, Any]:
        try:
            if DEDUP_FILE.exists():
                with open(DEDUP_FILE) as f:
                    return json.load(f)
        except Exception as e:
            logger.debug("Failed to load dedup state: %s", e)
        return {}

    def _save_dedup_state(self) -> None:
        try:
            tmp = DEDUP_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self.dedup_state, f)
            tmp.replace(DEDUP_FILE)
        except Exception as e:
            logger.error("Failed to save dedup state: %s", e)

    def evaluate(self) -> dict[str, Any]:
        cve_alerts = self._check_cve_results()
        stale_scans = self._check_scan_freshness()
        release_alerts = self._check_release_alerts()

        all_alerts = cve_alerts + release_alerts
        filtered_alerts = self._deduplicate(all_alerts)

        critical = sum(1 for a in filtered_alerts if a.get("severity") == "critical")
        high = sum(1 for a in filtered_alerts if a.get("severity") == "high")
        medium = sum(1 for a in filtered_alerts if a.get("severity") == "medium")

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "critical": critical,
            "high": high,
            "medium": medium,
            "alerts": filtered_alerts,
            "stale_scans": stale_scans,
        }

    def _check_cve_results(self) -> list[dict[str, Any]]:
        alerts = []
        cve_file = self.security_dir / "cve-scan-results.json"
        if not cve_file.exists():
            return alerts

        try:
            with open(cve_file) as f:
                data = json.load(f)
            vulns = data.get("vulnerabilities", [])
            for v in vulns:
                cvss = v.get("cvss_score", 0.0)
                if cvss >= 9.0:
                    severity = "critical"
                elif cvss >= 7.0:
                    severity = "high"
                elif cvss >= 4.0:
                    severity = "medium"
                else:
                    severity = "low"

                alerts.append(
                    {
                        "cve_id": v.get("id", "UNKNOWN"),
                        "package": v.get("package", "unknown"),
                        "severity": severity,
                        "description": v.get("summary", "")[:200],
                        "recommended_action": "Update package to latest version",
                        "first_seen": v.get("published", datetime.now(UTC).isoformat()),
                        "source": "cve-scanner",
                    }
                )
        except Exception as e:
            logger.debug("Failed to check CVE results: %s", e)

        return alerts

    def _check_scan_freshness(self) -> list[dict[str, Any]]:
        stale = []
        now = datetime.now(UTC)

        scan_dir = Path("/var/log/clamav-scans")
        if scan_dir.exists():
            try:
                logs = sorted(scan_dir.glob("scan-*.log"), reverse=True)
                if logs:
                    latest = logs[0]
                    mtime = datetime.fromtimestamp(latest.stat().st_mtime, UTC)
                    age_hours = (now - mtime).total_seconds() / 3600
                    if age_hours > 25:
                        stale.append(
                            {
                                "scan_name": "clamav",
                                "last_run": mtime.isoformat(),
                                "expected_interval_hours": 24,
                            }
                        )
            except Exception:  # noqa: S110
                pass

        health_dir = Path("/var/log/system-health")
        if health_dir.exists():
            try:
                logs = sorted(health_dir.glob("health-*.log"), reverse=True)
                if logs:
                    latest = logs[0]
                    mtime = datetime.fromtimestamp(latest.stat().st_mtime, UTC)
                    age_hours = (now - mtime).total_seconds() / 3600
                    if age_hours > 25:
                        stale.append(
                            {
                                "scan_name": "system-health",
                                "last_run": mtime.isoformat(),
                                "expected_interval_hours": 24,
                            }
                        )
            except Exception:  # noqa: S110
                pass

        release_file = self.security_dir / "release-watch.json"
        if release_file.exists():
            try:
                mtime = datetime.fromtimestamp(release_file.stat().st_mtime, UTC)
                age_hours = (now - mtime).total_seconds() / 3600
                if age_hours > 25:
                    stale.append(
                        {
                            "scan_name": "release-watch",
                            "last_run": mtime.isoformat(),
                            "expected_interval_hours": 24,
                        }
                    )
            except Exception:  # noqa: S110
                pass

        return stale

    def _check_release_alerts(self) -> list[dict[str, Any]]:
        alerts = []
        release_file = self.security_dir / "release-watch.json"
        if not release_file.exists():
            return alerts

        try:
            with open(release_file) as f:
                data = json.load(f)
            releases = data.get("releases", [])
            for r in releases:
                desc = r.get("description", "").lower()
                if "security" in desc or "critical" in desc or "cve" in desc:
                    alerts.append(
                        {
                            "cve_id": r.get("tag_name", "UNKNOWN"),
                            "package": r.get("repo", "unknown"),
                            "severity": "high",
                            "description": r.get("description", "")[:200],
                            "recommended_action": "Review release for security implications",
                            "first_seen": r.get("published_at", datetime.now(UTC).isoformat()),
                            "source": "release-watch",
                        }
                    )
        except Exception as e:
            logger.debug("Failed to check release alerts: %s", e)

        return alerts

    def _deduplicate(self, alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not alerts:
            return []

        now = datetime.now(UTC)
        cutoff = now - timedelta(days=7)
        filtered = []

        for alert in alerts:
            key = f"{alert.get('cve_id', '')}:{alert.get('package', '')}"
            if key in self.dedup_state:
                last_notified = datetime.fromisoformat(self.dedup_state[key])
                if last_notified > cutoff:
                    continue

            filtered.append(alert)
            self.dedup_state[key] = now.isoformat()

        self._save_dedup_state()
        return filtered

    def _save_results(self, results: dict[str, Any]) -> None:
        try:
            tmp = ALERTS_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(results, f, indent=2)
            tmp.replace(ALERTS_FILE)
        except Exception as e:
            logger.error("Failed to save alerts: %s", e)


def run_alert_evaluation() -> dict[str, Any]:
    evaluator = SecurityAlertEvaluator()
    results = evaluator.evaluate()
    evaluator._save_results(results)
    return results
