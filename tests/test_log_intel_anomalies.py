"""Unit tests for ai/log_intel/anomalies.py — anomaly detection."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from ai.log_intel.anomalies import (
    acknowledge,
    detect_anomalies,
    get_unacknowledged,
    run_checks,
    store_anomalies,
    update_status_file,
)


class TestAnomalyDetection:
    """Core anomaly detection logic tests."""

    def test_thermal_absolute_critical_gpu(self):
        """GPU temperature exceeding absolute threshold triggers critical anomaly."""
        record = {
            "id": "test-1",
            "gpu_temp_c": 95.0,
            "cpu_temp_c": 60.0,
        }
        anomalies = detect_anomalies(record, record_type="health")

        assert len(anomalies) >= 1
        thermal = [a for a in anomalies if a["category"] == "thermal"]
        assert len(thermal) >= 1
        assert thermal[0]["severity"] == "critical"
        assert "GPU" in thermal[0]["message"]
        assert "95" in thermal[0]["message"]

    def test_thermal_absolute_critical_cpu(self):
        """CPU temperature exceeding absolute threshold triggers critical anomaly."""
        record = {
            "id": "test-2",
            "gpu_temp_c": 60.0,
            "cpu_temp_c": 92.0,
        }
        anomalies = detect_anomalies(record, record_type="health")

        thermal = [
            a for a in anomalies if a["category"] == "thermal" and a["severity"] == "critical"
        ]
        assert len(thermal) >= 1
        assert "CPU" in thermal[0]["message"]

    def test_disk_fill_acceleration_triggers_warning(self):
        """Rapid disk usage increase triggers disk anomaly."""
        previous = {
            "id": "prev-1",
            "disk_usage_pct": 50.0,
            "steam_usage_pct": 30.0,
        }
        current = {
            "id": "current-1",
            "disk_usage_pct": 57.0,  # +7% jump
            "steam_usage_pct": 30.0,
        }
        anomalies = detect_anomalies(current, record_type="health", previous=previous)

        disk_anomalies = [a for a in anomalies if a["category"] == "disk"]
        assert len(disk_anomalies) >= 1
        assert "Root" in disk_anomalies[0]["message"]
        assert disk_anomalies[0]["severity"] == "warning"

    def test_disk_no_anomaly_under_threshold(self):
        """Small disk usage changes don't trigger anomalies."""
        previous = {"id": "prev-1", "disk_usage_pct": 50.0}
        current = {"id": "current-1", "disk_usage_pct": 52.0}  # +2%, below threshold

        anomalies = detect_anomalies(current, record_type="health", previous=previous)
        disk_anomalies = [a for a in anomalies if a["category"] == "disk"]

        assert len(disk_anomalies) == 0

    def test_failed_services_triggers_warning(self):
        """Failed systemd services trigger service anomaly."""
        record = {
            "id": "test-3",
            "services_down": 2,
        }
        anomalies = detect_anomalies(record, record_type="health")

        service_anomalies = [a for a in anomalies if a["category"] == "service"]
        assert len(service_anomalies) == 1
        assert "2" in service_anomalies[0]["message"]
        assert "service(s)" in service_anomalies[0]["message"]

    def test_smart_failure_triggers_critical(self):
        """SMART self-test failure triggers critical anomaly."""
        record = {
            "id": "test-4",
            "smart_status": "FAILED",
        }
        anomalies = detect_anomalies(record, record_type="health")

        smart_anomalies = [a for a in anomalies if a["category"] == "smart"]
        assert len(smart_anomalies) == 1
        assert smart_anomalies[0]["severity"] == "critical"
        assert "FAILED" in smart_anomalies[0]["message"]

    def test_smart_passed_no_anomaly(self):
        """PASSED SMART status doesn't trigger anomaly."""
        record = {"id": "test-5", "smart_status": "PASSED"}
        anomalies = detect_anomalies(record, record_type="health")

        smart_anomalies = [a for a in anomalies if a["category"] == "smart"]
        assert len(smart_anomalies) == 0

    def test_threat_detection_scan_record(self):
        """Threats found in scan record trigger critical anomaly."""
        record = {
            "id": "scan-1",
            "threats_found": 3,
            "threat_names": "Trojan.Generic, Backdoor.SSH, Malware.Test",
        }
        anomalies = detect_anomalies(record, record_type="scan")

        threat_anomalies = [a for a in anomalies if a["category"] == "threat"]
        assert len(threat_anomalies) == 1
        assert threat_anomalies[0]["severity"] == "critical"
        assert "3" in threat_anomalies[0]["message"]
        assert "Trojan" in threat_anomalies[0]["message"]

    def test_no_anomalies_clean_record(self):
        """Clean health record produces no anomalies."""
        record = {
            "id": "clean-1",
            "gpu_temp_c": 65.0,
            "cpu_temp_c": 55.0,
            "disk_usage_pct": 45.0,
            "services_down": 0,
            "smart_status": "PASSED",
        }
        anomalies = detect_anomalies(record, record_type="health")

        assert len(anomalies) == 0

    def test_anomaly_structure(self):
        """Anomaly records have correct structure."""
        record = {"id": "test-6", "gpu_temp_c": 95.0}
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
        assert a["source_record_id"] == "test-6"


