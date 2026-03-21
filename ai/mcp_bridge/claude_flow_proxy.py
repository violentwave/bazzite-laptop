"""FastMCP proxy for claude-flow's stdio MCP server.

Uses FastMCP's create_proxy() to wrap claude-flow's stdio transport
as a proper MCP streamable-http server. This handles the full MCP
protocol (initialize, tools/list, tools/call, etc.) automatically.

    claude-flow (stdio) ←→ FastMCP proxy (HTTP on localhost:8768) ←→ Newelle

Usage:
    python -m ai.mcp_bridge.claude_flow_proxy --port 8768
"""

import argparse
import logging
import os

logger = logging.getLogger("ai.mcp_bridge.claude_flow_proxy")

DEFAULT_PORT = int(os.environ.get("CLAUDE_FLOW_MCP_PORT", "8768"))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLAUDE_FLOW_BIN = os.path.join(PROJECT_ROOT, "node_modules", ".bin", "claude-flow")


def create_app():
    """Create a FastMCP proxy that wraps claude-flow's stdio MCP server."""
    from fastmcp.server import create_proxy  # noqa: PLC0415

    # FastMCP create_proxy accepts a dict config for stdio transport
    # This tells FastMCP to spawn claude-flow as a subprocess and
    # communicate via stdin/stdout using the MCP stdio protocol
    proxy = create_proxy(
        {
            "mcpServers": {
                "claude-flow": {
                    "command": CLAUDE_FLOW_BIN,
                    "args": ["mcp", "start"],
                    "cwd": PROJECT_ROOT,
                }
            }
        },
        name="claude-flow-proxy",
    )

    return proxy


def main():
    parser = argparse.ArgumentParser(description="Claude-Flow MCP proxy (FastMCP)")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError("Must bind to localhost only")

    logging.basicConfig(level=logging.INFO)
    logger.info("Claude-flow MCP proxy starting on %s:%d", args.bind, args.port)
    logger.info("Backend: %s mcp start", CLAUDE_FLOW_BIN)

    app = create_app()
    app.run(transport="streamable-http", host=args.bind, port=args.port)


if __name__ == "__main__":
    main()
