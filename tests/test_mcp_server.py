"""Unit tests for ai/mcp_bridge/server.py — FastMCP server setup."""

import importlib
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
            self._middleware: list = []
            self._tool_annotations: dict = {}

        def tool(self, name: str, description: str = "", annotations=None, **kwargs):
            """Decorator that records the tool (and its annotations) and returns fn unchanged."""

            def decorator(fn):
                self._tool_manager._tools[name] = fn
                self._tool_annotations[name] = annotations
                return fn

            return decorator

        def add_middleware(self, middleware) -> None:
            """Record added middleware for test assertions."""
            self._middleware.append(middleware)

        def custom_route(self, path: str, methods: list | None = None):
            """Decorator that records a custom HTTP route (no-op in tests)."""

            def decorator(fn):
                return fn

            return decorator

        def run(
            self, transport: str = "streamable-http", host: str = "127.0.0.1", port: int = 8766
        ):  # noqa: E501
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
        fake_middleware = MagicMock()
        fake_middleware.PingMiddleware = MagicMock(return_value=MagicMock())
        with (
            patch.dict(
                sys.modules,
                {
                    "fastmcp": fake_fastmcp,
                    "fastmcp.server.middleware": fake_middleware,
                },
            ),
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
        ):
            from ai.mcp_bridge.server import create_app

            app = create_app()
            assert app is not None

    def test_startup_guard_fails_on_missing_keys(self):
        fake_fastmcp = _make_fastmcp_mock()
        fake_middleware = MagicMock()
        fake_middleware.PingMiddleware = MagicMock(return_value=MagicMock())
        with (
            patch.dict(
                sys.modules,
                {
                    "fastmcp": fake_fastmcp,
                    "fastmcp.server.middleware": fake_middleware,
                },
            ),
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

    def test_all_allowlisted_tools_registered(self):
        fake_fastmcp = _make_fastmcp_mock()
        fake_middleware = MagicMock()
        fake_middleware.PingMiddleware = MagicMock(return_value=MagicMock())
        with (
            patch.dict(
                sys.modules,
                {
                    "fastmcp": fake_fastmcp,
                    "fastmcp.server.middleware": fake_middleware,
                },
            ),
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
        ):
            from ai.mcp_bridge.server import create_app

            app = create_app()
            # 57 allowlisted tools + 1 health tool registered via mcp.tool()
            assert len(app._tool_manager._tools) == 58


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
            _assert_localhost("0.0.0.0")  # noqa: S104

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

    @pytest.mark.skip(reason="async test requires pytest-asyncio plugin")
    async def test_health_returns_ok(self):
        with patch("ai.mcp_bridge.server.load_keys", return_value=True):
            from ai.mcp_bridge.server import health_check

            result = await health_check()
            assert result["status"] == "ok"
            assert result["tools"] == 50


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


# ---------------------------------------------------------------------------
# TestPingMiddleware
# ---------------------------------------------------------------------------


class TestPingMiddleware:
    def setup_method(self):
        _reload_server()

    def test_ping_middleware_added_to_server(self):
        """create_app must call mcp.add_middleware(PingMiddleware(interval_ms=25000))."""
        fake_fastmcp = _make_fastmcp_mock()
        FakePing = MagicMock(return_value=MagicMock())
        fake_middleware = MagicMock()
        fake_middleware.PingMiddleware = FakePing

        with (
            patch.dict(
                sys.modules,
                {
                    "fastmcp": fake_fastmcp,
                    "fastmcp.server.middleware": fake_middleware,
                },
            ),
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
        ):
            from ai.mcp_bridge.server import create_app

            app = create_app()
            FakePing.assert_called_once_with(interval_ms=25000)
            assert len(app._middleware) == 1


# ---------------------------------------------------------------------------
# TestToolAnnotations
# ---------------------------------------------------------------------------


class TestToolAnnotations:
    def setup_method(self):
        _reload_server()

    def _make_app(self):
        """Helper: build app with all required mocks."""
        fake_fastmcp = _make_fastmcp_mock()
        fake_middleware = MagicMock()
        fake_middleware.PingMiddleware = MagicMock(return_value=MagicMock())

        with (
            patch.dict(
                sys.modules,
                {
                    "fastmcp": fake_fastmcp,
                    "fastmcp.server.middleware": fake_middleware,
                },
            ),
            patch("ai.mcp_bridge.server.load_keys", return_value=True),
        ):
            from ai.mcp_bridge.server import create_app

            return create_app()

    def test_readonly_tool_has_readonly_hint(self):
        """system.disk_usage must have readOnlyHint=True."""
        app = self._make_app()
        ann = app._tool_annotations.get("system.disk_usage")
        assert ann is not None
        assert ann.get("readOnlyHint") is True

    def test_destructive_tool_has_destructive_hint(self):
        """security.sandbox_submit must have destructiveHint=True."""
        app = self._make_app()
        ann = app._tool_annotations.get("security.sandbox_submit")
        assert ann is not None
        assert ann.get("destructiveHint") is True

    def test_all_44_allowlisted_tools_have_annotations(self):
        """Every allowlisted tool (excludes built-in health endpoint) must have annotations."""
        app = self._make_app()
        unannotated = [
            name for name, ann in app._tool_annotations.items() if name != "health" and ann is None
        ]
        assert unannotated == [], f"Missing annotations: {unannotated}"
