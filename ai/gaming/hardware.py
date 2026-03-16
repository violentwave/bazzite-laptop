"""Hardware state collector for gaming optimization context.

Reads GPU state from nvidia-smi, CPU info from /proc/cpuinfo,
memory from /proc/meminfo, and ZRAM from zramctl.

All operations are non-destructive. Failures result in zero/empty
values in the returned HardwareSnapshot (never raises).
"""

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from ai.config import APP_NAME
from ai.gaming.models import HardwareSnapshot

logger = logging.getLogger(APP_NAME)

_NVIDIA_SMI_QUERY = (
    "name,driver_version,memory.total,memory.used,"
    "temperature.gpu,power.draw,clocks.current.graphics,"
    "clocks.current.memory,utilization.gpu"
)


def get_hardware_snapshot() -> HardwareSnapshot:
    """Collect current hardware state. Never raises."""
    gpu = _get_gpu_info()
    cpu = _get_cpu_info()
    mem = _get_memory_info()
    zram = _get_zram_info()

    return HardwareSnapshot(
        gpu_name=gpu.get("name", ""),
        gpu_driver=gpu.get("driver", ""),
        gpu_vram_total_mb=gpu.get("vram_total", 0),
        gpu_vram_used_mb=gpu.get("vram_used", 0),
        gpu_temp_c=gpu.get("temp", 0),
        gpu_power_draw_w=gpu.get("power", 0.0),
        gpu_clock_mhz=gpu.get("clock", 0),
        gpu_mem_clock_mhz=gpu.get("mem_clock", 0),
        gpu_utilization_pct=gpu.get("util", 0),
        cpu_model=cpu.get("model", ""),
        cpu_cores=cpu.get("cores", 0),
        cpu_threads=cpu.get("threads", 0),
        ram_total_mb=mem.get("total", 0),
        ram_available_mb=mem.get("available", 0),
        swap_total_mb=mem.get("swap_total", 0),
        swap_used_mb=mem.get("swap_used", 0),
        zram_total_mb=zram.get("total", 0),
        zram_used_mb=zram.get("used", 0),
        timestamp=datetime.now(UTC).isoformat(),
    )


def _get_gpu_info() -> dict:
    """Parse nvidia-smi CSV output."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={_NVIDIA_SMI_QUERY}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.warning("nvidia-smi failed: %s", result.stderr.strip())
            return {}

        parts = [p.strip() for p in result.stdout.strip().split(", ")]
        if len(parts) < 9:
            return {}

        return {
            "name": parts[0],
            "driver": parts[1],
            "vram_total": _safe_int(parts[2]),
            "vram_used": _safe_int(parts[3]),
            "temp": _safe_int(parts[4]),
            "power": _safe_float(parts[5]),
            "clock": _safe_int(parts[6]),
            "mem_clock": _safe_int(parts[7]),
            "util": _safe_int(parts[8]),
        }
    except FileNotFoundError:
        logger.debug("nvidia-smi not found")
        return {}
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out")
        return {}
    except Exception:
        logger.exception("nvidia-smi parsing failed")
        return {}


def _get_cpu_info() -> dict:
    """Parse /proc/cpuinfo."""
    try:
        text = Path("/proc/cpuinfo").read_text()
        model = ""
        cores: set[tuple[str, str]] = set()  # (physical_id, core_id) pairs
        thread_count = 0
        current_phys_id = "0"

        for line in text.splitlines():
            if line.startswith("model name") and not model:
                model = line.split(":", 1)[1].strip()
            elif line.startswith("physical id"):
                current_phys_id = line.split(":", 1)[1].strip()
            elif line.startswith("core id"):
                core_id = line.split(":", 1)[1].strip()
                cores.add((current_phys_id, core_id))
            elif line.startswith("processor"):
                thread_count += 1

        return {
            "model": model,
            "cores": len(cores) if cores else thread_count,
            "threads": thread_count,
        }
    except OSError:
        logger.warning("Could not read /proc/cpuinfo")
        return {}


def _get_memory_info() -> dict:
    """Parse /proc/meminfo. Values in MB."""
    try:
        text = Path("/proc/meminfo").read_text()
        fields: dict[str, int] = {}
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                try:
                    val_kb = int(parts[1])
                    fields[key] = val_kb // 1024  # kB to MB
                except ValueError:
                    continue

        return {
            "total": fields.get("MemTotal", 0),
            "available": fields.get("MemAvailable", 0),
            "swap_total": fields.get("SwapTotal", 0),
            "swap_used": fields.get("SwapTotal", 0) - fields.get("SwapFree", 0),
        }
    except OSError:
        logger.warning("Could not read /proc/meminfo")
        return {}


def _get_zram_info() -> dict:
    """Parse zramctl output for ZRAM stats."""
    try:
        result = subprocess.run(
            ["zramctl", "--output-all", "--raw", "--noheadings"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return {}

        total = 0
        used = 0
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5:
                # Columns: NAME ALGORITHM DISKSIZE DATA COMPR ...
                total += _parse_size(parts[2])
                used += _parse_size(parts[3])

        return {"total": total // (1024 * 1024), "used": used // (1024 * 1024)}
    except FileNotFoundError:
        logger.debug("zramctl not found")
        return {}
    except subprocess.TimeoutExpired:
        logger.warning("zramctl timed out")
        return {}
    except Exception:
        logger.exception("zramctl parsing failed")
        return {}


def _safe_int(s: str) -> int:
    """Parse a string to int, returning 0 for N/A or invalid values."""
    try:
        return int(float(s)) if s not in ("[N/A]", "[Not Supported]", "") else 0
    except (ValueError, TypeError):
        return 0


def _safe_float(s: str) -> float:
    """Parse a string to float, returning 0.0 for N/A or invalid values."""
    try:
        return float(s) if s not in ("[N/A]", "[Not Supported]", "") else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_size(s: str) -> int:
    """Parse a size string like '16G', '512M', '1024K' to bytes."""
    s = s.strip()
    if not s:
        return 0
    try:
        suffix = s[-1].upper()
        if suffix == "G":
            return int(float(s[:-1]) * 1024 * 1024 * 1024)
        if suffix == "M":
            return int(float(s[:-1]) * 1024 * 1024)
        if suffix == "K":
            return int(float(s[:-1]) * 1024)
        return int(s)
    except (ValueError, IndexError):
        return 0
