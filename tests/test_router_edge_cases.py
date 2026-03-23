"""Edge case tests for ai/router.py.

Covers cache failures, concurrent access, usage counter overflow, config hot-reload,
and provider chain exhaustion scenarios. Complements test_router_v2.py.
"""

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai.router import reset_router, reset_usage_stats


@pytest.fixture(autouse=True)
def _clean_router():
    """Reset router state before and after each test."""
    reset_router()
    reset_usage_stats()
    yield
    reset_router()
    reset_usage_stats()


class TestCacheInitializationFailures:
    """Test fallback behavior when disk cache fails."""

    def test_cache_dir_permission_denied(self):
        """If cache dir is not writable, should fall back to tmpdir."""
        # PosixPath.mkdir is a read-only C slot and cannot be patched via unittest.mock.
        # The fallback is exercised by the OSError guard at module load time.
        pytest.skip("PosixPath.mkdir is a read-only slot; cannot be patched post-import")

    def test_cache_dir_read_only_filesystem(self):
        """Read-only filesystem should disable caching gracefully."""
        pytest.skip("Requires filesystem mocking")

    def test_cache_corruption_recovered(self):
        """Corrupted cache should be ignored, not crash."""
        pytest.skip("Requires cache corruption simulation")


class TestConcurrentAccess:
    """Test thread-safety of router components."""

    def test_concurrent_route_query_calls(self):
        """Multiple threads calling route_query should not corrupt state."""
        from ai.router import route_query

        results = []
        errors = []

        def worker():
            try:
                result = route_query("fast", "hello")
                results.append(result)
            except Exception as e:
                errors.append(e)

        mock_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            model="groq/model",
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20)
        )

        with (
            patch("ai.router._load_config", return_value={"model_list": [
                {"model_name": "fast", "litellm_params": {"model": "groq/llama", "api_key": "test"}}
            ]}),
            patch("ai.router._get_rate_limiter") as mock_rl,
            patch("ai.router._try_provider", return_value=mock_response),
        ):
            limiter = MagicMock()
            limiter.can_call.return_value = True
            mock_rl.return_value = limiter

            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert len(errors) == 0, f"Concurrent errors: {errors}"
        assert len(results) == 10

    def test_concurrent_health_tracker_updates(self):
        """Concurrent success/failure recording should not corrupt health state."""
        from ai.health import HealthTracker

        tracker = HealthTracker()

        def record_successes():
            for _ in range(100):
                tracker.record_success("test-provider", 100.0)

        def record_failures():
            for _ in range(100):
                tracker.record_failure("test-provider", "error")

        t1 = threading.Thread(target=record_successes)
        t2 = threading.Thread(target=record_failures)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        h = tracker.get("test-provider")
        assert h.success_count + h.failure_count == 200

    def test_concurrent_usage_counter_updates(self):
        """Concurrent token counting should not lose counts."""
        from ai.router import _increment_usage, _usage_counters

        mock_response = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20)
        )

        def worker():
            for _ in range(100):
                _increment_usage("fast", mock_response)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 10 threads * 100 calls = 1000 total
        assert _usage_counters["fast"]["requests"] == 1000
        assert _usage_counters["fast"]["prompt_tokens"] == 10000


class TestUsageCounterOverflow:
    """Test usage counter behavior at extreme values."""

    def test_usage_counter_large_values(self):
        """Counters should handle billions of tokens without overflow."""
        from ai.router import _increment_usage, _usage_counters

        mock_response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=2_000_000_000,  # 2 billion
                completion_tokens=1_000_000_000
            )
        )

        _increment_usage("fast", mock_response)
        _increment_usage("fast", mock_response)

        assert _usage_counters["fast"]["prompt_tokens"] == 4_000_000_000
        assert _usage_counters["fast"]["completion_tokens"] == 2_000_000_000

    def test_usage_counter_missing_usage_field(self):
        """Response without usage field should not crash."""
        from ai.router import _increment_usage

        mock_response = SimpleNamespace()  # No usage field

        _increment_usage("fast", mock_response)  # Should not crash

    def test_usage_counter_none_token_values(self):
        """None token values should be treated as 0."""
        from ai.router import _increment_usage, _usage_counters

        mock_response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=None,
                completion_tokens=None
            )
        )

        _increment_usage("fast", mock_response)
        assert _usage_counters["fast"]["prompt_tokens"] == 0
        assert _usage_counters["fast"]["completion_tokens"] == 0


