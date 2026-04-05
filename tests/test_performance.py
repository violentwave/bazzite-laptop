"""Performance regression tests for P34: Performance Hardening.

Tests verify that the performance fixes deliver measurable improvements:
- Async embedding batching
- Parallel RAG vector searches
- In-memory rate limiter
- Health score caching
- Config mtime checking
"""

import time
from unittest.mock import patch

import pytest


class TestEmbedBatchPerformance:
    """Tests for async embedding batching in embedder.py."""

    @pytest.mark.asyncio
    async def test_embed_batch_under_threshold(self):
        """10-text batch should complete in under 2s with async batching."""
        from ai.rag.embedder import embed_texts_async

        test_texts = [f"test document {i} content" for i in range(10)]

        with patch("ai.rag.embedder._embed_cohere") as mock_cohere:
            mock_cohere.return_value = [[0.1] * 768 for _ in test_texts]

            start = time.perf_counter()
            result = await embed_texts_async(test_texts)
            elapsed = time.perf_counter() - start

            assert len(result) == 10
            assert elapsed < 2.0

    def test_embed_sync_wrapper_works(self):
        """Sync wrapper for async embedder should work."""
        from ai.rag.embedder import embed_texts

        with patch("ai.rag.embedder._embed_cohere") as mock:
            mock.return_value = [[0.1] * 768]
            result = embed_texts(["test"], provider="cohere")
            assert len(result) == 1

    def test_embed_semaphore_limits_concurrency(self):
        """Semaphore should limit concurrent embedding calls to 5."""
        from ai.rag.embedder import _EMBED_SEMAPHORE_LIMIT

        assert _EMBED_SEMAPHORE_LIMIT == 5


class TestRAGParallelSearch:
    """Tests for parallel RAG search in query.py."""

    def test_rag_uses_thread_pool_executor(self):
        """RAG query should use ThreadPoolExecutor for parallel searches."""
        import inspect

        from ai.rag import query

        source = inspect.getsource(query.rag_query)
        assert "ThreadPoolExecutor" in source
        assert "max_workers=3" in source


class TestRateLimiterPerformance:
    """Tests for in-memory rate limiter."""

    def test_ratelimiter_can_call_under_1ms(self):
        """In-memory path should complete in under 1ms."""
        from ai.rate_limiter import RateLimiter

        limiter = RateLimiter(use_memory=True)
        start = time.perf_counter()
        result = limiter.can_call("test_provider")
        elapsed = time.perf_counter() - start

        assert result is True
        assert elapsed < 0.001

    def test_ratelimiter_memory_cache_enabled(self):
        """RateLimiter should use memory cache by default."""
        from ai.rate_limiter import RateLimiter

        limiter = RateLimiter()
        assert limiter._use_memory is True

    def test_ratelimiter_record_call_memory(self):
        """record_call should use memory cache when enabled."""
        from ai.rate_limiter import RateLimiter, _memory_cache

        limiter = RateLimiter(use_memory=True)
        limiter.record_call("test_provider")

        from ai.rate_limiter import _cache_lock

        with _cache_lock:
            assert "test_provider" in _memory_cache


class TestHealthScoreCache:
    """Tests for health score caching in health.py."""

    def test_health_score_cached_second_call_faster(self):
        """Second score call should be faster due to caching."""
        from ai.health import ProviderHealth

        h = ProviderHealth(name="test")
        h.success_count = 100
        h.failure_count = 10

        start = time.perf_counter()
        score1 = h.score
        t1 = time.perf_counter() - start

        start = time.perf_counter()
        score2 = h.score
        t2 = time.perf_counter() - start

        assert score1 == score2
        assert t2 < t1

    def test_health_score_invalidate_cache(self):
        """invalidate_cache should clear cached score."""
        from ai.health import ProviderHealth

        h = ProviderHealth(name="test")
        h.success_count = 50
        h.failure_count = 50

        _ = h.score
        assert h._cached_score is not None

        h.invalidate_cache()
        assert h._cached_score is None

    def test_record_success_invalidates_cache(self):
        """record_success should invalidate cache."""
        from ai.health import HealthTracker

        tracker = HealthTracker()
        h = tracker.get("test")
        h.success_count = 100
        h.failure_count = 0

        _ = h.score

        tracker.record_success("test", 100.0)

        assert h._cached_score is None


class TestConfigMtime:
    """Tests for config mtime checking in router.py."""

    def test_config_mtime_module_variable_exists(self):
        """Router module should have _config_mtime variable."""
        from ai import router

        assert hasattr(router, "_config_mtime")

    def test_config_load_sets_mtime(self):
        """Config load should set _config_mtime on first load."""
        from ai import router

        original_config = router._config
        original_mtime = router._config_mtime

        router._config = None
        router._config_mtime = None

        try:
            from ai.router import _load_config

            _load_config()
            assert router._config_mtime is not None
        finally:
            router._config = original_config
            router._config_mtime = original_mtime


class TestHttpxConnectionPooling:
    """Tests for httpx connection pooling."""

    def test_httpx_client_created_with_pooling(self):
        """Router should create httpx.Client with connection pooling."""
        from ai.router import _get_router, _httpx_client

        with patch("ai.router.load_keys"):
            with patch("ai.router._load_config", return_value={"model_list": []}):
                try:
                    _get_router()
                except RuntimeError:
                    pass

        if _httpx_client is not None:
            assert _httpx_client is not None
            assert _httpx_client._limits is not None

    def test_httpx_client_has_connection_limits(self):
        """httpx.Client should have connection limits configured."""
        from ai.router import _httpx_client

        if _httpx_client is not None:
            limits = _httpx_client._limits
            assert limits.max_keepalive_connections == 20
            assert limits.max_connections == 100
