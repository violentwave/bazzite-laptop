#!/bin/bash
# Bazzite Dependency Scanner Wrapper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Check for venv
if [ -d "$SKILL_DIR/.venv" ]; then
    source "$SKILL_DIR/.venv/bin/activate"
fi

PROJECT_PATH="${1:-$HOME/workspace/bazzite-laptop}"

exec python3 "$SCRIPT_DIR/scan.py" "$PROJECT_PATH"