#!/bin/bash
# Pre-commit hook: run ruff on staged .py files only.
# Install with: bash scripts/install-hooks.sh
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Collect staged .py files (added, copied, modified only — not deleted)
STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

# Nothing to check
[[ -z "$STAGED" ]] && exit 0

VENV=".venv/bin/activate"
if [[ ! -f "$VENV" ]]; then
    echo "pre-commit: .venv not found, skipping ruff check" >&2
    exit 0
fi

# shellcheck disable=SC1091
source "$VENV"

echo "pre-commit: running ruff on staged Python files..."
# shellcheck disable=SC2086
if ! ruff check $STAGED; then
    echo ""
    echo "pre-commit: ruff failed — fix lint errors before committing"
    echo "  Run: source .venv/bin/activate && ruff check --fix <file>"
    exit 1
fi
