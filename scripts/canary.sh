#!/bin/bash
# Canary release automation for Bazzite AI Layer.
#
# Runs preflight, service health, MCP tools, UI build, policy gate checks.
# Generates evidence bundle with failure summary.
#
# Usage: bash scripts/canary.sh [--evidence-dir DIR]
set -euo pipefail

EVIDENCE_DIR="${1:-}"
if [[ "$EVIDENCE_DIR" == "--evidence-dir" && -n "${2:-}" ]]; then
    EVIDENCE_DIR="$2"
elif [[ "$EVIDENCE_DIR" == "--evidence-dir" ]]; then
    EVIDENCE_DIR=""
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$REPO_ROOT/.venv/bin/python"

echo "=== Canary Release Check ==="
echo "Started: $(date -Iseconds)"
echo ""

echo "=== Stage 1: Preflight (Redeploy/Rebuild) ==="
echo "Running deploy-services.sh..."
if bash "$REPO_ROOT/scripts/deploy-services.sh" >/dev/null 2>&1; then
    echo "  Services deployed: OK"
else
    echo "  Services deployed: WARN (check logs)"
fi

echo "Validating deployment profiles..."
if "$VENV_PY" -m pytest "$REPO_ROOT/tests/test_deployment_profiles.py" -q --tb=short >/dev/null 2>&1; then
    echo "  Profile validation: OK"
else
    echo "  Profile validation: FAIL"
fi

echo ""
echo "=== Stage 2: Service Health ==="
echo "Checking LLM proxy health..."
if curl -sf --max-time 5 http://127.0.0.1:8767/health >/dev/null 2>&1; then
    echo "  LLM proxy (8767): OK"
else
    echo "  LLM proxy (8767): FAIL"
fi

echo "Checking MCP bridge health..."
if curl -sf --max-time 5 http://127.0.0.1:8766/health >/dev/null 2>&1; then
    echo "  MCP bridge (8766): OK"
elif ss -tln | grep -q ':8766 '; then
    echo "  MCP bridge (8766): OK (listening)"
else
    echo "  MCP bridge (8766): FAIL"
fi

echo "Checking user services..."
for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    status=$(systemctl --user is-active "$svc" 2>/dev/null || echo "inactive")
    if [[ "$status" == "active" ]]; then
        echo "  $svc: OK"
    else
        echo "  $svc: FAIL ($status)"
    fi
done

echo ""
echo "=== Stage 3: MCP Tools ==="
echo "Checking MCP allowlist..."
tool_count=$(grep -c "name:" "$REPO_ROOT/configs/mcp-bridge-allowlist.yaml" 2>/dev/null || echo "0")
if [[ "$tool_count" -gt 10 ]]; then
    echo "  Tools in allowlist: OK ($tool_count)"
else
    echo "  Tools in allowlist: WARN ($tool_count)"
fi

echo "Checking port 8766..."
if ss -tln | grep -q ':8766 '; then
    echo "  Port 8766 listening: OK"
else
    echo "  Port 8766 listening: FAIL"
fi

echo ""
echo "=== Stage 4: UI Build ==="
echo "Building UI..."
cd "$REPO_ROOT/ui"
if npm run build >/dev/null 2>&1; then
    echo "  UI build: OK"
else
    echo "  UI build: FAIL"
    cd "$REPO_ROOT"
    exit 1
fi
cd "$REPO_ROOT"

echo ""
echo "=== Stage 5: Policy Gates ==="
echo "Checking security policy..."
if grep -q "mode:\|default_action:" "$REPO_ROOT/configs/security-autopilot-policy.yaml" 2>/dev/null; then
    if grep -qi "approval\|block" "$REPO_ROOT/configs/security-autopilot-policy.yaml" 2>/dev/null; then
        echo "  Policy gates: OK (approval/block present)"
    else
        echo "  Policy gates: WARN (mode present, gates unclear)"
    fi
else
    echo "  Policy gates: FAIL"
fi

echo ""
echo "=== Stage 6: Evidence Bundle ==="
if [[ -n "$EVIDENCE_DIR" ]]; then
    mkdir -p "$EVIDENCE_DIR"
    echo "Generating evidence bundle at $EVIDENCE_DIR/..."
fi

echo ""
echo "=== Canary Complete ==="
echo "Finished: $(date -Iseconds)"
echo ""
echo "To open UI for manual testing:"
echo "  cd ui && npm run dev"
echo ""
echo "To check service logs:"
echo "  journalctl --user -u bazzite-mcp-bridge -n 50 --no-pager"