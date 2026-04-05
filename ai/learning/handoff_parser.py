"""Handoff parsing for automatic knowledge base population."""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)


@dataclass
class HandoffEntry:
    """Parsed handoff entry."""

    timestamp: str
    agent: str
    summary: str
    done_tasks: list[str]
    open_tasks: list[str]
    commit_hash: str | None = None


def parse_handoff(path: Path | str) -> list[HandoffEntry]:
    """Parse a HANDOFF.md file into structured entries.

    Args:
        path: Path to the HANDOFF.md file.

    Returns:
        List of HandoffEntry objects.
    """
    content = Path(path).read_text()
    entries: list[HandoffEntry] = []

    current_timestamp = ""
    current_agent = ""
    current_summary = ""
    done_tasks: list[str] = []
    open_tasks: list[str] = []

    lines = content.split("\n")
    for line in lines:
        line = line.strip()

        # Timestamp line: ### YYYY-MM-DDTHH:MM:SSZ — agent
        ts_match = re.match(r"^### (\d{4}-\d{2}-\d{2}T[\d:]+Z) — (.+)$", line)
        if ts_match:
            # Save previous entry if we have content
            if current_timestamp:
                entries.append(
                    HandoffEntry(
                        timestamp=current_timestamp,
                        agent=current_agent,
                        summary=current_summary,
                        done_tasks=done_tasks.copy(),
                        open_tasks=open_tasks.copy(),
                    )
                )
            # Start new entry
            current_timestamp = ts_match.group(1)
            current_agent = ts_match.group(2)
            current_summary = ""
            done_tasks = []
            open_tasks = []
            continue

        # Summary line: starts with [
        if line.startswith("["):
            summary_match = re.match(r"^\[(.+)\]$", line)
            if summary_match:
                current_summary = summary_match.group(1)
            continue

        # Task lines: - [ ] or - [x]
        task_match = re.match(r"^- \[([ x])\] (.+)$", line)
        if task_match:
            task_text = task_match.group(2)
            if task_match.group(1) == "x":
                done_tasks.append(task_text)
            else:
                open_tasks.append(task_text)
            continue

    # Don't forget the last entry
    if current_timestamp:
        entries.append(
            HandoffEntry(
                timestamp=current_timestamp,
                agent=current_agent,
                summary=current_summary,
                done_tasks=done_tasks.copy(),
                open_tasks=open_tasks.copy(),
            )
        )

    return entries


def correlate_with_commits(entry: HandoffEntry, repo_path: str | Path | None = None) -> list[str]:
    """Correlate a handoff entry with changed files using pydriller.

    Args:
        entry: The handoff entry to correlate.
        repo_path: Path to the git repository.

    Returns:
        List of changed file paths.
    """
    if repo_path is None:
        return []

    try:
        from pydriller import Repository

        repo = Repository(repo_path)
        changed_files = []

        # Find commits around this entry's timestamp
        entry_dt = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        for commit in repo.traverse_commits():
            commit_dt = datetime.fromtimestamp(commit.author_time)
            if abs((commit_dt - entry_dt).total_seconds()) < 3600:  # Within 1 hour
                for f in commit.modified_files:
                    changed_files.append(f.new_path or f.old_path)

        return list(set(changed_files))[:50]  # Limit to 50 files
    except Exception as e:
        logger.debug("Could not correlate commits: %s", e)
        return []


def entry_to_task_pattern(entry: HandoffEntry) -> dict[str, Any]:
    """Convert a handoff entry to a task pattern dict.

    Args:
        entry: The handoff entry to convert.

    Returns:
        Dict ready for TaskLogger.log_success().
    """
    return {
        "task_type": "handoff",
        "prompt": entry.summary,
        "result": "; ".join(entry.done_tasks) if entry.done_tasks else entry.summary,
        "success": True,
        "duration_seconds": 0,
        "tokens_used": 0,
        "metadata": {
            "agent": entry.agent,
            "timestamp": entry.timestamp,
            "open_tasks": entry.open_tasks,
            "commit_hash": entry.commit_hash,
        },
    }


def filter_by_date(
    entries: list[HandoffEntry], since_date: str | None = None
) -> list[HandoffEntry]:
    """Filter entries by date.

    Args:
        entries: List of handoff entries.
        since_date: ISO date string (YYYY-MM-DD), entries before this are excluded.

    Returns:
        Filtered list of entries.
    """
    if not since_date:
        return entries

    from datetime import datetime

    cutoff = datetime.fromisoformat(since_date).replace(tzinfo=UTC)
    filtered = []

    for entry in entries:
        entry_dt = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        if entry_dt >= cutoff:
            filtered.append(entry)

    return filtered
