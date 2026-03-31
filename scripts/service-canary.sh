#!/bin/bash
# service-canary.sh — Health check + auto-restart for Bazzite AI services.
# Called every 15 minutes by service-canary.timer (user scope).
#
# Pings MCP bridge (8766) and LLM proxy (8767).
# If either is unhealthy, logs a warning to syslog and restarts the service.
# Exits 0 silently if both are healthy.
set -euo pipefail

LOG_TAG="service-canary"

check_service() {
    local url="$1"
    local name="$2"
    local svc="$3"

    if ! curl --max-time 5 --silent --fail "$url" > /dev/null 2>&1; then
        logger -t "$LOG_TAG" "WARNING: $name ($url) unhealthy — restarting $svc"
        systemctl --user restart "$svc" || true
    fi
}

check_service "http://127.0.0.1:8766/health" "MCP bridge" "bazzite-mcp-bridge.service"
check_service "http://127.0.0.1:8767/health" "LLM proxy"  "bazzite-llm-proxy.service"
