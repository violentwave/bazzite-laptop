"""Unit tests for ai/llm_proxy.py — OpenAI-compatible LLM proxy.

All tests mock the router and Starlette internals — no real API calls.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture()
def mock_router():
    """Mock ai.router functions."""
    with patch("ai.llm_proxy.route_chat", new_callable=AsyncMock) as route_chat, \
         patch("ai.llm_proxy.route_query_stream") as route_stream, \
         patch("ai.llm_proxy.get_health_snapshot") as health, \
         patch("ai.llm_proxy.get_usage_stats") as usage:
        route_chat.return_value = "Mock response from router"

        async def mock_stream(task_type, messages):
            yield "Hello "
            yield "world"

        route_stream.return_value = mock_stream("fast", [])
        health.return_value = {"groq": {"score": 0.9}}
        usage.return_value = {"total_calls": 42}

        yield {
            "route_chat": route_chat,
            "route_stream": route_stream,
            "health": health,
            "usage": usage,
        }


@pytest.fixture()
def app(mock_router):
    """Create test app instance."""
    from ai.llm_proxy import create_app
    return create_app()


@pytest.fixture()
def client(app):
    """Create Starlette test client."""
    from starlette.testclient import TestClient
    return TestClient(app)


class TestChatCompletions:
    """Tests for /v1/chat/completions endpoint."""

    def test_non_streaming_request(self, client, mock_router):
        """Non-streaming chat completion request."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "fast",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "bazzite-router/fast"
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert "Mock response" in data["choices"][0]["message"]["content"]

        mock_router["route_chat"].assert_called_once()

    def test_streaming_request(self, client, mock_router):
        """Streaming chat completion request."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "fast",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        # Verify SSE format
        chunks = [c for c in response.text.split("\n\n") if c.strip()]
        assert len(chunks) >= 3  # At least 2 content chunks + [DONE]
        assert chunks[-1].strip() == "data: [DONE]"

    def test_streaming_error_sends_graceful_chunk(self, mock_router):
        """Post-commit stream failure sends error chunk, not raw error."""
        from starlette.testclient import TestClient

        from ai.llm_proxy import create_app

        async def error_stream(task_type, messages):
            yield "partial "
            raise RuntimeError("upstream died")

        with patch("ai.llm_proxy.route_query_stream") as mock_rqs:
            mock_rqs.return_value = error_stream("fast", [])
            app = create_app()
            client = TestClient(app)
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "fast",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            )
        assert response.status_code == 200
        text = response.text
        assert "Stream interrupted" in text
        assert "RuntimeError" in text
        assert text.rstrip().endswith("data: [DONE]")

    def test_model_name_mapping(self, client, mock_router):
        """Model names are mapped to task types correctly."""
        test_cases = [
            ("gpt-4o-mini", "fast"),
            ("gpt-4o", "reason"),
            ("llama-3.3-70b", "fast"),
            ("deepseek-chat", "reason"),
            ("code", "code"),
            ("unknown-model", "fast"),  # fallback
        ]

        for model, expected_task in test_cases:
            client.post(
                "/v1/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": "Hi"}]},
            )
            # Verify route_chat was called with correct task_type
            call_args = mock_router["route_chat"].call_args
            assert call_args[0][0] == expected_task
            mock_router["route_chat"].reset_mock()

    def test_invalid_json_request(self, client):
        """Invalid JSON returns 400."""
        response = client.post(
            "/v1/chat/completions",
            content="not valid json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]["message"]

    def test_empty_messages_array(self, client, mock_router):
        """Empty messages array is handled gracefully."""
        response = client.post(
            "/v1/chat/completions",
            json={"model": "fast", "messages": []},
        )
        assert response.status_code == 200
        mock_router["route_chat"].assert_called_once()

    def test_exhaustion_returns_graceful_response(self, mock_router):
        """AllProvidersExhausted returns a valid chat completion with friendly message."""
        from starlette.testclient import TestClient

        from ai.health import AllProvidersExhausted
        from ai.llm_proxy import create_app

        with patch("ai.llm_proxy.route_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = AllProvidersExhausted("fast")
            app = create_app()
            client = TestClient(app)
            response = client.post(
                "/v1/chat/completions",
                json={"model": "fast", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chatcmpl-error"
        assert data["object"] == "chat.completion"
        assert "temporarily unavailable" in data["choices"][0]["message"]["content"]
        assert data["choices"][0]["finish_reason"] == "stop"

    def test_router_error_returns_500(self, client, mock_router):
        """Router exceptions return 500 with error message."""
        mock_router["route_chat"].side_effect = RuntimeError("Provider unavailable")

        response = client.post(
            "/v1/chat/completions",
            json={"model": "fast", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 500
        assert "Provider unavailable" in response.json()["error"]["message"]

    @patch.dict("os.environ", {"ENABLE_CONVERSATION_MEMORY": "true"})
    @patch("ai.llm_proxy.retrieve_relevant_context")
    @patch("ai.llm_proxy.store_interaction")
    def test_conversation_memory_injection(self, mock_store, mock_retrieve, client, mock_router):
        """Conversation memory is injected when enabled."""
        mock_retrieve.return_value = ["Context from past conversation"]

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "fast",
                "messages": [{"role": "user", "content": "What did we discuss?"}],
            },
        )
        assert response.status_code == 200

        # Verify memory retrieval was called
        mock_retrieve.assert_called_once_with("What did we discuss?")

        # Verify memory storage was called after response
        mock_store.assert_called_once()

    @patch.dict("os.environ", {"ENABLE_CONVERSATION_MEMORY": "true"})
    @patch("ai.llm_proxy.retrieve_relevant_context")
    def test_memory_retrieval_failure_graceful(self, mock_retrieve, client, mock_router):
        """Memory retrieval failures don't break the request."""
        mock_retrieve.side_effect = RuntimeError("DB unavailable")

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "fast",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Request should still succeed
        assert response.status_code == 200


