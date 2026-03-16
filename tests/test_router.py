"""Unit tests for ai/router.py.

All tests mock litellm.Router — no real API calls or keys needed.
"""

from unittest.mock import MagicMock, patch

import pytest

from ai.router import (
    VALID_TASK_TYPES,
    _extract_provider,
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
    """Minimal litellm config for testing."""
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


@pytest.fixture()
def mock_router_instance():
    """A mock litellm.Router instance."""
    return MagicMock()


@pytest.fixture()
def patch_get_router(mock_router_instance):
    """Patch _get_router to return the mock router instance."""
    with patch("ai.router._get_router", return_value=mock_router_instance):
        yield mock_router_instance


@pytest.fixture()
def patch_config(mock_config):
    """Patch _load_config to return mock_config."""
    with patch("ai.router._load_config", return_value=mock_config):
        yield mock_config


@pytest.fixture()
def patch_keys():
    """Patch load_keys to be a no-op."""
    with patch("ai.router.load_keys", return_value=True):
        yield


@pytest.fixture()
def patch_limiter():
    """Patch the rate limiter to allow all calls."""
    limiter = MagicMock()
    limiter.can_call.return_value = True
    with patch("ai.router._get_rate_limiter", return_value=limiter):
        yield limiter


# ── Validation Tests ──


class TestValidation:
    def test_invalid_task_type(self):
        with pytest.raises(ValueError, match="task_type must be one of"):
            route_query("invalid", "hello")

    def test_valid_task_types_tuple(self):
        assert VALID_TASK_TYPES == ("fast", "reason", "batch", "code", "embed")


# ── Provider Extraction ──


class TestExtractProvider:
    def test_standard_model(self):
        assert _extract_provider("groq/llama-3.3-70b-versatile") == "groq"

    def test_no_slash(self):
        assert _extract_provider("gpt-4") == "gpt-4"

    def test_multiple_slashes(self):
        assert _extract_provider("anthropic/claude-sonnet-4-20250514") == "anthropic"


# ── Router Initialization ──


class TestRouterInit:
    def test_empty_config_raises(self, patch_keys, patch_limiter):
        with patch("ai.router._load_config", return_value={}):
            with pytest.raises(RuntimeError, match="no model_list"):
                route_query("fast", "hello")

    def test_empty_model_list_raises(self, patch_keys, patch_limiter):
        with patch("ai.router._load_config", return_value={"model_list": []}):
            with pytest.raises(RuntimeError, match="no model_list"):
                route_query("fast", "hello")

    def test_keys_loaded_before_router(self, mock_config, patch_limiter):
        import sys

        mock_litellm = MagicMock()
        mock_router = MagicMock()
        mock_router.completion.return_value = _make_completion_response("hi")
        mock_litellm.Router.return_value = mock_router

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router.load_keys", return_value=True) as mock_load,
            patch.dict(sys.modules, {"litellm": mock_litellm}),
        ):
            route_query("fast", "hello")
            mock_load.assert_called_once()


# ── Completion Tests ──


class TestCompletion:
    def test_completion_returns_text(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.completion.return_value = _make_completion_response(
            "Hello world"
        )
        result = route_query("fast", "Say hello")
        assert result == "Hello world"

    def test_completion_passes_kwargs(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.completion.return_value = _make_completion_response("ok")
        route_query("fast", "test", temperature=0.5, max_tokens=100)
        call_kwargs = patch_get_router.completion.call_args
        assert call_kwargs.kwargs["temperature"] == 0.5
        assert call_kwargs.kwargs["max_tokens"] == 100

    def test_completion_uses_correct_model_name(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.completion.return_value = _make_completion_response("ok")
        route_query("reason", "analyze this")
        call_kwargs = patch_get_router.completion.call_args
        assert call_kwargs.kwargs["model"] == "reason"


# ── Embedding Tests ──


class TestEmbedding:
    def test_embedding_returns_json(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.embedding.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}],
            "model": "ollama/nomic-embed-text",
        }
        result = route_query("embed", "test input")
        import json

        assert json.loads(result) == [0.1, 0.2, 0.3]

    def test_embedding_empty_data(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.embedding.return_value = {
            "data": [],
            "model": "ollama/nomic-embed-text",
        }
        result = route_query("embed", "test input")
        import json

        assert json.loads(result) == []


# ── Rate Limiting Tests ──


class TestRateLimiting:
    def test_all_providers_limited_raises(self, patch_config):
        limiter = MagicMock()
        limiter.can_call.return_value = False
        with patch("ai.router._get_rate_limiter", return_value=limiter):
            with pytest.raises(RuntimeError, match="All providers rate-limited"):
                route_query("fast", "hello")

    def test_records_call_after_success(
        self, patch_get_router, patch_config, patch_limiter
    ):
        resp = _make_completion_response("ok")
        resp.model = "groq/llama-3.3-70b-versatile"
        patch_get_router.completion.return_value = resp
        route_query("fast", "hello")
        patch_limiter.record_call.assert_called_with("groq")


# ── Error Handling Tests ──


class TestErrorHandling:
    def test_api_error_raises_runtime(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.completion.side_effect = Exception("API connection failed")
        with pytest.raises(RuntimeError, match="LLM call failed"):
            route_query("fast", "hello")

    def test_timeout_raises_runtime(
        self, patch_get_router, patch_config, patch_limiter
    ):
        patch_get_router.completion.side_effect = TimeoutError("timed out")
        with pytest.raises(RuntimeError, match="LLM call failed"):
            route_query("fast", "hello")


# ── Reset Tests ──


class TestReset:
    def test_reset_clears_state(self):
        from ai import router

        router._config = {"test": True}
        router._router = MagicMock()
        router._rate_limiter = MagicMock()
        reset_router()
        assert router._config is None
        assert router._router is None
        assert router._rate_limiter is None


# ── Helpers ──


def _make_completion_response(content: str) -> MagicMock:
    """Create a mock litellm completion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.model = ""
    return response
