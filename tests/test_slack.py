"""Tests for Slack MCP tools."""

from unittest.mock import patch


class TestSlackClient:
    """Test Slack client functionality."""

    def test_get_slack_config_loads_scoped(self, monkeypatch, tmp_path):
        """Test that get_slack_config uses scoped loading."""
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("SLACK_BOT_TOKEN=xoxb-test-token\n")

        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("ai.config.KEYS_ENV", new=keys_env):
            from ai.config import load_keys

            load_keys(scope="slack")

            from ai.slack import client as slack_client

            config = slack_client.get_slack_config()
            assert config.bot_token == "xoxb-test-token"

    def test_is_slack_configured_true(self, monkeypatch, tmp_path):
        """Test is_slack_configured returns True when token set."""
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("SLACK_BOT_TOKEN=xoxb-test-token\n")

        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("ai.config.KEYS_ENV", new=keys_env):
            from ai.config import load_keys

            load_keys(scope="slack")
            from ai.slack.client import is_slack_configured

            assert is_slack_configured() is True

    def test_is_slack_configured_false_no_token(self, monkeypatch, tmp_path):
        """Test is_slack_configured returns False when no token in keys.env."""
        # Use a temp keys.env with only unrelated keys
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("UNRELATED_KEY=value\n")

        import ai.config

        orig = ai.config.KEYS_ENV
        ai.config.KEYS_ENV = keys_env
        ai.config._scoped_keys_loaded.clear()
        __import__("os").environ.pop("SLACK_BOT_TOKEN", None)

        try:
            ai.config.load_keys(scope="slack")
            from ai.slack.client import is_slack_configured

            result = is_slack_configured()
            assert result is False
        finally:
            ai.config.KEYS_ENV = orig
            ai.config._scoped_keys_loaded.clear()
            ai.config.load_keys(scope="slack")

    def test_is_slack_configured_false_empty(self, monkeypatch, tmp_path):
        """Test is_slack_configured returns False when token empty."""
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("SLACK_BOT_TOKEN=\n")

        import ai.config

        orig = ai.config.KEYS_ENV
        ai.config.KEYS_ENV = keys_env
        ai.config._scoped_keys_loaded.clear()
        __import__("os").environ.pop("SLACK_BOT_TOKEN", None)

        try:
            ai.config.load_keys(scope="slack")
            from ai.slack.client import is_slack_configured

            result = is_slack_configured()
            assert result is False
        finally:
            ai.config.KEYS_ENV = orig
            ai.config._scoped_keys_loaded.clear()
            ai.config.load_keys(scope="slack")

    def test_redact_token_short(self):
        """Test token redaction for short tokens."""
        from ai.slack.client import redact_token

        result = redact_token("xoxb")
        assert result == "xoxb-****"

    def test_redact_token_long(self):
        """Test token redaction for long tokens."""
        from ai.slack.client import redact_token

        result = redact_token("xoxb-1234567890abcdef")
        assert "****" in result

    def test_redact_token_none(self):
        """Test token redaction for None."""
        from ai.slack.client import redact_token

        result = redact_token(None)
        assert result is None


class TestSlackHandlers:
    """Test Slack MCP tool handlers."""

    def test_list_channels_not_configured(self):
        """Test list_channels returns error when not configured."""
        import ai.slack.handlers as handlers

        with patch.object(handlers, "is_slack_configured", return_value=False):
            import asyncio

            result = asyncio.run(handlers.handle_slack_list_channels({}))
        assert "error" in result
        assert "not configured" in result["error"]

    def test_post_message_missing_args(self):
        """Test post_message returns error for missing args."""
        import ai.slack.handlers as handlers

        with patch.object(handlers, "is_slack_configured", return_value=True):
            import asyncio

            result = asyncio.run(handlers.handle_slack_post_message({}))
        assert "error" in result

    def test_list_users_not_configured(self):
        """Test list_users returns error when not configured."""
        import ai.slack.handlers as handlers

        with patch.object(handlers, "is_slack_configured", return_value=False):
            import asyncio

            result = asyncio.run(handlers.handle_slack_list_users({}))
        assert "error" in result

    def test_get_history_missing_channel(self):
        """Test get_history returns error when channel missing."""
        import ai.slack.handlers as handlers

        with patch.object(handlers, "is_slack_configured", return_value=True):
            import asyncio

            result = asyncio.run(handlers.handle_slack_get_history({}))
        assert "error" in result


class TestSlackScopedLoading:
    """Test that Slack uses scoped key loading."""

    def test_slack_scope_defined(self):
        """Test that slack scope is defined in KEY_SCOPES."""
        from ai.config import KEY_SCOPES

        assert "slack" in KEY_SCOPES
        assert "SLACK_BOT_TOKEN" in KEY_SCOPES["slack"]
        assert "SLACK_APP_TOKEN" in KEY_SCOPES["slack"]
        assert "SLACK_SIGNING_SECRET" in KEY_SCOPES["slack"]
