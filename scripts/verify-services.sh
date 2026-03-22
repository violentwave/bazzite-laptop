#!/bin/bash
# Post-reboot verification: check all bazzite-ai services are running correctly.
# Prints PASS/FAIL for each check and exits 1 if any check fails.
# Does NOT require sudo. Does NOT start or stop anything.
set -uo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }

check_user_service() {
    local svc="$1"
    if systemctl --user is-active --quiet "$svc"; then
        pass "User service active: $svc"
    else
        fail "User service not active: $svc  (run: systemctl --user start $svc)"
    fi
}

check_system_service_enabled() {
    local svc="$1"
    if systemctl is-enabled --quiet "$svc" 2>/dev/null; then
        pass "System service enabled: $svc"
    else
        fail "System service not enabled: $svc  (run: sudo systemctl enable $svc)"
    fi
}

check_http() {
    local label="$1"
    local url="$2"
    # Use --max-time 3 and ignore HTTP status codes (service may return 4xx on GET)
    local http_code
    http_code=$(curl -s --max-time 3 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || true)
    if [[ -n "$http_code" && "$http_code" != "000" ]]; then
        pass "$label responding (HTTP $http_code)"
    else
        fail "$label not reachable: $url"
    fi
}

echo ""
echo "=== Bazzite AI Service Verification ==="
echo ""

echo "--- User services ---"
check_user_service "bazzite-llm-proxy.service"
check_user_service "bazzite-mcp-bridge.service"

echo ""
echo "--- System services ---"
# Thermal protection
if systemctl is-active --quiet "thermal-protection.service" 2>/dev/null; then
    pass "System service active: thermal-protection.service"
else
    fail "System service not active: thermal-protection.service  (run: sudo systemctl start thermal-protection.service)"
fi
if [[ -f /etc/bazzite/thermal-protection.conf ]]; then
    pass "Config exists: /etc/bazzite/thermal-protection.conf"
else
    fail "Config missing: /etc/bazzite/thermal-protection.conf  (run: sudo install -m 644 configs/thermal-protection.conf /etc/bazzite/)"
fi
if [[ -d /var/log/bazzite ]]; then
    pass "Log dir exists: /var/log/bazzite"
else
    fail "Log dir missing: /var/log/bazzite  (run: sudo mkdir -p /var/log/bazzite)"
fi
check_system_service_enabled "system-health.timer"
if systemctl is-active --quiet "clamav-freshclam.service" 2>/dev/null; then
    pass "System service active: clamav-freshclam.service"
else
    fail "System service not active: clamav-freshclam.service  (run: sudo systemctl start clamav-freshclam)"
fi

echo ""
echo "--- Port checks ---"
check_http "LLM proxy  (127.0.0.1:8767)" "http://127.0.0.1:8767/v1/models"
check_http "MCP bridge (127.0.0.1:8766)" "http://127.0.0.1:8766/mcp"

echo ""
echo "--- Ollama ---"
check_http "Ollama API (127.0.0.1:11434)" "http://127.0.0.1:11434/api/tags"

echo ""
echo "=== Summary: ${PASS} passed, ${FAIL} failed ==="
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo -e "${RED}Some checks failed. See Phase B manual steps:${NC}"
    echo "  docs/phase-b-manual-steps.md"
    echo ""
    exit 1
fi

echo -e "${GREEN}All checks passed.${NC}"
echo ""
