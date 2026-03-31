#!/bin/bash
# Install git hooks for this repository.
# Usage: bash scripts/install-hooks.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
    echo "ERROR: .git/hooks not found — run from a git repository" >&2
    exit 1
fi

# Pre-commit: ruff lint on staged .py files
HOOK="$HOOKS_DIR/pre-commit"
cp "$REPO_ROOT/scripts/pre-commit-hook.sh" "$HOOK"
chmod +x "$HOOK"
echo "Installed pre-commit hook → $HOOK"

echo "Done. Hooks will run automatically on git commit."
