#!/bin/bash
# Start the MCP bridge server for Newelle integration.
# Exposes 22 tools on localhost via FastMCP streamable-http.
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

exec python -m ai.mcp_bridge --bind 127.0.0.1 --port "${MCP_BRIDGE_PORT:-8766}"
