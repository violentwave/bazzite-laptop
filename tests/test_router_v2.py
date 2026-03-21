"""Unit tests for ai/router.py V2 features.

Tests health-weighted selection, stream recovery, and provider exhaustion.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai.router import reset_router


@pytest.fixture(autouse=True)
def _clean_router():
    """Reset router state before and after each test."""
    reset_router()
    yield
    reset_router()


@pytest.fixture()
def mock_config():
    """Minimal litellm config with two providers for 'fast'."""
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
                "model_name": "fast",
                "litellm_params": {
                    "model": "cerebras/llama-3.3-70b",
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
        ],
        "router_settings": {
            "routing_strategy": "simple-shuffle",
            "num_retries": 0,
            "timeout": 5,
        },
    }


def _make_completion_response(content: str, model: str = "") -> SimpleNamespace:
    """Create a SimpleNamespace mimicking litellm completion response."""
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content),
        delta=SimpleNamespace(content=None),
    )
    return SimpleNamespace(choices=[choice], model=model)


# ── Health-Weighted Selection ──


class TestHealthWeightedSelection:
    def test_healthy_provider_tried_first(self, mock_config):
        """Providers are tried in health-score order; healthy one wins."""
        from ai import router

        # Patch internals
        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_rate_limiter") as mock_rl,
        ):
            limiter = MagicMock()
            limiter.can_call.return_value = True
            mock_rl.return_value = limiter

            # Pre-load health: make groq healthy, cerebras neutral
            router._health_tracker.record_success("groq", 100.0)
            router._health_tracker.record_success("groq", 100.0)

            call_order = []

            def fake_try_provider(provider_name, task_type, prompt, **kwargs):
                call_order.append(provider_name)
                if provider_name == "groq":
                    return _make_completion_response("hello", "groq/llama-3.3-70b-versatile")
                raise RuntimeError("fail")

            with patch("ai.router._try_provider", side_effect=fake_try_provider):
                from ai.router import route_query
                result = route_query("fast", "hi")

            assert result == "hello"
            assert call_order[0] == "groq", "Healthy provider should be tried first"

    def test_disabled_provider_skipped(self, mock_config):
        """Providers that are disabled (cooldown) are excluded from the order."""
        from ai import router

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_rate_limiter") as mock_rl,
        ):
            limiter = MagicMock()
            limiter.can_call.return_value = True
            mock_rl.return_value = limiter

            # Disable groq by recording many failures
            for _ in range(5):
                router._health_tracker.record_failure("groq", "timeout")
            # groq should now be disabled

            call_order = []

            def fake_try_provider(provider_name, task_type, prompt, **kwargs):
                call_order.append(provider_name)
                return _make_completion_response("ok", f"{provider_name}/model")

            with patch("ai.router._try_provider", side_effect=fake_try_provider):
                from ai.router import route_query
                route_query("fast", "hi")

            assert "groq" not in call_order, "Disabled provider should be skipped"


# ── Stream Recovery ──


class TestStreamRecovery:
    @pytest.mark.asyncio
    async def test_stream_retries_on_early_failure(self, mock_config):
        """Pre-commit stream failure retries the next provider."""
        from ai.router import route_query_stream

        call_count = 0

        async def fake_stream_provider(provider, task_type, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield "partial"
                raise RuntimeError("connection lost")
            yield "recovered-chunk"

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_provider_order", return_value=["groq", "cerebras"]),
            patch("ai.router._check_rate_limits"),
            patch("ai.router._stream_provider", side_effect=fake_stream_provider),
        ):
            chunks = []
            async for chunk in route_query_stream("fast", [{"role": "user", "content": "hi"}]):
                chunks.append(chunk)

            # Should have retried with second provider
            assert call_count == 2
            assert "recovered-chunk" in chunks
            # "partial" should NOT be in output (pre-commit discard)
            assert "partial" not in chunks

    @pytest.mark.asyncio
    async def test_stream_commits_after_2kb(self, mock_config):
        """After 2KB of buffered data, stream commits and yields live."""
        from ai.router import _STREAM_COMMIT_THRESHOLD, route_query_stream

        large_chunk = "x" * (_STREAM_COMMIT_THRESHOLD + 100)

        async def fake_stream_provider(provider, task_type, messages, **kwargs):
            yield large_chunk
            yield "tail"

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_provider_order", return_value=["groq"]),
            patch("ai.router._check_rate_limits"),
            patch("ai.router._stream_provider", side_effect=fake_stream_provider),
        ):
            chunks = []
            async for chunk in route_query_stream("fast", [{"role": "user", "content": "hi"}]):
                chunks.append(chunk)

            combined = "".join(chunks)
            assert large_chunk in combined
            assert "tail" in combined


# ── All Providers Exhausted ──


class TestAllProvidersExhausted:
    def test_raises_runtime_error(self, mock_config):
        """RuntimeError when every provider fails."""
        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_rate_limiter") as mock_rl,
        ):
            limiter = MagicMock()
            limiter.can_call.return_value = True
            mock_rl.return_value = limiter

            def fake_try_provider(provider_name, task_type, prompt, **kwargs):
                raise RuntimeError(f"{provider_name} down")

            with patch("ai.router._try_provider", side_effect=fake_try_provider):
                from ai.router import route_query
                with pytest.raises(RuntimeError, match="all providers exhausted"):
                    route_query("fast", "hi")


# ── Num Retries Zero ──


class TestNumRetriesZero:
    def test_litellm_router_num_retries_is_zero(self, mock_config):
        """litellm.Router is created with num_retries=0 (our code handles retries)."""
        import sys

        mock_litellm = MagicMock()
        mock_router = MagicMock()
        mock_litellm.Router.return_value = mock_router

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router.load_keys", return_value=True),
            patch.dict(sys.modules, {"litellm": mock_litellm}),
        ):
            from ai.router import _get_router
            _get_router()
            call_kwargs = mock_litellm.Router.call_args
            assert call_kwargs.kwargs.get("num_retries") == 0 or \
                   (len(call_kwargs.args) == 0 and call_kwargs[1].get("num_retries") == 0), \
                   "litellm.Router must be created with num_retries=0"
