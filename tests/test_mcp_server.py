"""Unit tests for ai/mcp_bridge/server.py — FastMCP server setup."""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_server():
    """Remove cached module so each test gets a fresh import."""
    for mod in list(sys.modules.keys()):
        if mod.startswith("ai.mcp_bridge.server"):
            del sys.modules[mod]


# ---------------------------------------------------------------------------
# FastMCP mock factory
# ---------------------------------------------------------------------------

def _make_fastmcp_mock():
    """Build a fake fastmcp module + FastMCP class that tracks tool registrations."""

    class FakeFastMCP:
        def __init__(self, name: str):
            self.name = name
            self._tool_manager = MagicMock()
            self._tool_manager._tools = {}

        def tool(self, name: str, description: str = ""):
            """Decorator that records the tool and returns the function unchanged."""
            def decorator(fn):
                self._tool_manager._tools[name] = fn
                return fn
            return decorator

        def run(self, transport: str = "streamable-http", host: str = "127.0.0.1", port: int = 8766):
            pass  # No-op in tests

    fake_module = MagicMock()
    fake_module.FastMCP = FakeFastMCP
    return fake_module


# ---------------------------------------------------------------------------
# TestServerCreation
# ---------------------------------------------------------------------------

class TestServerCreation:
    def setup_method(self):
        _reload_server()

    def test_creates_fastmcp_app(self):
        fake_fastmcp = _make_fastmcp_mock()
        with (
            patch.dict(sys.modules, {"fastmcp": fake_fastmcp}),
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
        ):
            from ai.mcp_bridge.server import create_app

            app = create_app()
            assert app is not None

    def test_startup_guard_fails_on_missing_keys(self):
        fake_fastmcp = _make_fastmcp_mock()
        with (
            patch.dict(sys.modules, {"fastmcp": fake_fastmcp}),
            patch("ai.mcp_bridge.server.load_keys", return_value=False),
        ):
            from ai.mcp_bridge.server import create_app

            with pytest.raises(RuntimeError, match="key loading failed"):
                create_app()


# ---------------------------------------------------------------------------
# TestToolRegistration
# ---------------------------------------------------------------------------

class TestToolRegistration:
    def setup_method(self):
        _reload_server()

    def test_all_13_tools_registered(self):
        fake_fastmcp = _make_fastmcp_mock()
        with (
            patch.dict(sys.modules, {"fastmcp": fake_fastmcp}),
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
        ):
            from ai.mcp_bridge.server import create_app

            app = create_app()
            # 13 allowlisted tools + 1 health tool registered via mcp.tool()
            assert len(app._tool_manager._tools) >= 13


# ---------------------------------------------------------------------------
# TestBindAssertion
# ---------------------------------------------------------------------------

class TestBindAssertion:
    def setup_method(self):
        _reload_server()

    def test_default_bind_is_localhost(self):
        from ai.mcp_bridge.server import DEFAULT_BIND

        assert DEFAULT_BIND == "127.0.0.1"

    def test_rejects_non_localhost_bind(self):
        from ai.mcp_bridge.server import _assert_localhost

        with pytest.raises(RuntimeError, match="localhost only"):
            _assert_localhost("0.0.0.0")

    def test_accepts_localhost(self):
        from ai.mcp_bridge.server import _assert_localhost

        _assert_localhost("127.0.0.1")  # Should not raise

    def test_accepts_loopback_ipv6(self):
        from ai.mcp_bridge.server import _assert_localhost

        _assert_localhost("::1")  # Should not raise


# ---------------------------------------------------------------------------
# TestHealthEndpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def setup_method(self):
        _reload_server()

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        with (
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
            patch("ai.mcp_bridge.server._get_g4f_status", return_value="stopped"),
        ):
            from ai.mcp_bridge.server import health_check

            result = await health_check()
            assert result["status"] == "ok"
            assert result["tools"] == 13
            assert result["g4f"] == "stopped"

    @pytest.mark.asyncio
    async def test_health_g4f_running(self):
        with (
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
            patch("ai.mcp_bridge.server._get_g4f_status", return_value="running"),
        ):
            from ai.mcp_bridge.server import health_check

            result = await health_check()
            assert result["g4f"] == "running"


# ---------------------------------------------------------------------------
# TestMainModule
# ---------------------------------------------------------------------------

class TestMainModule:
    def test_main_module_exists(self):
        """ai.mcp_bridge.__main__ must be importable."""
        mod = importlib.import_module("ai.mcp_bridge.__main__")
        assert hasattr(mod, "main")

    def test_load_keys_scope_is_threat_intel(self):
        """__main__.py must use load_keys(scope='threat_intel')."""
        main_path = Path(__file__).parent.parent / "ai" / "mcp_bridge" / "__main__.py"
        source = main_path.read_text()
        assert 'scope="threat_intel"' in source or "scope='threat_intel'" in source
