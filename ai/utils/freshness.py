"""Freshness utilities for runtime JSON files.

Provides timestamp stamping and age formatting for data freshness reporting.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def stamp_generated_at(payload: dict) -> dict:
    """Add generated_at timestamp to payload dict.

    Args:
        payload: Dictionary to stamp with timestamp.

    Returns:
        The same dict with generated_at field added/modified.
    """
    payload["generated_at"] = datetime.now(UTC).isoformat()
    return payload


def parse_generated_at(timestamp_str: str | None) -> datetime | None:
    """Parse ISO8601 timestamp string.

    Args:
        timestamp_str: ISO8601 timestamp or None.

    Returns:
        Parsed datetime or None if invalid/missing.
    """
    if not timestamp_str:
        return None
    try:
        # Handle both with and without timezone
        timestamp_str = timestamp_str.replace("Z", "+00:00")
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return None


def format_freshness_age(generated_at: datetime | str | None) -> str | None:
    """Format age of data for display.

    Returns None if data is fresh (<1 hour) or if timestamp is invalid.
    Returns concise age string if data is stale (>=1 hour).

    Args:
        generated_at: Timestamp as datetime, ISO string, or None.

    Returns:
        Age string like "Data is 3.2 hours old." or None if fresh/invalid.
    """
    if generated_at is None:
        return None

    if isinstance(generated_at, str):
        generated_at = parse_generated_at(generated_at)
        if generated_at is None:
            return None

    try:
        now = datetime.now(UTC)
        if generated_at.tzinfo is None:
            # Assume UTC if no timezone
            age = now - generated_at.replace(tzinfo=UTC)
        else:
            age = now - generated_at
    except (TypeError, AttributeError):
        return None

    hours = age.total_seconds() / 3600

    # Only report if >= 1 hour old
    if hours < 1:
        return None

    if hours < 24:
        return f"Data is {hours:.1f} hours old."
    else:
        days = hours / 24
        return f"Data is {days:.1f} days old."


def read_json_with_freshness(path: Path) -> tuple[dict | None, str | None]:
    """Read JSON file and return data with freshness warning if stale.

    Args:
        path: Path to JSON file.

    Returns:
        Tuple of (data dict or None if error, freshness warning or None).
    """
    import json

    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None, None

    if not isinstance(data, dict):
        return data, None

    freshness = format_freshness_age(data.get("generated_at"))
    return data, freshness
