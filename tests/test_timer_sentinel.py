"""Tests for ai.agents.timer_sentinel."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

from ai.agents.timer_sentinel import (
    EXPECTED_TIMERS,
    check_timers,
    format_timer_report,
    get_timer_age_hours,
)


def make_systemctl_json(timers: dict[str, int | None]) -> str:
    """Build mock systemctl --output=json output."""
    now = int(time.time())
    entries = []
    for name, last in timers.items():
        entries.append(
            {
                "unit": name,
                "last": last or 0,
                "next": now + 3600,
                "activates": name.replace(".timer", ".service"),
            }
        )
    return json.dumps(entries)


ALL_TIMER_NAMES = list(EXPECTED_TIMERS.keys())


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_all_healthy(mock_run):
    """Test when all timers are healthy."""
    now = int(time.time())
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=make_systemctl_json({name: now - 3600 for name in ALL_TIMER_NAMES}),
        stderr="",
    )
    result = check_timers()
    assert result["status"] == "healthy"
    assert len(result["timers"]) == 16
    assert result["stale"] == []
    assert result["missing"] == []


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_stale_daily_detected(mock_run):
    """Test stale daily timer detection."""
    now = int(time.time())
    timers = {name: now - 3600 for name in ALL_TIMER_NAMES}
    timers["system-health.timer"] = now - (27 * 3600)
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=make_systemctl_json(timers),
        stderr="",
    )
    result = check_timers()
    assert result["status"] == "warning"
    assert "system-health.timer" in result["stale"]
    assert result["missing"] == []


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_stale_canary_detected(mock_run):
    """Test stale 15min timer detection."""
    now = int(time.time())
    timers = {name: now - 3600 for name in ALL_TIMER_NAMES}
    timers["service-canary.timer"] = now - 7200
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=make_systemctl_json(timers),
        stderr="",
    )
    result = check_timers()
    assert result["status"] == "warning"
    assert "service-canary.timer" in result["stale"]


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_missing_timer(mock_run):
    """Test missing timer detection."""
    now = int(time.time())
    timers = {name: now - 3600 for name in ALL_TIMER_NAMES if name != "security-briefing.timer"}
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=make_systemctl_json(timers),
        stderr="",
    )
    result = check_timers()
    assert result["status"] == "critical"
    assert "security-briefing.timer" in result["missing"]


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_never_triggered(mock_run):
    """Test timer that never triggered."""
    now = int(time.time())
    timers = {name: now - 3600 for name in ALL_TIMER_NAMES}
    timers["clamav-deep.timer"] = 0
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=make_systemctl_json(timers),
        stderr="",
    )
    result = check_timers()
    assert result["status"] in ("warning", "critical")
    assert "clamav-deep.timer" in result["stale"]


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_subprocess_timeout(mock_run):
    """Test subprocess timeout handling."""
    mock_run.side_effect = __import__("subprocess").TimeoutExpired([], 10)
    result = check_timers()
    assert result["status"] == "critical"
    assert result["missing"] == ALL_TIMER_NAMES


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_timer_check_return_schema(mock_run):
    """Test that return schema is correct."""
    now = int(time.time())
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=make_systemctl_json({name: now - 3600 for name in ALL_TIMER_NAMES}),
        stderr="",
    )
    result = check_timers()
    assert "status" in result
    assert "checked_at" in result
    assert "timers" in result
    assert "stale" in result
    assert "missing" in result
    assert "summary" in result

    for t in result["timers"]:
        assert "name" in t
        assert "schedule" in t
        assert "max_age_hours" in t
        assert "last_trigger" in t
        assert "age_hours" in t
        assert "status" in t


@patch("ai.agents.timer_sentinel.subprocess.run")
@patch("ai.agents.timer_sentinel.datetime")
def test_get_timer_age_hours_found(mock_dt, mock_run):
    """Test getting timer age for found timer."""
    mock_dt.now.return_value = __import__("datetime").datetime(2026, 4, 3, 14, 30, 0)
    mock_dt.strptime = __import__("datetime").datetime.strptime

    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Thu 2026-04-03 14:00:00 EDT\n",
        stderr="",
    )
    result = get_timer_age_hours("service-canary.timer")
    assert result is not None
    assert 0.4 <= result <= 0.6


@patch("ai.agents.timer_sentinel.subprocess.run")
def test_get_timer_age_hours_not_found(mock_run):
    """Test getting timer age for non-existent timer."""
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
    result = get_timer_age_hours("nonexistent.timer")
    assert result is None


def test_format_timer_report():
    """Test human-readable timer report format."""
    with patch("ai.agents.timer_sentinel.check_timers") as mock_check:
        mock_check.return_value = {
            "status": "warning",
            "stale": ["system-health.timer"],
            "missing": [],
            "timers": [],
        }
        report = format_timer_report()
        assert "Timer Health: warning" in report
        assert "system-health.timer" in report
