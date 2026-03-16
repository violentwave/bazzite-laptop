"""Unit tests for the RAG log chunker module.

Covers: scan log chunking, health log chunking, file auto-detection,
and enriched JSONL parsing. No real files are read from /var/log.
"""

import json

import pytest

from ai.rag.chunker import (
    chunk_enriched_jsonl,
    chunk_file,
    chunk_health_log,
    chunk_scan_log,
)

# ── Inline Fixtures ──

SAMPLE_SCAN_LOG = """\
/home/lch/.cache/suspicious.exe: Win.Trojan.Agent-123456 FOUND
/tmp/test-eicar.txt: Eicar-Signature FOUND

----------- SCAN SUMMARY -----------
Known viruses: 8719137
Engine version: 1.4.2
Scanned directories: 1542
Scanned files: 28403
Infected files: 2
Data scanned: 12840.23 MB
Time: 342.118 sec (5 m 42 s)
Start Date: 2026:03:15 02:00:01
End Date:   2026:03:15 02:05:43
"""

SAMPLE_HEALTH_LOG = """\
=== System Health Snapshot ===
Date: 2026-03-15 08:00:01

--- SMART Health ---
/dev/sda: PASSED (SSD, temp=38C)
/dev/sdb: PASSED (HDD, temp=34C)

--- GPU Status ---
Driver: 570.86.16
GPU Temp: 42C
VRAM Used: 512MB / 6144MB

--- CPU Thermals ---
Package: 48C
Core 0: 46C
Core 1: 47C
"""


@pytest.fixture()
def scan_log_file(tmp_path):
    """Write sample scan log to a temp file inside a clamav-scans dir."""
    scan_dir = tmp_path / "clamav-scans"
    scan_dir.mkdir()
    f = scan_dir / "scan-2026-03-15.log"
    f.write_text(SAMPLE_SCAN_LOG)
    return f


@pytest.fixture()
def health_log_file(tmp_path):
    """Write sample health log to a temp file inside a system-health dir."""
    health_dir = tmp_path / "system-health"
    health_dir.mkdir()
    f = health_dir / "health-2026-03-15.log"
    f.write_text(SAMPLE_HEALTH_LOG)
    return f


@pytest.fixture()
def enriched_jsonl_file(tmp_path):
    """Write sample enriched JSONL to a temp file."""
    lines = [
        json.dumps({
            "hash": "a" * 64,
            "source": "virustotal",
            "family": "trojan.eicar/test",
            "risk_level": "high",
            "timestamp": "2026-03-15T12:00:00+00:00",
        }),
        json.dumps({
            "hash": "b" * 64,
            "source": "otx",
            "family": "Emotet",
            "risk_level": "medium",
            "timestamp": "2026-03-14T10:00:00+00:00",
        }),
    ]
    f = tmp_path / "enriched.jsonl"
    f.write_text("\n".join(lines) + "\n")
    return f


# ── Scan Log Tests ──


class TestChunkScanLog:
    def test_sections_detected(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG, "/var/log/clamav-scans/scan.log")
        section_names = [c.section for c in chunks]
        assert "detections" in section_names
        assert "SCAN SUMMARY" in section_names

    def test_timestamp_extracted(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG)
        for chunk in chunks:
            assert chunk.timestamp == "2026:03:15 02:00:01"

    def test_detection_grouping(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG)
        det = [c for c in chunks if c.section == "detections"][0]
        assert "Win.Trojan.Agent-123456 FOUND" in det.content
        assert "Eicar-Signature FOUND" in det.content

    def test_summary_content(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG)
        summary = [c for c in chunks if c.section == "SCAN SUMMARY"][0]
        assert "Known viruses: 8719137" in summary.content
        assert "Infected files: 2" in summary.content

    def test_log_type_is_scan(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG)
        for chunk in chunks:
            assert chunk.log_type == "scan"

    def test_source_file_set(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG, "/var/log/scan.log")
        for chunk in chunks:
            assert chunk.source_file == "/var/log/scan.log"

    def test_empty_log_returns_empty(self):
        assert chunk_scan_log("") == []
        assert chunk_scan_log("   \n\n  ") == []

    def test_no_found_lines_no_detections_section(self):
        log = """\
----------- SCAN SUMMARY -----------
Known viruses: 100
Infected files: 0
Start Date: 2026:03:15 02:00:01
"""
        chunks = chunk_scan_log(log)
        section_names = [c.section for c in chunks]
        assert "detections" not in section_names
        assert "SCAN SUMMARY" in section_names

    def test_found_lines_not_duplicated_in_summary(self):
        chunks = chunk_scan_log(SAMPLE_SCAN_LOG)
        summary = [c for c in chunks if c.section == "SCAN SUMMARY"][0]
        assert "FOUND" not in summary.content


# ── Health Log Tests ──


