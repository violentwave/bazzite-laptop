#!/bin/bash
# Bazzite Test Analyzer Wrapper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Check for venv
if [ -d "$SKILL_DIR/.venv" ]; then
    source "$SKILL_DIR/.venv/bin/activate"
fi

JUNIT_XML="${1:-./junit.xml}"
PROJECT_ROOT="${2:-$(dirname "$JUNIT_XML")}"

exec python3 "$SCRIPT_DIR/analyze.py" "$JUNIT_XML" --project-root "$PROJECT_ROOT"