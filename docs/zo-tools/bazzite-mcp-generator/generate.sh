#!/bin/bash
# Bazzite MCP Tool Generator Wrapper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Check for venv
if [ -d "$SKILL_DIR/.venv" ]; then
    source "$SKILL_DIR/.venv/bin/activate"
fi

# Install PyYAML if needed
if ! python3 -c "import yaml" 2>/dev/null; then
    pip install pyyaml -q
fi

# Default to workspace bazzite-laptop if exists
PROJECT_ROOT="${PROJECT_ROOT:-$HOME/workspace/bazzite-laptop}"
if [ ! -d "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="."
fi

exec python3 "$SCRIPT_DIR/generate.py" --project-root "$PROJECT_ROOT" "$@"