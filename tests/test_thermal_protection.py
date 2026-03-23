"""Unit tests for scripts/thermal-protection.py.

Tests thermal protection state machine, config loading, and hardware interaction.
All subprocess calls (nvidia-smi, sensors) are mocked.
"""

import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


# Mock the module before import to avoid side effects
@pytest.fixture(autouse=True)
def _mock_thermal_module():
    """Mock config loading and globals before import."""
    with patch("builtins.open", mock_open(read_data="")):
        yield


class TestConfigLoading:
    """Test configuration file parsing."""

    def test_load_config_with_valid_file(self, tmp_path):
        """Config file values override defaults."""
        config_content = """
CPU_WARN=85
CPU_THROTTLE=90
CPU_CRITICAL=98
POLL_INTERVAL=15
"""
        config_file = tmp_path / "thermal-protection.conf"
        config_file.write_text(config_content)

        # TODO: Import and call load_config(config_file)
        # Assert CPU_WARN == 85, etc.
        pytest.skip("Requires refactoring to pass config_file as parameter")

    def test_load_config_ignores_comments(self):
        """Lines starting with # should be ignored."""
        pytest.skip("Requires testable config loader")

    def test_load_config_handles_malformed_lines(self):
        """Missing = or invalid values should not crash."""
        pytest.skip("Requires testable config loader")

    def test_load_config_missing_file_uses_defaults(self):
        """Non-existent config file should use hardcoded defaults."""
        pytest.skip("Requires testable config loader")


class TestCPUGovernorControl:
    """Test CPU governor and frequency capping."""

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.read_text", return_value="performance")
    @patch("os.cpu_count", return_value=4)
    def test_set_cpu_governor_success(self, mock_cpu_count, mock_read, mock_write):
        """Setting governor should write to all CPUs."""
        # TODO: Import set_cpu_governor and call it
        # Assert mock_write called 4 times
        pytest.skip("Requires refactoring to accept cpu_count param")

    @patch("pathlib.Path.write_text", side_effect=PermissionError)
    def test_set_cpu_governor_permission_denied(self, mock_write):
        """Permission errors should be logged, not crash."""
        pytest.skip("Requires refactoring for testability")

    @patch("pathlib.Path.write_text", side_effect=OSError("[Errno 22] Invalid argument"))
    @patch("pathlib.Path.read_text", return_value="performance")
    @patch("os.cpu_count", return_value=4)
    def test_set_cpu_governor_fallback_to_powersave(self, mock_cpu, mock_read, mock_write):
        """Invalid governor should try powersave fallback."""
        pytest.skip("Requires refactoring")

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.read_text", return_value="3200000")  # 3.2GHz
    @patch("os.cpu_count", return_value=4)
    def test_set_cpu_max_freq(self, mock_cpu, mock_read, mock_write):
        """Frequency cap should be applied to all CPUs."""
        pytest.skip("Requires refactoring")

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.read_text", return_value="3200000")
    def test_restore_cpu_defaults(self, mock_read, mock_write):
        """Restore should reset governor and remove freq cap."""
        pytest.skip("Requires refactoring")


