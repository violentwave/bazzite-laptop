#!/bin/bash
# Bazzite Discovery Scraper Wrapper
# Runs discovery scraper to find free APIs, optimizations, and improvements

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
DISCOVERY_DIR="${HOME}/security/discovery"

# Ensure directory structure
mkdir -p "${DISCOVERY_DIR}"/{reports,raw}

# Check for venv
if [ -d "$SKILL_DIR/.venv" ]; then
    source "$SKILL_DIR/.venv/bin/activate"
fi

# Run discovery scraper
exec python3 "$SCRIPT_DIR/discovery_scraper.py" "$@"
