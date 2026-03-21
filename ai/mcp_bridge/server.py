"""FastMCP server for the Newelle MCP bridge.

Exposes 13 read-only tools on localhost. NEVER bind to 0.0.0.0.
NEVER import ai.router (it loads all keys unscoped).
"""

import logging

import yaml

from ai.config import CONFIGS_DIR, load_keys

logger = logging.getLogger("ai.mcp_bridge")

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = int(__import__("os").environ.get("MCP_BRIDGE_PORT", "8766"))

# Number of tools in the allowlist (used by health endpoint)
_TOOL_COUNT = 13


def _assert_localhost(bind: str) -> None:
    """Refuse to start on non-localhost addresses."""
    if bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(f"MCP bridge must bind to localhost only, got '{bind}'")


def _get_g4f_status() -> str:
    """Check g4f subprocess status without importing the router."""
    try:
        from ai.g4f_manager import get_manager  # noqa: PLC0415

        mgr = get_manager()
        return "running" if mgr.is_running else "stopped"
    except Exception:
        return "unavailable"


def _load_tool_defs() -> dict:
    """Load tool definitions from the allowlist YAML."""
    allowlist_path = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"
    with open(allowlist_path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("tools", {})


async def health_check() -> dict:
    """Health endpoint handler."""
    return {
        "status": "ok",
        "tools": _TOOL_COUNT,
        "g4f": _get_g4f_status(),
    }


def create_app():
    """Create and configure the FastMCP application.

    Raises:
        RuntimeError: If key loading fails.
    """
    from fastmcp import FastMCP  # noqa: PLC0415

    if not load_keys(scope="threat_intel"):
        raise RuntimeError("MCP bridge startup guard: key loading failed")

    mcp = FastMCP("bazzite-mcp-bridge")

    # Load tool definitions from the allowlist
    tool_defs = _load_tool_defs()

    # Register each allowlisted tool
    from ai.mcp_bridge.tools import execute_tool  # noqa: PLC0415

    for tool_name, tool_def in tool_defs.items():
        description = tool_def.get("description", tool_name)
        arg_defs = tool_def.get("args")

        if arg_defs is None:
            # No-argument tool — capture tool_name in default arg to avoid closure issue
            @mcp.tool(name=tool_name, description=description)
            async def _handler(_tn=tool_name):
                return await execute_tool(_tn, {})
        else:
            # Tool with arguments
            @mcp.tool(name=tool_name, description=description)
            async def _handler_with_args(_tn=tool_name, **kwargs):
                return await execute_tool(_tn, kwargs)

    # Built-in health tool
    @mcp.tool(name="health", description="Bridge health check")
    async def _health():
        return await health_check()

    return mcp
