#!/usr/bin/env python3
"""Headless daily security briefing — Phase 20."""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.config import SECURITY_DIR, VECTOR_DB_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BRIEFINGS_DIR = SECURITY_DIR / "briefings"

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


def read_json_file(path: Path) -> dict:
    """Read JSON file, return {} on any error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}



def get_output_path(date_str: str) -> Path:
    """Return unique briefing path, appending -2/-3 if today already exists."""
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    base = BRIEFINGS_DIR / f"briefing-{date_str}"
    path = base.with_suffix(".md")
    if not path.exists():
        return path
    for i in range(2, 10):
        path = base.parent / f"briefing-{date_str}-{i}.md"
        if not path.exists():
            return path
    return path


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


def check_timers() -> dict:
    """Validate all 16 timers fired within expected windows."""
    now = int(time.time())
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
                timer_last = {}
                for entry in timers_data:
                    unit = entry.get("unit", "")
                    last = entry.get("last", 0)
                    if unit and last:
                        timer_last[unit] = last
            except Exception:
                timer_last = {}
        else:
            timer_last = {}
    except Exception:
        timer_last = {}

    timers = []
    stale = []
    missing = []

    for name, spec in EXPECTED_TIMERS.items():
        last_trigger = timer_last.get(name, 0)
        if last_trigger == 0 or last_trigger > 2000000000:
            age_hours = None
            status = "stale"
            if name not in timer_last:
                missing.append(name)
                status = "missing"
            last_trigger_iso = None
        else:
            age_hours = (now - last_trigger) / 3600
            status = "stale" if age_hours > spec["max_age_hours"] else "ok"
            if status == "stale":
                stale.append(name)
            try:
                last_trigger_iso = datetime.fromtimestamp(last_trigger).isoformat()
            except Exception:
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

    overall_status = "critical" if missing else ("warning" if stale else "healthy")
    stale_list = stale
    missing_list = missing

    summary = f"{len(stale_list)} stale, {len(missing_list)} missing"
    if overall_status == "healthy":
        summary = "All 16 timers healthy"
    elif overall_status == "warning" and not missing_list:
        summary = f"{len(stale_list)} timer(s) stale"

    return {
        "status": overall_status,
        "checked_at": datetime.now().isoformat(),
        "timers": timers,
        "stale": stale_list,
        "missing": missing_list,
        "summary": summary,
    }


def get_anomalies() -> list:
    """Get unacknowledged anomalies from log_intel."""
    try:
        from ai.log_intel.queries import get_anomalies as log_intel_get_anomalies

        return log_intel_get_anomalies()
    except Exception:
        return []


def build_briefing() -> str:
    """Assemble the full markdown briefing string."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    log.info("Building security briefing for %s", date_str)

    status_data = read_json_file(SECURITY_DIR / ".status")
    log.info("Read .status: %s", "OK" if status_data else "missing")

    llm_status = read_json_file(SECURITY_DIR / "llm-status.json")
    log.info("Read llm-status.json: %s", "OK" if llm_status else "missing")

    key_status = read_json_file(SECURITY_DIR / "key-status.json")
    log.info("Read key-status.json: %s", "OK" if key_status else "missing")

    release_watch = read_json_file(SECURITY_DIR / "release-watch.json")
    log.info("Read release-watch.json: %s", "OK" if release_watch else "missing")

    fedora_updates = read_json_file(SECURITY_DIR / "fedora-updates.json")
    log.info("Read fedora-updates.json: %s", "OK" if fedora_updates else "missing")

    anomalies = get_anomalies()
    log.info("Retrieved %d anomalies", len(anomalies))

    timer_result = check_timers()
    log.info("Timer check: %s", timer_result["status"])

    archive_state = read_json_file(VECTOR_DB_DIR / ".archive-state.json")
    log.info("Read archive-state.json: %s", "OK" if archive_state else "missing")

    sections = []

    sections.append(f"# Security Briefing — {date_str} {time_str}\n")

    health_status = status_data.get("health_status", "unknown")
    last_scan_result = status_data.get("result", "unknown")
    last_scan_time = status_data.get("last_scan_time", "never")

    if last_scan_result == "clean":
        security_content = (
            f"- ClamAV: {last_scan_result}, last scan at {last_scan_time}\n"
            f"- Health status: {health_status}"
        )
    elif last_scan_result == "infected":
        security_content = (
            f"- ⚠ ClamAV: {last_scan_result}, last scan at {last_scan_time}\n"
            f"- Health status: {health_status}"
        )
    else:
        security_content = "⚠ Data unavailable"
    sections.append(f"## Security\n{security_content}\n")

    if anomalies:
        anomaly_list = "\n".join(
            f"- {a.get('type', 'unknown')}: {a.get('message', '')}" for a in anomalies[:5]
        )
        health_content = (
            f"- System health: {health_status}\n"
            f"- Unacknowledged anomalies: {len(anomalies)}\n{anomaly_list}"
        )
    else:
        health_content = f"- System health: {health_status}\n- No unacknowledged anomalies"
    sections.append(f"## Health\n{health_content}\n")

    providers_content = ""
    if llm_status.get("providers"):
        for provider, state in llm_status["providers"].items():
            icon = "✓" if state == "healthy" else "⚠" if state == "degraded" else "✗"
            providers_content += f"- {icon} {provider}: {state}\n"
    if not providers_content:
        providers_content = "⚠ Data unavailable"
    sections.append(f"## LLM Providers\n{providers_content}\n")

    updates_content = ""
    pending = fedora_updates.get("pending", [])
    if pending:
        updates_content += f"- Pending updates: {len(pending)}\n"
        critical_pkgs = [p.get("package") for p in pending if p.get("severity") == "security"]
        if critical_pkgs:
            updates_content += f"- ⚠ Critical: {', '.join(critical_pkgs[:3])}\n"
    else:
        updates_content += "- No pending updates\n"

    alerts = release_watch.get("alerts", [])
    if alerts:
        kev_alerts = [a for a in alerts if a.get("type") == "kev"]
        if kev_alerts:
            updates_content += f"- ⚠ KEV CVEs: {len(kev_alerts)}\n"
        new_releases = [a for a in alerts if a.get("type") == "release"]
        if new_releases:
            updates_content += f"- New upstream releases: {len(new_releases)}\n"

    if not updates_content:
        updates_content = "⚠ Data unavailable"
    sections.append(f"## Updates\n{updates_content}\n")

    pipeline_content = ""
    if archive_state:
        last_upload = archive_state.get("last_upload", "never")
        bytes_uploaded = archive_state.get("bytes_uploaded", 0)
        tables = archive_state.get("tables", {})
        table_list = ", ".join(tables.keys())
        pipeline_content = (
            f"- Last R2 upload: {last_upload}\n"
            f"- Bytes uploaded: {bytes_uploaded:,}\n"
            f"- Tables: {table_list}\n"
        )
    else:
        pipeline_content = "⚠ Data unavailable"
    sections.append(f"## Pipeline\n{pipeline_content}\n")

    timer_status = timer_result["status"]
    timer_icon = "✓" if timer_status == "healthy" else "⚠" if timer_status == "warning" else "✗"
    timers_content = f"- Overall: {timer_icon} {timer_status}\n"
    if timer_result["stale"]:
        timers_content += f"- Stale timers: {', '.join(timer_result['stale'])}\n"
    if timer_result["missing"]:
        timers_content += f"- Missing timers: {', '.join(timer_result['missing'])}\n"
    sections.append(f"## Timers\n{timers_content}\n")

    action_items = []

    last_scan_result = status_data.get("result", "clean")
    if last_scan_result != "clean":
        action_items.append(f"Review quarantine: {status_data.get('threat_name', 'unknown')}")

    if anomalies:
        action_items.append(f"Acknowledge {len(anomalies)} anomaly(ies) in Newelle or via logs")

    if llm_status.get("providers"):
        for provider, state in llm_status["providers"].items():
            if state in ("degraded", "down"):
                action_items.append(f"Check API key for {provider}")

    if alerts:
        for alert in alerts:
            if alert.get("type") == "kev":
                action_items.append(f"URGENT: Apply KEV patch for {alert.get('cve_id', 'unknown')}")

    if timer_result["stale"]:
        for stale_timer in timer_result["stale"]:
            for t in timer_result["timers"]:
                if t["name"] == stale_timer and t["age_hours"]:
                    action_items.append(
                        f"Investigate stale timer: {stale_timer} "
                        f"(last ran {t['age_hours']:.1f}h ago)"
                    )

    if pending:
        for pkg in pending[:2]:
            if pkg.get("severity") == "security":
                action_items.append(f"Apply update: {pkg.get('package', 'unknown')}")

    if not action_items:
        action_items.append("(none — system healthy)")

    action_content = "\n".join(f"- {item}" for item in action_items)
    sections.append(f"## Action Items\n{action_content}\n")

    return "\n".join(sections)


def main() -> int:
    """Entry point. Returns exit code 0 on success, 1 on fatal error."""
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    try:
        output_path = get_output_path(date_str)
    except Exception as e:
        log.error("Failed to determine output path: %s", e)
        return 1

    try:
        content = build_briefing()
    except Exception as e:
        log.error("Failed to build briefing: %s", e)
        return 1

    try:
        tmp_path = output_path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            f.write(content)
        import os

        os.replace(tmp_path, output_path)
    except Exception as e:
        log.error("Failed to write briefing: %s", e)
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception as exc:
            log.warning("Failed to clean up temp file: %s", exc)
        return 1

    log.info("Briefing written to %s", output_path)

    try:
        import os

        email_alerts = os.environ.get("EMAIL_ALERTS", "").lower()
        if email_alerts == "true":
            alert_script = Path(__file__).parent / "clamav-alert.sh"
            if alert_script.exists():
                result = subprocess.run(
                    ["bash", str(alert_script), str(output_path)],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    log.warning("Email alert failed: %s", result.stderr.decode())
    except Exception as e:
        log.warning("Email alert error: %s", e)

    log.info("Security briefing complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
