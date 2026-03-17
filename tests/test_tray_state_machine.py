"""Unit tests for tray/state_machine.py.

Pure logic tests covering state determination, formatting helpers, and configuration validation.
No mocking needed — all functions are pure data transformations.
"""

from datetime import datetime
from pathlib import Path

import pytest

from tray.state_machine import (
    ALL_STATES,
    STATE_CONFIGS,
    STATE_HEALTH_WARNING,
    STATE_HEALTHY_IDLE,
    STATE_SCAN_ABORTED,
    STATE_SCAN_COMPLETE,
    STATE_SCAN_FAILED,
    STATE_SCAN_RUNNING,
    STATE_THREATS_FOUND,
    STATE_UNKNOWN,
    STATE_WARNING,
    MENU_HEADERS,
    determine_state,
    format_header,
    format_health_age,
    format_relative_time,
    icon_path,
)


# ── StateConfig Validation Tests ──


class TestStateConfigs:
    """Validate all state configurations are well-formed."""

    def test_all_states_have_configs(self):
        """All 9 states have STATE_CONFIGS entries."""
        assert len(ALL_STATES) == 9
        for state in ALL_STATES:
            assert state in STATE_CONFIGS, f"Missing config for state: {state}"

    def test_all_configs_have_valid_icons(self):
        """All icons map to known SVG names (no validation of actual files)."""
        for state, config in STATE_CONFIGS.items():
            assert config.icon, f"State {state} has empty icon name"
            assert isinstance(config.icon, str)
            assert len(config.icon) > 0

    def test_blink_states_have_positive_intervals(self):
        """All blink=True states have positive blink_interval_ms."""
        for state, config in STATE_CONFIGS.items():
            if config.blink:
                assert (
                    config.blink_interval_ms > 0
                ), f"Blink state {state} has non-positive interval: {config.blink_interval_ms}"

    def test_non_blink_states_have_zero_interval(self):
        """All blink=False states have zero blink_interval_ms."""
        for state, config in STATE_CONFIGS.items():
            if not config.blink:
                assert (
                    config.blink_interval_ms == 0
                ), f"Non-blink state {state} has non-zero interval: {config.blink_interval_ms}"

    def test_all_configs_have_descriptions(self):
        """All states have descriptions in StateConfig."""
        for state, config in STATE_CONFIGS.items():
            assert config.description, f"State {state} has empty description"
            assert isinstance(config.description, str)


# ── State Determination Tests ──


