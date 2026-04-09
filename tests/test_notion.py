"""Tests for Notion MCP tools."""

from unittest.mock import patch


class TestNotionClient:
    """Test Notion client functionality."""

    def test_get_notion_config_loads_scoped(self, monkeypatch, tmp_path):
        """Test that get_notion_config uses scoped loading."""
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("NOTION_API_KEY=secret-test-key\n")

        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("ai.config.KEYS_ENV", new=keys_env):
            from ai.config import load_keys

            load_keys(scope="notion")

            from ai.notion import client as notion_client

            config = notion_client.get_notion_config()
            assert config.api_key == "secret-test-key"

    def test_is_notion_configured_true(self, monkeypatch, tmp_path):
        """Test is_notion_configured returns True when key set."""
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("NOTION_API_KEY=secret-test-key\n")

        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("ai.config.KEYS_ENV", new=keys_env):
            from ai.config import load_keys

            load_keys(scope="notion")
            from ai.notion.client import is_notion_configured

            assert is_notion_configured() is True

    def test_is_notion_configured_false_no_key(self, monkeypatch, tmp_path):
        """Test is_notion_configured returns False when no key in keys.env."""
        # Use a temp keys.env with only unrelated keys
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("UNRELATED_KEY=value\n")

        import ai.config

        orig = ai.config.KEYS_ENV
        ai.config.KEYS_ENV = keys_env
        ai.config._scoped_keys_loaded.clear()
        # Clear any previously loaded env var
        __import__("os").environ.pop("NOTION_API_KEY", None)

        try:
            ai.config.load_keys(scope="notion")
            from ai.notion.client import is_notion_configured

            result = is_notion_configured()
            assert result is False
        finally:
            ai.config.KEYS_ENV = orig
            ai.config._scoped_keys_loaded.clear()
            ai.config.load_keys(scope="notion")

    def test_is_notion_configured_false_empty(self, monkeypatch, tmp_path):
        """Test is_notion_configured returns False when key empty."""
        keys_env = tmp_path / "keys.env"
        keys_env.write_text("NOTION_API_KEY=\n")

        import ai.config

        orig = ai.config.KEYS_ENV
        ai.config.KEYS_ENV = keys_env
        ai.config._scoped_keys_loaded.clear()
        __import__("os").environ.pop("NOTION_API_KEY", None)

        try:
            ai.config.load_keys(scope="notion")
            from ai.notion.client import is_notion_configured

            result = is_notion_configured()
            assert result is False
        finally:
            ai.config.KEYS_ENV = orig
            ai.config._scoped_keys_loaded.clear()
            ai.config.load_keys(scope="notion")

    def test_redact_api_key_short(self):
        """Test API key redaction for short keys."""
        from ai.notion.client import redact_api_key

        result = redact_api_key("secret")
        assert result == "secret_****"

    def test_redact_api_key_long(self):
        """Test API key redaction for long keys."""
        from ai.notion.client import redact_api_key

        result = redact_api_key("secret_1234567890abcdef")
        assert "****" in result

    def test_redact_api_key_none(self):
        """Test API key redaction for None."""
        from ai.notion.client import redact_api_key

        result = redact_api_key(None)
        assert result is None


class TestNotionHandlers:
    """Test Notion MCP tool handlers."""

    def test_search_not_configured(self):
        """Test search returns error when not configured."""
        import ai.notion.handlers as handlers

        with patch.object(handlers, "is_notion_configured", return_value=False):
            import asyncio

            result = asyncio.run(handlers.handle_notion_search({}))
        assert "error" in result
        assert "not configured" in result["error"]

    def test_get_page_missing_args(self):
        """Test get_page returns error for missing args."""
        import ai.notion.handlers as handlers

        with patch.object(handlers, "is_notion_configured", return_value=True):
            import asyncio

            result = asyncio.run(handlers.handle_notion_get_page({}))
        assert "error" in result

    def test_get_page_content_missing_args(self):
        """Test get_page_content returns error for missing args."""
        import ai.notion.handlers as handlers

        with patch.object(handlers, "is_notion_configured", return_value=True):
            import asyncio

            result = asyncio.run(handlers.handle_notion_get_page_content({}))
        assert "error" in result

    def test_query_database_missing_args(self):
        """Test query_database returns error for missing args."""
        import ai.notion.handlers as handlers

        with patch.object(handlers, "is_notion_configured", return_value=True):
            import asyncio

            result = asyncio.run(handlers.handle_notion_query_database({}))
        assert "error" in result

    def test_query_database_not_configured(self):
        """Test query_database returns error when not configured."""
        import ai.notion.handlers as handlers

        with patch.object(handlers, "is_notion_configured", return_value=False):
            import asyncio

            result = asyncio.run(handlers.handle_notion_query_database({}))
        assert "error" in result


class TestNotionScopedLoading:
    """Test that Notion uses scoped key loading."""

    def test_notion_scope_defined(self):
        """Test that notion scope is defined in KEY_SCOPES."""
        from ai.config import KEY_SCOPES

        assert "notion" in KEY_SCOPES
        assert "NOTION_API_KEY" in KEY_SCOPES["notion"]
