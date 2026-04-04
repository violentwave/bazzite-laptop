#!/usr/bin/env python3
"""LanceDB retention and compaction.

Prunes old records from LanceDB tables based on per-table retention
policies, compacts file fragments, and removes leftover temp directories.

Usage:
    python scripts/lancedb-prune.py [--dry-run] [--retention-days N]
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

HOME = Path.home()

# Project root on path so ai.config resolves correctly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.config import VECTOR_DB_DIR  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Table configuration ────────────────────────────────────────────────────────

# Tables that receive timestamp-based retention deletes + compact + cleanup.
# Value is fixed retention days, or None to use --retention-days (default 90).
# All tables store timestamps as ISO 8601 strings in a column named "timestamp".
RETENTION_TABLES: dict[str, int | None] = {
    "health_records": None,  # 90-day default
    "scan_records": None,  # 90-day default
    "sig_updates": None,  # 90-day default
    "security_logs": None,  # 90-day default
    "threat_intel": 180,  # threats kept longer for historical lookups
    # P22-P28 tables
    "task_patterns": None,  # 90-day default; task learning outcomes (P22)
    "semantic_cache": 30,  # LLM response cache — high churn, short retention (P23)
    "metrics": 30,  # observability time-series — high volume (P24)
    "conversation_memory": None,  # 90-day default; importance >= 4 pruned by ai/memory.py (P25)
    "system_insights": 365,  # weekly insight snapshots — keep 1 year (P28)
}

# Tables that only get compact + cleanup — no retention deletes.
COMPACT_ONLY_TABLES = ["docs", "code_files"]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _format_bytes(num_bytes: int) -> str:
    """Format bytes as human-readable string (KB, MB, GB)."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def _cutoff_iso(days: int) -> str:
    """Return an ISO 8601 timestamp string for *days* ago (UTC)."""
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _count_matching(table, predicate: str) -> int:
    """Count rows matching *predicate* without loading full row data.

    Tries the modern ``count_rows(filter=...)`` API first, then falls back
    to a PyLance dataset call, then to a minimal column scan.
    """
    try:
        return table.count_rows(filter=predicate)
    except Exception:  # noqa: S110
        pass
    try:
        return table.to_lance().count_rows(filter=predicate)
    except Exception:  # noqa: S110
        pass
    try:
        rows = table.search().where(predicate, prefilter=True).select(["id"]).limit(None).to_list()
        return len(rows)
    except Exception:
        logger.warning("Could not count rows matching '%s'; reporting 0", predicate)
        return 0


def _run_maintenance(table, name: str) -> None:
    """Compact fragments and remove old versions for *table*."""
    logger.info("%s: compact_files()", name)
    table.compact_files()
    logger.info("%s: cleanup_old_versions(older_than_days=1)", name)
    table.cleanup_old_versions(older_than_days=1)


# ── Per-table operations ───────────────────────────────────────────────────────


def prune_table(db, name: str, retention_days: int, *, dry_run: bool) -> dict:
    """Delete rows older than *retention_days* then compact.  Returns stats."""
    result: dict = {
        "table": name,
        "rows_before": 0,
        "rows_deleted": 0,
        "rows_after": 0,
        "skipped": False,
        "skip_reason": "",
    }

    tables_response = db.list_tables()
    existing_tables = (
        tables_response.tables if hasattr(tables_response, "tables") else list(tables_response)
    )
    if name not in existing_tables:
        result["skipped"] = True
        result["skip_reason"] = "table not found"
        logger.warning("Table '%s' not found — skipping", name)
        return result

    table = db.open_table(name)
    rows_before = table.count_rows()
    result["rows_before"] = rows_before

    cutoff = _cutoff_iso(retention_days)
    predicate = f"timestamp < '{cutoff}'"

    if dry_run:
        would_delete = _count_matching(table, predicate)
        result["rows_deleted"] = would_delete
        result["rows_after"] = rows_before - would_delete
        logger.info(
            "[DRY-RUN] %s: %d rows total, would delete %d (cutoff %s, %d-day retention)",
            name,
            rows_before,
            would_delete,
            cutoff[:10],
            retention_days,
        )
    else:
        logger.info(
            "%s: %d rows — deleting rows older than %d days (cutoff %s)",
            name,
            rows_before,
            retention_days,
            cutoff[:10],
        )
        table.delete(predicate)
        rows_after = table.count_rows()
        rows_deleted = rows_before - rows_after
        result["rows_deleted"] = rows_deleted
        result["rows_after"] = rows_after
        logger.info("%s: deleted %d rows, %d remain", name, rows_deleted, rows_after)
        _run_maintenance(table, name)

    return result


