#!/bin/bash
# Ingest markdown documentation into RAG vector database.
# Embeds docs from docs/ and docs/reference/ into LanceDB so Newelle
# can answer questions about the system via knowledge.rag_query.
#
# Usage: bash scripts/ingest-docs.sh [--force]
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== Ingesting docs into RAG database ==="
python -m ai.rag.ingest_docs --dir docs/ "$@"
echo "=== Done ==="
