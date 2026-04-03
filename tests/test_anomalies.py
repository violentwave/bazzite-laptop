"""Test coverage for ai/log_intel/anomalies.py."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


class TestCheckAnomalies:
    """Test check_anomalies function."""

    def test_thermal_absolute_critical_gpu(self):
        """Detects GPU temp above TEMP_ABS_CRITICAL_C (90°C)."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "gpu_temp_c": 95.0,
            "cpu_temp_c": 60.0,
        }

        anomalies = check_anomalies(health_record=health_record)

        assert len(anomalies) == 1
        assert anomalies[0]["category"] == "thermal"
        assert anomalies[0]["severity"] == "critical"
        assert "GPU" in anomalies[0]["message"]

    def test_thermal_absolute_critical_cpu(self):
        """Detects CPU temp above TEMP_ABS_CRITICAL_C (90°C)."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "gpu_temp_c": 60.0,
            "cpu_temp_c": 92.0,
        }

        anomalies = check_anomalies(health_record=health_record)

        assert len(anomalies) == 1
        assert anomalies[0]["category"] == "thermal"
        assert "CPU" in anomalies[0]["message"]

    def test_thermal_spike_warning(self):
        """Detects temperature spike > TEMP_SPIKE_DELTA_C above 7-day average."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "gpu_temp_c": 80.0,
        }

        # Mock _recent_health_records to return history with lower avg
        history = [{"gpu_temp_c": 60.0} for _ in range(7)]

        with patch("ai.log_intel.anomalies._recent_health_records", return_value=history):
            anomalies = check_anomalies(health_record=health_record)

            # 80 - 60 = 20 > TEMP_SPIKE_DELTA_C (10)
            assert any(a["category"] == "thermal" and a["severity"] == "warning" for a in anomalies)

    def test_disk_fill_acceleration(self):
        """Detects disk usage jump > DISK_ACCEL_PCT."""
        from ai.log_intel.anomalies import check_anomalies

        current = {
            "id": "current-id",
            "disk_usage_pct": 80.0,
            "steam_usage_pct": 75.0,
        }

        previous = {
            "id": "prev-id",
            "disk_usage_pct": 70.0,
            "steam_usage_pct": 68.0,
        }

        with patch("ai.log_intel.anomalies._last_health_record", return_value=previous):
            anomalies = check_anomalies(health_record=current)

            # Root: 80 - 70 = 10 > DISK_ACCEL_PCT (5.0)
            # Steam: 75 - 68 = 7 > DISK_ACCEL_PCT (5.0)
            disk_anomalies = [a for a in anomalies if a["category"] == "disk"]
            assert len(disk_anomalies) == 2

    def test_failed_services_warning(self):
        """Detects services_down > 0."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "services_down": 3,
        }

        anomalies = check_anomalies(health_record=health_record)

        assert len(anomalies) == 1
        assert anomalies[0]["category"] == "service"
        assert anomalies[0]["severity"] == "warning"
        assert "3" in anomalies[0]["message"]

    def test_smart_failure_critical(self):
        """Detects SMART status != PASSED."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "smart_status": "FAILED",
        }

        anomalies = check_anomalies(health_record=health_record)

        assert len(anomalies) == 1
        assert anomalies[0]["category"] == "smart"
        assert anomalies[0]["severity"] == "critical"
        assert "FAILED" in anomalies[0]["message"]

    def test_threat_detected_critical(self):
        """Detects threats_found > 0 in scan records."""
        from ai.log_intel.anomalies import check_anomalies

        scan_record = {
            "id": "scan-id",
            "threats_found": 2,
            "threat_names": "Win32.Trojan, JS.Miner",
        }

        anomalies = check_anomalies(scan_record=scan_record)

        assert len(anomalies) == 1
        assert anomalies[0]["category"] == "threat"
        assert anomalies[0]["severity"] == "critical"
        assert "2 threat(s)" in anomalies[0]["message"]

    def test_no_anomalies_nominal_conditions(self):
        """Returns empty list when all conditions are nominal."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "gpu_temp_c": 60.0,
            "cpu_temp_c": 55.0,
            "disk_usage_pct": 50.0,
            "steam_usage_pct": 40.0,
            "services_down": 0,
            "smart_status": "PASSED",
        }

        with patch("ai.log_intel.anomalies._recent_health_records", return_value=[]):
            with patch("ai.log_intel.anomalies._last_health_record", return_value=None):
                anomalies = check_anomalies(health_record=health_record)

                assert len(anomalies) == 0

    def test_multiple_anomalies_same_record(self):
        """Detects multiple anomalies in a single record."""
        from ai.log_intel.anomalies import check_anomalies

        health_record = {
            "id": "test-id",
            "gpu_temp_c": 92.0,  # Critical
            "cpu_temp_c": 91.0,  # Critical
            "services_down": 2,  # Warning
            "smart_status": "FAILED",  # Critical
        }

        anomalies = check_anomalies(health_record=health_record)

        assert len(anomalies) == 4  # GPU, CPU, services, SMART


class TestStoreAnomalies:
    """Test store_anomalies function."""

    def test_store_anomalies_creates_table(self):
        """Creates anomalies table if it doesn't exist."""
        from ai.log_intel.anomalies import store_anomalies

        anomalies = [
            {
                "id": "test-id",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "category": "thermal",
                "severity": "warning",
                "message": "Test anomaly",
                "acknowledged": False,
                "source_record_id": "source-id",
            }
        ]

        with patch("ai.log_intel.anomalies._connect") as mock_connect:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.list_tables.return_value = []
            mock_db.create_table.return_value = mock_table

            store_anomalies(anomalies)

            mock_db.create_table.assert_called_once()
            mock_table.add.assert_called_once_with(anomalies)

    def test_store_anomalies_empty_list(self):
        """Does nothing when anomalies list is empty."""
        from ai.log_intel.anomalies import store_anomalies

        with patch("ai.log_intel.anomalies._connect") as mock_connect:
            store_anomalies([])

            mock_connect.assert_not_called()

    def test_store_anomalies_handles_db_errors(self):
        """Logs error and continues on database failure."""
        from ai.log_intel.anomalies import store_anomalies

        anomalies = [
            {
                "id": "test-id",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "category": "thermal",
                "severity": "warning",
                "message": "Test anomaly",
                "acknowledged": False,
                "source_record_id": "source-id",
            }
        ]

        with patch("ai.log_intel.anomalies._connect", side_effect=Exception("DB error")):
            # Should not raise, just log
            store_anomalies(anomalies)


