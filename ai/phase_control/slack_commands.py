"""Narrow Slack command parser for phase-control thread actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SlackCommandType(StrEnum):
    """Supported command verbs."""

    APPROVE = "approve"
    REJECT = "reject"
    HOLD = "hold"
    RESUME = "resume"
    CANCEL = "cancel"
    STATUS = "status"


@dataclass
class SlackCommand:
    """Parsed command payload."""

    command: SlackCommandType
    reason_text: str = ""


def parse_slack_command(
    text: str,
    *,
    channel: str,
    thread_ts: str | None,
    expected_channel: str | None,
    expected_thread_ts: str | None,
) -> SlackCommand | None:
    """Parse supported command only when event is in the tracked phase thread."""
    if expected_channel is None or expected_thread_ts is None:
        return None
    if channel != expected_channel or thread_ts != expected_thread_ts:
        return None

    raw = text.strip()
    if not raw:
        return None

    parts = raw.split(maxsplit=1)
    verb = parts[0].lower()
    if verb not in {c.value for c in SlackCommandType}:
        return None

    reason_text = parts[1].strip() if len(parts) > 1 else ""
    return SlackCommand(command=SlackCommandType(verb), reason_text=reason_text)
