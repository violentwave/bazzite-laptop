"""Tests for scripts/security-briefing.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

SAMPLE_STATUS = {
    "state": "complete",
    "result": "clean",
    "health_status": "healthy",
    "last_scan_time": "2026-04-03T12:57:42-04:00",
}

SAMPLE_LLM_STATUS = {
    "providers": {
        "gemini": "healthy",
        "groq": "healthy",
    }
}

SAMPLE_KEY_STATUS = {
    "GEMINI_API_KEY": True,
    "GROQ_API_KEY": True,
}

SAMPLE_TIMER_RESULT = {
    "status": "healthy",
    "checked_at": "2026-04-03T08:45:00",
    "timers": [],
    "stale": [],
    "missing": [],
    "summary": "All 16 timers healthy",
}


@pytest.fixture
def briefing_module():
    """Load the security briefing module."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "security_briefing",
        Path(__file__).parent.parent / "scripts" / "security-briefing.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["security_briefing"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_briefing_output_format(briefing_module):
    """Test that briefing contains all 7 required sections."""
    with (
        patch("security_briefing.read_json_file") as mock_json,
        patch("security_briefing.get_anomalies") as mock_anom,
        patch("security_briefing.check_timers") as mock_timers,
    ):

        def json_side_effect(path):
            path_str = str(path)
            if ".status" in path_str:
                return SAMPLE_STATUS
            elif "llm-status" in path_str:
                return SAMPLE_LLM_STATUS
            elif "key-status" in path_str:
                return SAMPLE_KEY_STATUS
            elif "release-watch" in path_str:
                return {"alerts": []}
            elif "fedora-updates" in path_str:
                return {"pending": []}
            elif "archive-state" in path_str:
                return {"last_upload": "never", "bytes_uploaded": 0, "tables": {}}
            return {}

        mock_json.side_effect = json_side_effect
        mock_anom.return_value = []
        mock_timers.return_value = SAMPLE_TIMER_RESULT

        content = briefing_module.build_briefing()

        assert "# Security Briefing —" in content
        assert "## Security\n" in content
        assert "## Health\n" in content
        assert "## LLM Providers\n" in content
        assert "## Updates\n" in content
        assert "## Pipeline\n" in content
        assert "## Timers\n" in content
        assert "## Action Items\n" in content


def test_briefing_no_overwrite(tmp_path, briefing_module):
    """Test that running twice creates -2 suffixed file instead of overwriting."""
    with patch("security_briefing.BRIEFINGS_DIR", tmp_path):
        tmp_path.mkdir(parents=True, exist_ok=True)

        first_path = briefing_module.get_output_path("2026-04-03")
        first_path.write_text("original")

        second_path = briefing_module.get_output_path("2026-04-03")

        assert first_path.name == "briefing-2026-04-03.md"
        assert second_path.name == "briefing-2026-04-03-2.md"


def test_briefing_action_items_kev_cve(briefing_module):
    """Test KEV CVE action item generation."""
    with (
        patch("security_briefing.read_json_file") as mock_json,
        patch("security_briefing.get_anomalies") as mock_anom,
        patch("security_briefing.check_timers") as mock_timers,
    ):

        def json_side_effect(path):
            path_str = str(path)
            if "release-watch" in path_str:
                return {
                    "alerts": [{"type": "kev", "cve_id": "CVE-2024-99999", "package": "openssl"}]
                }
            elif ".status" in path_str:
                return SAMPLE_STATUS
            return {}

        mock_json.side_effect = json_side_effect
        mock_anom.return_value = []
        mock_timers.return_value = SAMPLE_TIMER_RESULT

        content = briefing_module.build_briefing()

        assert "CVE-2024-99999" in content
        assert "URGENT" in content.upper()


def test_briefing_action_items_stale_timer(briefing_module):
    """Test stale timer action item generation."""
    stale_timer_result = {
        "status": "warning",
        "checked_at": "2026-04-03T08:45:00",
        "timers": [{"name": "clamav-quick.timer", "age_hours": 27.5, "status": "stale"}],
        "stale": ["clamav-quick.timer"],
        "missing": [],
        "summary": "1 stale, 0 missing",
    }

    with (
        patch("security_briefing.read_json_file") as mock_json,
        patch("security_briefing.get_anomalies") as mock_anom,
        patch("security_briefing.check_timers") as mock_timers,
    ):

        def json_side_effect(path):
            if ".status" in str(path):
                return SAMPLE_STATUS
            return {}

        mock_json.side_effect = json_side_effect
        mock_anom.return_value = []
        mock_timers.return_value = stale_timer_result

        content = briefing_module.build_briefing()

        assert "clamav-quick.timer" in content


def test_briefing_missing_data_source_graceful(briefing_module):
    """Test that missing data sources don't crash the briefing."""
    with (
        patch("security_briefing.read_json_file") as mock_json,
        patch("security_briefing.get_anomalies") as mock_anom,
        patch("security_briefing.check_timers") as mock_timers,
    ):
        mock_json.return_value = {}
        mock_anom.return_value = []
        mock_timers.return_value = {
            "status": "healthy",
            "stale": [],
            "missing": [],
            "timers": [],
            "summary": "All 16 timers healthy",
        }

        try:
            content = briefing_module.build_briefing()
            assert content is not None
            assert "⚠" in content or "unavailable" in content.lower()
        except Exception as e:
            pytest.fail(f"Briefing should not raise exception on missing data: {e}")


def test_briefing_healthy_no_action_items(briefing_module):
    """Test that healthy system has no action items."""
    healthy_timer_result = {
        "status": "healthy",
        "checked_at": "2026-04-03T08:45:00",
        "timers": [],
        "stale": [],
        "missing": [],
        "summary": "All 16 timers healthy",
    }

    with (
        patch("security_briefing.read_json_file") as mock_json,
        patch("security_briefing.get_anomalies") as mock_anom,
        patch("security_briefing.check_timers") as mock_timers,
    ):

        def json_side_effect(path):
            if ".status" in str(path):
                return SAMPLE_STATUS
            return {"providers": {}}

        mock_json.side_effect = json_side_effect
        mock_anom.return_value = []
        mock_timers.return_value = healthy_timer_result

        content = briefing_module.build_briefing()

        assert "(none" in content or "system healthy" in content.lower()