class TestChunkHealthLog:
    def test_sections_detected(self):
        chunks = chunk_health_log(SAMPLE_HEALTH_LOG)
        section_names = [c.section for c in chunks]
        assert "SMART Health" in section_names
        assert "GPU Status" in section_names
        assert "CPU Thermals" in section_names

    def test_equals_delimiter_detected(self):
        chunks = chunk_health_log(SAMPLE_HEALTH_LOG)
        section_names = [c.section for c in chunks]
        assert "System Health Snapshot" in section_names

    def test_timestamp_extracted(self):
        chunks = chunk_health_log(SAMPLE_HEALTH_LOG)
        for chunk in chunks:
            assert chunk.timestamp == "2026-03-15 08:00:01"

    def test_log_type_is_health(self):
        chunks = chunk_health_log(SAMPLE_HEALTH_LOG)
        for chunk in chunks:
            assert chunk.log_type == "health"

    def test_section_content(self):
        chunks = chunk_health_log(SAMPLE_HEALTH_LOG)
        gpu = [c for c in chunks if c.section == "GPU Status"][0]
        assert "Driver: 570.86.16" in gpu.content
        assert "VRAM Used:" in gpu.content

    def test_empty_log_returns_empty(self):
        assert chunk_health_log("") == []

    def test_empty_section_filtered(self):
        log = """\
--- Empty Section ---
--- Next Section ---
Some content here
"""
        chunks = chunk_health_log(log)
        section_names = [c.section for c in chunks]
        assert "Empty Section" not in section_names
        assert "Next Section" in section_names


# ── File Auto-Detection Tests ──


class TestChunkFile:
    def test_scan_detected_by_path(self, scan_log_file):
        chunks = chunk_file(scan_log_file)
        assert len(chunks) > 0
        assert all(c.log_type == "scan" for c in chunks)

    def test_health_detected_by_path(self, health_log_file):
        chunks = chunk_file(health_log_file)
        assert len(chunks) > 0
        assert all(c.log_type == "health" for c in chunks)

    def test_scan_detected_by_content(self, tmp_path):
        f = tmp_path / "random.log"
        f.write_text(SAMPLE_SCAN_LOG)
        chunks = chunk_file(f)
        assert all(c.log_type == "scan" for c in chunks)

    def test_health_detected_by_content(self, tmp_path):
        f = tmp_path / "random.log"
        f.write_text(SAMPLE_HEALTH_LOG)
        chunks = chunk_file(f)
        assert all(c.log_type == "health" for c in chunks)

    def test_unknown_fallback(self, tmp_path):
        f = tmp_path / "mystery.log"
        f.write_text("just some random text\nnothing special")
        chunks = chunk_file(f)
        assert len(chunks) == 1
        assert chunks[0].section == "full"
        assert chunks[0].log_type == "unknown"

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.log"
        f.write_text("")
        chunks = chunk_file(f)
        assert chunks == []

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            chunk_file(tmp_path / "nonexistent.log")

    def test_source_file_populated(self, scan_log_file):
        chunks = chunk_file(scan_log_file)
        for chunk in chunks:
            assert chunk.source_file == str(scan_log_file)


# ── Enriched JSONL Tests ──


class TestChunkEnrichedJsonl:
    def test_parses_all_lines(self, enriched_jsonl_file):
        results = chunk_enriched_jsonl(enriched_jsonl_file)
        assert len(results) == 2

    def test_fields_populated(self, enriched_jsonl_file):
        results = chunk_enriched_jsonl(enriched_jsonl_file)
        first = results[0]
        assert first["hash"] == "a" * 64
        assert first["source"] == "virustotal"
        assert first["family"] == "trojan.eicar/test"
        assert first["risk_level"] == "high"
        assert first["timestamp"] == "2026-03-15T12:00:00+00:00"

    def test_content_generated(self, enriched_jsonl_file):
        results = chunk_enriched_jsonl(enriched_jsonl_file)
        first = results[0]
        assert "virustotal" in first["content"]
        assert "trojan.eicar/test" in first["content"]
        assert "high" in first["content"]
        # Hash should be truncated
        assert ("a" * 16 + "...") in first["content"]

    def test_uuid_generated(self, enriched_jsonl_file):
        results = chunk_enriched_jsonl(enriched_jsonl_file)
        for r in results:
            # Validate it looks like a UUID
            assert len(r["id"]) == 36
            assert r["id"].count("-") == 4

    def test_vector_empty(self, enriched_jsonl_file):
        results = chunk_enriched_jsonl(enriched_jsonl_file)
        for r in results:
            assert r["vector"] == []

    def test_malformed_lines_skipped(self, tmp_path):
        f = tmp_path / "bad.jsonl"
        f.write_text(
            json.dumps({"hash": "a" * 64, "source": "vt", "family": "X", "risk_level": "low"})
            + "\nNOT VALID JSON\n"
            + json.dumps({"hash": "b" * 64, "source": "otx", "family": "Y", "risk_level": "high"})
            + "\n"
        )
        results = chunk_enriched_jsonl(f)
        assert len(results) == 2

    def test_empty_lines_skipped(self, tmp_path):
        f = tmp_path / "sparse.jsonl"
        f.write_text(
            "\n"
            + json.dumps({"hash": "c" * 64, "source": "mb"})
            + "\n\n"
        )
        results = chunk_enriched_jsonl(f)
        assert len(results) == 1

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            chunk_enriched_jsonl(tmp_path / "missing.jsonl")

    def test_missing_fields_default(self, tmp_path):
        f = tmp_path / "minimal.jsonl"
        f.write_text(json.dumps({"hash": "d" * 64}) + "\n")
        results = chunk_enriched_jsonl(f)
        assert len(results) == 1
        assert results[0]["source"] == ""
        assert results[0]["family"] == ""
        assert results[0]["risk_level"] == "unknown"
        assert results[0]["timestamp"] == ""