class TestUpdateStatusFile:
    """Test update_status_file function."""

    def test_update_status_file_atomic_write(self, tmp_path):
        """Uses tempfile + rename for crash safety."""
        from ai.log_intel.anomalies import update_status_file

        anomalies = [
            {
                "id": "test-id",
                "timestamp": "2026-04-02T12:00:00Z",
                "category": "thermal",
                "severity": "warning",
                "message": "Test anomaly",
                "acknowledged": False,
                "source_record_id": "source-id",
            }
        ]

        status_file = tmp_path / ".status"

        with patch("ai.log_intel.anomalies.STATUS_FILE", status_file):
            update_status_file(anomalies)

            assert status_file.exists()

    def test_update_status_file_preserves_existing_keys(self, tmp_path):
        """Preserves ClamAV and health keys from existing status."""
        import json

        from ai.log_intel.anomalies import update_status_file

        status_file = tmp_path / ".status"
        existing = {
            "scan_type": "quick",
            "last_scan_time": "2026-04-01T10:00:00Z",
            "health_status": "ok",
        }
        status_file.write_text(json.dumps(existing))

        anomalies = [
            {
                "id": "test-id",
                "timestamp": "2026-04-02T12:00:00Z",
                "category": "thermal",
                "severity": "warning",
                "message": "Test anomaly",
                "acknowledged": False,
                "source_record_id": "source-id",
            }
        ]

        with patch("ai.log_intel.anomalies.STATUS_FILE", status_file):
            update_status_file(anomalies)

            updated = json.loads(status_file.read_text())

            # Original keys preserved
            assert updated["scan_type"] == "quick"
            assert updated["last_scan_time"] == "2026-04-01T10:00:00Z"

            # New keys added
            assert updated["anomaly_count"] == 1
            assert updated["last_anomaly"] == "2026-04-02T12:00:00Z"

    def test_update_status_file_increments_count(self, tmp_path):
        """Increments anomaly_count on subsequent calls."""
        import json

        from ai.log_intel.anomalies import update_status_file

        status_file = tmp_path / ".status"
        existing = {"anomaly_count": 5}
        status_file.write_text(json.dumps(existing))

        anomalies = [
            {
                "id": "test-id-1",
                "timestamp": "2026-04-02T12:00:00Z",
                "category": "thermal",
                "severity": "warning",
                "message": "Test 1",
                "acknowledged": False,
                "source_record_id": "source-id",
            },
            {
                "id": "test-id-2",
                "timestamp": "2026-04-02T12:01:00Z",
                "category": "disk",
                "severity": "warning",
                "message": "Test 2",
                "acknowledged": False,
                "source_record_id": "source-id",
            },
        ]

        with patch("ai.log_intel.anomalies.STATUS_FILE", status_file):
            update_status_file(anomalies)

            updated = json.loads(status_file.read_text())

            assert updated["anomaly_count"] == 7  # 5 + 2

    def test_update_status_file_handles_corrupted_json(self, tmp_path):
        """Starts fresh when existing status is corrupted."""
        from ai.log_intel.anomalies import update_status_file

        status_file = tmp_path / ".status"
        status_file.write_text("{ invalid json")

        anomalies = [
            {
                "id": "test-id",
                "timestamp": "2026-04-02T12:00:00Z",
                "category": "thermal",
                "severity": "warning",
                "message": "Test anomaly",
                "acknowledged": False,
                "source_record_id": "source-id",
            }
        ]

        with patch("ai.log_intel.anomalies.STATUS_FILE", status_file):
            update_status_file(anomalies)

            # Should succeed with fresh status
            assert status_file.exists()


