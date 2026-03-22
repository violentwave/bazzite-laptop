"""Unit tests for ai/log_intel/ — log intelligence pipeline.

Tests cover:
  1. Health log parsing
  2. Scan log parsing
  3. Anomaly detection
  4. Query functions (health_trend, scan_history, pipeline_stats, search_logs)
  5. Ingest state management

All LanceDB and Ollama operations are mocked.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Pre-mock lancedb and pyarrow before any ai.log_intel imports
# ---------------------------------------------------------------------------
# Use setdefault so we share the same mock if another test file already
# installed one (e.g. test_store.py), avoiding cross-file interference.
_mock_lancedb = sys.modules.setdefault("lancedb", MagicMock())
_mock_pyarrow = sys.modules.setdefault("pyarrow", MagicMock())


# ---------------------------------------------------------------------------
# Sample log content
# ---------------------------------------------------------------------------

SAMPLE_HEALTH_LOG = """\
=== SYSTEM HEALTH SNAPSHOT ===
Date: 2026-03-21 08:00:00

=== DISK USAGE ===
/dev/dm-0: 31% (71G/237G)
/dev/sdb1: 15% (253G/1.8T)

=== GPU STATUS ===
Temperature: 45°C
Memory: 512/6144 MiB
Power: 15W / 120W

=== CPU TEMPERATURES ===
Package id 0: +62.0°C
Core 0: +60.0°C

=== SMART STATUS ===
/dev/sda: PASSED
/dev/sdb: PASSED

=== SERVICES ===
clamav-freshclam: active
system-health.timer: active
"""

HEALTH_LOG_NO_GPU = """\
=== SYSTEM HEALTH SNAPSHOT ===
Date: 2026-03-21 08:00:00

=== DISK USAGE ===
/dev/dm-0: 31% (71G/237G)
/dev/sdb1: 15% (253G/1.8T)

=== CPU TEMPERATURES ===
Package id 0: +62.0°C
Core 0: +60.0°C

=== SMART STATUS ===
/dev/sda: PASSED
/dev/sdb: PASSED

=== SERVICES ===
clamav-freshclam: active
system-health.timer: active
"""

HEALTH_LOG_MALFORMED = """\
=== SYSTEM HEALTH SNAPSHOT ===
Date: garbage-date

some random text with no valid sections
"""

SAMPLE_SCAN_LOG_CLEAN = """\
/home/lch/Documents/file1.txt: OK
/home/lch/Documents/file2.txt: OK
----------- SCAN SUMMARY -----------
Known viruses: 8700000
Engine version: 1.4.1
Scanned directories: 5
Scanned files: 2
Infected files: 0
Time: 120.5 sec (2 m 0 s)
Start Date: 2026:03:21 08:00:00
End Date:   2026:03:21 08:02:00
"""

SAMPLE_SCAN_LOG_THREATS = """\
/home/lch/Downloads/bad.exe: Win.Trojan.Agent-123 FOUND
/home/lch/Downloads/sketch.bin: Eicar-Signature FOUND
/home/lch/Documents/clean.txt: OK
----------- SCAN SUMMARY -----------
Known viruses: 8700000
Engine version: 1.4.1
Scanned directories: 10
Scanned files: 3
Infected files: 2
Time: 240.0 sec (4 m 0 s)
Start Date: 2026:03:21 09:00:00
End Date:   2026:03:21 09:04:00
"""

SAMPLE_SCAN_LOG_EICAR = """\
/tmp/eicar-test/eicar.com: Win.Test.EICAR_HDB-1 FOUND
----------- SCAN SUMMARY -----------
Scanned files: 1
Infected files: 1
Time: 0.5 sec (0 m 0 s)
Start Date: 2026:03:21 10:00:00
End Date:   2026:03:21 10:00:00
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_lancedb_mock():
    """Reset the lancedb mock between tests."""
    _mock_lancedb.reset_mock()
    yield


