"""Log pipeline status: ingest/archive/retention health, pending files, table row counts."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger("ai.system.pipeline_status")

_HEALTH_LOG_DIR = Path("/var/log/system-health")
_SCAN_LOG_DIR = Path("/var/log/clamav-scans")

_RETENTION_DEFAULTS = {
    "log_tables_days": 90,
    "threat_intel_days": 180,
    "r2_days": 180,
}

_STALE_THRESHOLD_DAYS = 8


def get_pipeline_status() -> dict:
    """Get pipeline status: ingest, archive, retention, and table counts.

    Returns:
        dict with keys: status, ingest, archive, retention, tables
    """
    result: dict = {
        "status": "error",
        "ingest": {},
        "archive": {},
        "retention": _RETENTION_DEFAULTS.copy(),
        "tables": {},
    }

    ingest_state: dict = {}
    archive_state: dict = {}

    # Load ingest state
    try:
        ingest_state = json.loads(
            (VECTOR_DB_DIR / ".ingest-state.json").read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    # Load archive state
    try:
        archive_state = json.loads(
            (VECTOR_DB_DIR / ".archive-state.json").read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    # Extract ingest timestamps
    last_health_ingest = ingest_state.get("last_health_ingest")
    last_scan_ingest = ingest_state.get("last_scan_ingest")

    result["ingest"]["last_health_ingest"] = last_health_ingest
    result["ingest"]["last_scan_ingest"] = last_scan_ingest
    result["ingest"]["pending_files"] = []
    result["ingest"]["pending_count"] = 0

    # Extract archive timestamps
    last_archive_run = archive_state.get("last_archive_run")
    total_archived = archive_state.get("total_archived", 0)
    total_bytes = archive_state.get("total_bytes_archived", 0)

    result["archive"]["last_run"] = last_archive_run
    result["archive"]["total_archived"] = total_archived
    result["archive"]["total_bytes_archived"] = total_bytes

    # Determine status based on timestamps
    now = datetime.now(UTC)
    ingest_stale = True
    archive_stale = True

    # Check ingest freshness
    for ts_key in ("last_health_ingest", "last_scan_ingest"):
        ts = ingest_state.get(ts_key)
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age_days = (now - dt).total_seconds() / 86400
                if age_days < _STALE_THRESHOLD_DAYS:
                    ingest_stale = False
            except (ValueError, TypeError):
                pass

    # Check archive freshness
    if last_archive_run:
        try:
            dt = datetime.fromisoformat(last_archive_run.replace("Z", "+00:00"))
            age_days = (now - dt).total_seconds() / 86400
            if age_days < _STALE_THRESHOLD_DAYS:
                archive_stale = False
        except (ValueError, TypeError):
            pass

    # Set overall status
    if not last_health_ingest and not last_scan_ingest and not last_archive_run:
        result["status"] = "error"
    elif ingest_stale or archive_stale:
        result["status"] = "stale"
    else:
        result["status"] = "healthy"

    # Find pending files (log files newer than last ingest)
    pending_files: list[str] = []

    # Get last health file timestamp
    last_health_time: float | None = None
    if last_health_ingest:
        try:
            dt = datetime.fromisoformat(last_health_ingest.replace("Z", "+00:00"))
            last_health_time = dt.timestamp()
        except (ValueError, TypeError):
            pass

    if _HEALTH_LOG_DIR.exists():
        for log_file in _HEALTH_LOG_DIR.glob("health-*.log"):
            try:
                mtime = log_file.stat().st_mtime
                if last_health_time and mtime > last_health_time:
                    pending_files.append(log_file.name)
            except OSError:
                pass

    # Get last scan file timestamp
    last_scan_time: float | None = None
    if last_scan_ingest:
        try:
            dt = datetime.fromisoformat(last_scan_ingest.replace("Z", "+00:00"))
            last_scan_time = dt.timestamp()
        except (ValueError, TypeError):
            pass

    if _SCAN_LOG_DIR.exists():
        for log_file in _SCAN_LOG_DIR.glob("scan-*.log"):
            try:
                mtime = log_file.stat().st_mtime
                if last_scan_time and mtime > last_scan_time:
                    pending_files.append(log_file.name)
            except OSError:
                pass

    result["ingest"]["pending_files"] = pending_files
    result["ingest"]["pending_count"] = len(pending_files)

    # Get LanceDB table counts
    table_names = ["health_records", "scan_records", "security_logs", "sig_updates", "threat_intel"]

    try:
        import lancedb  # noqa: PLC0415
    except ImportError:
        return result

    try:
        db = lancedb.connect(str(VECTOR_DB_DIR))
    except Exception:
        return result

    for table_name in table_names:
        if table_name in db.table_names():
            try:
                table = db.open_table(table_name)
                result["tables"][table_name] = table.count_rows()
            except Exception:
                result["tables"][table_name] = None
        else:
            result["tables"][table_name] = None

    return result
