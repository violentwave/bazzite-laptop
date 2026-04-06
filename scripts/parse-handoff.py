#!/usr/bin/env python
"""CLI for parsing HANDOFF.md and populating knowledge base.

Usage:
    python scripts/parse-handoff.py --dry-run
    python scripts/parse-handoff.py --since-date 2026-01-01
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.config import APP_NAME, PROJECT_ROOT
from ai.learning.handoff_parser import (
    entry_to_task_pattern,
    filter_by_date,
    parse_handoff,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(APP_NAME)


def main():
    parser = argparse.ArgumentParser(description="Parse HANDOFF.md into knowledge base")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be logged, don't write"
    )
    parser.add_argument(
        "--since-date", type=str, help="Only process entries after this date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--handoff-path", type=Path, default=PROJECT_ROOT / "HANDOFF.md", help="Path to HANDOFF.md"
    )
    args = parser.parse_args()

    if not args.handoff_path.exists():
        logger.error("HANDOFF.md not found at %s", args.handoff_path)
        return 1

    logger.info("Parsing %s...", args.handoff_path)
    entries = parse_handoff(args.handoff_path)
    logger.info("Found %d entries", len(entries))

    if args.since_date:
        entries = filter_by_date(entries, args.since_date)
        logger.info("Filtered to %d entries after %s", len(entries), args.since_date)

    if not entries:
        logger.warning("No entries to process")
        return 0

    logged_count = 0

    for entry in entries:
        logger.info("")
        logger.info("=== %s (%s) ===", entry.agent, entry.timestamp)
        logger.info("Summary: %s", entry.summary[:100] if entry.summary else "(none)")
        logger.info("Done: %d tasks", len(entry.done_tasks))
        logger.info("Open: %d tasks", len(entry.open_tasks))

        if entry.done_tasks:
            for task in entry.done_tasks:
                logger.info("  - %s", task[:80])

        if args.dry_run:
            logger.info("[DRY RUN] Would log to knowledge base")
            continue

        try:
            from ai.learning.task_logger import TaskLogger

            tl = TaskLogger()
            pattern = entry_to_task_pattern(entry)
            tl.log_success(
                description=pattern.get("prompt", "")[:500],
                approach=pattern.get("task_type", "handoff"),
                outcome=pattern.get("result", "")[:500],
                phase="P31",
                duration_minutes=int(pattern.get("duration_seconds", 0) / 60),
            )
            logged_count += 1
        except Exception as e:
            logger.error("Failed to log entry: %s", e)

    logger.info("")
    logger.info("Logged %d entries to knowledge base", logged_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