class TestGetUnacknowledged:
    """Test get_unacknowledged function."""

    def test_get_unacknowledged_filters_acknowledged(self):
        """Returns only anomalies where acknowledged is False."""
        import pandas as pd

        from ai.log_intel.anomalies import get_unacknowledged

        with patch("ai.log_intel.anomalies._connect") as mock_connect:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.list_tables.return_value = ["anomalies"]
            mock_db.open_table.return_value = mock_table

            df = pd.DataFrame(
                [
                    {"id": "1", "acknowledged": False, "message": "Unacked 1"},
                    {"id": "2", "acknowledged": True, "message": "Acked"},
                    {"id": "3", "acknowledged": False, "message": "Unacked 2"},
                ]
            )
            mock_table.to_pandas.return_value = df

            result = get_unacknowledged()

            assert len(result) == 2
            assert all(r["acknowledged"] is False for r in result)

    def test_get_unacknowledged_empty_table(self):
        """Returns empty list when no anomalies exist."""
        from ai.log_intel.anomalies import get_unacknowledged

        with patch("ai.log_intel.anomalies._connect") as mock_connect:
            mock_db = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.list_tables.return_value = []

            result = get_unacknowledged()

            assert result == []

    def test_get_unacknowledged_handles_db_errors(self):
        """Returns empty list on database errors."""
        from ai.log_intel.anomalies import get_unacknowledged

        with patch("ai.log_intel.anomalies._connect", side_effect=Exception("DB error")):
            result = get_unacknowledged()

            assert result == []


class TestAcknowledge:
    """Test acknowledge function."""

    def test_acknowledge_marks_anomaly_acknowledged(self):
        """Sets acknowledged=True for the specified anomaly ID."""
        import pandas as pd

        from ai.log_intel.anomalies import acknowledge

        with patch("ai.log_intel.anomalies._connect") as mock_connect:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.list_tables.return_value = ["anomalies"]
            mock_db.open_table.return_value = mock_table

            df = pd.DataFrame(
                [
                    {"id": "target-id", "acknowledged": False, "message": "Test"},
                    {"id": "other-id", "acknowledged": False, "message": "Other"},
                ]
            )
            mock_table.to_pandas.return_value = df

            acknowledge("target-id")

            # Should drop and recreate table with updated data
            mock_db.drop_table.assert_called_once_with("anomalies")
            mock_db.create_table.assert_called_once()

    def test_acknowledge_nonexistent_id(self):
        """Logs warning when ID not found."""
        import pandas as pd

        from ai.log_intel.anomalies import acknowledge

        with patch("ai.log_intel.anomalies._connect") as mock_connect:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.list_tables.return_value = ["anomalies"]
            mock_db.open_table.return_value = mock_table

            df = pd.DataFrame([{"id": "other-id", "acknowledged": False}])
            mock_table.to_pandas.return_value = df

            # Should not raise
            acknowledge("nonexistent-id")

    def test_acknowledge_handles_db_errors(self):
        """Logs error and continues on database failure."""
        from ai.log_intel.anomalies import acknowledge

        with patch("ai.log_intel.anomalies._connect", side_effect=Exception("DB error")):
            # Should not raise
            acknowledge("test-id")


class TestRunChecks:
    """Test run_checks entry point."""

    def test_run_checks_full_pipeline(self):
        """Runs detect, store, and update in sequence."""
        from ai.log_intel.anomalies import run_checks

        health_record = {
            "id": "test-id",
            "gpu_temp_c": 95.0,
        }

        with patch("ai.log_intel.anomalies.check_anomalies") as mock_check:
            with patch("ai.log_intel.anomalies.store_anomalies") as mock_store:
                with patch("ai.log_intel.anomalies.update_status_file") as mock_update:
                    mock_check.return_value = [
                        {
                            "id": "anom-id",
                            "timestamp": "2026-04-02T12:00:00Z",
                            "category": "thermal",
                            "severity": "critical",
                            "message": "GPU critical",
                            "acknowledged": False,
                            "source_record_id": "test-id",
                        }
                    ]

                    result = run_checks(health_record=health_record)

                    mock_check.assert_called_once_with(health_record, None)
                    mock_store.assert_called_once()
                    mock_update.assert_called_once()
                    assert len(result) == 1

    def test_run_checks_no_anomalies(self):
        """Skips store/update when no anomalies detected."""
        from ai.log_intel.anomalies import run_checks

        health_record = {"id": "test-id", "gpu_temp_c": 60.0}

        with patch("ai.log_intel.anomalies.check_anomalies", return_value=[]):
            with patch("ai.log_intel.anomalies.store_anomalies") as mock_store:
                with patch("ai.log_intel.anomalies.update_status_file") as mock_update:
                    result = run_checks(health_record=health_record)

                    mock_store.assert_not_called()
                    mock_update.assert_not_called()
                    assert result == []
