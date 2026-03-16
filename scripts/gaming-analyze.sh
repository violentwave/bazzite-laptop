#!/bin/bash
# gaming-analyze.sh — MangoHud log analysis wrapper
# Deploy to: /usr/local/bin/gaming-analyze.sh (chmod 755)
# Usage: gaming-analyze.sh <mangohud_log> [--game "Game Name"] [--no-ai]
set -euo pipefail

REPO_DIR="/home/lch/projects/bazzite-laptop"
VENV="${REPO_DIR}/.venv/bin/activate"

if [[ ! -f "$VENV" ]]; then
    echo "Error: AI venv not found at $VENV" >&2
    exit 2
fi

# shellcheck disable=SC1090
source "$VENV"
cd "$REPO_DIR"

exec python -m ai.gaming analyze "$@"