def compact_table(db, name: str, *, dry_run: bool) -> dict:
    """Compact and clean a table without any retention delete.  Returns stats."""
    result: dict = {
        "table": name,
        "rows_before": 0,
        "rows_deleted": 0,
        "rows_after": 0,
        "skipped": False,
        "skip_reason": "",
    }

    tables_response = db.list_tables()
    existing_tables = (
        tables_response.tables if hasattr(tables_response, "tables") else list(tables_response)
    )
    if name not in existing_tables:
        result["skipped"] = True
        result["skip_reason"] = "table not found"
        logger.warning("Table '%s' not found — skipping", name)
        return result

    table = db.open_table(name)
    rows = table.count_rows()
    result["rows_before"] = rows
    result["rows_after"] = rows

    if dry_run:
        logger.info(
            "[DRY-RUN] %s: %d rows — would compact + cleanup (no retention delete)",
            name,
            rows,
        )
    else:
        logger.info("%s: %d rows — compact + cleanup only", name, rows)
        _run_maintenance(table, name)

    return result


def clean_tmp_dirs(db_path: Path, *, dry_run: bool) -> int:
    """Remove .tmp* and empty _indices/ directories.  Returns count of items."""
    removed = 0

    for item in sorted(db_path.rglob(".tmp*")):
        if item.is_dir():
            if dry_run:
                logger.info("[DRY-RUN] Would remove temp dir: %s", item)
            else:
                logger.info("Removing temp dir: %s", item)
                shutil.rmtree(item, ignore_errors=True)
            removed += 1

    for item in sorted(db_path.rglob("_indices")):
        if item.is_dir():
            try:
                is_empty = not any(item.iterdir())
            except PermissionError:
                continue
            if is_empty:
                if dry_run:
                    logger.info("[DRY-RUN] Would remove empty _indices dir: %s", item)
                else:
                    logger.info("Removing empty _indices dir: %s", item)
                    try:
                        item.rmdir()
                    except OSError as exc:
                        logger.warning("Could not remove %s: %s", item, exc)
                removed += 1

    return removed


def clean_llm_cache(cache_dir: Path, *, dry_run: bool) -> int:
    """Remove expired LLM cache entries. Returns count of removed entries."""
    removed = 0

    if not cache_dir.exists():
        return 0

    import json
    import time

    now = time.time()
    for shard_dir in cache_dir.iterdir():
        if not shard_dir.is_dir():
            continue
        for json_file in shard_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text())
                if now > data.get("expires_at", 0):
                    if dry_run:
                        logger.info("[DRY-RUN] Would remove expired cache: %s", json_file)
                    else:
                        logger.info("Removing expired cache: %s", json_file)
                        json_file.unlink()
                    removed += 1
            except (OSError, json.JSONDecodeError):
                pass

    return removed


def clean_cost_archives(archive_dir: Path, age_days: int = 90, *, dry_run: bool) -> int:
    """Remove old cost archive files older than age_days. Returns count removed."""
    removed = 0

    if not archive_dir.exists():
        return 0

    import time

    cutoff = time.time() - (age_days * 24 * 3600)
    for json_file in archive_dir.glob("cost-archive-*.json"):
        try:
            if json_file.stat().st_mtime < cutoff:
                if dry_run:
                    logger.info("[DRY-RUN] Would remove old cost archive: %s", json_file)
                else:
                    logger.info("Removing old cost archive: %s", json_file)
                    json_file.unlink()
                removed += 1
        except OSError:
            pass

    return removed


# Cache TTLs in seconds
_CACHE_TTL_SECONDS: dict[str, int] = {
    "threat-cache": 7 * 24 * 3600,  # 7 days
    "rag-cache": 1 * 24 * 3600,  # 1 day
    "ip-cache": 1 * 24 * 3600,  # 1 day
    "ioc-cache": 7 * 24 * 3600,  # 7 days
}


