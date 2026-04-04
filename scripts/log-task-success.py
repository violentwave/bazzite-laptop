#!/usr/bin/env python3
"""CLI script to log successful task patterns to LanceDB.

Usage:
    python scripts/log-task-success.py --description "..." --approach "..." --outcome "..."

All fields except --description, --approach, --outcome are optional.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
import sys

from ai.learning.task_logger import TaskLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Log a successful task pattern to LanceDB.",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Task description",
    )
    parser.add_argument(
        "--approach",
        required=True,
        help="Implementation approach taken",
    )
    parser.add_argument(
        "--outcome",
        required=True,
        help="Result/outcome of the task",
    )
    parser.add_argument(
        "--files",
        help="Comma-separated file paths (or 'none')",
    )
    parser.add_argument(
        "--tools",
        help="Comma-separated tool names (or 'none')",
    )
    parser.add_argument(
        "--tests-added",
        type=int,
        default=0,
        help="Number of tests added",
    )
    parser.add_argument(
        "--phase",
        help="Phase identifier (e.g., P22)",
    )
    parser.add_argument(
        "--agent",
        default="claude-code",
        help="Agent name",
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=0,
        help="Estimated duration in minutes",
    )
    parser.add_argument(
        "--token-estimate",
        type=int,
        default=0,
        help="Estimated token count",
    )
    parser.add_argument(
        "--db-path",
        help="Path to LanceDB directory (optional)",
    )

    args = parser.parse_args()

    files = []
    if args.files:
        if args.files.lower() != "none":
            files = [f.strip() for f in args.files.split(",") if f.strip()]

    tools = []
    if args.tools:
        if args.tools.lower() != "none":
            tools = [t.strip() for t in args.tools.split(",") if t.strip()]

    try:
        logger_obj = TaskLogger(db_path=args.db_path)
        task_id = logger_obj.log_success(
            description=args.description,
            approach=args.approach,
            outcome=args.outcome,
            files_touched=files if files else None,
            tools_used=tools if tools else None,
            tests_added=args.tests_added,
            phase=args.phase,
            agent=args.agent,
            duration_minutes=args.duration_minutes,
            token_estimate=args.token_estimate,
        )
        print(f"✓ Logged task [{task_id}] to task_patterns")
        return 0
    except Exception as e:
        logger.error("Failed to log task: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
