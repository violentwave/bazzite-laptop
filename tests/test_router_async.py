"""Unit tests for async router functions (route_chat, route_query_stream).

Tests async conversation routing, streaming with recovery, and error handling.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clean_router():
    """Reset router state before and after each test."""
    from ai.router import reset_router
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
        ],
        "router_settings": {
            "routing_strategy": "simple-shuffle",
            "timeout": 5,
        },
    }


@pytest.fixture()
def patch_config(mock_config):
    """Patch _load_config to return mock_config."""
    with patch("ai.router._load_config", return_value=mock_config):
        yield mock_config


@pytest.fixture()
def patch_limiter():
    """Patch the rate limiter to allow all calls."""
    limiter = MagicMock()
    limiter.can_call.return_value = True
    with patch("ai.router._get_rate_limiter", return_value=limiter):
        yield limiter


@pytest.fixture()
def patch_health():
    """Patch health tracker."""
    with patch("ai.router._health_tracker") as health:
        health.get_sorted.return_value = [
            MagicMock(name="groq", score=0.9)
        ]
        yield health


# ── route_chat() Tests ──


class TestRouteChat:
    """Tests for async route_chat() function."""

    @pytest.mark.asyncio()
    async def test_route_chat_basic(self, patch_config, patch_limiter, patch_health):
        """Basic multi-turn chat routing."""
        from ai.router import route_chat

        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from AI"
        mock_response.model = "groq/llama-3.3-70b-versatile"

        async def mock_acompletion(**kwargs):
            return mock_response

        mock_router.acompletion = mock_acompletion

        with patch("ai.router._get_router", return_value=mock_router):
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"},
            ]
            result = await route_chat("fast", messages)
            assert result == "Hello from AI"

    @pytest.mark.asyncio()
    async def test_route_chat_preserves_conversation_history(
        self, patch_config, patch_limiter, patch_health
    ):
        """Verify all messages are passed to the router."""
        from ai.router import route_chat

        mock_router = MagicMock()
        captured_messages = None

        async def mock_acompletion(**kwargs):
            nonlocal captured_messages
            captured_messages = kwargs["messages"]
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = "Response"
            resp.model = ""
            return resp

        mock_router.acompletion = mock_acompletion

        with patch("ai.router._get_router", return_value=mock_router):
            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Question 1"},
                {"role": "assistant", "content": "Answer 1"},
                {"role": "user", "content": "Question 2"},
            ]
            await route_chat("fast", messages)
            assert captured_messages == messages

    @pytest.mark.asyncio()
    async def test_route_chat_invalid_task_type(self):
        """route_chat rejects invalid task types."""
        from ai.router import route_chat

        with pytest.raises(ValueError, match="task_type must be one of"):
            await route_chat("invalid", [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio()
    async def test_route_chat_rejects_embed(self):
        """route_chat rejects 'embed' task type."""
        from ai.router import route_chat

        with pytest.raises(ValueError, match="task_type must be one of"):
            await route_chat("embed", [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio()
    async def test_route_chat_retries_on_provider_failure(
        self, patch_config, patch_limiter, patch_health
    ):
        """route_chat tries fallback providers on failure."""
        from ai.router import route_chat

        patch_health.get_sorted.return_value = [
            MagicMock(name="provider1", score=0.9),
            MagicMock(name="provider2", score=0.8),
        ]

        mock_router = MagicMock()
        call_count = 0

        async def mock_acompletion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Provider 1 failed")
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = "Success from provider2"
            resp.model = "provider2/model"
            return resp

        mock_router.acompletion = mock_acompletion

        with patch("ai.router._get_router", return_value=mock_router):
            result = await route_chat("fast", [{"role": "user", "content": "hi"}])
            assert result == "Success from provider2"
            assert call_count == 2

    @pytest.mark.asyncio()
    async def test_route_chat_all_providers_exhausted(
        self, patch_config, patch_limiter, patch_health
    ):
        """route_chat raises RuntimeError when all providers fail."""
        from ai.router import route_chat

        mock_router = MagicMock()

        async def mock_acompletion(**kwargs):
            raise Exception("All providers down")

        mock_router.acompletion = mock_acompletion

        with patch("ai.router._get_router", return_value=mock_router):
            with pytest.raises(RuntimeError, match="all providers exhausted"):
                await route_chat("fast", [{"role": "user", "content": "hi"}])


# ── route_query_stream() Tests ──


class TestRouteQueryStream:
    """Tests for async route_query_stream() with recovery."""

    @pytest.mark.asyncio()
    async def test_stream_basic(self, patch_config, patch_limiter, patch_health):
        """Basic streaming response."""
        from ai.router import route_query_stream

        async def mock_stream_provider(provider, task_type, messages, **kwargs):
            yield "Hello "
            yield "world"
            yield "!"

        with patch("ai.router._stream_provider", side_effect=mock_stream_provider):
            chunks = []
            async for chunk in route_query_stream(
                "fast",
                [{"role": "user", "content": "Say hello"}]
            ):
                chunks.append(chunk)

            assert chunks == ["Hello ", "world", "!"]

    @pytest.mark.asyncio()
    async def test_stream_pre_commit_recovery(
        self, patch_config, patch_limiter, patch_health
    ):
        """Stream recovers from pre-commit failures."""
        from ai.router import route_query_stream

        patch_health.get_sorted.return_value = [
            MagicMock(name="provider1", score=0.9),
            MagicMock(name="provider2", score=0.8),
        ]

        call_count = 0

        async def mock_stream_provider(provider, task_type, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Provider 1 stream failed")
            yield "Recovered "
            yield "from provider2"

        with patch("ai.router._stream_provider", side_effect=mock_stream_provider):
            chunks = []
            async for chunk in route_query_stream(
                "fast",
                [{"role": "user", "content": "test"}]
            ):
                chunks.append(chunk)

            assert call_count == 2
            assert chunks == ["Recovered ", "from provider2"]

    @pytest.mark.asyncio()
    async def test_stream_post_commit_failure_raises(
        self, patch_config, patch_limiter, patch_health
    ):
        """Stream raises on post-commit failure (cannot recover)."""
        from ai.router import route_query_stream

        async def mock_stream_provider(provider, task_type, messages, **kwargs):
            # Yield enough data to hit commit threshold (>8KB)
            yield "x" * 8200
            # Then fail post-commit
            raise Exception("Post-commit failure")

        with patch("ai.router._stream_provider", side_effect=mock_stream_provider):
            with pytest.raises(RuntimeError, match="failed after commit"):
                async for _ in route_query_stream(
                    "fast",
                    [{"role": "user", "content": "test"}]
                ):
                    pass

    @pytest.mark.asyncio()
    async def test_stream_all_providers_exhausted(
        self, patch_config, patch_limiter, patch_health
    ):
        """Stream raises RuntimeError when all providers fail pre-commit."""
        from ai.router import route_query_stream

        async def mock_stream_provider(provider, task_type, messages, **kwargs):
            raise Exception("Provider failed")

        with patch("ai.router._stream_provider", side_effect=mock_stream_provider):
            with pytest.raises(RuntimeError, match="all providers exhausted"):
                async for _ in route_query_stream(
                    "fast",
                    [{"role": "user", "content": "test"}]
                ):
                    pass

    @pytest.mark.asyncio()
    async def test_stream_small_response_below_threshold(
        self, patch_config, patch_limiter, patch_health
    ):
        """Small responses buffered entirely (below 8KB threshold)."""
        from ai.router import route_query_stream

        async def mock_stream_provider(provider, task_type, messages, **kwargs):
            yield "Small "
            yield "response"

        with patch("ai.router._stream_provider", side_effect=mock_stream_provider):
            chunks = []
            async for chunk in route_query_stream(
                "fast",
                [{"role": "user", "content": "test"}]
            ):
                chunks.append(chunk)

            assert chunks == ["Small ", "response"]

    @pytest.mark.asyncio()
    async def test_stream_commit_threshold_behavior(
        self, patch_config, patch_limiter, patch_health
    ):
        """Stream commits after 8KB, then switches to live streaming."""
        from ai.router import route_query_stream

        async def mock_stream_provider(provider, task_type, messages, **kwargs):
            # Yield chunks: 4KB + 4KB (hits threshold) + 500B
            yield "a" * 4096
            yield "b" * 4096  # Threshold hit here
            yield "c" * 500

        with patch("ai.router._stream_provider", side_effect=mock_stream_provider):
            chunks = []
            async for chunk in route_query_stream(
                "fast",
                [{"role": "user", "content": "test"}]
            ):
                chunks.append(chunk)

            # All chunks should be yielded
            assert len(chunks) == 3
            assert len("".join(chunks)) == 8692

    @pytest.mark.asyncio()
    async def test_stream_invalid_task_type(self):
        """route_query_stream rejects invalid task types."""
        from ai.router import route_query_stream

        with pytest.raises(ValueError, match="task_type must be one of"):
            async for _ in route_query_stream(
                "invalid",
                [{"role": "user", "content": "test"}]
            ):
                pass

    @pytest.mark.asyncio()
    async def test_stream_rejects_embed(self):
        """route_query_stream rejects 'embed' task type."""
        from ai.router import route_query_stream

        with pytest.raises(ValueError, match="task_type must be one of"):
            async for _ in route_query_stream(
                "embed",
                [{"role": "user", "content": "test"}]
            ):
                pass
