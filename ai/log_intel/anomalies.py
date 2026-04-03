"""Automatic anomaly detection for system health and scan records.

Runs after each log ingestion to check for temperature spikes, disk fill
acceleration, new threats, failed services, and SMART failures. Detected
anomalies are stored in a LanceDB ``anomalies`` table and surfaced via
the ``~/security/.status`` JSON file.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ai.config import APP_NAME, STATUS_FILE, VECTOR_DB_DIR

logger = logging.getLogger(APP_NAME)

# ── Thresholds ──

TEMP_ABS_CRITICAL_C = 90
TEMP_SPIKE_DELTA_C = 10
DISK_ACCEL_PCT = 5.0
HISTORY_DAYS = 7


# ── Schema ──


def _get_anomaly_schema():
    """Lazy-load pyarrow schema to avoid import-time overhead."""
    import pyarrow as pa  # noqa: PLC0415

    return pa.schema(
        [
            pa.field("id", pa.utf8()),
            pa.field("timestamp", pa.utf8()),
            pa.field("category", pa.utf8()),
            pa.field("severity", pa.utf8()),
            pa.field("message", pa.utf8()),
            pa.field("acknowledged", pa.bool_()),
            pa.field("source_record_id", pa.utf8()),
        ]
    )


def _connect():
    """Return a LanceDB connection, creating the directory if needed."""
    import lancedb  # noqa: PLC0415

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(VECTOR_DB_DIR))


def _ensure_table(db, name: str, schema):
    """Open or create a table by name."""
    _r = db.list_tables()
    _existing = _r.tables if hasattr(_r, "tables") else list(_r)
    if name in _existing:
        return db.open_table(name)
    return db.create_table(name, schema=schema)


# ── Helpers ──


def _recent_health_records(days: int = HISTORY_DAYS) -> list[dict]:
    """Fetch health_records from LanceDB within the last *days* days."""
    try:
        db = _connect()
        _r = db.list_tables()
        if "health_records" not in (_r.tables if hasattr(_r, "tables") else list(_r)):
            return []
        table = db.open_table("health_records")
        df = table.to_pandas()
        if df.empty:
            return []
        cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()
        df = df[df["timestamp"] >= cutoff]
        return df.to_dict(orient="records")
    except Exception:
        logger.exception("Failed to fetch recent health records")
        return []


def _last_health_record() -> dict | None:
    """Return the most recent health record before the current one, or None."""
    records = _recent_health_records(days=1)
    if len(records) < 2:
        return None
    # Sort descending by timestamp, return second-most-recent
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[1]


def _make_anomaly(
    category: str,
    severity: str,
    message: str,
    source_record_id: str,
) -> dict:
    """Build an anomaly dict with a fresh UUID and timestamp."""
    return {
        "id": str(uuid4()),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "category": category,
        "severity": severity,
        "message": message,
        "acknowledged": False,
        "source_record_id": source_record_id,
    }


# ── Core Detection ──


def check_anomalies(
    health_record: dict | None = None,
    scan_record: dict | None = None,
) -> list[dict]:
    """Inspect the latest ingested record for anomalous conditions.

    Args:
        health_record: A freshly ingested health record dict, or None.
        scan_record: A freshly ingested scan record dict, or None.

    Returns:
        A list of anomaly dicts (may be empty).
    """
    anomalies: list[dict] = []

    if health_record:
        rid = health_record.get("id", "")
        gpu = health_record.get("gpu_temp_c")
        cpu = health_record.get("cpu_temp_c")

        # Absolute thermal threshold
        for label, temp in [("GPU", gpu), ("CPU", cpu)]:
            if temp is not None and temp > TEMP_ABS_CRITICAL_C:
                anomalies.append(
                    _make_anomaly(
                        "thermal",
                        "critical",
                        f"{label} temperature {temp:.0f} C exceeds {TEMP_ABS_CRITICAL_C} C",
                        rid,
                    )
                )

        # Relative thermal spike (7-day average)
        history = _recent_health_records()
        if history:
            for label, field in [("GPU", "gpu_temp_c"), ("CPU", "cpu_temp_c")]:
                temps = [r[field] for r in history if r.get(field) is not None]
                current = health_record.get(field)
                if temps and current is not None:
                    avg = sum(temps) / len(temps)
                    if current - avg > TEMP_SPIKE_DELTA_C:
                        anomalies.append(
                            _make_anomaly(
                                "thermal",
                                "warning",
                                f"{label} temperature {current:.0f} C is "
                                f"{current - avg:.1f} C above 7-day average ({avg:.0f} C)",
                                rid,
                            )
                        )

        # Disk fill acceleration
        prev = _last_health_record()
        if prev:
            for field, label in [("disk_usage_pct", "Root"), ("steam_usage_pct", "Steam")]:
                cur_val = health_record.get(field)
                prev_val = prev.get(field)
                if cur_val is not None and prev_val is not None:
                    delta = cur_val - prev_val
                    if delta > DISK_ACCEL_PCT:
                        anomalies.append(
                            _make_anomaly(
                                "disk",
                                "warning",
                                f"{label} disk usage jumped {delta:.1f}% "
                                f"(from {prev_val:.1f}% to {cur_val:.1f}%)",
                                rid,
                            )
                        )

        # Failed services
        services_down = health_record.get("services_down", 0)
        if services_down and services_down > 0:
            anomalies.append(
                _make_anomaly(
                    "service",
                    "warning",
                    f"{services_down} systemd service(s) are down",
                    rid,
                )
            )

        # SMART failure
        smart = health_record.get("smart_status", "PASSED")
        if smart != "PASSED":
            anomalies.append(
                _make_anomaly(
                    "smart",
                    "critical",
                    f"SMART self-test status: {smart}",
                    rid,
                )
            )

    if scan_record:
        rid = scan_record.get("id", "")
        threats = scan_record.get("threats_found", 0)
        if threats and threats > 0:
            names = scan_record.get("threat_names", "unknown")
            anomalies.append(
                _make_anomaly(
                    "threat",
                    "critical",
                    f"{threats} threat(s) detected: {names}",
                    rid,
                )
            )

    return anomalies


def detect_anomalies(
    record: dict,
    record_type: str = "health",
    previous: dict | None = None,
) -> list[dict]:
    """Test-friendly anomaly detection interface.

    Args:
        record: A parsed health or scan record dict.
        record_type: ``"health"`` or ``"scan"``.
        previous: An optional previous record for delta-based checks
                  (disk fill acceleration).  If *None*, deltas are skipped
                  unless a previous record is available in LanceDB.

    Returns:
        A list of anomaly dicts (may be empty).
    """
    if record_type == "scan":
        return check_anomalies(scan_record=record)

    # For health records, we need to handle the ``previous`` parameter
    # so disk-delta checks work without querying LanceDB.
    rid = record.get("id", "")
    anomalies: list[dict] = []

    gpu = record.get("gpu_temp_c")
    cpu = record.get("cpu_temp_c")

    # Absolute thermal threshold
    for label, temp in [("GPU", gpu), ("CPU", cpu)]:
        if temp is not None and temp > TEMP_ABS_CRITICAL_C:
            anomalies.append(
                _make_anomaly(
                    "thermal",
                    "critical",
                    f"{label} temperature {temp:.0f} C exceeds {TEMP_ABS_CRITICAL_C} C",
                    rid,
                )
            )

    # Disk fill acceleration (using provided previous, or from DB)
    prev = previous
    if prev is None:
        prev = _last_health_record()
    if prev:
        for field, label in [("disk_usage_pct", "Root"), ("steam_usage_pct", "Steam")]:
            cur_val = record.get(field)
            prev_val = prev.get(field)
            if cur_val is not None and prev_val is not None:
                delta = cur_val - prev_val
                if delta > DISK_ACCEL_PCT:
                    anomalies.append(
                        _make_anomaly(
                            "disk",
                            "warning",
                            f"{label} disk usage jumped {delta:.1f}% "
                            f"(from {prev_val:.1f}% to {cur_val:.1f}%)",
                            rid,
                        )
                    )

    # Failed services
    services_down = record.get("services_down", 0)
    if services_down and services_down > 0:
        anomalies.append(
            _make_anomaly(
                "service",
                "warning",
                f"{services_down} systemd service(s) are down",
                rid,
            )
        )

    # SMART failure
    smart = record.get("smart_status", "PASSED")
    if smart != "PASSED":
        anomalies.append(
            _make_anomaly(
                "smart",
                "critical",
                f"SMART self-test status: {smart}",
                rid,
            )
        )

    return anomalies


# ── Storage ──


def store_anomalies(anomalies: list[dict]) -> None:
    """Persist anomaly records to the LanceDB ``anomalies`` table."""
    if not anomalies:
        return
    try:
        db = _connect()
        schema = _get_anomaly_schema()
        table = _ensure_table(db, "anomalies", schema)
        table.add(anomalies)
        logger.info("Stored %d anomaly record(s)", len(anomalies))
    except Exception:
        logger.exception("Failed to store %d anomaly records", len(anomalies))


def update_status_file(anomalies: list[dict]) -> None:
    """Atomically update ~/security/.status with anomaly summary fields.

    Uses tempfile + os.rename for crash safety. Only touches anomaly-related
    keys; other keys (ClamAV scan status, health keys) are preserved.
    """
    if not anomalies:
        return

    status: dict = {}
    try:
        if STATUS_FILE.exists():
            status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read status file, starting fresh: %s", exc)

    latest = max(anomalies, key=lambda a: a["timestamp"])
    prev_count = status.get("anomaly_count", 0)
    status["anomaly_count"] = prev_count + len(anomalies)
    status["last_anomaly"] = latest["timestamp"]
    status["last_anomaly_message"] = latest["message"]

    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(STATUS_FILE.parent),
            suffix=".tmp",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(status, fh, indent=2)
            fh.write("\n")
        os.rename(tmp_path, str(STATUS_FILE))
        logger.debug("Updated status file with %d new anomalies", len(anomalies))
    except OSError:
        logger.exception("Failed to write status file")
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── Queries ──


def get_unacknowledged() -> list[dict]:
    """Return all anomaly records where ``acknowledged`` is False."""
    try:
        db = _connect()
        _r = db.list_tables()
        if "anomalies" not in (_r.tables if hasattr(_r, "tables") else list(_r)):
            return []
        table = db.open_table("anomalies")
        df = table.to_pandas()
        if df.empty:
            return []
        unacked = df[df["acknowledged"] == False]  # noqa: E712
        return unacked.to_dict(orient="records")
    except Exception:
        logger.exception("Failed to query unacknowledged anomalies")
        return []


def acknowledge(anomaly_id: str) -> None:
    """Mark a single anomaly as acknowledged by its id.

    LanceDB does not support in-place row updates, so this reads the full
    table, patches the target row, and overwrites the table.
    """
    try:
        db = _connect()
        _r = db.list_tables()
        if "anomalies" not in (_r.tables if hasattr(_r, "tables") else list(_r)):
            logger.warning("No anomalies table to acknowledge id=%s", anomaly_id)
            return
        table = db.open_table("anomalies")
        df = table.to_pandas()
        mask = df["id"] == anomaly_id
        if not mask.any():
            logger.warning("Anomaly id=%s not found", anomaly_id)
            return
        df.loc[mask, "acknowledged"] = True
        schema = _get_anomaly_schema()
        db.drop_table("anomalies")
        new_table = db.create_table("anomalies", schema=schema)
        new_table.add(df.to_dict(orient="records"))
        logger.info("Acknowledged anomaly id=%s", anomaly_id)
    except Exception:
        logger.exception("Failed to acknowledge anomaly id=%s", anomaly_id)


# ── Entry Point ──


def run_checks(
    health_record: dict | None = None,
    scan_record: dict | None = None,
) -> list[dict]:
    """Main entry: detect anomalies, store them, update status file.

    Args:
        health_record: A freshly ingested health record, or None.
        scan_record: A freshly ingested scan record, or None.

    Returns:
        The list of detected anomalies (may be empty).
    """
    anomalies = check_anomalies(health_record, scan_record)
    if anomalies:
        logger.warning(
            "Detected %d anomaly(ies): %s",
            len(anomalies),
            ", ".join(a["category"] for a in anomalies),
        )
        store_anomalies(anomalies)
        update_status_file(anomalies)
    else:
        logger.info("No anomalies detected")
    return anomalies