class TestAnomalyStorage:
    """Anomaly storage and persistence tests."""

    @patch("ai.log_intel.anomalies._connect")
    def test_store_anomalies_creates_table(self, mock_connect):
        """store_anomalies creates LanceDB table and adds records."""
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.list_tables.return_value = []
        mock_db.create_table.return_value = mock_table
        mock_connect.return_value = mock_db

        anomalies = [
            {
                "id": "a1",
                "timestamp": datetime.now(UTC).isoformat(),
                "category": "thermal",
                "severity": "critical",
                "message": "Test anomaly",
                "acknowledged": False,
                "source_record_id": "src-1",
            }
        ]

        store_anomalies(anomalies)

        mock_db.create_table.assert_called_once()
        mock_table.add.assert_called_once_with(anomalies)

    @patch("ai.log_intel.anomalies._connect")
    def test_store_anomalies_empty_list_noop(self, mock_connect):
        """Empty anomaly list is a no-op."""
        store_anomalies([])

        mock_connect.assert_not_called()

    def test_update_status_file_creates_file(self, tmp_path):
        """update_status_file creates status JSON file atomically."""
        import ai.log_intel.anomalies as anom_module

        original = anom_module.STATUS_FILE
        anom_module.STATUS_FILE = tmp_path / ".status"

        try:
            anomalies = [
                {
                    "id": "a1",
                    "timestamp": "2026-03-31T10:00:00Z",
                    "message": "Test anomaly message",
                }
            ]
            update_status_file(anomalies)

            assert (tmp_path / ".status").exists()
            status = json.loads((tmp_path / ".status").read_text())

            assert status["anomaly_count"] == 1
            assert status["last_anomaly"] == "2026-03-31T10:00:00Z"
            assert status["last_anomaly_message"] == "Test anomaly message"
        finally:
            anom_module.STATUS_FILE = original

    def test_update_status_file_preserves_existing_keys(self, tmp_path):
        """update_status_file preserves non-anomaly keys in status file."""
        import ai.log_intel.anomalies as anom_module

        original = anom_module.STATUS_FILE
        status_file = tmp_path / ".status"
        anom_module.STATUS_FILE = status_file

        try:
            # Pre-populate with other keys
            status_file.write_text(
                json.dumps(
                    {
                        "scan_status": "completed",
                        "scan_time": "2026-03-30T08:00:00Z",
                        "anomaly_count": 5,
                    }
                )
            )

            anomalies = [
                {
                    "id": "a2",
                    "timestamp": "2026-03-31T12:00:00Z",
                    "message": "New anomaly",
                }
            ]
            update_status_file(anomalies)

            status = json.loads(status_file.read_text())

            # Check preservation
            assert status["scan_status"] == "completed"
            assert status["scan_time"] == "2026-03-30T08:00:00Z"
            # Check updates
            assert status["anomaly_count"] == 6  # 5 + 1
            assert status["last_anomaly"] == "2026-03-31T12:00:00Z"
        finally:
            anom_module.STATUS_FILE = original


class TestAnomalyQueries:
    """Anomaly query and acknowledgment tests."""

    @patch("ai.log_intel.anomalies._connect")
    def test_get_unacknowledged_filters_correctly(self, mock_connect):
        """get_unacknowledged returns only unacknowledged anomalies."""
        import pandas as pd

        mock_db = MagicMock()
        mock_table = MagicMock()

        df = pd.DataFrame(
            [
                {"id": "a1", "acknowledged": False, "message": "Unacked 1"},
                {"id": "a2", "acknowledged": True, "message": "Acked"},
                {"id": "a3", "acknowledged": False, "message": "Unacked 2"},
            ]
        )
        mock_table.to_pandas.return_value = df
        mock_db.list_tables.return_value = ["anomalies"]
        mock_db.open_table.return_value = mock_table
        mock_connect.return_value = mock_db

        result = get_unacknowledged()

        assert len(result) == 2
        assert all(not r["acknowledged"] for r in result)

    @patch("ai.log_intel.anomalies._connect")
    def test_acknowledge_marks_anomaly(self, mock_connect):
        """acknowledge() marks a single anomaly as acknowledged."""
        import pandas as pd

        mock_db = MagicMock()
        mock_table = MagicMock()

        df = pd.DataFrame(
            [
                {"id": "a1", "acknowledged": False},
                {"id": "a2", "acknowledged": False},
            ]
        )
        mock_table.to_pandas.return_value = df.copy()
        mock_db.list_tables.return_value = ["anomalies"]
        mock_db.open_table.return_value = mock_table
        mock_db.create_table.return_value = MagicMock()
        mock_connect.return_value = mock_db

        acknowledge("a1")

        # Verify table was recreated with updated data
        mock_db.drop_table.assert_called_once_with("anomalies")
        mock_db.create_table.assert_called_once()


