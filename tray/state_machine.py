"""Security tray state machine — shared between tray icon and dashboard.

Reads ~/security/.status (JSON) and determines the current visual state.
No GUI dependencies — pure data logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

STATUS_FILE = Path.home() / "security" / ".status"

# --- States ---

STATE_HEALTHY_IDLE = "healthy_idle"
STATE_SCAN_RUNNING = "scan_running"
STATE_SCAN_COMPLETE = "scan_complete"
STATE_WARNING = "warning"
STATE_SCAN_FAILED = "scan_failed"
STATE_SCAN_ABORTED = "scan_aborted"
STATE_THREATS_FOUND = "threats_found"
STATE_HEALTH_WARNING = "health_warning"
STATE_UNKNOWN = "unknown"

ALL_STATES = (
    STATE_HEALTHY_IDLE, STATE_SCAN_RUNNING, STATE_SCAN_COMPLETE,
    STATE_WARNING, STATE_SCAN_FAILED, STATE_SCAN_ABORTED,
    STATE_THREATS_FOUND, STATE_HEALTH_WARNING, STATE_UNKNOWN,
)


@dataclass(frozen=True)
class StateConfig:
    icon: str
    description: str
    blink: bool = False
    blink_interval_ms: int = 0


STATE_CONFIGS: dict[str, StateConfig] = {
    STATE_HEALTHY_IDLE: StateConfig("bazzite-sec-green", "All clear"),
    STATE_SCAN_RUNNING: StateConfig("bazzite-sec-teal", "Scan in progress", True, 1000),
    STATE_SCAN_COMPLETE: StateConfig("bazzite-sec-blue", "Scan complete", True, 500),
    STATE_WARNING: StateConfig("bazzite-sec-yellow", "Warning"),
    STATE_SCAN_FAILED: StateConfig("bazzite-sec-red", "Scan error"),
    STATE_SCAN_ABORTED: StateConfig("bazzite-sec-red", "Scan aborted", True, 500),
    STATE_THREATS_FOUND: StateConfig("bazzite-sec-red", "Threats found", True, 1000),
    STATE_HEALTH_WARNING: StateConfig("bazzite-sec-health-warn", "Health warnings detected"),
    STATE_UNKNOWN: StateConfig("bazzite-sec-yellow", "Status unknown"),
}

MENU_HEADERS: dict[str, str] = {
    STATE_HEALTHY_IDLE: "\u25cf All clear",
    STATE_SCAN_RUNNING: "\u25cf Scan running...",
    STATE_SCAN_COMPLETE: "\u25cf Scan complete \u2014 log updated",
    STATE_WARNING: "\u26a0 Warning \u2014 check signatures",
    STATE_SCAN_FAILED: "\u2717 Scan error",
    STATE_SCAN_ABORTED: "\u2717 Scan aborted",
    STATE_THREATS_FOUND: "\u2717 {count} threat(s) found",
    STATE_HEALTH_WARNING: "\u26a0 System health: {issues} warning(s)",
    STATE_UNKNOWN: "? Status unknown",
}

# --- Icon paths ---

ICON_DIR = Path.home() / "security" / "icons"
ICON_DIR_HICOLOR = ICON_DIR / "hicolor" / "scalable" / "status"
BLANK_ICON = "bazzite-sec-blank"


def icon_path(icon_name: str) -> Path:
    """Return absolute path to an SVG icon.

    Checks hicolor subdirectory first (has all 7 icons),
    falls back to root icons directory.
    """
    hicolor = ICON_DIR_HICOLOR / f"{icon_name}.svg"
    if hicolor.exists():
        return hicolor
    return ICON_DIR / f"{icon_name}.svg"


# --- Script paths ---

SCAN_SCRIPT = "/usr/local/bin/clamav-scan.sh"
HEALTHCHECK_SCRIPT = "/usr/local/bin/clamav-healthcheck.sh"
HEALTH_SNAPSHOT_SCRIPT = "/usr/local/bin/system-health-snapshot.sh"
TEST_SUITE_SCRIPT = "/usr/local/bin/bazzite-security-test.sh"
HEALTH_LOG = Path("/var/log/system-health/health-latest.log")
QUARANTINE_DIR = Path.home() / "security" / "quarantine"
LOG_DIR = Path("/var/log/clamav-scans")


# --- State determination ---

def read_status() -> dict[str, Any] | None:
    """Read and parse ~/security/.status JSON."""
    try:
        text = STATUS_FILE.read_text(encoding="utf-8")
        return json.loads(text)
    except Exception:
        return None


def determine_state(
    data: dict[str, Any] | None,
    last_completion_timestamp: str | None = None,
) -> tuple[str, str | None]:
    """Determine the current state from .status data.

    Returns (state, new_completion_timestamp). The caller should track
    the completion timestamp to avoid re-triggering SCAN_COMPLETE.
    """
    if data is None:
        return STATE_UNKNOWN, last_completion_timestamp

    state = data.get("state", "")
    result = data.get("result", "")

    if state in ("scanning", "updating"):
        return STATE_SCAN_RUNNING, last_completion_timestamp

    if state == "complete":
        if result == "clean":
            timestamp = data.get("last_scan_time") or data.get("timestamp", "")
            if timestamp and timestamp != last_completion_timestamp:
                return STATE_SCAN_COMPLETE, timestamp
            return _check_health_overlay(data), last_completion_timestamp
        if result == "threats":
            return STATE_THREATS_FOUND, last_completion_timestamp
        if result == "error":
            return STATE_SCAN_FAILED, last_completion_timestamp
        return _check_health_overlay(data), last_completion_timestamp

    if state == "idle":
        last_result = data.get("last_scan_result", "")
        if last_result == "threats":
            return STATE_THREATS_FOUND, last_completion_timestamp
        if last_result == "error":
            return STATE_SCAN_FAILED, last_completion_timestamp
        return _check_health_overlay(data), last_completion_timestamp

    return STATE_UNKNOWN, last_completion_timestamp


def _check_health_overlay(data: dict[str, Any]) -> str:
    """When ClamAV is idle/healthy, check health monitoring for warnings."""
    health = data.get("health_status", "")
    if not isinstance(health, str):
        return STATE_HEALTHY_IDLE
    if health.upper() in ("WARNING", "CRITICAL"):
        return STATE_HEALTH_WARNING
    return STATE_HEALTHY_IDLE


# --- Formatting helpers ---

def format_header(state: str, status_data: dict[str, Any]) -> str:
    """Format the menu header text for a given state."""
    template = MENU_HEADERS.get(state, MENU_HEADERS[STATE_UNKNOWN])
    if state == STATE_THREATS_FOUND:
        count = status_data.get("threat_count", 0) or "?"
        return template.format(count=count)
    if state == STATE_HEALTH_WARNING:
        issues = status_data.get("health_issues", 0) or "?"
        return template.format(issues=issues)
    return template


def format_relative_time(iso_str: str) -> str:
    """Format an ISO timestamp as a relative time string."""
    if not iso_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now()
        if dt.date() == now.date():
            return f"Today {dt.strftime('%I:%M %p').lstrip('0')}"
        delta = (now.date() - dt.date()).days
        if delta == 1:
            return f"Yesterday {dt.strftime('%I:%M %p').lstrip('0')}"
        return dt.strftime("%b %d, %I:%M %p").lstrip("0")
    except Exception:
        return iso_str


def format_health_age(timestamp_str: str) -> str:
    """Format health check timestamp as age string."""
    if not timestamp_str:
        return "unknown"
    # Try multiple timestamp formats
    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            delta = datetime.now() - dt
            hours = int(delta.total_seconds() / 3600)
            if hours < 1:
                return "just now"
            if hours < 24:
                return f"{hours}h ago"
            return f"{hours // 24}d ago"
        except ValueError:
            continue
    return timestamp_str
