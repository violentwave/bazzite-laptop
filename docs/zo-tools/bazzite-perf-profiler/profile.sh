#!/bin/bash
# Bazzite Performance Profiler Wrapper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Check for venv
if [ -d "$SKILL_DIR/.venv" ]; then
    source "$SKILL_DIR/.venv/bin/activate"
fi

# Ensure psutil is available
if ! python3 -c "import psutil" 2>/dev/null; then
    echo "Installing psutil..."
    pip install psutil -q
fi

exec python3 "$SCRIPT_DIR/profile.py" "$@"