"""Tests for LiteLLM cost tracking in ai/router.py."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ai.router import get_cost_stats, reset_cost_stats


@pytest.fixture(autouse=True)
def _reset():
    reset_cost_stats()
    yield
    reset_cost_stats()


def _make_response(prompt_tokens=100, completion_tokens=50, model="groq/llama"):
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return SimpleNamespace(usage=usage, model=model)


class TestTrackCost:
    def test_track_cost_accumulates_tokens(self):
        """_track_cost adds prompt + completion tokens to total_tokens."""
        from ai.router import _track_cost

        resp = _make_response(100, 50)
        with patch("litellm.completion_cost", return_value=0.001):
            _track_cost(resp, task_type="fast", provider="groq")

        stats = get_cost_stats()
        assert stats["total_tokens"] == 150
        assert stats["call_count"] == 1

    def test_track_cost_accumulates_usd(self):
        """_track_cost adds cost to total_cost_usd."""
        from ai.router import _track_cost

        resp = _make_response(100, 50)
        with patch("litellm.completion_cost", return_value=0.002):
            _track_cost(resp, task_type="fast", provider="groq")
            _track_cost(resp, task_type="reason", provider="gemini")

        stats = get_cost_stats()
        assert stats["total_cost_usd"] == pytest.approx(0.004)
        assert stats["by_provider"]["groq"] == pytest.approx(0.002)
        assert stats["by_provider"]["gemini"] == pytest.approx(0.002)
        assert stats["by_task_type"]["fast"] == pytest.approx(0.002)

    def test_track_cost_missing_usage_is_noop(self):
        """_track_cost handles response with no .usage attribute."""
        from ai.router import _track_cost

        resp = SimpleNamespace()  # no .usage
        _track_cost(resp, task_type="fast", provider="groq")  # must not raise
        assert get_cost_stats()["call_count"] == 0

    def test_track_cost_completion_cost_failure_is_noop(self):
        """litellm.completion_cost errors never propagate."""
        from ai.router import _track_cost

        resp = _make_response(10, 5)
        with patch("litellm.completion_cost", side_effect=RuntimeError("boom")):
            _track_cost(resp, task_type="fast", provider="groq")  # must not raise

        assert get_cost_stats()["call_count"] == 0

    def test_get_cost_stats_has_started_at(self):
        """get_cost_stats always contains a started_at timestamp."""
        stats = get_cost_stats()
        assert "started_at" in stats
        assert stats["started_at"].endswith("Z")

    def test_reset_cost_stats_zeroes_counters(self):
        """reset_cost_stats zeroes all counters (used in tests)."""
        from ai.router import _track_cost

        resp = _make_response(50, 25)
        with patch("litellm.completion_cost", return_value=0.001):
            _track_cost(resp, task_type="fast", provider="groq")

        reset_cost_stats()
        stats = get_cost_stats()
        assert stats["total_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["call_count"] == 0
