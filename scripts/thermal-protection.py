#!/usr/bin/env python3
"""
Bazzite Thermal Protection Service
Hardware: GTX 1060 + Intel HD 630 hybrid, Fedora Atomic Bazzite
Reads config from /etc/bazzite/thermal-protection.conf
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# ── Defaults (overridden by config file) ─────────────────────────────────────
CPU_WARN     = 80
CPU_THROTTLE = 88
CPU_CRITICAL = 95
GPU_WARN     = 75
GPU_THROTTLE = 83
GPU_CRITICAL = 90
POLL_INTERVAL = 10

CONFIG_FILE = Path("/etc/bazzite/thermal-protection.conf")
LOG_DIR     = Path("/var/log/bazzite")
LOG_FILE    = LOG_DIR / "thermal-protection.log"

# ── Load config file ──────────────────────────────────────────────────────────
def load_config():
    global CPU_WARN, CPU_THROTTLE, CPU_CRITICAL
    global GPU_WARN, GPU_THROTTLE, GPU_CRITICAL
    global POLL_INTERVAL

    if not CONFIG_FILE.exists():
        return

    try:
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key == "CPU_WARN":        CPU_WARN     = int(val)
            elif key == "CPU_THROTTLE":  CPU_THROTTLE = int(val)
            elif key == "CPU_CRITICAL":  CPU_CRITICAL = int(val)
            elif key == "GPU_WARN":      GPU_WARN     = int(val)
            elif key == "GPU_THROTTLE":  GPU_THROTTLE = int(val)
            elif key == "GPU_CRITICAL":  GPU_CRITICAL = int(val)
            elif key == "POLL_INTERVAL": POLL_INTERVAL = int(val)
    except Exception as e:
        print(f"[thermal] Warning: could not parse config: {e}", file=sys.stderr)

load_config()

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("thermal-protection")

# ── Signal handling ───────────────────────────────────────────────────────────
_running = True

def _shutdown(signum, frame):
    global _running
    log.info("Received signal %s — shutting down gracefully.", signum)
    _running = False

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

# ── Desktop notifications ─────────────────────────────────────────────────────
# Find the logged-in user's DBUS session so notify-send works from root service
def _get_user_env() -> dict:
    """Get DBUS/DISPLAY env for user lch so notify-send reaches the desktop."""
    env = os.environ.copy()
    try:
        uid_out = subprocess.check_output(["id", "-u", "lch"], text=True).strip()
        dbus_path = f"/run/user/{uid_out}/bus"
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={dbus_path}"
        env["DISPLAY"] = ":0"
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid_out}"
    except Exception:
        pass
    return env

def notify(title: str, body: str, urgency: str = "normal"):
    """Send a desktop notification to the lch session."""
    try:
        subprocess.run(
            ["sudo", "-u", "lch", "notify-send", "-u", urgency,
             "-a", "Thermal Protection", title, body],
            env=_get_user_env(),
            timeout=5,
            capture_output=True,
        )
    except Exception as e:
        log.debug("notify-send failed (non-fatal): %s", e)

# ── CPU helpers ───────────────────────────────────────────────────────────────
CPU_GOVERNOR_PATH  = "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor"
CPU_MAX_FREQ_PATH  = "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_max_freq"
CPU_INFO_MAX_PATH  = "/sys/devices/system/cpu/cpu{}/cpufreq/cpuinfo_max_freq"

_saved_governor: str | None = None

def get_cpu_count() -> int:
    return os.cpu_count() or 4

def read_current_governor() -> str:
    """Read governor from cpu0 as representative."""
    try:
        return Path(CPU_GOVERNOR_PATH.format(0)).read_text().strip()
    except Exception:
        return "performance"

def save_governor():
    """Save current governor so we can restore it on exit."""
    global _saved_governor
    _saved_governor = read_current_governor()
    log.info("Saved current CPU governor: %s", _saved_governor)

def set_cpu_governor(governor: str) -> bool:
    cpu_count = get_cpu_count()
    success = True
    for i in range(cpu_count):
        try:
            Path(CPU_GOVERNOR_PATH.format(i)).write_text(governor + "\n")
        except (PermissionError, FileNotFoundError) as e:
            log.error("Cannot set governor for cpu%d: %s", i, e)
            success = False
        except OSError as e:
            log.warning("Governor '%s' rejected for cpu%d (Invalid argument) — trying powersave fallback: %s", governor, i, e)
            try:
                Path(CPU_GOVERNOR_PATH.format(i)).write_text("powersave\n")
                log.info("Fallback powersave accepted for cpu%d", i)
            except OSError:
                log.warning("Fallback powersave also rejected for cpu%d — governor unchanged", i)
            success = False
    if success:
        log.info("CPU governor → %s", governor)
    return success

def set_cpu_max_freq(freq_khz: int) -> bool:
    cpu_count = get_cpu_count()
    success = True
    for i in range(cpu_count):
        try:
            Path(CPU_MAX_FREQ_PATH.format(i)).write_text(str(freq_khz) + "\n")
        except (PermissionError, FileNotFoundError) as e:
            log.warning("Cannot set max freq for cpu%d: %s", i, e)
            success = False
    if success:
        log.info("CPU max freq capped → %d kHz", freq_khz)
    return success

def restore_cpu_defaults():
    """Restore saved governor and remove freq cap."""
    governor = _saved_governor if _saved_governor else "performance"
    set_cpu_governor(governor)
    cpu_count = get_cpu_count()
    for i in range(cpu_count):
        try:
            max_freq = Path(CPU_INFO_MAX_PATH.format(i)).read_text().strip()
            Path(CPU_MAX_FREQ_PATH.format(i)).write_text(max_freq + "\n")
        except Exception as e:
            log.warning("Cannot restore max freq for cpu%d: %s", i, e)
    log.info("CPU defaults restored (governor: %s)", governor)

# ── GPU helpers ───────────────────────────────────────────────────────────────
def get_gpu_temp() -> float | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5
        )
        return float(out.strip())
    except Exception as e:
        log.debug("GPU temp unavailable: %s", e)
        return None

def throttle_gpu_power(limit_watts: int):
    try:
        subprocess.run(
            ["nvidia-smi", "-pl", str(limit_watts)],
            check=True, timeout=5, capture_output=True
        )
        log.info("GPU power limit → %dW", limit_watts)
    except Exception as e:
        log.warning("Cannot set GPU power limit: %s", e)

def restore_gpu_power():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=power.default_limit",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5
        )
        default_w = int(float(out.strip()))
        subprocess.run(
            ["nvidia-smi", "-pl", str(default_w)],
            check=True, timeout=5, capture_output=True
        )
        log.info("GPU power limit restored → %dW", default_w)
    except Exception as e:
        log.warning("Cannot restore GPU power: %s", e)

# ── Sensor reading ────────────────────────────────────────────────────────────
def get_cpu_temps() -> list[float]:
    try:
        out = subprocess.check_output(
            ["sensors", "-A", "-j"], text=True, timeout=5
        )
        data = json.loads(out)
        temps = []
        for chip, sensors in data.items():
            for sensor_name, readings in sensors.items():
                if not isinstance(readings, dict):
                    continue
                for key, val in readings.items():
                    if key.endswith("_input") and isinstance(val, (int, float)):
                        if 0 < val < 120:
                            temps.append(float(val))
        return list(set(temps))
    except Exception as e:
        log.warning("Could not read CPU temps: %s", e)
        return []

# ── State machine ─────────────────────────────────────────────────────────────
class State:
    NORMAL   = "normal"
    WARN     = "warn"
    THROTTLE = "throttle"
    CRITICAL = "critical"

current_state = State.NORMAL

def evaluate_and_act(max_cpu: float, gpu: float | None):
    global current_state

    if max_cpu >= CPU_CRITICAL or (gpu is not None and gpu >= GPU_CRITICAL):
        target = State.CRITICAL
    elif max_cpu >= CPU_THROTTLE or (gpu is not None and gpu >= GPU_THROTTLE):
        target = State.THROTTLE
    elif max_cpu >= CPU_WARN or (gpu is not None and gpu >= GPU_WARN):
        target = State.WARN
    else:
        target = State.NORMAL

    if target == current_state:
        return

    gpu_str = f"{gpu:.1f}°C" if gpu is not None else "N/A"
    log.info("State: %s → %s  (CPU=%.1f°C GPU=%s)", current_state, target, max_cpu, gpu_str)
    current_state = target

    if target == State.NORMAL:
        restore_cpu_defaults()
        restore_gpu_power()
        notify("Thermals Normal", f"CPU {max_cpu:.0f}°C · GPU {gpu_str} — restored defaults.")

    elif target == State.WARN:
        set_cpu_governor("schedutil")
        notify("Thermal Warning ⚠️",
               f"CPU {max_cpu:.0f}°C · GPU {gpu_str}\nSwitched to schedutil governor.",
               urgency="normal")

    elif target == State.THROTTLE:
        set_cpu_governor("powersave")
        set_cpu_max_freq(1600000)
        throttle_gpu_power(60)
        notify("Thermal Throttle 🔥",
               f"CPU {max_cpu:.0f}°C · GPU {gpu_str}\nCPU capped 1.6GHz · GPU 60W.",
               urgency="critical")

    elif target == State.CRITICAL:
        set_cpu_governor("powersave")
        set_cpu_max_freq(800000)
        throttle_gpu_power(40)
        notify("CRITICAL TEMP 🚨",
               f"CPU {max_cpu:.0f}°C · GPU {gpu_str}\nEmergency: CPU 800MHz · GPU 40W!\nClose heavy workloads now.",
               urgency="critical")

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    log.info("Thermal protection started. Config: %s", CONFIG_FILE)
    log.info("CPU thresholds — warn:%d throttle:%d critical:%d",
             CPU_WARN, CPU_THROTTLE, CPU_CRITICAL)
    log.info("GPU thresholds — warn:%d throttle:%d critical:%d",
             GPU_WARN, GPU_THROTTLE, GPU_CRITICAL)
    log.info("Poll interval: %ds", POLL_INTERVAL)

    save_governor()  # Save governor state at startup

    while _running:
        cpu_temps = get_cpu_temps()
        gpu_temp  = get_gpu_temp()
        max_cpu   = max(cpu_temps) if cpu_temps else 0.0

        if cpu_temps:
            log.debug("CPU temps: %s  max=%.1f°C",
                      [f"{t:.1f}" for t in cpu_temps], max_cpu)
        if gpu_temp is not None:
            log.debug("GPU: %.1f°C", gpu_temp)

        evaluate_and_act(max_cpu, gpu_temp)
        time.sleep(POLL_INTERVAL)

    log.info("Restoring defaults before exit...")
    restore_cpu_defaults()
    restore_gpu_power()
    log.info("Thermal protection stopped.")

if __name__ == "__main__":
    main()
