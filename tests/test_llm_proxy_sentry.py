"""Tests for Sentry initialization in ai/llm_proxy.py."""

from unittest.mock import MagicMock, patch

import pytest


class TestInitSentry:
    def test_init_sentry_noop_when_dsn_empty(self):
        """_init_sentry must not raise when SENTRY_DSN is empty."""
        with patch("ai.llm_proxy.load_keys", return_value={"SENTRY_DSN": ""}):
            from ai.llm_proxy import _init_sentry
            _init_sentry()  # must not raise

    def test_init_sentry_noop_when_sentry_not_installed(self):
        """_init_sentry must not raise when sentry_sdk import fails."""
        with (
            patch.dict("sys.modules", {"sentry_sdk": None}),  # None causes ImportError on import
            patch("ai.llm_proxy.load_keys", return_value={"SENTRY_DSN": "https://abc@sentry.io/1"}),
        ):
            from ai.llm_proxy import _init_sentry
            _init_sentry()  # must not raise

    def test_init_sentry_calls_sentry_init_with_dsn(self):
        """_init_sentry calls sentry_sdk.init() with the configured DSN."""
        mock_sentry = MagicMock()

        with (
            patch.dict("sys.modules", {"sentry_sdk": mock_sentry}),
            patch("ai.llm_proxy.load_keys", return_value={"SENTRY_DSN": "https://abc@sentry.io/123"}),
        ):
            from ai import llm_proxy
            llm_proxy._init_sentry()

        mock_sentry.init.assert_called_once()
        call_kwargs = mock_sentry.init.call_args[1]
        assert call_kwargs["dsn"] == "https://abc@sentry.io/123"
        assert call_kwargs["traces_sample_rate"] == pytest.approx(0.1)
        assert call_kwargs["environment"] == "production"
        assert call_kwargs["release"] == "bazzite-ai@phase14"
