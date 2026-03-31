#!/usr/bin/env bash
set -euo pipefail

# LanceDB compaction — merges fragments, prunes old versions, refreshes indexes
# Run weekly via systemd timer

VENV="${HOME}/projects/bazzite-laptop/.venv"
source "${VENV}/bin/activate"

python3 -c "
import lancedb
from pathlib import Path
from datetime import timedelta
import sys

db_path = Path.home() / 'security' / 'vector-db'
if not db_path.exists():
    print('Vector DB not found, skipping')
    sys.exit(0)

db = lancedb.connect(str(db_path))
tables = db.list_tables()
print(f'Optimizing {len(tables)} tables...')

for name in tables:
    try:
        t = db.open_table(name)
        row_count = t.count_rows()
        t.optimize()
        print(f'  {name}: {row_count} rows — optimized')
    except Exception as e:
        print(f'  {name}: ERROR — {e}')

print('Done')
"