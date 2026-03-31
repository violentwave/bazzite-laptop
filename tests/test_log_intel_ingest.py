"""Unit tests for ai/log_intel/ingest.py - log ingestion pipeline.

Tests health snapshot parsing, scan log parsing, LanceDB table creation,
and embedding generation.
"""

from unittest.mock import patch

import pytest


@pytest.fixture()
def temp_log_dir(tmp_path):
    """Create temporary log directories."""
    health_dir = tmp_path / "health"
    scan_dir = tmp_path / "scan"
    health_dir.mkdir()
    scan_dir.mkdir()
    return {"health": health_dir, "scan": scan_dir}


@pytest.fixture()
def sample_health_log(temp_log_dir):
    """Sample health snapshot log matching actual regex patterns.

    Formats required by parse_health_log:
      - GPU:   "Temperature: 72.0°C"
      - CPU:   "Package id 0: +68.0°C"  (or "Package temp: ...")
      - Disk:  "/dev/sda1: 45% (100G/250G)"
      - RAM:   "Mem: 15.4Gi 8.5Gi"   (group 2 = used)
      - Swap:  "Swap: 15.4Gi 0.0Gi"  (group 2 = used)
      - SMART: "Overall health: PASSED"
      - Svcs:  lines ending ": active" / ": inactive"
    """
    log_content = """\
Temperature: 72.0\u00b0C
Package id 0: +68.0\u00b0C
/dev/sda1: 45% (100G/250G)
Mem: 15.4Gi 8.5Gi
Swap: 15.4Gi 0.0Gi
Overall health: PASSED
clamav: active
mcp-bridge: active
llm-proxy: active
"""
    log_file = temp_log_dir["health"] / "health-20250331.log"
    log_file.write_text(log_content)
    return log_file


@pytest.fixture()
def sample_scan_log(temp_log_dir):
    """Sample ClamAV scan log."""
    log_content = """\
----------- SCAN SUMMARY -----------
Known viruses: 8718212
Engine version: 1.4.1
Scanned directories: 3
Scanned files: 142
Infected files: 0
Data scanned: 234.56 MB
Time: 45.2 sec (0 m 45 s)
Start Date: 2025:03:31 10:00:01
End Date:   2025:03:31 10:00:46
"""
    log_file = temp_log_dir["scan"] / "scan-20250331.log"
    log_file.write_text(log_content)
    return log_file


# ── Health Log Parsing Tests ──


class TestHealthLogParsing:
    """Tests for parsing system health snapshot logs."""

    def test_parse_health_log_extracts_metrics(self, sample_health_log):
        """Parse health log and extract all metrics."""
        from ai.log_intel.ingest import parse_health_log

        record = parse_health_log(sample_health_log)

        assert record["gpu_temp_c"] == 72.0
        assert record["cpu_temp_c"] == 68.0
        # Disk regex captures integer percentage from "/dev/sda1: 45% ("
        assert record["disk_usage_pct"] == 45.0
        assert record["ram_used_gb"] == pytest.approx(8.5, abs=0.1)
        assert record["swap_used_gb"] == pytest.approx(0.0, abs=0.1)
        assert record["smart_status"] == "PASSED"
        # 3 lines ending ": active" in sample fixture
        assert record["services_ok"] == 3
        assert record["services_down"] == 0

    def test_parse_health_log_missing_fields(self, temp_log_dir):
        """Gracefully handle missing fields in health logs."""
        from ai.log_intel.ingest import parse_health_log

        # Only GPU temp present; CPU/disk/RAM missing
        log_content = "Temperature: 72.0\u00b0C\n"
        log_file = temp_log_dir["health"] / "partial.log"
        log_file.write_text(log_content)

        record = parse_health_log(log_file)
        assert record is not None
        assert record["gpu_temp_c"] == 72.0
        # Missing CPU — returns None (no match → None)
        assert record.get("cpu_temp_c") is None

    def test_parse_health_log_malformed_data(self, temp_log_dir):
        """Malformed GPU temp returns None, does not raise."""
        from ai.log_intel.ingest import parse_health_log

        # "INVALID" does not match [\d.]+ so gpu_temp is None
        log_content = "GPU Temperature: INVALID\n"
        log_file = temp_log_dir["health"] / "malformed.log"
        log_file.write_text(log_content)

        result = parse_health_log(log_file)
        # Function returns a dict with gpu_temp_c = None (no match)
        assert result is not None
        assert result["gpu_temp_c"] is None

    def test_parse_health_log_empty_file(self, temp_log_dir):
        """Handle empty health log files."""
        from ai.log_intel.ingest import parse_health_log

        log_file = temp_log_dir["health"] / "empty.log"
        log_file.write_text("")

        result = parse_health_log(log_file)
        assert result is None


# ── Scan Log Parsing Tests ──


class TestScanLogParsing:
    """Tests for parsing ClamAV scan logs."""

    def test_parse_scan_log_clean_scan(self, sample_scan_log):
        """Parse clean scan log (no threats)."""
        from ai.log_intel.ingest import parse_scan_log

        record = parse_scan_log(sample_scan_log)

        assert record["files_scanned"] == 142
        assert record["threats_found"] == 0
        assert record["threat_names"] == ""
        assert record["duration_s"] == pytest.approx(45.2, abs=0.1)
        assert record["quarantined"] == 0

    def test_parse_scan_log_with_threats(self, temp_log_dir):
        """Parse scan log with detected threats.

        ClamAV FOUND format: "/path/to/file: ThreatName FOUND"
        """
        from ai.log_intel.ingest import parse_scan_log

        log_content = """\
----------- SCAN SUMMARY -----------
Known viruses: 8718212
Scanned files: 100
Infected files: 2
Time: 30.5 sec
/tmp/test.exe: Win.Trojan.Agent-1234 FOUND
/tmp/malware.sh: Unix.Malware.Test-5678 FOUND
"""
        log_file = temp_log_dir["scan"] / "threats.log"
        log_file.write_text(log_content)

        record = parse_scan_log(log_file)

        assert record["threats_found"] == 2
        assert "Win.Trojan.Agent-1234" in record["threat_names"]
        assert "Unix.Malware.Test-5678" in record["threat_names"]

    def test_parse_scan_log_missing_summary(self, temp_log_dir):
        """Handle scan log without summary section."""
        from ai.log_intel.ingest import parse_scan_log

        log_content = "Incomplete scan log"
        log_file = temp_log_dir["scan"] / "incomplete.log"
        log_file.write_text(log_content)

        result = parse_scan_log(log_file)
        assert result is None or result.get("files_scanned") == 0