def cleanup_caches(base_dir: Path, *, dry_run: bool) -> tuple[int, int]:
    """Clean stale cache files by TTL and old cost archives.

    Returns (total_files_cleaned, total_bytes_freed).
    """
    import time

    total_removed = 0
    total_bytes = 0
    now = time.time()

    # Clean stale cache files by TTL
    for cache_name, ttl_seconds in _CACHE_TTL_SECONDS.items():
        cache_dir = base_dir / cache_name
        if not cache_dir.exists():
            logger.debug("Cache dir not found, skipping: %s", cache_dir)
            continue

        cutoff = now - ttl_seconds
        removed_from_dir = 0

        for json_file in cache_dir.rglob("*.json"):
            try:
                if json_file.stat().st_mtime < cutoff:
                    size = json_file.stat().st_size
                    if dry_run:
                        logger.info("[DRY-RUN] Would remove stale cache: %s", json_file)
                    else:
                        logger.info("Removing stale cache: %s", json_file)
                        json_file.unlink()
                    total_bytes += size
                    removed_from_dir += 1
            except OSError:
                pass

        if removed_from_dir > 0:
            logger.info("Cleaned %d stale files from %s", removed_from_dir, cache_name)
        total_removed += removed_from_dir

    # Clean old cost archives: keep only 5 most recent
    cost_archives = sorted(
        base_dir.glob("cost-archive-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    archives_to_delete = cost_archives[5:]  # Keep 5, delete rest

    for archive_file in archives_to_delete:
        try:
            size = archive_file.stat().st_size
            if dry_run:
                logger.info("[DRY-RUN] Would remove old cost archive: %s", archive_file)
            else:
                logger.info("Removing old cost archive: %s", archive_file)
                archive_file.unlink()
            total_bytes += size
            total_removed += 1
        except OSError:
            pass

    return total_removed, total_bytes


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prune old LanceDB records and compact table fragments.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without modifying any data",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        metavar="N",
        help="Retention period in days for log tables (default: 90)",
    )
    args = parser.parse_args()

    if not VECTOR_DB_DIR.exists():
        logger.error("Vector DB directory not found: %s", VECTOR_DB_DIR)
        return 1

    try:
        import lancedb  # noqa: PLC0415
    except ImportError:
        logger.error("lancedb package is not installed in the current environment")
        return 1

    if args.dry_run:
        logger.info("=== DRY-RUN MODE — no data will be modified ===")

    logger.info("Connecting to LanceDB at %s", VECTOR_DB_DIR)
    try:
        db = lancedb.connect(str(VECTOR_DB_DIR))
    except Exception:
        logger.exception("Failed to connect to LanceDB")
        return 1

    stats: list[dict] = []
    had_error = False

    # Retention tables
    for table_name, fixed_days in RETENTION_TABLES.items():
        days = fixed_days if fixed_days is not None else args.retention_days
        try:
            result = prune_table(db, table_name, days, dry_run=args.dry_run)
        except Exception:
            logger.exception("Unexpected error processing table '%s'", table_name)
            had_error = True
            result = {
                "table": table_name,
                "rows_before": 0,
                "rows_deleted": 0,
                "rows_after": 0,
                "skipped": True,
                "skip_reason": "error (see log)",
            }
        stats.append(result)

    # Compact-only tables
    for table_name in COMPACT_ONLY_TABLES:
        try:
            result = compact_table(db, table_name, dry_run=args.dry_run)
        except Exception:
            logger.exception("Unexpected error compacting table '%s'", table_name)
            had_error = True
            result = {
                "table": table_name,
                "rows_before": 0,
                "rows_deleted": 0,
                "rows_after": 0,
                "skipped": True,
                "skip_reason": "error (see log)",
            }
        stats.append(result)

    # Temporary directory cleanup
    try:
        removed_count = clean_tmp_dirs(VECTOR_DB_DIR, dry_run=args.dry_run)
        verb = "would remove" if args.dry_run else "removed"
        logger.info("Temp/empty dirs %s: %d", verb, removed_count)
    except Exception:
        logger.exception("Error during temp directory cleanup")
        had_error = True

    # LLM cache cleanup
    llm_cache_dir = HOME / "security" / "llm-cache"
    try:
        cache_removed = clean_llm_cache(llm_cache_dir, dry_run=args.dry_run)
        verb = "would remove" if args.dry_run else "removed"
        logger.info("LLM cache entries %s: %d", verb, cache_removed)
    except Exception:
        logger.exception("Error during LLM cache cleanup")
        had_error = True

    # Cost archive cleanup
    cost_archive_dir = HOME / "security" / "cost-archives"
    if cost_archive_dir.exists():
        try:
            cost_removed = clean_cost_archives(cost_archive_dir, age_days=90, dry_run=args.dry_run)
            verb = "would remove" if args.dry_run else "removed"
            logger.info("Cost archives %s: %d", verb, cost_removed)
        except Exception:
            logger.exception("Error during cost archive cleanup")
            had_error = True

    # Disk-level cache cleanup (threat-cache, rag-cache, ip-cache, ioc-cache)
    security_dir = HOME / "security"
    try:
        cache_files_cleaned, cache_bytes_freed = cleanup_caches(security_dir, dry_run=args.dry_run)
        logger.info(
            "Disk cache cleanup: %d files, ~%s bytes freed",
            cache_files_cleaned,
            _format_bytes(cache_bytes_freed),
        )
    except Exception:
        logger.exception("Error during disk cache cleanup")
        had_error = True

    # Summary table
    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{prefix}=== LanceDB Prune Summary ===")
    print(f"{'Table':<20} {'Before':>8} {'Deleted':>8} {'After':>8}  Notes")
    print("-" * 62)
    for s in stats:
        name = s["table"]
        if s["skipped"]:
            print(f"{name:<20} {'—':>8} {'—':>8} {'—':>8}  SKIPPED ({s['skip_reason']})")
        elif name in COMPACT_ONLY_TABLES:
            print(f"{name:<20} {s['rows_before']:>8} {'—':>8} {s['rows_after']:>8}  (compact only)")
        else:
            print(f"{name:<20} {s['rows_before']:>8} {s['rows_deleted']:>8} {s['rows_after']:>8}")
    print()

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
