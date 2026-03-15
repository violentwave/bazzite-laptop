#!/bin/bash
# threat-lookup.sh — Thin wrapper for AI threat intelligence lookup
# Deploy to: /usr/local/bin/threat-lookup.sh (chmod 755)
# Usage: echo "hash1\nhash2" | threat-lookup.sh --batch --format html
#    or: threat-lookup.sh --hash <sha256> --format json
#
# Called by clamav-alert.sh via:
#   runuser -u lch -- /usr/local/bin/threat-lookup.sh --batch --format html
#
# Outputs HTML or JSON to stdout. Errors to stderr.
# Exit codes: 0=enriched, 1=no results, 2=venv not found
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

exec python -m ai.threat_intel.lookup "$@"
