"""Timer sentinel agent — validates all 16 systemd timers fired within expected windows."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from datetime import datetime

logger = logging.getLogger(__name__)

EXPECTED_TIMERS = {
    "system-health.timer": {"schedule": "daily", "max_age_hours": 26},
    "security-audit.timer": {"schedule": "daily", "max_age_hours": 26},
    "performance-tuning.timer": {"schedule": "daily", "max_age_hours": 26},
    "rag-embed.timer": {"schedule": "daily", "max_age_hours": 26},
    "knowledge-storage.timer": {"schedule": "daily", "max_age_hours": 26},
    "release-watch.timer": {"schedule": "daily", "max_age_hours": 26},
    "clamav-quick.timer": {"schedule": "daily", "max_age_hours": 26},
    "service-canary.timer": {"schedule": "15min", "max_age_hours": 1},
    "clamav-healthcheck.timer": {"schedule": "weekly", "max_age_hours": 170},
    "clamav-deep.timer": {"schedule": "weekly", "max_age_hours": 170},
    "cve-scanner.timer": {"schedule": "weekly", "max_age_hours": 170},
    "log-ingest.timer": {"schedule": "weekly", "max_age_hours": 170},
    "log-archive.timer": {"schedule": "weekly", "max_age_hours": 170},
    "lancedb-optimize.timer": {"schedule": "weekly", "max_age_hours": 170},
    "fedora-updates.timer": {"schedule": "weekly", "max_age_hours": 170},
    "security-briefing.timer": {"schedule": "daily", "max_age_hours": 26},
}


def check_timers() -> dict:
    """Validate all 16 timers fired within expected windows.

    Returns:
        dict with keys:
            - status: "healthy" | "warning" | "critical"
            - checked_at: ISO8601 timestamp
            - timers: list of timer entries
            - stale: list of stale timer names
            - missing: list of missing timer names
            - summary: human-readable summary
    """
    now = int(time.time())
    timer_last: dict[str, int] = {}

    try:
        result = subprocess.run(
            ["systemctl", "list-timers", "--all", "--output=json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            try:
                timers_data = json.loads(result.stdout)
                for entry in timers_data:
                    unit = entry.get("unit", "")
                    last = entry.get("last", 0)
                    if unit:
                        timer_last[unit] = last
            except json.JSONDecodeError:
                logger.warning("Failed to parse systemctl JSON output")
        else:
            logger.warning("systemctl list-timers returned non-zero: %d", result.returncode)
    except subprocess.TimeoutExpired:
        logger.error("systemctl list-timers timed out")
    except FileNotFoundError:
        logger.error("systemctl not found")
    except Exception as e:
        logger.error("Failed to get timer list: %s", e)

    timers: list[dict] = []
    stale: list[str] = []
    missing: list[str] = []

    for name, spec in EXPECTED_TIMERS.items():
        last_trigger = timer_last.get(name, 0)

        if last_trigger == 0 or last_trigger > 2000000000:
            age_hours = None
            if name not in timer_last:
                status = "missing"
                missing.append(name)
            else:
                status = "stale"
                stale.append(name)
            last_trigger_iso = None
        else:
            age_hours = (now - last_trigger) / 3600
            status = "stale" if age_hours > spec["max_age_hours"] else "ok"
            if status == "stale":
                stale.append(name)
            try:
                last_trigger_iso = datetime.fromtimestamp(last_trigger).isoformat()
            except (OSError, ValueError):
                last_trigger_iso = None

        timers.append(
            {
                "name": name,
                "schedule": spec["schedule"],
                "max_age_hours": spec["max_age_hours"],
                "last_trigger": last_trigger_iso,
                "age_hours": round(age_hours, 1) if age_hours is not None else None,
                "status": status,
            }
        )

    if missing:
        overall_status = "critical"
    elif stale:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    if overall_status == "healthy":
        summary = "All 16 timers healthy"
    else:
        summary = f"{len(stale)} stale, {len(missing)} missing"

    return {
        "status": overall_status,
        "checked_at": datetime.now().isoformat(),
        "timers": timers,
        "stale": stale,
        "missing": missing,
        "summary": summary,
    }


def get_timer_age_hours(timer_name: str) -> float | None:
    """Get hours since last trigger for a single timer. None if not found."""
    try:
        result = subprocess.run(
            ["systemctl", "show", "-p", "ActiveEnterTimestamp", "--value", timer_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        timestamp = result.stdout.strip()
        if not timestamp:
            return None
        dt = datetime.strptime(timestamp, "%a %Y-%m-%d %H:%M:%S %Z")
        now = datetime.now()
        age = (now - dt).total_seconds() / 3600
        return age
    except Exception:
        return None


def format_timer_report() -> str:
    """Return a human-readable string summary for use in briefing output."""
    result = check_timers()
    lines = [f"Timer Health: {result['status']}"]

    if result["stale"]:
        lines.append(f"Stale timers: {', '.join(result['stale'])}")
    if result["missing"]:
        lines.append(f"Missing timers: {', '.join(result['missing'])}")

    if not result["stale"] and not result["missing"]:
        lines.append("All 16 timers running on schedule")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    result = check_timers()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "healthy" else 1)
