#!/usr/bin/env python3
"""Metrics compaction script for LanceDB metrics table.

Deletes raw metric events older than retention-days (default 30) to manage
storage. Use --dry-run to preview deletions without applying them.
"""

import argparse
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import lancedb

from ai.config import VECTOR_DB_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def compact_metrics(db_path: Path, retention_days: int = 30, dry_run: bool = False) -> int:
    """Delete metrics older than retention_days.

    Args:
        db_path: Path to LanceDB database.
        retention_days: Number of days to retain (default: 30).
        dry_run: If True, only report what would be deleted.

    Returns:
        Number of rows deleted.
    """
    db = lancedb.connect(str(db_path))

    try:
        table = db.open_table("metrics")
    except Exception:
        logger.info("No metrics table found, nothing to compact")
        return 0

    df = table.to_pandas()
    if df.empty:
        logger.info("Metrics table is empty, nothing to compact")
        return 0

    cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
    old_rows = df[df["ts"] < cutoff]

    if old_rows.empty:
        logger.info(f"No metrics older than {retention_days} days to delete")
        return 0

    count = len(old_rows)
    if dry_run:
        logger.info(f"[DRY RUN] Would delete {count} metrics older than {retention_days} days")
        return count

    try:
        table.delete(f"ts < '{cutoff}'")
        logger.info(f"Deleted {count} metrics older than {retention_days} days")
    except Exception as e:
        logger.error(f"Failed to delete old metrics: {e}")
        return 0

    try:
        table.compact_files()
        logger.info("Compacted metrics table")
    except Exception as e:
        logger.warning(f"Compaction skipped: {e}")

    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact LanceDB metrics table")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Delete metrics older than this many days (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions without applying them",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=VECTOR_DB_DIR,
        help="Path to LanceDB database",
    )
    args = parser.parse_args()

    try:
        deleted = compact_metrics(args.db_path, args.retention_days, args.dry_run)
        logger.info(f"Metrics compaction complete: {deleted} rows processed")
        return 0
    except Exception as e:
        logger.error(f"Metrics compaction failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