class TestModelsEndpoint:
    """Tests for /v1/models endpoint."""

    def test_list_models(self, client):
        """Models endpoint returns available task types."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 5

        model_ids = {m["id"] for m in data["data"]}
        assert model_ids == {"fast", "reason", "batch", "code", "auto"}


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Health endpoint returns ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "bazzite-llm-proxy"


class TestLocalhostBinding:
    """Tests for localhost-only binding enforcement."""

    def test_assert_localhost_accepts_valid(self):
        """Valid localhost addresses are accepted."""
        from ai.llm_proxy import _assert_localhost

        for addr in ["127.0.0.1", "localhost", "::1"]:
            _assert_localhost(addr)  # Should not raise

    def test_assert_localhost_rejects_external(self):
        """External addresses are rejected."""
        from ai.llm_proxy import _assert_localhost

        with pytest.raises(RuntimeError, match="must bind to localhost only"):
            _assert_localhost("0.0.0.0")  # noqa: S104

        with pytest.raises(RuntimeError, match="must bind to localhost only"):
            _assert_localhost("192.168.1.1")


class TestStatusWriter:
    """Tests for LLM status file writer."""

    @patch("ai.llm_proxy.get_health_snapshot")
    @patch("ai.llm_proxy.get_cost_stats")
    def test_write_llm_status_creates_file(self, mock_cost, mock_health, tmp_path):
        """Status writer creates atomic JSON file."""
        from ai.llm_proxy import _write_llm_status

        mock_health.return_value = {"groq": {"score": 0.9}}
        mock_cost.return_value = {"total_calls": 100}

        # Monkey-patch status file path to temp directory
        import ai.llm_proxy
        original_path = ai.llm_proxy._LLM_STATUS_FILE
        ai.llm_proxy._LLM_STATUS_FILE = tmp_path / "llm-status.json"

        try:
            _write_llm_status()

            # Verify file was written
            assert (tmp_path / "llm-status.json").exists()

            # Verify JSON structure
            data = json.loads((tmp_path / "llm-status.json").read_text())
            assert "updated_at" in data
            assert data["providers"] == {"groq": {"score": 0.9}}
            assert data["usage"] == {"total_calls": 100}
            assert "models" in data
        finally:
            ai.llm_proxy._LLM_STATUS_FILE = original_path

    def test_write_llm_status_graceful_failure(self, caplog):
        """Status writer logs errors but doesn't crash."""
        from ai.llm_proxy import _write_llm_status

        with patch("ai.llm_proxy.get_health_snapshot", side_effect=RuntimeError("DB down")):
            _write_llm_status()  # Should not raise

            assert "Failed to write LLM status" in caplog.text
