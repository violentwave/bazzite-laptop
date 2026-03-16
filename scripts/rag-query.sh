#!/bin/bash
# rag-query.sh — Query the security knowledge base via RAG
# Deploy to: /usr/local/bin/rag-query.sh (chmod 755)
# Usage: rag-query.sh "What threats were detected this week?"
#        rag-query.sh --top-k 5 "SMART disk errors"
#
# Outputs answer to stdout. Errors to stderr.
# Exit codes: 0=results found, 1=no results, 2=venv not found
set -euo pipefail

REPO_DIR="/home/lch/projects/bazzite-laptop"
VENV="${REPO_DIR}/.venv/bin/activate"

if [[ ! -f "$VENV" ]]; then
    echo "Error: AI venv not found at $VENV" >&2
    exit 2
fi

# shellcheck disable=SC1090
source "$VENV"

# Change to repo dir so Python can find ai/ package
cd "$REPO_DIR"

exec python -m ai.rag "$@"
