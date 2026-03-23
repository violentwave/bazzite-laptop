"""Tests for ai/llm_proxy.py status file writer."""

import json
from pathlib import Path
from unittest.mock import patch

import yaml

_FAKE_CFG = {
    "model_list": [
        {"model_name": "fast",   "litellm_params": {"model": "gemini/gemini-2.0-flash"}},
        {"model_name": "reason", "litellm_params": {"model": "gemini/gemini-2.0-pro"}},
        {"model_name": "batch",  "litellm_params": {"model": "mistral/mistral-small"}},
        {"model_name": "code",   "litellm_params": {"model": "zai/glm-4-32b"}},
    ]
}

_FAKE_HEALTH = {"gemini": {"score": 0.95, "auth_broken": False}}
_FAKE_USAGE = {
    "fast":   {"prompt_tokens": 10, "completion_tokens": 5, "requests": 1},
    "reason": {"prompt_tokens": 0,  "completion_tokens": 0, "requests": 0},
    "batch":  {"prompt_tokens": 0,  "completion_tokens": 0, "requests": 0},
    "code":   {"prompt_tokens": 0,  "completion_tokens": 0, "requests": 0},
}


def _run_writer(status_file: Path) -> None:
    """Run _write_llm_status with all external calls mocked."""
    import io

    cfg_stream = io.StringIO(yaml.dump(_FAKE_CFG))

    with (
        patch("ai.llm_proxy._LLM_STATUS_FILE", status_file),
        patch("builtins.open", return_value=cfg_stream),
        patch("ai.llm_proxy.get_health_snapshot", return_value=_FAKE_HEALTH),
        patch("ai.llm_proxy.get_usage_stats", return_value=_FAKE_USAGE),
    ):
        import ai.llm_proxy as m
        m._write_llm_status()


class TestNonStreamingChatCompletions:
    """Non-streaming /v1/chat/completions must pass full message history to route_chat."""

    def _make_request(self, messages: list[dict], model: str = "fast", stream: bool = False):
        import json
        from unittest.mock import patch

        from starlette.testclient import TestClient

        with patch("ai.llm_proxy.route_chat", return_value="mocked response") as mock_chat:
            from ai.llm_proxy import create_app
            client = TestClient(create_app())
            body = {"model": model, "messages": messages, "stream": stream}
            resp = client.post("/v1/chat/completions", content=json.dumps(body),
                               headers={"content-type": "application/json"})
            return resp, mock_chat

    def test_full_message_history_passed_to_route_chat(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow-up"},
        ]
        resp, mock_chat = self._make_request(messages)
        assert resp.status_code == 200
        called_messages = mock_chat.call_args[0][1]
        assert len(called_messages) == 4
        assert called_messages[0]["role"] == "system"
        assert called_messages[-1]["content"] == "Follow-up"

    def test_response_contains_route_chat_result(self):
        messages = [{"role": "user", "content": "hello"}]
        resp, _ = self._make_request(messages)
        data = resp.json()
        assert data["choices"][0]["message"]["content"] == "mocked response"


class TestWriteLlmStatus:
    def test_produces_valid_json_with_expected_keys(self, tmp_path):
        status_file = tmp_path / "llm-status.json"
        _run_writer(status_file)

        data = json.loads(status_file.read_text())
        assert "updated_at" in data
        assert "providers" in data
        assert "usage" in data
        assert "models" in data

    def test_models_has_all_four_task_types(self, tmp_path):
        status_file = tmp_path / "llm-status.json"
        _run_writer(status_file)

        data = json.loads(status_file.read_text())
        for key in ("fast", "reason", "batch", "code"):
            assert key in data["models"]

    def test_atomic_write_uses_tmp_then_rename(self, tmp_path):
        status_file = tmp_path / "llm-status.json"
        renamed: list[str] = []
        original_rename = Path.rename

        def track_rename(self, target):
            renamed.append(str(self))
            return original_rename(self, target)

        with patch.object(Path, "rename", track_rename):
            _run_writer(status_file)

        assert any(p.endswith(".tmp") for p in renamed)
        assert status_file.exists()