class TestIntegration:
    """Integration tests for full anomaly workflow."""

    @patch("ai.log_intel.anomalies.store_anomalies")
    @patch("ai.log_intel.anomalies.update_status_file")
    def test_run_checks_detects_and_stores(self, mock_update, mock_store):
        """run_checks detects anomalies and stores them."""
        health_record = {
            "id": "h1",
            "gpu_temp_c": 95.0,
            "smart_status": "FAILED",
        }

        anomalies = run_checks(health_record=health_record)

        # Should detect both thermal and SMART anomalies
        assert len(anomalies) >= 2

        # Verify storage was called
        mock_store.assert_called_once()
        mock_update.assert_called_once()

    @patch("ai.log_intel.anomalies.store_anomalies")
    @patch("ai.log_intel.anomalies.update_status_file")
    def test_run_checks_clean_record_no_storage(self, mock_update, mock_store):
        """run_checks with clean record doesn't call storage."""
        health_record = {
            "id": "h2",
            "gpu_temp_c": 60.0,
            "cpu_temp_c": 50.0,
            "smart_status": "PASSED",
            "services_down": 0,
        }

        anomalies = run_checks(health_record=health_record)

        assert len(anomalies) == 0
        mock_store.assert_not_called()
        mock_update.assert_not_called()


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_none_temperature_values(self):
        """None temperature values don't crash."""
        record = {
            "id": "test-7",
            "gpu_temp_c": None,
            "cpu_temp_c": None,
        }
        anomalies = detect_anomalies(record, record_type="health")

        # Should not crash, should produce no thermal anomalies
        thermal = [a for a in anomalies if a["category"] == "thermal"]
        assert len(thermal) == 0

    def test_missing_disk_usage_fields(self):
        """Missing disk usage fields don't crash."""
        previous = {"id": "prev", "disk_usage_pct": 50.0}
        current = {"id": "curr"}  # Missing disk_usage_pct

        anomalies = detect_anomalies(current, record_type="health", previous=previous)

        # Should not crash
        assert isinstance(anomalies, list)

    def test_zero_services_down_no_anomaly(self):
        """Zero services down doesn't trigger anomaly."""
        record = {"id": "test-8", "services_down": 0}
        anomalies = detect_anomalies(record, record_type="health")

        service_anomalies = [a for a in anomalies if a["category"] == "service"]
        assert len(service_anomalies) == 0

    def test_zero_threats_no_anomaly(self):
        """Zero threats in scan record doesn't trigger anomaly."""
        record = {"id": "scan-2", "threats_found": 0}
        anomalies = detect_anomalies(record, record_type="scan")

        threat_anomalies = [a for a in anomalies if a["category"] == "threat"]
        assert len(threat_anomalies) == 0

    @patch("ai.log_intel.anomalies._connect", side_effect=RuntimeError("DB unavailable"))
    def test_storage_failure_graceful(self, mock_connect):
        """Storage failure is handled gracefully."""
        anomalies = [{"id": "a1", "message": "Test"}]

        # Should not raise
        store_anomalies(anomalies)

    def test_malformed_status_file_recovers(self, tmp_path):
        """Malformed status file is overwritten gracefully."""
        import ai.log_intel.anomalies as anom_module

        original = anom_module.STATUS_FILE
        status_file = tmp_path / ".status"
        anom_module.STATUS_FILE = status_file

        try:
            # Write malformed JSON
            status_file.write_text("not valid json{")

            anomalies = [
                {
                    "id": "a1",
                    "timestamp": "2026-03-31T10:00:00Z",
                    "message": "Recovery test",
                }
            ]
            update_status_file(anomalies)

            # Should recover and write valid JSON
            status = json.loads(status_file.read_text())
            assert status["anomaly_count"] == 1
        finally:
            anom_module.STATUS_FILE = original