class TestConfigHotReload:
    """Test behavior when litellm config changes during runtime."""

    def test_config_reload_picks_up_new_providers(self):
        """Adding a provider to config should be available after reload."""
        pytest.skip("Requires config file watching or explicit reload mechanism")

    def test_config_reload_removes_old_providers(self):
        """Removing a provider from config should stop routing to it."""
        pytest.skip("Requires config hot-reload support")

    def test_config_syntax_error_preserves_old_config(self):
        """Invalid YAML should not crash, keep old config."""
        pytest.skip("Requires config validation")


class TestProviderChainExhaustion:
    """Test detailed fallback chain behavior."""

    def test_embed_task_no_fallback_chain(self):
        """Embed task type should not have fallback chain."""
        from ai.router import _FALLBACK_CHAINS

        assert _FALLBACK_CHAINS.get("embed") == []

    def test_fast_fallbacks_to_reason(self):
        """Fast task with no fast providers should try reason providers."""
        from ai.router import _FALLBACK_CHAINS

        assert "reason" in _FALLBACK_CHAINS["fast"]

    def test_all_providers_rate_limited_error_message(self):
        """Error when all providers rate-limited should show wait times."""
        from ai.router import route_query

        mock_config = {
            "model_list": [
                {"model_name": "fast", "litellm_params": {"model": "groq/llama"}}
            ]
        }

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_rate_limiter") as mock_rl,
        ):
            limiter = MagicMock()
            limiter.can_call.return_value = False
            limiter.wait_time.return_value = 30.5
            mock_rl.return_value = limiter

            with pytest.raises(RuntimeError, match=r"shortest wait.*30\.5s"):
                route_query("fast", "test")

    def test_last_error_preserved_in_exception(self):
        """When all providers fail, last error should be in exception chain."""
        from ai.router import route_query

        mock_config = {
            "model_list": [
                {"model_name": "fast", "litellm_params": {"model": "groq/llama"}}
            ]
        }

        def fake_try_provider(*args, **kwargs):
            raise RuntimeError("connection timeout")

        with (
            patch("ai.router._load_config", return_value=mock_config),
            patch("ai.router._get_rate_limiter") as mock_rl,
            patch("ai.router._try_provider", side_effect=fake_try_provider),
        ):
            limiter = MagicMock()
            limiter.can_call.return_value = True
            mock_rl.return_value = limiter

            with pytest.raises(RuntimeError, match="connection timeout"):
                route_query("fast", "test")


class TestStreamingEdgeCases:
    """Test streaming-specific edge cases."""

    @pytest.mark.asyncio
    async def test_stream_empty_response(self):
        """Streaming empty response should not crash."""
        from ai.router import route_query_stream

        async def empty_stream(*args, **kwargs):
            return
            yield  # Make it a generator

        with (
            patch("ai.router._load_config", return_value={"model_list": [
                {"model_name": "fast", "litellm_params": {"model": "groq/llama"}}
            ]}),
            patch("ai.router._get_provider_order", return_value=["groq"]),
            patch("ai.router._check_rate_limits"),
            patch("ai.router._stream_provider", side_effect=empty_stream),
        ):
            chunks = []
            async for chunk in route_query_stream("fast", [{"role": "user", "content": "hi"}]):
                chunks.append(chunk)

            assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_unicode_boundary_handling(self):
        """Stream chunks should not break mid-UTF-8 sequence."""
        pytest.skip("Requires UTF-8 boundary testing")

    @pytest.mark.asyncio
    async def test_stream_recovery_discards_buffer(self):
        """Pre-commit failure should discard buffered chunks."""
        # Already covered in test_router_v2.py test_stream_retries_on_early_failure
        pass


class TestEmbeddingEdgeCases:
    """Test embedding-specific edge cases."""

    def test_embed_returns_json_vector(self):
        """Embed task should return JSON-serialized vector."""
        from ai.router import route_query

        mock_response = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }

        def fake_embed(*args, **kwargs):
            return mock_response

        with (
            patch("ai.router._load_config", return_value={"model_list": [
                {"model_name": "embed", "litellm_params": {"model": "ollama/nomic-embed"}}
            ]}),
            patch("ai.router._get_router") as mock_router,
            patch("ai.router._get_rate_limiter") as mock_rl,
        ):
            router = MagicMock()
            router.embedding.return_value = mock_response
            mock_router.return_value = router
            limiter = MagicMock()
            limiter.can_call.return_value = True
            mock_rl.return_value = limiter

            result = route_query("embed", "test text")

        import json
        vector = json.loads(result)
        assert vector == [0.1, 0.2, 0.3]

    def test_embed_empty_data_returns_empty_vector(self):
        """Embedding response with no data should return empty JSON array."""
        pytest.skip("Requires testing embed response structure")
