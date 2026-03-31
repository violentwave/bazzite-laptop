#!/bin/bash
# Check installed Python package versions against docs/verified-deps.md pinned versions.
# Usage: bash scripts/check-deps.sh
#
# Exit codes: 0=all match, 1=mismatch or missing packages
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO_DIR/.venv/bin/activate"

if [[ ! -f "$VENV" ]]; then
    echo "ERROR: .venv not found at $REPO_DIR/.venv" >&2
    exit 2
fi

# shellcheck disable=SC1090
source "$VENV"

# ── Pinned versions from docs/verified-deps.md ────────────────────────────────
declare -A PINNED=(
    ["litellm"]="1.82.2"
    ["diskcache"]="5.6.3"
    ["lancedb"]="0.29.2"
    ["fastmcp"]="3.1.1"
    ["uvicorn"]="0.42.0"
    ["starlette"]="0.52.1"
    ["python-dotenv"]="1.2.2"
    ["PyYAML"]="6.0.3"
    ["pydantic"]="2.12.5"
    ["httpx"]="0.28.1"
    ["requests"]="2.32.5"
    ["openai"]="2.28.0"
    ["ollama"]="0.6.1"
    ["boto3"]="1.42.73"
    ["cohere"]="5.20.7"
    ["pytest"]="9.0.2"
    ["pytest-asyncio"]="1.3.0"
    ["ruff"]="0.15.6"
    ["bandit"]="1.9.4"
)

# ANSI colours
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

OK=0
MISMATCH=0
MISSING=0

for pkg in "${!PINNED[@]}"; do
    pinned="${PINNED[$pkg]}"
    installed=$(pip show "$pkg" 2>/dev/null | grep "^Version:" | awk '{print $2}' || true)

    if [[ -z "$installed" ]]; then
        printf "${RED}[MISSING]${NC}  %-25s pinned=%-12s installed=<not found>\n" "$pkg" "$pinned"
        MISSING=$((MISSING + 1))
    elif [[ "$installed" == "$pinned" ]]; then
        printf "${GREEN}[OK]${NC}       %-25s %s\n" "$pkg" "$installed"
        OK=$((OK + 1))
    else
        printf "${YELLOW}[MISMATCH]${NC} %-25s pinned=%-12s installed=%s\n" "$pkg" "$pinned" "$installed"
        MISMATCH=$((MISMATCH + 1))
    fi
done

echo ""
echo "Summary: ${OK} OK, ${MISMATCH} mismatched, ${MISSING} missing"

if [[ "$MISMATCH" -gt 0 || "$MISSING" -gt 0 ]]; then
    echo "Update docs/verified-deps.md or pin versions with: uv pip install -r requirements.txt"
    exit 1
fi
exit 0
