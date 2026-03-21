#!/bin/bash
# Start the MCP bridge server for Newelle integration.
# Manages g4f subprocess lifecycle automatically.
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

exec python -m ai.mcp_bridge --bind 127.0.0.1 --port "${MCP_BRIDGE_PORT:-8766}"
