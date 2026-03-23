#!/usr/bin/env bash
# migrate-embeddings.sh — Drop and re-embed all LanceDB tables using Gemini Embedding 001
#
# Run AFTER setting GEMINI_API_KEY in ~/.config/bazzite-ai/keys.env.
# This script is irreversible — backup ~/security/vector-db first.
#
# Usage: bash scripts/migrate-embeddings.sh [--dry-run]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
DRY_RUN=0

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=1
done

log() { echo "[migrate-embeddings] $*"; }
die() { echo "[migrate-embeddings] ERROR: $*" >&2; exit 1; }

[[ -x "$VENV_PYTHON" ]] || die ".venv not found at $REPO_ROOT/.venv — run: uv pip install -r requirements.txt"

log "Checking GEMINI_API_KEY presence..."
"$VENV_PYTHON" - <<'PYCHECK'
import sys
from pathlib import Path
keys_env = Path.home() / ".config" / "bazzite-ai" / "keys.env"
if not keys_env.exists():
    print("ERROR: keys.env not found", file=sys.stderr); sys.exit(1)
with open(keys_env) as f:
    content = f.read()
if "GEMINI_API_KEY" not in content or "GEMINI_API_KEY=" not in content:
    print("ERROR: GEMINI_API_KEY not set in keys.env", file=sys.stderr); sys.exit(1)
print("GEMINI_API_KEY found.")
PYCHECK

VECTOR_DB="$HOME/security/vector-db"
BACKUP_DIR="$HOME/security/vector-db-backup-$(date +%Y%m%d-%H%M%S)"

if [[ $DRY_RUN -eq 1 ]]; then
  log "DRY RUN — no changes will be made."
  log "Would backup: $VECTOR_DB -> $BACKUP_DIR"
  log "Would drop tables: security_logs, threat_intel, docs, health_records, scan_records"
  log "Would re-ingest all tables using Gemini Embedding 001 (768-dim)"
  exit 0
fi

# Backup current vector-db
if [[ -d "$VECTOR_DB" ]]; then
  log "Backing up $VECTOR_DB -> $BACKUP_DIR"
  cp -r "$VECTOR_DB" "$BACKUP_DIR"
  log "Backup complete."
else
  log "No existing vector-db found at $VECTOR_DB, skipping backup."
fi

# Drop and recreate all tables
log "Dropping all LanceDB tables..."
"$VENV_PYTHON" - <<'PYDROP'
import sys
sys.path.insert(0, ".")
from pathlib import Path
import lancedb

db_path = Path.home() / "security" / "vector-db"
if not db_path.exists():
    print("vector-db not found, nothing to drop.")
    sys.exit(0)

db = lancedb.connect(str(db_path))
tables = ["security_logs", "threat_intel", "docs", "health_records", "scan_records"]
for table in tables:
    try:
        db.drop_table(table)
        print(f"Dropped: {table}")
    except Exception as e:
        print(f"Skip {table}: {e}")
print("All tables dropped.")
PYDROP

# Re-run ingestion pipelines
log "Re-ingesting logs and threat intel..."
cd "$REPO_ROOT"

if "$VENV_PYTHON" -m ai.log_intel --all 2>&1; then
  log "log_intel ingestion complete."
else
  log "WARNING: log_intel ingestion failed or not available. Continue."
fi

if [[ -f "scripts/ingest-docs.sh" ]]; then
  log "Re-ingesting docs..."
  bash scripts/ingest-docs.sh --force 2>&1 || log "WARNING: doc ingestion failed. Continue."
else
  log "scripts/ingest-docs.sh not found, skipping doc ingestion."
fi

log "Migration complete. Verify with: python -m ai.rag.query 'test query'"
log "Backup available at: $BACKUP_DIR"
log "Remove backup when satisfied: rm -rf $BACKUP_DIR"
