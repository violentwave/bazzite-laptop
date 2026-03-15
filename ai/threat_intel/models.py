"""Data models for the threat intelligence lookup engine."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ThreatReport:
    """Structured threat intelligence report for a single file hash.

    Populated by provider-specific lookup functions in lookup.py.
    Serialized to JSONL for the enriched hashes log.
    """

    hash: str
    filename: str = ""
    source: str = ""
    family: str = ""
    category: str = ""
    detection_ratio: str = ""
    risk_level: str = "unknown"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    vt_link: str = ""
    timestamp: str = ""
    raw_data: dict = field(default_factory=dict)

    def to_jsonl(self) -> str:
        """Serialize to a JSON string for quarantine-hashes-enriched.jsonl.

        Excludes raw_data to keep the JSONL file compact.
        """
        data = {
            "hash": self.hash,
            "filename": self.filename,
            "source": self.source,
            "family": self.family,
            "category": self.category,
            "detection_ratio": self.detection_ratio,
            "risk_level": self.risk_level,
            "description": self.description,
            "tags": self.tags,
            "vt_link": self.vt_link,
            "timestamp": self.timestamp or datetime.now(tz=UTC).isoformat(),
        }
        return json.dumps(data)

    @property
    def has_data(self) -> bool:
        """True if this report contains actual threat intelligence data."""
        return bool(self.source) and self.source != "none"
