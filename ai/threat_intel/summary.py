"""Threat summary aggregator.

Reads the latest JSON report from each agent/scan report directory and
compiles a single consolidated summary. Writes atomically to
~/security/threat-summary/threat-YYYY-MM-DD.json.

Report directories (all under ~/security/):
  audit-reports/   — security audit (agents.security_audit)
  perf-reports/    — performance tuning (agents.performance_tuning)
  storage-reports/ — knowledge storage (agents.knowledge_storage)
  code-reports/    — code quality (agents.code_quality_agent)
  cve-reports/     — CVE scan (threat_intel.cve_scanner)

Usage:
    from ai.threat_intel.summary import build_summary
    report = build_summary()

CLI:
    python -m ai.threat_intel.summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from ai.config import APP_NAME, SECURITY_DIR, setup_logging

logger = logging.getLogger(APP_NAME)

# ── Constants ─────────────────────────────────────────────────────────────────

THREAT_SUMMARY_DIR = SECURITY_DIR / "threat-summary"

_REPORT_DIRS: dict[str, Path] = {
    "audit": SECURITY_DIR / "audit-reports",
    "perf": SECURITY_DIR / "perf-reports",
    "storage": SECURITY_DIR / "storage-reports",
    "code": SECURITY_DIR / "code-reports",
    "cve": SECURITY_DIR / "cve-reports",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _latest_json(directory: Path) -> dict[str, Any] | None:
    """Return the contents of the most recently modified *.json in directory.

    Returns None if the directory does not exist, is empty, or the newest
    file cannot be parsed.
    """
    if not directory.is_dir():
        return None

    candidates = sorted(
        directory.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None

    try:
        return json.loads(candidates[0].read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read %s: %s", candidates[0], e)
        return None


def _extract_cve_highlights(cve_data: dict[str, Any]) -> dict[str, Any]:
    """Pull the key CVE metrics for the summary."""
    return {
        "packages_scanned": cve_data.get("packages_scanned", 0),
        "total_cves": cve_data.get("total_cves", 0),
        "high_severity": cve_data.get("high_severity", 0),
        "kev_cves": cve_data.get("kev_cves", 0),
    }


def _extract_audit_highlights(audit_data: dict[str, Any]) -> dict[str, Any]:
    """Pull the key audit metrics for the summary."""
    return {
        "status": audit_data.get("status", "unknown"),
        "rag_summary": str(audit_data.get("rag_summary", ""))[:300],
    }


def _extract_perf_highlights(perf_data: dict[str, Any]) -> dict[str, Any]:
    """Pull key performance metrics for the summary."""
    return {
        "status": perf_data.get("status", "unknown"),
        "recommendations": perf_data.get("recommendations", [])[:3],
    }


def _extract_storage_highlights(storage_data: dict[str, Any]) -> dict[str, Any]:
    """Pull key storage metrics for the summary."""
    return {
        "status": storage_data.get("status", "unknown"),
        "recommendations": storage_data.get("recommendations", [])[:3],
    }


def _extract_code_highlights(code_data: dict[str, Any]) -> dict[str, Any]:
    """Pull key code-quality metrics for the summary."""
    return {
        "status": code_data.get("status", "unknown"),
        "ruff_issues": code_data.get("ruff_issues", 0),
        "bandit_issues": code_data.get("bandit_issues", 0),
    }


def _overall_status(sections: dict[str, dict[str, Any]]) -> str:
    """Derive a top-level status from all section statuses.

    Returns "critical" > "issues" > "warnings" > "clean" > "unknown".
    """
    order = {"critical": 4, "issues": 3, "warnings": 2, "clean": 1, "unknown": 0}
    worst = "unknown"
    for section in sections.values():
        s = str(section.get("status", "unknown")).lower()
        if order.get(s, 0) > order.get(worst, 0):
            worst = s

    # CVE-specific escalation
    cve = sections.get("cve", {})
    if cve.get("kev_cves", 0) > 0:
        if order.get(worst, 0) < order["critical"]:
            worst = "critical"
    elif cve.get("high_severity", 0) > 0:
        if order.get(worst, 0) < order["issues"]:
            worst = "issues"

    return worst


def _calculate_risk_score(sections: dict[str, dict[str, Any]]) -> str:
    """Calculate overall risk score: low, medium, high, critical."""
    score = 0

    # Check CVE severity
    cve = sections.get("cve", {})
    score += cve.get("kev_cves", 0) * 3
    score += cve.get("high_severity", 0) * 2
    score += cve.get("medium_severity", 0) * 1

    # Check audit issues
    audit = sections.get("audit", {})
    score += audit.get("critical_issues", 0) * 3
    score += audit.get("high_issues", 0) * 2
    score += audit.get("medium_issues", 0) * 1

    # Check storage issues
    storage = sections.get("storage", {})
    if storage.get("db_healthy") is False:
        score += 2
    if storage.get("disk_space_critical", False):
        score += 2

    # Determine risk level
    if score >= 10:
        return "critical"
    elif score >= 5:
        return "high"
    elif score >= 2:
        return "medium"
    return "low"


def _extract_correlation_links(sections: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Extract correlation links between findings."""
    links = []

    # Link CVEs to related findings
    cve = sections.get("cve", {})
    for cve_id in cve.get("top_cves", [])[:3]:
        links.append(
            {
                "type": "cve_to_audit",
                "source": f"cve:{cve_id}",
                "target": "audit:security_checks",
                "relationship": "may_exploit",
            }
        )

    # Link storage to perf
    storage = sections.get("storage", {})
    if not storage.get("db_healthy", True):
        links.append(
            {
                "type": "storage_to_perf",
                "source": "storage:vector_db",
                "target": "perf:query_latency",
                "relationship": "degraded",
            }
        )

    return links


