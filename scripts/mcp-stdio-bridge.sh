#!/usr/bin/env bash
# mcp-stdio-bridge.sh — stdio-to-HTTP shim for OpenCode → bazzite-mcp-bridge
#
# OpenCode MCP clients expect stdio transport; our bridge uses streamable-HTTP
# on localhost:8766. This shim proxies between the two.
#
# Usage in opencode.json mcp config:
#   "bazzite": {
#     "command": "bash",
#     "args": ["scripts/mcp-stdio-bridge.sh"]
#   }

set -euo pipefail

MCP_BRIDGE_URL="${MCP_BRIDGE_URL:-http://127.0.0.1:8766}"
SESSION_ID="opencode-$$-$(date +%s)"

# Check bridge is reachable
if ! curl -sf --max-time 2 "${MCP_BRIDGE_URL}/health" > /dev/null 2>&1; then
  echo '{"jsonrpc":"2.0","error":{"code":-32603,"message":"MCP bridge not reachable at '"${MCP_BRIDGE_URL}"'"},"id":null}' >&2
  exit 1
fi

# Proxy stdin (JSON-RPC messages) to HTTP endpoint and write responses to stdout
exec npx -y mcp-remote "${MCP_BRIDGE_URL}/mcp" --transport streamable-http 2>/dev/null \
  || exec node - <<'EOF'
// Minimal fallback: relay JSON-RPC lines via curl
const readline = require("readline");
const { execSync } = require("child_process");
const rl = readline.createInterface({ input: process.stdin });
const url = process.env.MCP_BRIDGE_URL || "http://127.0.0.1:8766";

rl.on("line", (line) => {
  try {
    const resp = execSync(
      `curl -sf -X POST -H 'Content-Type: application/json' -d '${line.replace(/'/g, "'\\''")}' '${url}/mcp'`,
      { timeout: 30000 }
    );
    process.stdout.write(resp + "\n");
  } catch (e) {
    process.stderr.write(`Bridge error: ${e.message}\n`);
  }
});
EOF
