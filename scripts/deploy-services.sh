#!/bin/bash
# Deploy/update all Newelle-related systemd user services.
# Run this after any service file changes.
set -euo pipefail

echo "=== Deploying Bazzite Newelle Services ==="

SRC="$(cd "$(dirname "$0")/.." && pwd)/systemd"
DEST="$HOME/.config/systemd/user"
mkdir -p "$DEST"

# Copy service files
# NOTE: bazzite-claude-flow-mcp is intentionally excluded — it is WIP.
#   The proxy uses plain JSON-RPC HTTP but Newelle expects MCP streamable-http.
#   Do not enable it until the protocol is updated. See ai/mcp_bridge/claude_flow_proxy.py.
for svc in bazzite-llm-proxy.service bazzite-mcp-bridge.service; do
    if [[ -f "$SRC/$svc" ]]; then
        cp "$SRC/$svc" "$DEST/$svc"
        echo "  Copied $svc"
    fi
done

# Reload and restart
systemctl --user daemon-reload
echo "  Daemon reloaded"

for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    systemctl --user enable "$svc.service" 2>/dev/null || true
    systemctl --user restart "$svc.service"
    echo "  Restarted $svc"
done

sleep 3

echo ""
echo "=== Service Status ==="
for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    status=$(systemctl --user is-active "$svc.service" 2>/dev/null || echo "failed")
    printf "  %-30s %s\n" "$svc" "$status"
done
echo "  (bazzite-claude-flow-mcp: SKIPPED — WIP, see deploy-services.sh for details)"

echo ""
echo "=== Health Checks ==="
curl -s http://127.0.0.1:8767/health 2>/dev/null && echo "" || echo "  LLM proxy: not responding"
curl -s http://127.0.0.1:8766/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' 2>/dev/null | head -c 100 && echo "" || echo "  MCP bridge: not responding"
# Claude-flow proxy health check skipped — service is WIP and not deployed

echo ""
echo "Done. Services will auto-start on login."