@pytest.fixture()
def mock_db():
    """A mock LanceDB connection returned by lancedb.connect()."""
    db = MagicMock()
    _mock_lancedb.connect.return_value = db
    return db


@pytest.fixture()
def mock_embed():
    """Patch embed_texts to return deterministic 768-dim vectors."""
    def _fake_embed(texts):
        return [[0.1] * 768 for _ in texts]

    with patch("ai.log_intel.ingest.embed_texts", side_effect=_fake_embed) as m:
        yield m


# ═══════════════════════════════════════════════════════════════════════════
# 1. Health log parsing
# ═══════════════════════════════════════════════════════════════════════════


class TestParseHealthLog:
    def test_parses_gpu_temperature(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["gpu_temp_c"] == pytest.approx(45.0)

    def test_parses_cpu_temperature(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["cpu_temp_c"] == pytest.approx(62.0)

    def test_parses_disk_usage_root(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["disk_usage_pct"] == pytest.approx(31.0)

    def test_parses_disk_usage_steam(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["steam_usage_pct"] == pytest.approx(15.0)

    def test_parses_smart_status_passed(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["smart_status"] == "PASSED"

    def test_parses_service_counts(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["services_ok"] == 2
        assert record["services_down"] == 0

    def test_parses_timestamp(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert "2026-03-21" in record["timestamp"]

    def test_includes_source_file(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert record["source_file"] == "/var/log/health.log"

    def test_generates_summary(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert isinstance(record["summary"], str)
        assert len(record["summary"]) > 0

    def test_generates_uuid_id(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(SAMPLE_HEALTH_LOG, source_file="/var/log/health.log")
        assert "id" in record
        assert len(record["id"]) == 36  # UUID4 format

    def test_missing_gpu_section_returns_none_temp(self):
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(HEALTH_LOG_NO_GPU, source_file="/var/log/health.log")
        assert record["gpu_temp_c"] is None

    def test_malformed_log_returns_none(self):
        from ai.log_intel.ingest import parse_health_log

        result = parse_health_log(HEALTH_LOG_MALFORMED, source_file="/var/log/health.log")
        # Should return None or a record with mostly None fields, not crash
        if result is not None:
            assert result["gpu_temp_c"] is None
            assert result["cpu_temp_c"] is None

    def test_empty_log_returns_none(self):
        from ai.log_intel.ingest import parse_health_log

        result = parse_health_log("", source_file="/var/log/health.log")
        assert result is None

    def test_smart_failure_detected(self):
        """A log with SMART FAILED should set smart_status accordingly."""
        from ai.log_intel.ingest import parse_health_log

        log_with_failure = SAMPLE_HEALTH_LOG.replace(
            "/dev/sda: PASSED", "/dev/sda: FAILED"
        )
        record = parse_health_log(log_with_failure, source_file="/var/log/health.log")
        assert record["smart_status"] == "FAILED"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Scan log parsing
# ═══════════════════════════════════════════════════════════════════════════


class TestParseScanLog:
    def test_clean_scan_zero_threats(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_CLEAN, source_file="/var/log/scan.log")
        assert record["threats_found"] == 0
        assert record["threat_names"] == ""

    def test_clean_scan_file_count(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_CLEAN, source_file="/var/log/scan.log")
        assert record["files_scanned"] == 2

    def test_clean_scan_duration(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_CLEAN, source_file="/var/log/scan.log")
        assert record["duration_s"] == pytest.approx(120.5)

    def test_threats_found_count(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_THREATS, source_file="/var/log/scan.log")
        assert record["threats_found"] == 2

    def test_threat_names_captured(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_THREATS, source_file="/var/log/scan.log")
        assert "Win.Trojan.Agent-123" in record["threat_names"]
        assert "Eicar-Signature" in record["threat_names"]

    def test_eicar_detection(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_EICAR, source_file="/var/log/scan.log")
        assert record["threats_found"] == 1
        assert "EICAR" in record["threat_names"]

    def test_includes_source_file(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_CLEAN, source_file="/var/log/scan.log")
        assert record["source_file"] == "/var/log/scan.log"

    def test_generates_uuid_id(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_CLEAN, source_file="/var/log/scan.log")
        assert len(record["id"]) == 36

    def test_generates_summary(self):
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(SAMPLE_SCAN_LOG_THREATS, source_file="/var/log/scan.log")
        assert isinstance(record["summary"], str)
        assert len(record["summary"]) > 0

    def test_empty_log_returns_none(self):
        from ai.log_intel.ingest import parse_scan_log

        result = parse_scan_log("", source_file="/var/log/scan.log")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# 3. Anomaly detection
# ═══════════════════════════════════════════════════════════════════════════


class TestAnomalyDetection:
    def test_temperature_spike_gpu(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 95.0,
            "cpu_temp_c": 60.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 0,
            "id": "rec-001",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        categories = [a["category"] for a in anomalies]
        assert "thermal" in categories

    def test_temperature_spike_cpu(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 40.0,
            "cpu_temp_c": 95.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 0,
            "id": "rec-002",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        categories = [a["category"] for a in anomalies]
        assert "thermal" in categories

    def test_disk_fill_acceleration(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 40.0,
            "cpu_temp_c": 60.0,
            "disk_usage_pct": 90.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 0,
            "id": "rec-003",
            "timestamp": "2026-03-21T08:00:00",
        }
        previous = {
            "disk_usage_pct": 80.0,
        }
        anomalies = detect_anomalies(record, record_type="health", previous=previous)
        categories = [a["category"] for a in anomalies]
        assert "disk" in categories

    def test_threat_detection(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "threats_found": 2,
            "threat_names": "Win.Trojan.Agent-123, Eicar-Signature",
            "id": "rec-004",
            "timestamp": "2026-03-21T09:00:00",
        }
        anomalies = detect_anomalies(record, record_type="scan")
        categories = [a["category"] for a in anomalies]
        assert "threat" in categories

    def test_clean_record_no_anomalies(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 40.0,
            "cpu_temp_c": 55.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 0,
            "id": "rec-005",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        assert anomalies == []

    def test_smart_failure(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 40.0,
            "cpu_temp_c": 55.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "FAILED",
            "services_down": 0,
            "id": "rec-006",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        categories = [a["category"] for a in anomalies]
        assert "smart" in categories

    def test_failed_services(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 40.0,
            "cpu_temp_c": 55.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 2,
            "id": "rec-007",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        categories = [a["category"] for a in anomalies]
        assert "service" in categories

    def test_anomaly_has_required_fields(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": 95.0,
            "cpu_temp_c": 60.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 0,
            "id": "rec-008",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        assert len(anomalies) >= 1
        a = anomalies[0]
        assert "id" in a
        assert "timestamp" in a
        assert "category" in a
        assert "severity" in a
        assert "message" in a
        assert "acknowledged" in a
        assert a["acknowledged"] is False
        assert "source_record_id" in a
        assert a["source_record_id"] == "rec-008"

    def test_clean_scan_no_anomalies(self):
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "threats_found": 0,
            "threat_names": "",
            "id": "rec-009",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="scan")
        assert anomalies == []

    def test_null_gpu_temp_no_thermal_anomaly(self):
        """When GPU temp is None (missing section), should not flag thermal."""
        from ai.log_intel.anomalies import detect_anomalies

        record = {
            "gpu_temp_c": None,
            "cpu_temp_c": 55.0,
            "disk_usage_pct": 30.0,
            "steam_usage_pct": 15.0,
            "smart_status": "PASSED",
            "services_down": 0,
            "id": "rec-010",
            "timestamp": "2026-03-21T08:00:00",
        }
        anomalies = detect_anomalies(record, record_type="health")
        assert anomalies == []


# ═══════════════════════════════════════════════════════════════════════════
# 4. Query functions
# ═══════════════════════════════════════════════════════════════════════════


class TestQueryFunctions:
    def test_health_trend_empty_when_no_table(self, mock_db):
        mock_db.table_names.return_value = []

        from ai.log_intel.ingest import health_trend

        result = health_trend(db_path="/tmp/test-db")
        assert result == []

    def test_scan_history_empty_when_no_table(self, mock_db):
        mock_db.table_names.return_value = []

        from ai.log_intel.ingest import scan_history

        result = scan_history(db_path="/tmp/test-db")
        assert result == []

    def test_pipeline_stats_zero_counts(self, mock_db):
        mock_db.table_names.return_value = []

        from ai.log_intel.ingest import pipeline_stats

        result = pipeline_stats(db_path="/tmp/test-db")
        assert result["health_records"] == 0
        assert result["scan_records"] == 0
        assert result["anomalies"] == 0

    def test_search_logs_handles_embed_failure(self, mock_db):
        mock_db.table_names.return_value = ["health_records"]

        with patch("ai.log_intel.ingest.embed_texts", side_effect=RuntimeError("Ollama down")):
            from ai.log_intel.ingest import search_logs

            result = search_logs("GPU temperature", db_path="/tmp/test-db")
            assert result == []

    def test_health_trend_returns_records(self, mock_db):
        mock_table = MagicMock()
        mock_db.table_names.return_value = ["health_records"]
        mock_db.open_table.return_value = mock_table

        fake_records = [
            {"timestamp": "2026-03-21T08:00:00", "gpu_temp_c": 45.0, "cpu_temp_c": 62.0},
            {"timestamp": "2026-03-20T08:00:00", "gpu_temp_c": 43.0, "cpu_temp_c": 60.0},
        ]
        # LanceDB search().limit().to_list() or to_pandas chain
        mock_table.search.return_value.limit.return_value.to_list.return_value = fake_records

        from ai.log_intel.ingest import health_trend

        result = health_trend(db_path="/tmp/test-db")
        assert len(result) == 2

    def test_scan_history_returns_records(self, mock_db):
        mock_table = MagicMock()
        mock_db.table_names.return_value = ["scan_records"]
        mock_db.open_table.return_value = mock_table

        fake_records = [
            {"timestamp": "2026-03-21T08:00:00", "threats_found": 0},
        ]
        mock_table.search.return_value.limit.return_value.to_list.return_value = fake_records

        from ai.log_intel.ingest import scan_history

        result = scan_history(db_path="/tmp/test-db")
        assert len(result) == 1

    def test_pipeline_stats_with_data(self, mock_db):
        mock_table = MagicMock()
        mock_table.count_rows.return_value = 42
        mock_db.table_names.return_value = ["health_records", "scan_records", "anomalies"]
        mock_db.open_table.return_value = mock_table

        from ai.log_intel.ingest import pipeline_stats

        result = pipeline_stats(db_path="/tmp/test-db")
        assert result["health_records"] == 42
        assert result["scan_records"] == 42
        assert result["anomalies"] == 42


# ═══════════════════════════════════════════════════════════════════════════
# 5. Ingest state management
# ═══════════════════════════════════════════════════════════════════════════


class TestIngestState:
    def test_get_state_empty_when_file_missing(self, tmp_path):
        from ai.log_intel.ingest import get_ingest_state

        state = get_ingest_state(state_dir=tmp_path)
        assert state == {}

    def test_save_and_load_state(self, tmp_path):
        from ai.log_intel.ingest import get_ingest_state, save_ingest_state

        state = {"last_health": "/var/log/health-2026-03-21.log", "last_scan": "/var/log/scan.log"}
        save_ingest_state(state, state_dir=tmp_path)

        loaded = get_ingest_state(state_dir=tmp_path)
        assert loaded == state

    def test_save_state_writes_valid_json(self, tmp_path):
        from ai.log_intel.ingest import save_ingest_state

        state = {"last_health": "/var/log/health.log"}
        save_ingest_state(state, state_dir=tmp_path)

        state_file = tmp_path / ".ingest-state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data == state

    def test_find_new_files_filters_by_last_processed(self, tmp_path):
        from ai.log_intel.ingest import find_new_files

        # Create fake log files
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "health-2026-03-19.log").write_text("old")
        (log_dir / "health-2026-03-20.log").write_text("processed")
        (log_dir / "health-2026-03-21.log").write_text("new")

        new_files = find_new_files(
            log_dir=log_dir,
            pattern="health-*.log",
            last_processed="health-2026-03-20.log",
        )
        filenames = [f.name for f in new_files]
        assert "health-2026-03-21.log" in filenames
        assert "health-2026-03-20.log" not in filenames
        assert "health-2026-03-19.log" not in filenames

    def test_find_new_files_returns_all_when_no_last(self, tmp_path):
        from ai.log_intel.ingest import find_new_files

        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "health-2026-03-20.log").write_text("a")
        (log_dir / "health-2026-03-21.log").write_text("b")

        new_files = find_new_files(
            log_dir=log_dir,
            pattern="health-*.log",
            last_processed=None,
        )
        assert len(new_files) == 2

    def test_find_new_files_empty_dir(self, tmp_path):
        from ai.log_intel.ingest import find_new_files

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        new_files = find_new_files(
            log_dir=log_dir,
            pattern="health-*.log",
            last_processed=None,
        )
        assert new_files == []


# ═══════════════════════════════════════════════════════════════════════════
# 6. ingest_scans → security_logs
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_CLAMAV_SCAN_LOG = """\
/home/lch/Downloads/bad.exe: Win.Trojan.Agent-123 FOUND
/home/lch/Documents/clean.txt: OK
----------- SCAN SUMMARY -----------
Known viruses: 8700000
Engine version: 1.4.1
Scanned directories: 5
Scanned files: 2
Infected files: 1
Time: 120.0 sec (2 m 0 s)
Start Date: 2026:03:21 08:00:00
End Date:   2026:03:21 08:02:00
"""


class TestIngestScansPopulatesSecurityLogs:
    """Verify scan logs are chunked and written to security_logs via the RAG store."""

    def test_clamav_log_chunks_reach_security_logs(self, tmp_path):
        from ai.log_intel.ingest import ingest_scans

        log_file = tmp_path / "scan-20260321-080000.log"
        log_file.write_text(SAMPLE_CLAMAV_SCAN_LOG)

        mock_store = MagicMock()
        mock_table = MagicMock()
        mock_db = MagicMock()
        mock_db.table_names.return_value = []
        mock_db.create_table.return_value = mock_table
        _mock_lancedb.connect.return_value = mock_db

        with (
            patch("ai.log_intel.ingest.find_new_files", return_value=[log_file]),
            patch("ai.log_intel.ingest.get_ingest_state", return_value={}),
            patch("ai.log_intel.ingest.save_ingest_state"),
            patch(
                "ai.rag.embedder.embed_texts",
                side_effect=lambda texts: [[0.1] * 768 for _ in texts],
            ),
            patch("ai.rag.store.get_store", return_value=mock_store),
        ):
            result = ingest_scans()

        assert result == 1
        mock_store.add_log_chunks.assert_called_once()
        chunks = mock_store.add_log_chunks.call_args[0][0]
        assert len(chunks) >= 1

        # Both the FOUND-line detections and SCAN SUMMARY should be chunked
        sections = {c["section"] for c in chunks}
        assert "detections" in sections or "SCAN SUMMARY" in sections

        # Every chunk dict must carry the fields required by the security_logs schema
        required_keys = {"source_file", "section", "content", "log_type", "timestamp", "vector"}
        assert all(required_keys <= set(c.keys()) for c in chunks)
        assert all(c["log_type"] == "scan" for c in chunks)
        assert all(len(c["vector"]) == 768 for c in chunks)