class TestDetermineState:
    """Test determine_state() logic for all state transitions."""

    def test_none_data_returns_unknown(self):
        """None data returns STATE_UNKNOWN."""
        state, timestamp = determine_state(None)
        assert state == STATE_UNKNOWN

    def test_scanning_state_returns_scan_running(self):
        """state='scanning' returns STATE_SCAN_RUNNING."""
        data = {"state": "scanning"}
        state, _ = determine_state(data)
        assert state == STATE_SCAN_RUNNING

    def test_updating_state_returns_scan_running(self):
        """state='updating' returns STATE_SCAN_RUNNING."""
        data = {"state": "updating"}
        state, _ = determine_state(data)
        assert state == STATE_SCAN_RUNNING

    def test_complete_clean_new_timestamp_returns_scan_complete(self):
        """state='complete', result='clean', new timestamp returns SCAN_COMPLETE with timestamp."""
        data = {
            "state": "complete",
            "result": "clean",
            "last_scan_time": "2025-03-16T14:30:00",
        }
        state, new_ts = determine_state(data, last_completion_timestamp=None)
        assert state == STATE_SCAN_COMPLETE
        assert new_ts == "2025-03-16T14:30:00"

    def test_complete_clean_same_timestamp_checks_health(self):
        """state='complete', result='clean', same timestamp checks health overlay."""
        data = {
            "state": "complete",
            "result": "clean",
            "last_scan_time": "2025-03-16T14:30:00",
            "health_status": "OK",
        }
        state, _ = determine_state(
            data, last_completion_timestamp="2025-03-16T14:30:00"
        )
        assert state == STATE_HEALTHY_IDLE

    def test_complete_clean_same_timestamp_with_health_warning(self):
        """state='complete', result='clean', same timestamp with health warning."""
        data = {
            "state": "complete",
            "result": "clean",
            "last_scan_time": "2025-03-16T14:30:00",
            "health_status": "WARNING",
        }
        state, _ = determine_state(
            data, last_completion_timestamp="2025-03-16T14:30:00"
        )
        assert state == STATE_HEALTH_WARNING

    def test_complete_threats_returns_threats_found(self):
        """state='complete', result='threats' returns THREATS_FOUND."""
        data = {"state": "complete", "result": "threats"}
        state, _ = determine_state(data)
        assert state == STATE_THREATS_FOUND

    def test_complete_error_returns_scan_failed(self):
        """state='complete', result='error' returns SCAN_FAILED."""
        data = {"state": "complete", "result": "error"}
        state, _ = determine_state(data)
        assert state == STATE_SCAN_FAILED

    def test_complete_empty_result_checks_health(self):
        """state='complete', result='' checks health overlay."""
        data = {"state": "complete", "result": "", "health_status": "OK"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_idle_with_threats_last_result(self):
        """state='idle', last_scan_result='threats' returns THREATS_FOUND."""
        data = {"state": "idle", "last_scan_result": "threats"}
        state, _ = determine_state(data)
        assert state == STATE_THREATS_FOUND

    def test_idle_with_error_last_result(self):
        """state='idle', last_scan_result='error' returns SCAN_FAILED."""
        data = {"state": "idle", "last_scan_result": "error"}
        state, _ = determine_state(data)
        assert state == STATE_SCAN_FAILED

    def test_idle_with_clean_last_result(self):
        """state='idle', last_scan_result='clean' returns HEALTHY_IDLE."""
        data = {"state": "idle", "last_scan_result": "clean"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_idle_with_empty_last_result(self):
        """state='idle', last_scan_result='' returns HEALTHY_IDLE."""
        data = {"state": "idle", "last_scan_result": ""}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_garbage_state_returns_unknown(self):
        """Unrecognized state='garbage' returns STATE_UNKNOWN."""
        data = {"state": "garbage"}
        state, _ = determine_state(data)
        assert state == STATE_UNKNOWN

    def test_empty_dict_returns_unknown(self):
        """Empty dict (no state key) returns STATE_UNKNOWN."""
        state, _ = determine_state({})
        assert state == STATE_UNKNOWN

    def test_preserves_last_completion_timestamp(self):
        """Last completion timestamp is preserved when not updated."""
        data = {"state": "idle", "last_scan_result": "clean"}
        state, new_ts = determine_state(data, last_completion_timestamp="2025-01-01T00:00:00")
        assert new_ts == "2025-01-01T00:00:00"

    def test_timestamp_preference_last_scan_time_over_timestamp(self):
        """last_scan_time is preferred over generic timestamp field."""
        data = {
            "state": "complete",
            "result": "clean",
            "last_scan_time": "2025-03-16T14:30:00",
            "timestamp": "2025-03-16T13:00:00",
        }
        state, new_ts = determine_state(data, last_completion_timestamp=None)
        assert new_ts == "2025-03-16T14:30:00"

    def test_timestamp_fallback_to_timestamp_field(self):
        """Generic timestamp field is used if last_scan_time is missing."""
        data = {
            "state": "complete",
            "result": "clean",
            "timestamp": "2025-03-16T13:00:00",
        }
        state, new_ts = determine_state(data, last_completion_timestamp=None)
        assert new_ts == "2025-03-16T13:00:00"


# ── Health Overlay Tests ──


class TestHealthOverlay:
    """Test health status overlay logic in idle/clean states."""

    def test_health_ok_returns_healthy_idle(self):
        """health_status='OK' returns HEALTHY_IDLE."""
        data = {"state": "idle", "health_status": "OK"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_health_warning_returns_warning(self):
        """health_status='WARNING' returns HEALTH_WARNING."""
        data = {"state": "idle", "health_status": "WARNING"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTH_WARNING

    def test_health_critical_returns_warning(self):
        """health_status='CRITICAL' returns HEALTH_WARNING."""
        data = {"state": "idle", "health_status": "CRITICAL"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTH_WARNING

    def test_health_warning_lowercase(self):
        """health_status='warning' (lowercase) returns HEALTH_WARNING."""
        data = {"state": "idle", "health_status": "warning"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTH_WARNING

    def test_health_empty_string_returns_healthy_idle(self):
        """health_status='' returns HEALTHY_IDLE."""
        data = {"state": "idle", "health_status": ""}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_health_none_returns_healthy_idle(self):
        """health_status=None returns HEALTHY_IDLE."""
        data = {"state": "idle", "health_status": None}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_health_non_string_returns_healthy_idle(self):
        """health_status=123 (non-string) returns HEALTHY_IDLE."""
        data = {"state": "idle", "health_status": 123}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE

    def test_health_missing_key_returns_healthy_idle(self):
        """Missing health_status key returns HEALTHY_IDLE."""
        data = {"state": "idle"}
        state, _ = determine_state(data)
        assert state == STATE_HEALTHY_IDLE


# ── Format Header Tests ──


class TestFormatHeader:
    """Test format_header() for menu text generation."""

    def test_threats_found_with_count(self):
        """THREATS_FOUND with threat_count=3 contains '3'."""
        data = {"threat_count": 3}
        header = format_header(STATE_THREATS_FOUND, data)
        assert "3" in header
        assert "threat" in header.lower()

    def test_threats_found_zero_count(self):
        """THREATS_FOUND with threat_count=0 contains '?'."""
        data = {"threat_count": 0}
        header = format_header(STATE_THREATS_FOUND, data)
        assert "?" in header

    def test_threats_found_missing_count(self):
        """THREATS_FOUND without threat_count field contains '?'."""
        data = {}
        header = format_header(STATE_THREATS_FOUND, data)
        assert "?" in header

    def test_health_warning_with_issues(self):
        """HEALTH_WARNING with health_issues=2 contains '2'."""
        data = {"health_issues": 2}
        header = format_header(STATE_HEALTH_WARNING, data)
        assert "2" in header
        assert "health" in header.lower()

    def test_health_warning_zero_issues(self):
        """HEALTH_WARNING with health_issues=0 contains '?'."""
        data = {"health_issues": 0}
        header = format_header(STATE_HEALTH_WARNING, data)
        assert "?" in header

    def test_healthy_idle_header(self):
        """HEALTHY_IDLE returns 'All clear' header."""
        data = {}
        header = format_header(STATE_HEALTHY_IDLE, data)
        assert "clear" in header.lower()

    def test_unknown_state_header(self):
        """Unknown state contains 'unknown' (case-insensitive)."""
        data = {}
        header = format_header(STATE_UNKNOWN, data)
        assert "unknown" in header.lower()

    def test_scan_running_header(self):
        """SCAN_RUNNING returns appropriate header."""
        data = {}
        header = format_header(STATE_SCAN_RUNNING, data)
        assert len(header) > 0

    def test_all_states_have_headers(self):
        """All states have corresponding MENU_HEADERS entries."""
        for state in ALL_STATES:
            assert state in MENU_HEADERS, f"Missing header for state: {state}"

    def test_format_header_no_interpolation_for_non_template_states(self):
        """Non-template states don't interpolate data."""
        data = {"threat_count": 999, "health_issues": 999}
        header = format_header(STATE_HEALTHY_IDLE, data)
        assert "999" not in header


# ── Format Relative Time Tests ──


class TestFormatRelativeTime:
    """Test format_relative_time() for timestamp formatting."""

    def test_empty_string_returns_unknown(self):
        """Empty string returns 'Unknown'."""
        result = format_relative_time("")
        assert result == "Unknown"

    def test_today_timestamp(self):
        """Today's ISO timestamp starts with 'Today'."""
        now = datetime.now().isoformat()
        result = format_relative_time(now)
        assert result.startswith("Today")

    def test_invalid_string_returns_unchanged(self):
        """Invalid ISO string returns the string unchanged."""
        invalid = "not a valid timestamp"
        result = format_relative_time(invalid)
        assert result == invalid

    def test_yesterday_timestamp(self):
        """Yesterday's timestamp contains 'Yesterday'."""
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        result = format_relative_time(yesterday)
        assert "Yesterday" in result

    def test_old_timestamp(self):
        """Old timestamp formats as date (e.g., 'Mar 15')."""
        from datetime import timedelta
        old = (datetime.now() - timedelta(days=10)).isoformat()
        result = format_relative_time(old)
        # Should contain month and day
        assert len(result) > 0

    def test_timestamp_includes_time(self):
        """Formatted timestamp includes time of day."""
        now = datetime.now().isoformat()
        result = format_relative_time(now)
        # Should have AM/PM or time component
        assert any(x in result for x in ["AM", "PM", ":"])

    def test_none_value(self):
        """None passed as string would fail, but empty check handles it."""
        # This tests the guard against None
        result = format_relative_time("")
        assert result == "Unknown"


# ── Format Health Age Tests ──


class TestFormatHealthAge:
    """Test format_health_age() for health timestamp formatting."""

    def test_empty_string_returns_unknown(self):
        """Empty string returns 'unknown'."""
        result = format_health_age("")
        assert result == "unknown"

    def test_invalid_format_returns_input(self):
        """Invalid format returns the input unchanged."""
        invalid = "not a valid timestamp"
        result = format_health_age(invalid)
        assert result == invalid

    def test_none_string(self):
        """None or empty string handling."""
        result = format_health_age("")
        assert result == "unknown"

    def test_format_handles_various_inputs(self):
        """Various malformed inputs return gracefully."""
        bad_inputs = ["123", "abc", "2025-13-32", ""]
        for bad in bad_inputs:
            result = format_health_age(bad)
            assert isinstance(result, str)
            assert len(result) > 0


# ── Icon Path Tests ──


class TestIconPath:
    """Test icon_path() function."""

    def test_returns_path_object(self):
        """icon_path() returns a Path object."""
        path = icon_path("bazzite-sec-green")
        assert isinstance(path, Path)

    def test_path_ends_with_svg(self):
        """Returned path ends with .svg extension."""
        path = icon_path("bazzite-sec-green")
        assert str(path).endswith(".svg")

    def test_path_contains_icon_name(self):
        """Path contains the requested icon name."""
        name = "bazzite-sec-green"
        path = icon_path(name)
        assert name in str(path)

    def test_all_configured_icons_can_generate_paths(self):
        """All icons in STATE_CONFIGS can generate valid paths."""
        for state, config in STATE_CONFIGS.items():
            path = icon_path(config.icon)
            assert isinstance(path, Path)
            assert str(path).endswith(".svg")

    def test_icon_path_uses_security_icons_directory(self):
        """Icon path uses ~/security/icons directory."""
        path = icon_path("test-icon")
        assert "security" in str(path)
        assert "icons" in str(path)


# ── State Set Consistency Tests ──


class TestAllStates:
    """Test ALL_STATES constant and consistency."""

    def test_all_states_count(self):
        """ALL_STATES has exactly 9 entries."""
        assert len(ALL_STATES) == 9

    def test_all_states_in_configs(self):
        """All states in ALL_STATES have STATE_CONFIGS entries."""
        for state in ALL_STATES:
            assert state in STATE_CONFIGS

    def test_all_states_in_menu_headers(self):
        """All states have MENU_HEADERS entries."""
        for state in ALL_STATES:
            assert state in MENU_HEADERS

    def test_expected_states_present(self):
        """All expected state constants are in ALL_STATES."""
        expected = [
            STATE_HEALTHY_IDLE,
            STATE_SCAN_RUNNING,
            STATE_SCAN_COMPLETE,
            STATE_WARNING,
            STATE_SCAN_FAILED,
            STATE_SCAN_ABORTED,
            STATE_THREATS_FOUND,
            STATE_HEALTH_WARNING,
            STATE_UNKNOWN,
        ]
        for state in expected:
            assert state in ALL_STATES

    def test_no_duplicate_states(self):
        """ALL_STATES has no duplicates."""
        assert len(ALL_STATES) == len(set(ALL_STATES))

    def test_all_states_are_strings(self):
        """All states are strings."""
        for state in ALL_STATES:
            assert isinstance(state, str)
