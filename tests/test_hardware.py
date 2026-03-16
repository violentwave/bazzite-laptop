"""Unit tests for the hardware state collector.

All subprocess calls and /proc reads are mocked. No real hardware access.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ai.gaming.hardware import (
    _get_cpu_info,
    _get_gpu_info,
    _get_memory_info,
    _get_zram_info,
    _parse_size,
    get_hardware_snapshot,
)
from ai.gaming.models import HardwareSnapshot

# ── Sample Data ──

SAMPLE_NVIDIA_SMI = (
    "NVIDIA GeForce GTX 1060, 570.86.16, 6144, 412, 52, 15.23, 1506, 4004, 3\n"
)

SAMPLE_CPUINFO = """\
processor\t: 0
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 0

processor\t: 1
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 1

processor\t: 2
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 2

processor\t: 3
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 3

processor\t: 4
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 0

processor\t: 5
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 1

processor\t: 6
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 2

processor\t: 7
model name\t: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
physical id\t: 0
core id\t\t: 3
"""

SAMPLE_MEMINFO = """\
MemTotal:       16384000 kB
MemFree:         2048000 kB
MemAvailable:    8192000 kB
SwapTotal:      16384000 kB
SwapFree:       15360000 kB
"""

SAMPLE_ZRAMCTL = "zram0 zstd 16G 2.1G 1.0G 4096 8\n"


# ── Helpers ──


def _make_run_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Build a mock subprocess.CompletedProcess."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# ── GPU Tests ──


class TestGPUInfo:
    """Tests for _get_gpu_info / nvidia-smi parsing."""

    @patch("ai.gaming.hardware.subprocess.run")
    def test_nvidia_smi_parsed(self, mock_run):
        mock_run.return_value = _make_run_result(stdout=SAMPLE_NVIDIA_SMI)

        info = _get_gpu_info()

        assert info["name"] == "NVIDIA GeForce GTX 1060"
        assert info["driver"] == "570.86.16"
        assert info["vram_total"] == 6144
        assert info["vram_used"] == 412
        assert info["temp"] == 52
        assert info["power"] == pytest.approx(15.23)
        assert info["clock"] == 1506
        assert info["mem_clock"] == 4004
        assert info["util"] == 3

    @patch("ai.gaming.hardware.subprocess.run")
    def test_nvidia_smi_na_values(self, mock_run):
        na_output = (
            "NVIDIA GeForce GTX 1060, 570.86.16, 6144, 412,"
            " [N/A], [Not Supported], [N/A], [N/A], [N/A]\n"
        )
        mock_run.return_value = _make_run_result(stdout=na_output)

        info = _get_gpu_info()

        assert info["name"] == "NVIDIA GeForce GTX 1060"
        assert info["temp"] == 0
        assert info["power"] == 0.0
        assert info["clock"] == 0
        assert info["mem_clock"] == 0
        assert info["util"] == 0

    @patch("ai.gaming.hardware.subprocess.run")
    def test_nvidia_smi_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError

        info = _get_gpu_info()

        assert info == {}

    @patch("ai.gaming.hardware.subprocess.run")
    def test_nvidia_smi_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=5)

        info = _get_gpu_info()

        assert info == {}

    @patch("ai.gaming.hardware.subprocess.run")
    def test_nvidia_smi_nonzero_exit(self, mock_run):
        mock_run.return_value = _make_run_result(
            returncode=1, stderr="NVIDIA-SMI has failed"
        )

        info = _get_gpu_info()

        assert info == {}

    @patch("ai.gaming.hardware.subprocess.run")
    def test_nvidia_smi_short_output(self, mock_run):
        mock_run.return_value = _make_run_result(stdout="only, three, fields\n")

        info = _get_gpu_info()

        assert info == {}


# ── CPU Tests ──


class TestCPUInfo:
    """Tests for _get_cpu_info / /proc/cpuinfo parsing."""

    @patch("ai.gaming.hardware.Path.read_text")
    def test_cpuinfo_parsed(self, mock_read):
        mock_read.return_value = SAMPLE_CPUINFO

        info = _get_cpu_info()

        assert info["model"] == "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz"
        assert info["cores"] == 4
        assert info["threads"] == 8

    @patch("ai.gaming.hardware.Path.read_text")
    def test_cpuinfo_unreadable(self, mock_read):
        mock_read.side_effect = OSError("Permission denied")

        info = _get_cpu_info()

        assert info == {}

    @patch("ai.gaming.hardware.Path.read_text")
    def test_cpuinfo_no_physical_id(self, mock_read):
        """Single-socket system without physical id fields."""
        simple = (
            "processor\t: 0\n"
            "model name\t: AMD Ryzen 5 3600\n\n"
            "processor\t: 1\n"
            "model name\t: AMD Ryzen 5 3600\n"
        )
        mock_read.return_value = simple

        info = _get_cpu_info()

        assert info["model"] == "AMD Ryzen 5 3600"
        # Without core id lines, falls back to thread count
        assert info["cores"] == 2
        assert info["threads"] == 2


# ── Memory Tests ──


class TestMemoryInfo:
    """Tests for _get_memory_info / /proc/meminfo parsing."""

    @patch("ai.gaming.hardware.Path.read_text")
    def test_meminfo_parsed(self, mock_read):
        mock_read.return_value = SAMPLE_MEMINFO

        info = _get_memory_info()

        # 16384000 kB // 1024 = 16000 MB
        assert info["total"] == 16000
        # 8192000 kB // 1024 = 8000 MB
        assert info["available"] == 8000
        assert info["swap_total"] == 16000
        # SwapTotal - SwapFree = 16384000 - 15360000 = 1024000 kB // 1024 = 1000 MB
        assert info["swap_used"] == 1000

    @patch("ai.gaming.hardware.Path.read_text")
    def test_meminfo_unreadable(self, mock_read):
        mock_read.side_effect = OSError("No such file")

        info = _get_memory_info()

        assert info == {}


# ── ZRAM Tests ──


class TestZRAMInfo:
    """Tests for _get_zram_info / zramctl parsing."""

    @patch("ai.gaming.hardware.subprocess.run")
    def test_zramctl_parsed(self, mock_run):
        mock_run.return_value = _make_run_result(stdout=SAMPLE_ZRAMCTL)

        info = _get_zram_info()

        # 16G = 16 * 1024 MB = 16384 MB
        assert info["total"] == 16384
        # 2.1G = 2.1 * 1024 = 2150.4 -> int = 2150 MB (from bytes: 2254857830 // 1048576)
        assert info["total"] > 0
        assert info["used"] > 0

    @patch("ai.gaming.hardware.subprocess.run")
    def test_zramctl_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError

        info = _get_zram_info()

        assert info == {}

    @patch("ai.gaming.hardware.subprocess.run")
    def test_zramctl_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="zramctl", timeout=5)

        info = _get_zram_info()

        assert info == {}

    @patch("ai.gaming.hardware.subprocess.run")
    def test_zramctl_nonzero_exit(self, mock_run):
        mock_run.return_value = _make_run_result(returncode=1)

        info = _get_zram_info()

        assert info == {}


# ── Parse Size Tests ──


class TestParseSize:
    """Tests for the _parse_size helper."""

    def test_gigabytes(self):
        assert _parse_size("16G") == 16 * 1024 * 1024 * 1024

    def test_megabytes(self):
        assert _parse_size("512M") == 512 * 1024 * 1024

    def test_kilobytes(self):
        assert _parse_size("1024K") == 1024 * 1024

    def test_bytes(self):
        assert _parse_size("4096") == 4096

    def test_fractional(self):
        assert _parse_size("2.1G") == int(2.1 * 1024 * 1024 * 1024)

    def test_empty(self):
        assert _parse_size("") == 0

    def test_invalid(self):
        assert _parse_size("abc") == 0


# ── Full Snapshot Tests ──


class TestHardwareSnapshot:
    """Integration tests for get_hardware_snapshot and HardwareSnapshot model."""

    @patch("ai.gaming.hardware.subprocess.run")
    @patch("ai.gaming.hardware.Path.read_text")
    def test_full_snapshot(self, mock_read, mock_run):
        """All subsystems return valid data."""

        def read_side_effect(*_args, **_kwargs):
            # Path("/proc/cpuinfo") or Path("/proc/meminfo")
            # We need to distinguish based on the Path instance
            return SAMPLE_CPUINFO

        # subprocess.run is called for nvidia-smi and zramctl
        mock_run.side_effect = [
            _make_run_result(stdout=SAMPLE_NVIDIA_SMI),  # nvidia-smi
            _make_run_result(stdout=SAMPLE_ZRAMCTL),  # zramctl
        ]
        # Path.read_text is called for cpuinfo then meminfo
        mock_read.side_effect = [SAMPLE_CPUINFO, SAMPLE_MEMINFO]

        snap = get_hardware_snapshot()

        assert isinstance(snap, HardwareSnapshot)
        assert snap.gpu_name == "NVIDIA GeForce GTX 1060"
        assert snap.gpu_vram_total_mb == 6144
        assert snap.cpu_model == "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz"
        assert snap.cpu_cores == 4
        assert snap.cpu_threads == 8
        assert snap.ram_total_mb == 16000
        assert snap.ram_available_mb == 8000
        assert snap.zram_total_mb > 0
        assert snap.timestamp  # non-empty ISO timestamp

    def test_vram_pressure_pct(self):
        snap = HardwareSnapshot(gpu_vram_total_mb=6144, gpu_vram_used_mb=412)
        expected = (412 / 6144) * 100
        assert snap.vram_pressure_pct == pytest.approx(expected)

    def test_vram_pressure_zero_total(self):
        snap = HardwareSnapshot(gpu_vram_total_mb=0, gpu_vram_used_mb=0)
        assert snap.vram_pressure_pct == 0.0

    def test_ram_pressure_pct(self):
        snap = HardwareSnapshot(ram_total_mb=16000, ram_available_mb=8000)
        assert snap.ram_pressure_pct == pytest.approx(50.0)

    def test_to_context_string(self):
        snap = HardwareSnapshot(
            gpu_name="NVIDIA GeForce GTX 1060",
            gpu_driver="570.86.16",
            gpu_vram_total_mb=6144,
            gpu_vram_used_mb=412,
            gpu_temp_c=52,
            gpu_power_draw_w=15.23,
            gpu_clock_mhz=1506,
            gpu_mem_clock_mhz=4004,
            gpu_utilization_pct=3,
            cpu_model="Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz",
            cpu_cores=4,
            cpu_threads=8,
            ram_total_mb=16000,
            ram_available_mb=8000,
            swap_total_mb=16000,
            swap_used_mb=1000,
            zram_total_mb=16384,
            zram_used_mb=2150,
            timestamp="2026-03-15T08:00:00+00:00",
        )
        ctx = snap.to_context_string()

        assert "GTX 1060" in ctx
        assert "i7-7700HQ" in ctx
        assert "RAM" in ctx
        assert "ZRAM" in ctx
        assert "Swap" in ctx
        assert "412/6144" in ctx

    def test_to_dict_structure(self):
        snap = HardwareSnapshot(
            gpu_name="GTX 1060",
            cpu_model="i7-7700HQ",
            ram_total_mb=16000,
        )
        d = snap.to_dict()

        assert "gpu" in d
        assert "cpu" in d
        assert "memory" in d
        assert "timestamp" in d
        assert d["gpu"]["name"] == "GTX 1060"
        assert d["cpu"]["model"] == "i7-7700HQ"
        assert d["memory"]["ram_total_mb"] == 16000

    @patch("ai.gaming.hardware.subprocess.run")
    @patch("ai.gaming.hardware.Path.read_text")
    def test_partial_failure(self, mock_read, mock_run):
        """GPU fails, but CPU and memory still populate."""
        mock_run.side_effect = [
            FileNotFoundError,  # nvidia-smi not found
            _make_run_result(returncode=1),  # zramctl fails
        ]
        mock_read.side_effect = [SAMPLE_CPUINFO, SAMPLE_MEMINFO]

        snap = get_hardware_snapshot()

        # GPU fields should be defaults
        assert snap.gpu_name == ""
        assert snap.gpu_vram_total_mb == 0
        # CPU/memory should be populated
        assert snap.cpu_model == "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz"
        assert snap.cpu_cores == 4
        assert snap.ram_total_mb == 16000
        # ZRAM should be defaults
        assert snap.zram_total_mb == 0
