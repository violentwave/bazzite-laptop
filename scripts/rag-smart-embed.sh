#!/bin/bash
# rag-smart-embed.sh — Intelligent RAG re-embed with staleness detection.
#
# Checks whether docs/ or ai/ source files have changed since the last embed.
# Only re-ingests when content has actually changed, then always runs log ingestion.
#
# Usage: bash scripts/rag-smart-embed.sh [--all | --scan-only | --health-only | --threat-only]
#   (extra args are forwarded to ai.rag.embed_pipeline for log ingestion)
#
# Timestamp files (epoch seconds):
#   ~/security/vector-db/.last-embed-docs   — last docs ingest
#   ~/security/vector-db/.last-embed-code   — last code ingest
#
# Exit codes: 0=success, 1=partial failure, 2=venv not found
set -euo pipefail

REPO_DIR="/home/lch/projects/bazzite-laptop"
VENV="${REPO_DIR}/.venv/bin/activate"
VECTOR_DB="/home/lch/security/vector-db"
LAST_DOCS="${VECTOR_DB}/.last-embed-docs"
LAST_CODE="${VECTOR_DB}/.last-embed-code"

if [[ ! -f "$VENV" ]]; then
    echo "Error: AI venv not found at $VENV" >&2
    exit 2
fi

# shellcheck disable=SC1090
source "$VENV"

cd "$REPO_DIR"

# ── Timestamp comparison ────────────────────────────────────────────────────────

NOW=$(date +%s)

# Find newest .md file in docs/ (epoch seconds, integer)
NEWEST_DOC=$(find docs/ -name "*.md" -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1 || echo 0)
# Find newest .py file in ai/ (epoch seconds, integer)
NEWEST_CODE=$(find ai/ -name "*.py" -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1 || echo 0)

LAST_DOCS_TS=$(cat "$LAST_DOCS" 2>/dev/null || echo 0)
LAST_CODE_TS=$(cat "$LAST_CODE" 2>/dev/null || echo 0)

CHANGED=0

# ── Docs ingest (if stale) ──────────────────────────────────────────────────────
if [[ "${NEWEST_DOC:-0}" -gt "$LAST_DOCS_TS" ]]; then
    echo "=== Docs changed (newest: ${NEWEST_DOC}, last embed: ${LAST_DOCS_TS}) — re-ingesting... ==="
    python -m ai.rag.ingest_docs --force
    echo "$NOW" > "$LAST_DOCS"
    echo "=== Docs ingest complete ==="
    CHANGED=1
else
    echo "Docs unchanged (newest: ${NEWEST_DOC}, last embed: ${LAST_DOCS_TS}) — skipping"
fi

# ── Code ingest (if stale) ──────────────────────────────────────────────────────
if [[ "${NEWEST_CODE:-0}" -gt "$LAST_CODE_TS" ]]; then
    echo "=== Code changed (newest: ${NEWEST_CODE}, last embed: ${LAST_CODE_TS}) — re-ingesting... ==="
    bash "${REPO_DIR}/scripts/ingest-code.sh" --force
    echo "$NOW" > "$LAST_CODE"
    echo "=== Code ingest complete ==="
    CHANGED=1
else
    echo "Code unchanged (newest: ${NEWEST_CODE}, last embed: ${LAST_CODE_TS}) — skipping"
fi

if [[ "$CHANGED" -eq 0 ]]; then
    echo "No changes detected, skipping re-embed"
fi

# ── Log ingestion (always run) ──────────────────────────────────────────────────
echo "=== Running log/threat-intel ingestion (always) ==="
exec python -m ai.rag.embed_pipeline "$@"
