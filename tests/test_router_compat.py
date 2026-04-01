"""Backward compatibility tests for ai/router.py V2.

Ensures that the public API (route_query, route_query_stream, reset_router,
VALID_TASK_TYPES) remains unchanged after the V2 rewrite.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai.router import (
    VALID_TASK_TYPES,
    reset_router,
    route_query,
)


@pytest.fixture(autouse=True)
def _clean_router():
    """Reset router state before and after each test."""
    reset_router()
    yield
    reset_router()


@pytest.fixture()
def mock_config():
    """Minimal litellm config for compat testing."""
    return {
        "model_list": [
            {
                "model_name": "fast",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": "fake-key",
                },
            },
            {
                "model_name": "reason",
                "litellm_params": {
                    "model": "anthropic/claude-sonnet-4-20250514",
                    "api_key": "fake-key",
                },
            },
            {
                "model_name": "embed",
                "litellm_params": {
                    "model": "ollama/nomic-embed-text",
                    "api_base": "http://localhost:11434",
                },
            },
        ],
        "router_settings": {
            "routing_strategy": "simple-shuffle",
            "num_retries": 0,
            "timeout": 5,
        },
    }


class TestBackwardCompat:
    def test_valid_task_types_unchanged(self):
        """VALID_TASK_TYPES must remain the same tuple."""
        assert VALID_TASK_TYPES == ("fast", "reason", "batch", "code", "embed")

    def test_invalid_task_type_raises_valueerror(self):
        """Invalid task_type must raise ValueError, not TypeError or KeyError."""
        with pytest.raises(ValueError, match="task_type must be one of"):
            route_query("invalid", "hello")

    def test_route_query_returns_string(self, mock_config):
        """route_query() for non-embed tasks returns a plain string."""
        from types import SimpleNamespace

        def fake_try_provider(provider_name, task_type, prompt, **kwargs):
            choice = SimpleNamespace(
                message=SimpleNamespace(content="Hello world"),
            )
            return SimpleNamespace(choices=[choice], model="groq/llama")

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._check_rate_limits"),
            patch("ai.router._get_provider_order", return_value=["groq"]),
            patch("ai.router._try_provider", side_effect=fake_try_provider),
        ):
            result = route_query("fast", "Say hello")
            assert isinstance(result, str)
            assert result == "Hello world"

    def test_route_query_embed_returns_json(self, mock_config):
        """route_query('embed', ...) returns a JSON-serialized vector."""
        mock_router = MagicMock()
        mock_router.embedding.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}],
            "model": "ollama/nomic-embed-text",
        }

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._check_rate_limits"),
            patch("ai.router._get_router", return_value=mock_router),
        ):
            result = route_query("embed", "test input")
            assert json.loads(result) == [0.1, 0.2, 0.3]

    def test_all_rate_limited_raises_runtime(self, mock_config):
        """All providers rate-limited must raise RuntimeError."""
        limiter = MagicMock()
        limiter.can_call.return_value = False

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_rate_limiter", return_value=limiter),
        ):
            with pytest.raises(RuntimeError, match="all providers rate-limited"):
                route_query("fast", "hello")

    def test_reset_clears_state(self):
        """reset_router() must clear _router, _config, _rate_limiter, _health_tracker."""
        from ai import router
        from ai.health import HealthTracker

        router._config = {"test": True}
        router._router = MagicMock()
        router._rate_limiter = MagicMock()
        router._health_tracker.record_success("test", 100)

        reset_router()

        assert router._config is None
        assert router._router is None
        assert router._rate_limiter is None
        # _health_tracker should be a fresh HealthTracker
        assert isinstance(router._health_tracker, HealthTracker)
        assert len(router._health_tracker._providers) == 0