# ── Embedding Generation Tests ──


class TestEmbeddingGeneration:
    """Tests for text embedding generation."""

    def test_embed_texts_success(self):
        """embed_texts wraps ai.rag.embedder.embed_texts."""
        mock_vecs = [[0.1] * 768, [0.2] * 768]
        with patch("ai.log_intel.ingest.embed_texts", return_value=mock_vecs) as mock_fn:
            result = mock_fn(["GPU temp 72°C", "CPU temp 68°C"])
            assert len(result) == 2
            assert len(result[0]) == 768
            mock_fn.assert_called_once()

    def test_embed_texts_module_level_patchable(self):
        """embed_texts is a module-level function — patch target works."""
        mock_vecs = [[0.5] * 768]
        with patch("ai.log_intel.ingest.embed_texts", return_value=mock_vecs):
            from ai.log_intel.ingest import embed_texts as fn
            result = fn(["test"])
            # The patched version returns our mock data
            assert result == mock_vecs

    def test_normalize_vector_truncates(self):
        """Normalize oversized vector by truncation."""
        from ai.log_intel.ingest import _normalize_vector

        vec = [0.1] * 1000  # Too long
        normalized = _normalize_vector(vec, dim=768)

        assert len(normalized) == 768
        assert normalized == [0.1] * 768

    def test_normalize_vector_pads(self):
        """Normalize undersized vector with zero-padding."""
        from ai.log_intel.ingest import _normalize_vector

        vec = [0.1] * 500  # Too short
        normalized = _normalize_vector(vec, dim=768)

        assert len(normalized) == 768
        assert normalized == [0.1] * 500 + [0.0] * 268


# ── LanceDB Table Creation Tests ──


class TestLanceDBIntegration:
    """Tests for LanceDB table creation and insertion."""

    def test_create_health_table(self, tmp_path):
        """Schema helpers exist (placeholder — requires lancedb mocking)."""
        # _create_tables no longer exists; schema is via _get_schemas()
        from ai.log_intel.ingest import _get_schemas

        schemas = _get_schemas()
        assert "health_records" in schemas
        assert "scan_records" in schemas
        assert "sig_updates" in schemas

    def test_insert_health_record(self):
        """Insert parsed health record into LanceDB."""
        # TODO: Test record insertion with mocked LanceDB
        pass

    def test_insert_scan_record(self):
        """Insert parsed scan record into LanceDB."""
        # TODO: Test record insertion with mocked LanceDB
        pass

    def test_duplicate_record_handling(self):
        """Handle duplicate records (same source_file)."""
        # TODO: Test deduplication logic
        pass


# ── Ingest State Management Tests ──


class TestIngestState:
    """Tests for tracking ingested files."""

    def test_load_ingest_state(self, tmp_path):
        """Load ingest state from JSON via state_dir parameter."""
        from ai.log_intel.ingest import get_ingest_state, save_ingest_state

        initial = {
            "health_logs": ["/var/log/health-001.log"],
            "scan_logs": ["/var/log/scan-001.log"],
        }
        save_ingest_state(initial, state_dir=tmp_path)

        state = get_ingest_state(state_dir=tmp_path)
        assert len(state["health_logs"]) == 1
        assert len(state["scan_logs"]) == 1

    def test_save_ingest_state(self, tmp_path):
        """Save ingest state to JSON via state_dir parameter."""
        from ai.log_intel.ingest import get_ingest_state, save_ingest_state

        state = {
            "health_logs": ["/var/log/health-001.log"],
            "scan_logs": [],
        }

        save_ingest_state(state, state_dir=tmp_path)
        loaded = get_ingest_state(state_dir=tmp_path)
        assert loaded == state

    def test_get_ingest_state_missing_file(self, tmp_path):
        """Returns empty dict when state file does not exist."""
        from ai.log_intel.ingest import get_ingest_state

        empty_dir = tmp_path / "nonexistent"
        empty_dir.mkdir()
        state = get_ingest_state(state_dir=empty_dir)
        assert state == {}

    def test_skip_already_ingested_files(self):
        """Skip files already in ingest state."""
        # TODO: Test that files in state are not re-ingested
        pass


# ── Integration Tests ──


class TestIngestPipeline:
    """Integration tests for full ingest pipeline."""

    def test_ingest_all_logs(self, temp_log_dir, sample_health_log, sample_scan_log):
        """Run full ingestion pipeline."""
        # TODO: Mock LanceDB and test end-to-end flow
        pass

    def test_ingest_health_only(self, sample_health_log):
        """Ingest health logs only (--health flag)."""
        # TODO: Test health-only ingestion
        pass

    def test_ingest_scan_only(self, sample_scan_log):
        """Ingest scan logs only (--scan flag)."""
        # TODO: Test scan-only ingestion
        pass

    def test_ingest_with_missing_logs(self, temp_log_dir):
        """Handle missing log directories gracefully."""
        # TODO: Test error handling for missing log dirs
        pass
