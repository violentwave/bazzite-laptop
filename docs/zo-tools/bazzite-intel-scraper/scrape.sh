#!/bin/bash
# Bazzite Intel Scraper Wrapper Script
# Runs the Python scraper with proper environment setup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
INTEL_DIR="${HOME}/security/intel"

mkdir -p "${INTEL_DIR}"/github/{commits,prs,issues,releases}
mkdir -p "${INTEL_DIR}"/security
mkdir -p "${INTEL_DIR}"/tech_news
mkdir -p "${INTEL_DIR}"/ingest
mkdir -p "${INTEL_DIR}"/logs

if [[ -f "${HOME}/.config/bazzite-ai/keys.env" ]]; then
    export GITHUB_TOKEN=$(grep GITHUB_TOKEN "${HOME}/.config/bazzite-ai/keys.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "")
fi

cd "${SKILL_DIR}"
if [[ -d ".venv" ]]; then
    source .venv/bin/activate
fi

python3 "${SCRIPT_DIR}/scraper.py" "$@"

echo "[$(date -Iseconds)] Scraper completed" >> "${INTEL_DIR}/logs/scraper.log"
