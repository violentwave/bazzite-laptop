#!/bin/bash
# rag-embed.sh — Embed security logs and threat intel into LanceDB
# Deploy to: /usr/local/bin/rag-embed.sh (chmod 755)
# Usage: rag-embed.sh [--all | --scan-only | --health-only | --threat-only]
#
# Called by systemd timer (rag-embed.timer) or manually.
# Embeds the last 7 days of scan/health logs + enriched threat intel.
#
# Exit codes: 0=success, 1=partial failure (nothing embedded), 2=venv not found
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

exec python -m ai.rag.embed_pipeline "$@"
