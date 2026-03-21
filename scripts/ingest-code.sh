#!/bin/bash
# Ingest Python source files into RAG code_files LanceDB table.
# Indexes repo Python files by function/class for code-aware RAG queries.
#
# Usage: bash scripts/ingest-code.sh [--repo-root PATH] [--force]
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== Ingesting Python source into RAG code database ==="
python -m ai.rag.ingest_code --repo-root . "$@"
echo "=== Done ==="
