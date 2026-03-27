#!/usr/bin/env bash
# newelle-exec.sh — run any ai.* Python module from within the project venv
# Usage: newelle-exec.sh <module> [args...]
# Example: newelle-exec.sh ai.health --reset
set -euo pipefail

REPO_DIR="${HOME}/projects/bazzite-laptop"

cd "${REPO_DIR}"
# shellcheck source=/dev/null
source .venv/bin/activate

exec python -m "$@"
