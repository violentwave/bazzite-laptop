"""Shared test fixtures for the Bazzite AI test suite."""

import os

import pytest

# Ensure PYTEST_CURRENT_TEST is set for Sentry filtering
os.environ.setdefault("PYTEST_CURRENT_TEST", "1")

# Pre-load pyarrow so that test files using sys.modules.setdefault("pyarrow", MagicMock())
# are no-ops. Without this, pandas' Cython code (lib.is_pyarrow_array) crashes when it
# encounters a MagicMock instead of the real pyarrow C extension.
try:
    import pyarrow as _pyarrow  # noqa: F401
except Exception:  # noqa: S110
    pass

# Must be set before PySide6 is imported anywhere in the test session.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped headless QApplication for widget tests."""
    PySide6 = pytest.importorskip("PySide6")  # noqa: F841
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def sample_scan_log():
    """A realistic ClamAV scan log for chunker testing."""
    return """----------- SCAN SUMMARY -----------
Known viruses: 8719137
Engine version: 1.4.2
Scanned directories: 1542
Scanned files: 28403
Infected files: 2
Data scanned: 12840.23 MB
Time: 342.118 sec (5 m 42 s)
Start Date: 2026:03:15 02:00:01
End Date:   2026:03:15 02:05:43

/home/lch/.cache/suspicious.exe: Win.Trojan.Agent-123456 FOUND
/tmp/test-eicar.txt: Eicar-Signature FOUND
"""


@pytest.fixture()
def sample_health_log():
    """A realistic system health snapshot for chunker testing."""
    return """=== System Health Snapshot ===
Date: 2026-03-15 08:00:01
Hostname: acer-predator

--- SMART Health ---
/dev/sda: PASSED (SSD, temp=38C, power_on=12840h, reallocated=0)
/dev/sdb: PASSED (HDD, temp=34C, power_on=8420h, reallocated=0)

--- GPU Status ---
Driver: 570.86.16
GPU: NVIDIA GeForce GTX 1060 6GB
Temperature: 42C (idle)
Fan: 0% (auto)
Memory: 412/6144 MiB
Power: 12W / 120W

--- CPU Thermals ---
Package: 48C
Core 0: 46C | Core 1: 48C | Core 2: 45C | Core 3: 47C

--- Storage ---
/dev/sda1 (/):        42G / 100G (42%)
/dev/sdb1 (/run/media/lch/SteamLibrary): 380G / 931G (41%)

--- ZRAM ---
/dev/zram0: 2.1G / 8.0G (26%) [algo: zstd]
vm.swappiness: 180
"""


@pytest.fixture()
def sample_enriched_jsonl():
    """Sample enriched threat intel JSONL for store testing."""
    return (
        '{"hash":"aaaa","source":"virustotal","family":"Trojan.Agent","risk_level":"high","detection_ratio":"62/72","tags":["trojan"],"timestamp":"2026-03-15T02:06:00+00:00"}\n'
        '{"hash":"bbbb","source":"otx","family":"Emotet","risk_level":"medium","detection_ratio":"","tags":["banking"],"timestamp":"2026-03-15T02:06:01+00:00"}\n'
    )


@pytest.fixture()
def mock_embedding():
    """A 768-dim zero vector for embedding tests (matches nomic-embed-text-v2-moe)."""
    return [0.0] * 768


pytest_plugins = ["ai.testing.pytest_plugin"]
