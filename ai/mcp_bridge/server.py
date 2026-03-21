"""FastMCP server for the Newelle MCP bridge.

Exposes 21 tools + 1 health endpoint on localhost.
NEVER bind to 0.0.0.0. NEVER import ai.router (it loads all keys unscoped).
"""

import logging

import yaml

from ai.config import CONFIGS_DIR, load_keys

logger = logging.getLogger("ai.mcp_bridge")

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = int(__import__("os").environ.get("MCP_BRIDGE_PORT", "8766"))

# Number of tools in the allowlist (excludes health endpoint itself)
_TOOL_COUNT = 23


def _assert_localhost(bind: str) -> None:
    """Refuse to start on non-localhost addresses."""
    if bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(f"MCP bridge must bind to localhost only, got '{bind}'")


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

        # FastMCP 3.x does not support **kwargs in tool functions.
        # Build explicit-arg handlers for tools that accept arguments.
        if arg_defs is None:
            @mcp.tool(name=tool_name, description=description)
            async def _handler(_tn=tool_name):
                return await execute_tool(_tn, {})
        elif "hash" in arg_defs:
            @mcp.tool(name=tool_name, description=description)
            async def _handler_hash(hash: str, _tn=tool_name):
                return await execute_tool(_tn, {"hash": hash})
        elif "question" in arg_defs:
            @mcp.tool(name=tool_name, description=description)
            async def _handler_question(question: str, _tn=tool_name):
                return await execute_tool(_tn, {"question": question})
        elif "game" in arg_defs:
            @mcp.tool(name=tool_name, description=description)
            async def _handler_game(game: str, _tn=tool_name):
                return await execute_tool(_tn, {"game": game})
        elif "query" in arg_defs:
            @mcp.tool(name=tool_name, description=description)
            async def _handler_query(query: str, _tn=tool_name):
                return await execute_tool(_tn, {"query": query})
        elif "scan_type" in arg_defs:
            @mcp.tool(name=tool_name, description=description)
            async def _handler_scan(scan_type: str = "quick", _tn=tool_name):
                return await execute_tool(_tn, {"scan_type": scan_type})

    # Built-in health tool
    @mcp.tool(name="health", description="Bridge health check")
    async def _health():
        return await health_check()

    return mcp
