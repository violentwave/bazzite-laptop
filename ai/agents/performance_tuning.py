"""Automated performance analysis workflow for Bazzite.

Collects CPU/GPU temps, memory, disk, and load metrics locally.
Generates hardcoded rule-based recommendations (no cloud LLM calls).
Writes a structured JSON report to ~/security/perf-reports/.

Usage:
    python -m ai.agents.performance_tuning
    from ai.agents.performance_tuning import run_tuning
"""

from __future__ import annotations

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

HEALTH_LOG_DIR = Path("/var/log/system-health")
HEALTH_LATEST = HEALTH_LOG_DIR / "health-latest.log"
STEAM_MOUNT = Path("/var/mnt/ext-ssd")

PERF_REPORTS_DIR = SECURITY_DIR / "perf-reports"


# ── Metric collectors ─────────────────────────────────────────────────────────


def _run(cmd: list[str], timeout: int = 10) -> str | None:
    """Run a command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout
        logger.debug("Command %s failed (rc=%d)", cmd[0], result.returncode)
        return None
    except Exception as e:
        logger.debug("Command %s error: %s", cmd[0], e)
        return None


def _collect_cpu_temps() -> tuple[float, float]:
    """Return (avg_temp, max_temp) from sensors, or (0.0, 0.0) on failure."""
    out = _run(["sensors", "-A", "-j"])
    if not out:
        return 0.0, 0.0
    try:
        data = json.loads(out)
        temps: list[float] = []
        for _chip, sensors in data.items():
            for _sensor, readings in sensors.items():
                if not isinstance(readings, dict):
                    continue
                for key, val in readings.items():
                    if key.endswith("_input") and isinstance(val, (int, float)):
                        if 0 < float(val) < 120:
                            temps.append(float(val))
        if not temps:
            return 0.0, 0.0
        return round(sum(temps) / len(temps), 1), round(max(temps), 1)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.debug("sensors parse error: %s", e)
        return 0.0, 0.0


def _collect_gpu_stats() -> dict:
    """Return GPU metrics dict or {'unavailable': True} if nvidia-smi fails."""
    out = _run(
        [
            "nvidia-smi",
            "--query-gpu=temperature.gpu,utilization.gpu,power.draw,memory.used",
            "--format=csv,noheader,nounits",
        ]
    )
    if not out:
        return {"unavailable": True}
    try:
        parts = [p.strip() for p in out.strip().split(",")]
        if len(parts) < 4:
            return {"unavailable": True}
        return {
            "temp": int(parts[0]),
            "utilization": int(parts[1]),
            "power_watts": round(float(parts[2]), 2),
            "memory_used_mb": int(parts[3]),
        }
    except (ValueError, IndexError) as e:
        logger.debug("nvidia-smi parse error: %s", e)
        return {"unavailable": True}


def _collect_memory() -> tuple[float, float]:
    """Return (memory_used_pct, swap_used_pct) from free -b."""
    out = _run(["free", "-b"])
    if not out:
        return 0.0, 0.0
    mem_pct = 0.0
    swap_pct = 0.0
    for line in out.splitlines():
        fields = line.split()
        if fields[0] == "Mem:" and len(fields) >= 3:
            total = int(fields[1])
            used = int(fields[2])
            if total > 0:
                mem_pct = round(used / total * 100, 1)
        elif fields[0] == "Swap:" and len(fields) >= 3:
            total = int(fields[1])
            used = int(fields[2])
            if total > 0:
                swap_pct = round(used / total * 100, 1)
    return mem_pct, swap_pct


def _collect_disk() -> dict[str, float | None]:
    """Return disk usage percentages for /home and Steam drive."""
    targets = ["/home"]
    if STEAM_MOUNT.exists():
        targets.append(str(STEAM_MOUNT))

    out = _run(["df", "-B1"] + targets)
    result: dict[str, float | None] = {"home": None, "steam": None}
    if not out:
        return result

    for line in out.splitlines()[1:]:  # skip header
        fields = line.split()
        if len(fields) < 6:
            continue
        mount = fields[5]
        try:
            use_pct = float(fields[4].rstrip("%"))
        except (ValueError, IndexError):
            continue
        if mount == "/home":
            result["home"] = use_pct
        elif mount == str(STEAM_MOUNT):
            result["steam"] = use_pct

    return result


def _collect_load() -> tuple[float, float, float]:
    """Return (load_1m, load_5m, load_15m) from /proc/loadavg."""
    try:
        text = Path("/proc/loadavg").read_text().strip()
        parts = text.split()
        return float(parts[0]), float(parts[1]), float(parts[2])
    except Exception as e:
        logger.debug("loadavg read error: %s", e)
        return 0.0, 0.0, 0.0


def _read_health_snapshot() -> str:
    """Return last 20 lines of the latest health log, or empty string."""
    target = None
    if HEALTH_LATEST.exists():
        target = HEALTH_LATEST
    else:
        candidates = sorted(
            HEALTH_LOG_DIR.glob("health-*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            target = candidates[0]
    if target is None:
        return ""
    try:
        lines = target.read_text(errors="replace").splitlines()
        return "\n".join(lines[-20:])
    except OSError:
        return ""


def _get_gaming_profiles_count() -> int:
    """Return number of configured game profiles, or 0 if unavailable."""
    try:
        from ai.gaming.scopebuddy import list_profiles  # noqa: PLC0415

        profiles = list_profiles()
        # list_profiles returns {"message": "..."} when no profiles configured
        if "message" in profiles:
            return 0
        return len(profiles)
    except ImportError:
        return 0
    except Exception as e:
        logger.debug("Gaming profiles unavailable: %s", e)
        return 0


# ── Recommendation engine ─────────────────────────────────────────────────────


def _build_recommendations(
    cpu_max: float,
    gpu: dict,
    mem_pct: float,
    swap_pct: float,
    disk: dict[str, float | None],
    load_1m: float,
) -> tuple[list[str], str]:
    """Apply threshold rules and return (recommendations, status).

    Status levels:
        attention_needed — at least one hard threshold breached
        acceptable       — minor thresholds elevated, no hard breach
        optimal          — all nominal
    """
    recs: list[str] = []
    hard_warnings = 0
    minor_warnings = 0

    # CPU temperature
    if cpu_max >= 80:
        recs.append("CPU running hot, check thermal paste / cooling")
        hard_warnings += 1
    elif cpu_max >= 70:
        recs.append(f"CPU temps slightly elevated ({cpu_max:.0f}°C), monitor under load")
        minor_warnings += 1
    else:
        recs.append("CPU temps nominal, no throttling risk")

    # GPU
    if gpu.get("unavailable"):
        recs.append("GPU status unavailable (may be in integrated GPU mode)")
    else:
        gpu_temp = gpu.get("temp", 0)
        if gpu_temp >= 75:
            recs.append("GPU running warm, check case airflow")
            hard_warnings += 1
        elif gpu_temp >= 65:
            recs.append(f"GPU temperature elevated ({gpu_temp}°C), monitor during gaming")
            minor_warnings += 1
        else:
            recs.append("GPU idle — no active gaming workload detected")

    # Memory
    if mem_pct >= 85:
        recs.append("High memory pressure, close unused apps before gaming")
        hard_warnings += 1
    elif mem_pct >= 75:
        recs.append(f"Memory usage at {mem_pct:.0f}%, consider closing background apps")
        minor_warnings += 1

    # Swap
    if swap_pct >= 50:
        recs.append("Heavy swap usage, system may feel sluggish")
        hard_warnings += 1
    elif swap_pct >= 20:
        recs.append(f"Swap in use ({swap_pct:.0f}%), normal for ZRAM but watch for growth")
        minor_warnings += 1

    # Home disk
    home_pct = disk.get("home")
    if home_pct is not None:
        if home_pct >= 85:
            recs.append("Home SSD nearly full, consider cleanup")
            hard_warnings += 1
        elif home_pct >= 78:
            recs.append(f"Home SSD at {home_pct:.0f}% — consider cleanup if above 85%")
            minor_warnings += 1

    # Steam disk
    steam_pct = disk.get("steam")
    if steam_pct is not None:
        if steam_pct >= 90:
            recs.append("Steam drive nearly full, uninstall unused games")
            hard_warnings += 1
        elif steam_pct >= 80:
            recs.append(f"Steam drive at {steam_pct:.0f}%, monitor usage")
            minor_warnings += 1

    # System load
    if load_1m >= 4.0:
        recs.append("High system load, check for runaway processes")
        hard_warnings += 1

    # All nominal
    if not recs:
        recs.append("System running optimally")

    # Determine status
    if hard_warnings > 0:
        status = "attention_needed"
    elif minor_warnings > 0:
        status = "acceptable"
    else:
        status = "optimal"

    return recs, status


# ── Main workflow ─────────────────────────────────────────────────────────────


def run_tuning() -> dict:
    """Run the automated performance analysis workflow.

    Collects CPU/GPU temps, memory, disk, and load metrics locally.
    Generates rule-based recommendations. No cloud API calls.

    Returns:
        dict with keys: timestamp, cpu_temp_avg, cpu_temp_max, gpu_temp,
        gpu_utilization, gpu_power_watts, memory_used_pct, swap_used_pct,
        disk_home_used_pct, disk_steam_used_pct, load_avg_1m,
        gaming_profiles_count, recommendations, status.
    """
    now = datetime.now(UTC)
    timestamp = now.isoformat()

    # Collect metrics
    cpu_avg, cpu_max = _collect_cpu_temps()
    gpu = _collect_gpu_stats()
    mem_pct, swap_pct = _collect_memory()
    disk = _collect_disk()
    load_1m, _load_5m, _load_15m = _collect_load()
    profiles_count = _get_gaming_profiles_count()

    # Build recommendations and determine status
    recs, status = _build_recommendations(
        cpu_max=cpu_max,
        gpu=gpu,
        mem_pct=mem_pct,
        swap_pct=swap_pct,
        disk=disk,
        load_1m=load_1m,
    )

    report: dict = {
        "timestamp": timestamp,
        "cpu_temp_avg": cpu_avg,
        "cpu_temp_max": cpu_max,
        "gpu_temp": None if gpu.get("unavailable") else gpu.get("temp"),
        "gpu_utilization": None if gpu.get("unavailable") else gpu.get("utilization"),
        "gpu_power_watts": None if gpu.get("unavailable") else gpu.get("power_watts"),
        "memory_used_pct": mem_pct,
        "swap_used_pct": swap_pct,
        "disk_home_used_pct": disk.get("home"),
        "disk_steam_used_pct": disk.get("steam"),
        "load_avg_1m": load_1m,
        "gaming_profiles_count": profiles_count,
        "recommendations": recs,
        "status": status,
    }

    # Atomic write
    PERF_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"perf-{now.strftime('%Y-%m-%d-%H%M')}.json"
    report_path = PERF_REPORTS_DIR / filename

    fd, tmp_path = tempfile.mkstemp(dir=PERF_REPORTS_DIR, suffix=".tmp")
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

    logger.info("Performance report written to %s", report_path)

    # Record outcome for learning hooks
    try:
        from ai.hooks import record_task_outcome

        quality = 1.0 if status == "optimal" else (0.7 if status == "good" else 0.4)
        record_task_outcome(
            task_id="agents.performance_tuning",
            quality=quality,
            success=True,
            duration_seconds=time.time() - now.timestamp(),
            agent_type="performance",
        )
    except Exception:
        pass  # Best-effort, non-blocking

    return report


if __name__ == "__main__":
    import sys

    from ai.config import setup_logging

    setup_logging()
    result = run_tuning()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] != "attention_needed" else 1)
