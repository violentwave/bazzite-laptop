#!/bin/bash
# code-quality.sh — Run the AI-enhanced code quality pipeline
# Deploy to: /usr/local/bin/code-quality.sh (chmod 755)
# Usage: code-quality.sh [--format text|json|html] [--no-ai]
#
# Runs parallel linters + optional AI fix suggestions.
# Exit codes: 0=clean, 1=errors found, 2=venv not found
set -euo pipefail

REPO_DIR="/home/lch/projects/bazzite-laptop"
VENV="${REPO_DIR}/.venv/bin/activate"

if [[ ! -f "$VENV" ]]; then
    echo "Error: AI venv not found at $VENV" >&2
    echo "Run: cd ${REPO_DIR} && uv venv && uv pip install -r requirements.txt" >&2
    exit 2
fi

# shellcheck disable=SC1090
source "$VENV"

# Change to repo dir so Python can find ai/ package
cd "$REPO_DIR"

exec python -m ai.code_quality "$@"
