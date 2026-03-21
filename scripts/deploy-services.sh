#!/bin/bash
# Deploy/update Bazzite systemd services (user + system).
#
# User services (Newelle AI layer):
#   bazzite-llm-proxy, bazzite-mcp-bridge
#
# System services (health monitoring):
#   system-health.timer/service, system-health-snapshot.sh
#
# Usage: bash scripts/deploy-services.sh          (no sudo!)
set -euo pipefail

# ── Guard: refuse to run as root ──────────────────────────────────
if [[ "$EUID" -eq 0 ]]; then
    echo "ERROR: Do not run with sudo. User services need your user session."
    echo "Usage: bash scripts/deploy-services.sh"
    exit 1
fi

SRC="$(cd "$(dirname "$0")/.." && pwd)/systemd"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"

# ══════════════════════════════════════════════════════════════════
# 1. User services (systemctl --user, no sudo)
# ══════════════════════════════════════════════════════════════════
echo "=== Deploying User Services ==="

DEST="$HOME/.config/systemd/user"
mkdir -p "$DEST"

for svc in bazzite-llm-proxy.service bazzite-mcp-bridge.service; do
    if [[ -f "$SRC/$svc" ]]; then
        cp "$SRC/$svc" "$DEST/$svc"
        echo "  Copied $svc"
    fi
done

systemctl --user daemon-reload
echo "  Daemon reloaded"

for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    systemctl --user enable "$svc.service" 2>/dev/null || true
    systemctl --user restart "$svc.service"
    echo "  Restarted $svc"
done

# ══════════════════════════════════════════════════════════════════
# 2. System services (requires sudo for /etc/systemd/system)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying System Services (requires sudo) ==="

# Deploy health snapshot script
if [[ -f "$SCRIPTS/system-health-snapshot.sh" ]]; then
    sudo cp "$SCRIPTS/system-health-snapshot.sh" /usr/local/bin/system-health-snapshot.sh
    sudo chmod 755 /usr/local/bin/system-health-snapshot.sh
    echo "  Deployed system-health-snapshot.sh to /usr/local/bin/"
fi

# Deploy system-health timer and service
for unit in system-health.service system-health.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo cp "$SRC/$unit" "/etc/systemd/system/$unit"
        echo "  Copied $unit to /etc/systemd/system/"
    fi
done

sudo systemctl daemon-reload
sudo systemctl enable system-health.timer 2>/dev/null || true
sudo systemctl start system-health.timer || echo "  WARNING: timer start failed"
echo "  Enabled system-health.timer"

# ══════════════════════════════════════════════════════════════════
# 3. Status checks
# ══════════════════════════════════════════════════════════════════
sleep 3

echo ""
echo "=== User Service Status ==="
for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    status=$(systemctl --user is-active "$svc.service" 2>/dev/null || echo "failed")
    printf "  %-35s %s\n" "$svc" "$status"
done

echo ""
echo "=== System Service Status ==="
timer_enabled=$(sudo systemctl is-enabled system-health.timer 2>/dev/null || echo "disabled")
printf "  %-35s %s\n" "system-health.timer" "$timer_enabled"
sudo systemctl list-timers system-health.timer --no-pager 2>/dev/null | grep -q system-health \
    && sudo systemctl list-timers system-health.timer --no-pager 2>/dev/null | grep system-health \
    || echo "  (timer not scheduled — run: sudo systemctl start system-health.timer)"

# ══════════════════════════════════════════════════════════════════
# 4. Health checks (port listening + HTTP where available)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Health Checks ==="
# LLM proxy has a real /health HTTP endpoint
curl -sf --max-time 2 http://127.0.0.1:8767/health 2>/dev/null \
    && echo "" || echo "  LLM proxy (8767): not responding"
# MCP bridge uses FastMCP streamable-http — no standalone /health route
ss -tln | grep -q ':8766 ' \
    && echo "  MCP bridge (8766): listening" \
    || echo "  MCP bridge (8766): not responding"

echo ""
echo "Done. User services auto-start on login. Health timer runs daily at 8 AM."
