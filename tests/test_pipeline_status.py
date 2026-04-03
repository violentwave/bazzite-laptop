"""Tests for ai/system/pipeline_status.py."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestPipelineStatus:
    @pytest.fixture
    def mock_vector_db_dir(self, tmp_path):
        """Create a temporary vector-db directory with state files."""
        vector_db = tmp_path / "vector-db"
        vector_db.mkdir()
        return vector_db

    @pytest.fixture
    def mock_log_dirs(self, tmp_path):
        """Create temporary log directories."""
        health_dir = tmp_path / "system-health"
        scan_dir = tmp_path / "clamav-scans"
        health_dir.mkdir()
        scan_dir.mkdir()
        return health_dir, scan_dir

    def test_pipeline_status_healthy(self, mock_vector_db_dir, mock_log_dirs):
        """Mock recent timestamps, verify status is healthy."""
        health_dir, scan_dir = mock_log_dirs
        now = datetime.now(UTC)

        # Recent ingest times (within 8 days)
        recent_health = (now - timedelta(days=2)).isoformat()
        recent_scan = (now - timedelta(days=1)).isoformat()
        recent_archive = (now - timedelta(days=3)).isoformat()

        ingest_state = {
            "last_health_ingest": recent_health,
            "last_health_file": "health-test.log",
            "last_scan_ingest": recent_scan,
            "last_scan_file": "scan-test.log",
        }

        archive_state = {
            "last_archive_run": recent_archive,
            "total_archived": 42,
            "total_bytes_archived": 567890,
        }

        with patch("ai.system.pipeline_status.VECTOR_DB_DIR", mock_vector_db_dir):
            with patch("ai.system.pipeline_status._HEALTH_LOG_DIR", health_dir):
                with patch("ai.system.pipeline_status._SCAN_LOG_DIR", scan_dir):
                    # Write state files
                    (mock_vector_db_dir / ".ingest-state.json").write_text(json.dumps(ingest_state))
                    (mock_vector_db_dir / ".archive-state.json").write_text(
                        json.dumps(archive_state)
                    )

                    # Create a mock lancedb module
                    mock_table = MagicMock()
                    mock_table.count_rows.return_value = 10

                    mock_db = MagicMock()
                    mock_db.table_names.return_value = [
                        "health_records",
                        "scan_records",
                        "security_logs",
                    ]
                    mock_db.open_table.return_value = mock_table

                    # Patch at the point of import in the function
                    with patch("lancedb.connect", return_value=mock_db):
                        from ai.system.pipeline_status import get_pipeline_status

                        result = get_pipeline_status()

        assert result["status"] == "healthy"
        assert "ingest" in result
        assert "archive" in result
        assert "retention" in result
        assert "tables" in result
        assert result["archive"]["total_archived"] == 42

    def test_pipeline_status_stale(self, mock_vector_db_dir, mock_log_dirs):
        """Mock old timestamps (> 8 days), verify status is stale."""
        health_dir, scan_dir = mock_log_dirs
        now = datetime.now(UTC)

        # Old timestamps (> 8 days)
        old_health = (now - timedelta(days=10)).isoformat()
        old_scan = (now - timedelta(days=9)).isoformat()
        old_archive = (now - timedelta(days=12)).isoformat()

        ingest_state = {
            "last_health_ingest": old_health,
            "last_health_file": "health-old.log",
            "last_scan_ingest": old_scan,
            "last_scan_file": "scan-old.log",
        }

        archive_state = {
            "last_archive_run": old_archive,
            "total_archived": 100,
            "total_bytes_archived": 1000000,
        }

        with patch("ai.system.pipeline_status.VECTOR_DB_DIR", mock_vector_db_dir):
            with patch("ai.system.pipeline_status._HEALTH_LOG_DIR", health_dir):
                with patch("ai.system.pipeline_status._SCAN_LOG_DIR", scan_dir):
                    (mock_vector_db_dir / ".ingest-state.json").write_text(json.dumps(ingest_state))
                    (mock_vector_db_dir / ".archive-state.json").write_text(
                        json.dumps(archive_state)
                    )

                    from ai.system.pipeline_status import get_pipeline_status

                    result = get_pipeline_status()

        assert result["status"] == "stale"

    def test_pipeline_status_missing_state(self, mock_vector_db_dir, mock_log_dirs):
        """Mock missing state files, verify status is error without crash."""
        health_dir, scan_dir = mock_log_dirs

        with patch("ai.system.pipeline_status.VECTOR_DB_DIR", mock_vector_db_dir):
            with patch("ai.system.pipeline_status._HEALTH_LOG_DIR", health_dir):
                with patch("ai.system.pipeline_status._SCAN_LOG_DIR", scan_dir):
                    from ai.system.pipeline_status import get_pipeline_status

                    result = get_pipeline_status()

        assert result["status"] == "error"
        assert "ingest" in result
        assert "archive" in result

    def test_pipeline_status_pending_files(self, mock_vector_db_dir, mock_log_dirs):
        """Create temp log files newer than mock ingest, verify in pending_files."""
        health_dir, scan_dir = mock_log_dirs
        now = datetime.now(UTC)

        # Recent ingest time
        recent = (now - timedelta(hours=1)).isoformat()

        ingest_state = {
            "last_health_ingest": recent,
            "last_health_file": "health-old.log",
            "last_scan_ingest": recent,
            "last_scan_file": "scan-old.log",
        }

        archive_state = {
            "last_archive_run": recent,
            "total_archived": 1,
            "total_bytes_archived": 100,
        }

        with patch("ai.system.pipeline_status.VECTOR_DB_DIR", mock_vector_db_dir):
            with patch("ai.system.pipeline_status._HEALTH_LOG_DIR", health_dir):
                with patch("ai.system.pipeline_status._SCAN_LOG_DIR", scan_dir):
                    (mock_vector_db_dir / ".ingest-state.json").write_text(json.dumps(ingest_state))
                    (mock_vector_db_dir / ".archive-state.json").write_text(
                        json.dumps(archive_state)
                    )

                    # Create log files with current mtime (newer than recent ingest)
                    health_file = health_dir / "health-new.log"
                    health_file.touch()

                    scan_file = scan_dir / "scan-new.log"
                    scan_file.touch()

                    from ai.system.pipeline_status import get_pipeline_status

                    result = get_pipeline_status()

        assert result["status"] == "healthy"
        assert result["ingest"]["pending_count"] >= 1
        pending = result["ingest"]["pending_files"]
        assert "health-new.log" in pending or "scan-new.log" in pending