def _extract_recommended_actions(sections: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Extract recommended next actions from all sections."""
    actions = []

    # CVE recommendations
    cve = sections.get("cve", {})
    if cve.get("kev_cves", 0) > 0:
        actions.append(
            {
                "priority": "critical",
                "action": "Review KEV CVEs",
                "tool": "security.cve_check",
                "finding": f"{cve.get('kev_cves', 0)} KEV CVEs found",
            }
        )
    if cve.get("high_severity", 0) > 0:
        actions.append(
            {
                "priority": "high",
                "action": "Apply high-severity patches",
                "tool": "system.fedora_updates",
                "finding": f"{cve.get('high_severity', 0)} high-severity CVEs",
            }
        )

    # Audit recommendations
    audit = sections.get("audit", {})
    if audit.get("critical_issues", 0) > 0:
        actions.append(
            {
                "priority": "critical",
                "action": "Run security audit",
                "tool": "agents.security_audit",
                "finding": f"{audit.get('critical_issues', 0)} critical issues",
            }
        )

    # Storage recommendations
    storage = sections.get("storage", {})
    if not storage.get("db_healthy", True):
        actions.append(
            {
                "priority": "high",
                "action": "Check vector DB health",
                "tool": "agents.knowledge_storage",
                "finding": "Database unhealthy",
            }
        )

    return actions


# ── Orchestration ─────────────────────────────────────────────────────────────


def build_summary() -> dict[str, Any]:
    """Read latest reports from all dirs and compile a threat summary.

    Returns:
        Dict with top-level keys: generated_at, date, overall_status,
        risk_score, correlation_links, recommended_actions, and one
        sub-dict per report source. Missing dirs are recorded
        in ``missing_sources`` rather than raising.
    """
    now = datetime.now(tz=UTC)
    sections: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    raw: dict[str, Any] = {}
    for key, directory in _REPORT_DIRS.items():
        data = _latest_json(directory)
        if data is None:
            missing.append(key)
        else:
            raw[key] = data

    if "audit" in raw:
        sections["audit"] = _extract_audit_highlights(raw["audit"])
    if "perf" in raw:
        sections["perf"] = _extract_perf_highlights(raw["perf"])
    if "storage" in raw:
        sections["storage"] = _extract_storage_highlights(raw["storage"])
    if "code" in raw:
        sections["code"] = _extract_code_highlights(raw["code"])
    if "cve" in raw:
        sections["cve"] = _extract_cve_highlights(raw["cve"])

    overall = _overall_status(sections)
    risk_score = _calculate_risk_score(sections)
    correlation_links = _extract_correlation_links(sections)
    recommended_actions = _extract_recommended_actions(sections)

    summary: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "date": date.today().isoformat(),
        "overall_status": overall,
        "risk_score": risk_score,
        "correlation_links": correlation_links,
        "recommended_actions": recommended_actions,
        "missing_sources": missing,
        **sections,
    }

    _write_summary(summary, now)
    return summary


def _write_summary(summary: dict[str, Any], now: datetime) -> Path:
    """Atomically write the summary JSON to ~/security/threat-summary/."""
    THREAT_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"threat-{now.strftime('%Y-%m-%d')}.json"
    out_path = THREAT_SUMMARY_DIR / filename

    fd, tmp_name = tempfile.mkstemp(dir=THREAT_SUMMARY_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(summary, f, indent=2)
        os.rename(tmp_name, out_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    logger.info("Threat summary written to %s", out_path)
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for threat summary aggregation."""
    parser = argparse.ArgumentParser(
        description="Aggregate threat summary from all report directories"
    )
    parser.parse_args()

    setup_logging()
    summary = build_summary()
    print(json.dumps(summary, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
