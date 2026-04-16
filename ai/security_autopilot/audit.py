"""Audit and evidence handling for Security Autopilot."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai.config import SECURITY_DIR
from ai.security_autopilot.models import AuditEvent, EvidenceBundle, EvidenceItem, next_id

_REDACTION_TOKEN = "[REDACTED]"  # noqa: S105


class EvidenceManager:
    """Create redacted evidence bundles for safe storage and audit."""

    SECRET_PATTERNS = (
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    )

    def create_bundle(self, source: str, raw_items: dict[str, Any]) -> EvidenceBundle:
        items: list[EvidenceItem] = []
        redaction_count = 0
        for key, value in raw_items.items():
            redacted_value, count = self._redact_value(value)
            items.append(
                EvidenceItem(
                    item_id=next_id("evidence"),
                    key=key,
                    value=redacted_value,
                    redacted=count > 0,
                )
            )
            redaction_count += count
        return EvidenceBundle(
            bundle_id=next_id("bundle"),
            source=source,
            items=items,
            redaction_count=redaction_count,
        )

    def _redact_value(self, value: Any) -> tuple[Any, int]:
        if isinstance(value, str):
            redacted = value
            count = 0
            for pattern in self.SECRET_PATTERNS:
                redacted, replacements = pattern.subn(_REDACTION_TOKEN, redacted)
                count += replacements
            return redacted, count

        if isinstance(value, dict):
            total = 0
            redacted_dict: dict[str, Any] = {}
            for key, inner_value in value.items():
                redacted_inner, count = self._redact_value(inner_value)
                redacted_dict[key] = redacted_inner
                total += count
            return redacted_dict, total

        if isinstance(value, list):
            total = 0
            redacted_list: list[Any] = []
            for item in value:
                redacted_item, count = self._redact_value(item)
                redacted_list.append(redacted_item)
                total += count
            return redacted_list, total

        return value, 0


class AuditLedger:
    """Append-only JSONL audit log with lightweight hash chaining."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SECURITY_DIR / "autopilot-audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: AuditEvent) -> AuditEvent:
        prev_hash = self._read_last_hash()
        payload = asdict(event)
        payload["prev_hash"] = prev_hash
        payload["event_hash"] = ""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        payload["event_hash"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")

        event.prev_hash = payload["prev_hash"]
        event.event_hash = payload["event_hash"]
        return event

    def _read_last_hash(self) -> str:
        if not self.path.exists():
            return ""
        with self.path.open(encoding="utf-8") as handle:
            lines = [line for line in handle.read().splitlines() if line.strip()]
        if not lines:
            return ""
        try:
            last = json.loads(lines[-1])
        except json.JSONDecodeError:
            return ""
        return str(last.get("event_hash", ""))
