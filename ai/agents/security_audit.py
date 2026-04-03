"""Automated security audit workflow for Bazzite.

Chains: ClamAV scan trigger → health snapshot trigger → log ingestion → RAG summary.
Skips any trigger whose log file is newer than 1 hour (cooldown guard).
Writes a structured JSON report to ~/security/audit-reports/.

Usage:
    python -m ai.agents.security_audit
    from ai.agents.security_audit import run_audit
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from ai.config import APP_NAME, SECURITY_DIR

logger = logging.getLogger(APP_NAME)

# Log directories (mirrors ai/log_intel/ingest.py constants)
HEALTH_LOG_DIR = Path("/var/log/system-health")
SCAN_LOG_DIR = Path("/var/log/clamav-scans")

AUDIT_REPORTS_DIR = SECURITY_DIR / "audit-reports"
_SCAN_COOLDOWN_S = 3600  # 1 hour


# ── Helpers ──────────────────────────────────────────────────────────────────


def _latest_mtime(log_dir: Path, pattern: str) -> float | None:
    """Return mtime of the most recently modified file matching pattern, or None."""
    candidates = sorted(
        log_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0].stat().st_mtime if candidates else None


def _ran_recently(log_dir: Path, pattern: str, within_s: int = _SCAN_COOLDOWN_S) -> bool:
    """Return True if the most recent matching log is newer than within_s seconds."""
    mtime = _latest_mtime(log_dir, pattern)
    if mtime is None:
        return False
    return (datetime.now(UTC).timestamp() - mtime) < within_s


def _trigger_systemctl(service: str) -> bool:
    """Start a systemd service. Returns True on success."""
    try:
        result = subprocess.run(
            ["systemctl", "start", service],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning(
                "systemctl start %s failed (rc=%d): %s",
                service,
                result.returncode,
                result.stderr.decode("utf-8", errors="replace").strip(),
            )
            return False
        return True
    except Exception as e:
        logger.warning("Failed to start %s: %s", service, e)
        return False


def _do_ingest() -> dict:
    """Run full log ingestion pipeline. Isolated for testability."""
    from ai.log_intel.ingest import ingest_all  # noqa: PLC0415

    return ingest_all()


def _do_rag_query(question: str) -> str:
    """Run RAG context-only query (no cloud API). Isolated for testability."""
    from ai.rag.query import rag_query  # noqa: PLC0415

    result = rag_query(question, use_llm=False)
    return result.answer


# ── Main workflow ─────────────────────────────────────────────────────────────


def run_audit() -> dict:
    """Run the automated security audit workflow.

    Steps:
    1. Trigger ClamAV quick scan if no scan ran in the last hour.
    2. Trigger system health snapshot if no snapshot ran in the last hour.
    3. Run log ingestion (health + scans + freshclam).
    4. Run RAG query for a 24-hour security summary (no LLM, context-only).
    5. Compile structured report with status: clean | warnings | issues.
    6. Write report atomically to ~/security/audit-reports/.

    Returns:
        dict with keys: timestamp, scan_triggered, health_triggered,
        logs_ingested, rag_summary, status.
    """
    now = datetime.now(UTC)
    timestamp = now.isoformat()

    # Step 1: ClamAV scan
    scan_triggered = False
    if _ran_recently(SCAN_LOG_DIR, "scan-*.log"):
        logger.info("ClamAV scan ran recently — skipping trigger")
    else:
        scan_triggered = _trigger_systemctl("clamav-quick.service")

    # Step 2: Health snapshot
    health_triggered = False
    if _ran_recently(HEALTH_LOG_DIR, "health-*.log"):
        logger.info("Health snapshot ran recently — skipping trigger")
    else:
        health_triggered = _trigger_systemctl("system-health.service")

    # Step 3: Log ingestion
    logs_ingested = False
    try:
        _do_ingest()
        logs_ingested = True
    except Exception as e:
        logger.warning("Log ingestion failed: %s", e)

    # Step 4: RAG summary (no cloud call)
    rag_summary = ""
    try:
        rag_summary = _do_rag_query(
            "Summarize any new security issues, anomalies, or warnings from the last 24 hours"
        )
    except Exception as e:
        logger.warning("RAG query failed: %s", e)
        rag_summary = f"RAG unavailable: {e}"

    # Step 5: Determine status from summary keywords
    summary_lower = rag_summary.lower()
    if any(w in summary_lower for w in ("threat", "infected", "malware", "critical")):
        status = "issues"
    elif any(w in summary_lower for w in ("warning", "anomaly", "spike", "high temp")):
        status = "warnings"
    else:
        status = "clean"

    report = {
        "timestamp": timestamp,
        "scan_triggered": scan_triggered,
        "health_triggered": health_triggered,
        "logs_ingested": logs_ingested,
        "rag_summary": rag_summary,
        "status": status,
    }

    # Step 6: Atomic write
    AUDIT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"audit-{now.strftime('%Y-%m-%d-%H%M')}.json"
    report_path = AUDIT_REPORTS_DIR / filename

    fd, tmp_path = tempfile.mkstemp(dir=AUDIT_REPORTS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(report, f, indent=2)
        os.rename(tmp_path, report_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Audit report written to %s", report_path)

    # Record outcome for learning hooks
    try:
        from ai.hooks import record_task_outcome

        quality = 1.0 if status == "clean" else (0.7 if status == "warnings" else 0.3)
        record_task_outcome(
            task_id="agents.security_audit",
            quality=quality,
            success=status != "issues",
            duration_seconds=time.time() - now.timestamp(),
            agent_type="security",
        )
    except Exception:
        pass  # Best-effort, non-blocking

    return report


if __name__ == "__main__":
    import sys

    from ai.config import setup_logging

    setup_logging()
    result = run_audit()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "clean" else 1)
