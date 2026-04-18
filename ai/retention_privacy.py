"""Retention, privacy, and export controls for P136.

Adds retention rules, redaction controls, and safe export behavior for
Security Autopilot data, Agent Workbench artifacts, provenance records,
and audit events.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class DataClass(Enum):
    """Data classes requiring retention/privacy controls."""

    SECURITY_AUTOPILOT_FINDING = "security_autopilot_finding"
    SECURITY_AUTOPILOT_INCIDENT = "security_autopilot_incident"
    SECURITY_AUTOPILOT_AUDIT = "security_autopilot_audit"
    SECURITY_AUTOPILOT_EVIDENCE = "security_autopilot_evidence"
    WORKBENCH_SESSION = "workbench_session"
    WORKBENCH_ARTIFACT = "workbench_artifact"
    PROVENANCE_RECORD = "provenance_record"
    MEMORY_ENTRY = "memory_entry"


class RetentionPolicy(Enum):
    """Retention policy options."""

    EPHEMERAL = "ephemeral"  # Delete after session
    SHORT_TERM = "short_term"  # 7 days
    MEDIUM_TERM = "medium_term"  # 30 days
    LONG_TERM = "long_term"  # 90 days
    INDEFINITE = "indefinite"  # Keep until explicit deletion
    ACCEPTANCE_REQUIRED = "acceptance_required"  # Keep for acceptance evidence


@dataclass
class RetentionRule:
    """A retention rule for a data class."""

    data_class: DataClass
    policy: RetentionPolicy
    retention_days: int | None
    description: str
    can_delete: bool = True
    evidence_required: bool = False


@dataclass
class ExportConfig:
    """Configuration for safe export behavior."""

    redact_enabled: bool = True
    include_metadata: bool = True
    include_audit_trail: bool = True
    max_age_days: int | None = None
    workspace_filter: str | None = None
    session_filter: str | None = None


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    record_count: int
    export_path: Path | None
    redaction_summary: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


DEFAULT_RETENTION_RULES = [
    RetentionRule(
        data_class=DataClass.SECURITY_AUTOPILOT_FINDING,
        policy=RetentionPolicy.LONG_TERM,
        retention_days=90,
        description="Security findings from autopilot scans",
        can_delete=True,
    ),
    RetentionRule(
        data_class=DataClass.SECURITY_AUTOPILOT_INCIDENT,
        policy=RetentionPolicy.INDEFINITE,
        retention_days=None,
        description="Security incidents - keep until explicit resolution",
        can_delete=True,
        evidence_required=True,
    ),
    RetentionRule(
        data_class=DataClass.SECURITY_AUTOPILOT_AUDIT,
        policy=RetentionPolicy.MEDIUM_TERM,
        retention_days=30,
        description="Audit events from security autopilot",
        can_delete=True,
    ),
    RetentionRule(
        data_class=DataClass.SECURITY_AUTOPILOT_EVIDENCE,
        policy=RetentionPolicy.ACCEPTANCE_REQUIRED,
        retention_days=None,
        description="Evidence bundles for acceptance - explicit delete only",
        can_delete=False,
        evidence_required=True,
    ),
    RetentionRule(
        data_class=DataClass.WORKBENCH_SESSION,
        policy=RetentionPolicy.SHORT_TERM,
        retention_days=7,
        description="Workbench session logs",
        can_delete=True,
    ),
    RetentionRule(
        data_class=DataClass.WORKBENCH_ARTIFACT,
        policy=RetentionPolicy.MEDIUM_TERM,
        retention_days=30,
        description="Workbench artifacts and handoff notes",
        can_delete=True,
    ),
    RetentionRule(
        data_class=DataClass.PROVENANCE_RECORD,
        policy=RetentionPolicy.LONG_TERM,
        retention_days=90,
        description="Provenance graph records",
        can_delete=True,
    ),
    RetentionRule(
        data_class=DataClass.MEMORY_ENTRY,
        policy=RetentionPolicy.MEDIUM_TERM,
        retention_days=30,
        description="Memory entries",
        can_delete=True,
    ),
]

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-_\.]+"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"xoxb-[a-zA-Z0-9\-]+"),
]

_PATH_PATTERNS = [
    re.compile(r"(?:/var/home|/home|~)/[^\s\"'`]+"),
    re.compile(r"/root/[^\s\"'`]+"),
]

_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
    re.compile(r"\b\d{9}\b"),  # Some ID formats
]


class RetentionPrivacyManager:
    """Manages retention, privacy, and export controls.

    Provides:
    1. Retention rules per data class
    2. Redaction for secrets, paths, PII
    3. Safe export with redaction
    4. Context isolation (P129) aware operations
    """

    def __init__(
        self,
        rules: list[RetentionRule] | None = None,
        data_dir: Path | None = None,
    ):
        self.rules = rules or DEFAULT_RETENTION_RULES
        self.data_dir = data_dir or VECTOR_DB_DIR
        self._rule_map = {r.data_class: r for r in self.rules}

    def get_rule(self, data_class: DataClass) -> RetentionRule | None:
        """Get retention rule for a data class."""
        return self._rule_map.get(data_class)

    def redact(self, data: Any) -> Any:
        """Redact secrets, paths, and PII from data."""
        if isinstance(data, str):
            for pattern in _SECRET_PATTERNS:
                data = pattern.sub("[REDACTED]", data)
            for pattern in _PATH_PATTERNS:
                data = pattern.sub("[REDACTED]", data)
            for pattern in _PII_PATTERNS:
                data = pattern.sub("[REDACTED]", data)
            return data
        elif isinstance(data, dict):
            return {k: self.redact(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact(v) for v in data]
        return data

    def redact_with_summary(self, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
        """Redact data and return count of redactions per type."""
        summary = {"secrets": 0, "paths": 0, "pii": 0}

        def count_redactions(value: str) -> None:
            for pattern in _SECRET_PATTERNS:
                if pattern.search(value):
                    summary["secrets"] += 1
            for pattern in _PATH_PATTERNS:
                if pattern.search(value):
                    summary["paths"] += 1
            for pattern in _PII_PATTERNS:
                if pattern.search(value):
                    summary["pii"] += 1

        redacted = self.redact(data)

        if isinstance(data, dict):
            for _key, value in data.items():
                if isinstance(value, str):
                    count_redactions(value)
        elif isinstance(data, str):
            count_redactions(data)

        return redacted, summary

    def can_delete(self, data_class: DataClass) -> bool:
        """Check if a data class can be deleted."""
        rule = self.get_rule(data_class)
        if not rule:
            return True
        return rule.can_delete

    def is_evidence_required(self, data_class: DataClass) -> bool:
        """Check if data class requires explicit evidence deletion."""
        rule = self.get_rule(data_class)
        if not rule:
            return False
        return rule.evidence_required

    def get_retention_days(self, data_class: DataClass) -> int | None:
        """Get retention period in days for a data class."""
        rule = self.get_rule(data_class)
        if not rule:
            return None
        return rule.retention_days

    def create_export_bundle(
        self,
        data_class: DataClass,
        records: list[dict[str, Any]],
        config: ExportConfig,
    ) -> ExportResult:
        """Create a safe export bundle with redaction applied."""
        if not records:
            return ExportResult(
                success=True,
                record_count=0,
                export_path=None,
                redaction_summary={"secrets": 0, "paths": 0, "pii": 0},
            )

        rule = self.get_rule(data_class)

        if config.max_age_days and rule and rule.retention_days:
            cutoff = datetime.now(tz=UTC) - timedelta(days=config.max_age_days)
            filtered = []
            for record in records:
                created_at = record.get("created_at", "")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at)
                        if dt >= cutoff:
                            filtered.append(record)
                    except ValueError:
                        filtered.append(record)
            records = filtered

        redacted_records = []
        total_redactions = {"secrets": 0, "paths": 0, "pii": 0}

        for record in records:
            redacted, summary = self.redact_with_summary(record)
            redacted_records.append(redacted)
            for k, v in summary.items():
                total_redactions[k] += v

        metadata = {
            "exported_at": _utc_now(),
            "data_class": data_class.value,
            "record_count": len(redacted_records),
            "redaction_summary": total_redactions,
            "redaction_applied": config.redact_enabled,
        }

        if config.include_metadata:
            redacted_records.append({"_metadata": metadata})

        export_dir = self.data_dir / "exports"
        export_dir.mkdir(exist_ok=True)

        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{data_class.value}_{timestamp}.json"
        export_path = export_dir / filename

        import json

        with export_path.open("w", encoding="utf-8") as f:
            json.dump(redacted_records, f, indent=2)

        warnings = []
        if total_redactions["secrets"] > 0:
            warnings.append(f"Redacted {total_redactions['secrets']} secret-like values")
        if total_redactions["paths"] > 0:
            warnings.append(f"Redacted {total_redactions['paths']} file paths")
        if total_redactions["pii"] > 0:
            warnings.append(f"Redacted {total_redactions['pii']} potential PII")

        return ExportResult(
            success=True,
            record_count=len(redacted_records),
            export_path=export_path,
            redaction_summary=total_redactions,
            warnings=warnings,
        )

    def get_retention_summary(self) -> dict[str, Any]:
        """Get summary of all retention rules."""
        return {
            "data_classes": [
                {
                    "data_class": rule.data_class.value,
                    "policy": rule.policy.value,
                    "retention_days": rule.retention_days,
                    "description": rule.description,
                    "can_delete": rule.can_delete,
                    "evidence_required": rule.evidence_required,
                }
                for rule in self.rules
            ]
        }

    def apply_workspace_filter(
        self,
        records: list[dict[str, Any]],
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """Filter records by workspace (P129 context isolation)."""
        return [r for r in records if r.get("workspace_id") == workspace_id]

    def apply_session_filter(
        self,
        records: list[dict[str, Any]],
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Filter records by session."""
        return [r for r in records if r.get("session_id") == session_id]


_instance: RetentionPrivacyManager | None = None


def get_retention_manager() -> RetentionPrivacyManager:
    """Get or create the retention/privacy manager singleton."""
    global _instance
    if _instance is None:
        _instance = RetentionPrivacyManager()
    return _instance