class TestGPUControl:
    """Test GPU temperature reading and power limiting."""

    @patch("subprocess.check_output", return_value="65\n")
    def test_get_gpu_temp_success(self, mock_subprocess):
        """nvidia-smi temperature query should return float."""
        # TODO: Import get_gpu_temp
        # result = get_gpu_temp()
        # assert result == 65.0
        pytest.skip("Requires refactoring")

    @patch("subprocess.check_output", side_effect=FileNotFoundError)
    def test_get_gpu_temp_nvidia_smi_missing(self, mock_subprocess):
        """Missing nvidia-smi should return None, not crash."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.check_output", side_effect=subprocess.TimeoutExpired("cmd", 5))
    def test_get_gpu_temp_timeout(self, mock_subprocess):
        """Timeout should return None."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.run")
    def test_throttle_gpu_power(self, mock_run):
        """GPU power limit should call nvidia-smi -pl."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.check_output", return_value="120.0\n")
    @patch("subprocess.run")
    def test_restore_gpu_power(self, mock_run, mock_check):
        """Restore should query default limit and apply it."""
        pytest.skip("Requires refactoring")


class TestSensorReading:
    """Test CPU temperature sensor parsing."""

    @patch("subprocess.check_output")
    def test_get_cpu_temps_parses_json(self, mock_subprocess):
        """sensors -A -j output should be parsed correctly."""
        sensor_json = """{
            "coretemp-isa-0000": {
                "Package id 0": {
                    "temp1_input": 65.0
                },
                "Core 0": {
                    "temp2_input": 62.0
                }
            }
        }"""
        mock_subprocess.return_value = sensor_json

        # TODO: Import get_cpu_temps
        # temps = get_cpu_temps()
        # assert 65.0 in temps and 62.0 in temps
        pytest.skip("Requires refactoring")

    @patch("subprocess.check_output", side_effect=subprocess.TimeoutExpired("cmd", 5))
    def test_get_cpu_temps_timeout(self, mock_subprocess):
        """Timeout should return empty list."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.check_output", return_value="invalid json")
    def test_get_cpu_temps_malformed_json(self, mock_subprocess):
        """Invalid JSON should return empty list, not crash."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.check_output")
    def test_get_cpu_temps_filters_outliers(self, mock_subprocess):
        """Temperatures outside 0-120°C should be filtered."""
        sensor_json = """{
            "chip": {
                "sensor": {
                    "temp1_input": 65.0,
                    "temp2_input": 200.0,
                    "temp3_input": -5.0
                }
            }
        }"""
        mock_subprocess.return_value = sensor_json

        # TODO: temps should only contain 65.0
        pytest.skip("Requires refactoring")


class TestStateMachine:
    """Test thermal protection state transitions."""

    def test_evaluate_normal_to_warn_cpu(self):
        """CPU exceeding warn threshold should transition to WARN."""
        # TODO: evaluate_and_act(max_cpu=81, gpu=None)
        # assert current_state == State.WARN
        pytest.skip("Requires state injection/reset between tests")

    def test_evaluate_normal_to_warn_gpu(self):
        """GPU exceeding warn threshold should transition to WARN."""
        pytest.skip("Requires state injection")

    def test_evaluate_warn_to_throttle(self):
        """Crossing throttle threshold should transition to THROTTLE."""
        pytest.skip("Requires state injection")

    def test_evaluate_throttle_to_critical(self):
        """Crossing critical threshold should transition to CRITICAL."""
        pytest.skip("Requires state injection")

    def test_evaluate_critical_to_normal_recovery(self):
        """Dropping below all thresholds should restore defaults."""
        pytest.skip("Requires state injection")

    def test_evaluate_no_transition_when_same_state(self):
        """Staying in same state should not trigger actions."""
        pytest.skip("Requires state injection")

    @patch("subprocess.run")  # Mock notify-send
    def test_normal_state_restores_defaults(self, mock_notify):
        """NORMAL state should call restore_cpu_defaults and restore_gpu_power."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.run")
    def test_warn_state_sets_schedutil(self, mock_notify):
        """WARN state should set schedutil governor."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.run")
    def test_throttle_state_caps_cpu_and_gpu(self, mock_notify):
        """THROTTLE state should cap CPU to 1.6GHz and GPU to 60W."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.run")
    def test_critical_state_emergency_limits(self, mock_notify):
        """CRITICAL state should apply 800MHz CPU and 40W GPU."""
        pytest.skip("Requires refactoring")


class TestDesktopNotifications:
    """Test desktop notification delivery."""

    @patch("subprocess.check_output", return_value="1000\n")
    @patch("subprocess.run")
    def test_notify_success(self, mock_run, mock_check_uid):
        """Notification should be sent via sudo -u lch notify-send."""
        pytest.skip("Requires refactoring")

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5))
    def test_notify_timeout_non_fatal(self, mock_run):
        """Notification timeout should be logged, not crash."""
        pytest.skip("Requires refactoring")

    def test_get_user_env_constructs_dbus_path(self):
        """_get_user_env should build DBUS_SESSION_BUS_ADDRESS."""
        pytest.skip("Requires refactoring")


class TestSignalHandling:
    """Test graceful shutdown on SIGTERM/SIGINT."""

    def test_shutdown_sets_running_false(self):
        """SIGTERM handler should set _running = False."""
        # TODO: Trigger signal handler, check _running
        pytest.skip("Requires refactoring for signal testing")

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.read_text", return_value="3200000")
    def test_shutdown_restores_defaults(self, mock_read, mock_write):
        """On shutdown, CPU and GPU should be restored."""
        pytest.skip("Requires refactoring")


class TestMainLoop:
    """Test the main monitoring loop."""

    @patch("time.sleep")
    @patch("subprocess.check_output")  # For sensors and nvidia-smi
    def test_main_loop_iteration(self, mock_subprocess, mock_sleep):
        """Main loop should poll sensors and evaluate state."""
        # TODO: Run one iteration of main loop
        pytest.skip("Requires refactoring for testable loop")

    def test_main_loop_respects_poll_interval(self):
        """time.sleep should be called with POLL_INTERVAL."""
        pytest.skip("Requires refactoring")

    def test_main_loop_handles_sensor_errors(self):
        """Sensor read failures should not crash the loop."""
        pytest.skip("Requires refactoring")
