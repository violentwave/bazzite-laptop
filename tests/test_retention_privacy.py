"""Tests for retention, privacy, and export controls (P136)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.retention_privacy import (
    DEFAULT_RETENTION_RULES,
    DataClass,
    ExportConfig,
    RetentionPrivacyManager,
)


def redact(data):
    return RetentionPrivacyManager().redact(data)


def redact_with_summary(data):
    return RetentionPrivacyManager().redact_with_summary(data)


@pytest.fixture
def manager(tmp_path: Path) -> RetentionPrivacyManager:
    return RetentionPrivacyManager(data_dir=tmp_path)


class TestDefaultRetentionRules:
    def test_rules_exist(self) -> None:
        assert len(DEFAULT_RETENTION_RULES) > 0

    def test_has_security_rules(self) -> None:
        classes = [r.data_class for r in DEFAULT_RETENTION_RULES]
        assert DataClass.SECURITY_AUTOPILOT_FINDING in classes
        assert DataClass.SECURITY_AUTOPILOT_AUDIT in classes

    def test_has_workbench_rules(self) -> None:
        classes = [r.data_class for r in DEFAULT_RETENTION_RULES]
        assert DataClass.WORKBENCH_SESSION in classes
        assert DataClass.WORKBENCH_ARTIFACT in classes


class TestRedactionSecrets:
    def test_redacts_openai_key(self) -> None:
        data = {"key": "sk-abc123def456ghi789jkl012mno345"}
        result = redact(data)
        assert result["key"] == "[REDACTED]"


class TestRedactionPaths:
    def test_redacts_home_path(self) -> None:
        data = {"path": "/home/user/documents/file.txt"}
        result = redact(data)
        assert result["path"] == "[REDACTED]"

    def test_redacts_var_home(self) -> None:
        data = {"path": "/var/home/lch/projects/file.txt"}
        result = redact(data)
        assert result["path"] == "[REDACTED]"

    def test_redacts_var_home_direct(self) -> None:
        data = {"file": "/var/home/lch/file.txt"}
        result = redact(data)
        assert result["file"] == "[REDACTED]"


class TestRedactionPII:
    def test_redacts_ssn(self) -> None:
        data = {"id": "123-45-6789"}
        result = redact(data)
        assert result["id"] == "[REDACTED]"


class TestRedactionWithSummary:
    def test_returns_summary_counts_secret(self) -> None:
        data = {"api_key": "sk-abc123def456ghi789jkl012"}
        redacted, summary = redact_with_summary(data)
        assert summary["secrets"] >= 1

    def test_returns_summary_counts_path(self) -> None:
        data = {"path": "/home/user/file.txt"}
        redacted, summary = redact_with_summary(data)
        assert summary["paths"] >= 1


class TestRetentionRules:
    def test_get_rule(self, manager: RetentionPrivacyManager) -> None:
        rule = manager.get_rule(DataClass.SECURITY_AUTOPILOT_FINDING)
        assert rule is not None

    def test_can_delete(self, manager: RetentionPrivacyManager) -> None:
        assert manager.can_delete(DataClass.SECURITY_AUTOPILOT_FINDING) is True

    def test_evidence_not_deletable(self, manager: RetentionPrivacyManager) -> None:
        assert manager.can_delete(DataClass.SECURITY_AUTOPILOT_EVIDENCE) is False

    def test_evidence_required_true(self, manager: RetentionPrivacyManager) -> None:
        assert manager.is_evidence_required(DataClass.SECURITY_AUTOPILOT_EVIDENCE) is True

    def test_get_retention_days(self, manager: RetentionPrivacyManager) -> None:
        days = manager.get_retention_days(DataClass.SECURITY_AUTOPILOT_FINDING)
        assert days == 90


class TestExportBundle:
    def test_create_export_creates_file(
        self, manager: RetentionPrivacyManager, tmp_path: Path
    ) -> None:
        records = [
            {"id": "1", "title": "Test", "created_at": "2026-04-17T10:00:00Z"},
        ]
        config = ExportConfig(redact_enabled=True, include_metadata=False)
        result = manager.create_export_bundle(DataClass.SECURITY_AUTOPILOT_FINDING, records, config)

        assert result.success is True
        assert result.record_count == 1
        assert result.export_path is not None

    def test_redaction_in_export(self, manager: RetentionPrivacyManager, tmp_path: Path) -> None:
        records = [
            {"id": "1", "api_key": "sk-abc123def456ghi789jkl012"},
        ]
        config = ExportConfig(redact_enabled=True, include_metadata=False)
        result = manager.create_export_bundle(DataClass.SECURITY_AUTOPILOT_FINDING, records, config)

        content = json.loads(result.export_path.read_text())
        assert content[0]["api_key"] == "[REDACTED]"

    def test_export_empty_records(self, manager: RetentionPrivacyManager, tmp_path: Path) -> None:
        result = manager.create_export_bundle(
            DataClass.SECURITY_AUTOPILOT_FINDING, [], ExportConfig()
        )
        assert result.success is True
        assert result.record_count == 0


class TestContextFilters:
    def test_workspace_filter(self, manager: RetentionPrivacyManager) -> None:
        records = [
            {"workspace_id": "ws1", "id": "1"},
            {"workspace_id": "ws2", "id": "2"},
        ]
        filtered = manager.apply_workspace_filter(records, "ws1")
        assert len(filtered) == 1

    def test_session_filter(self, manager: RetentionPrivacyManager) -> None:
        records = [
            {"session_id": "s1", "id": "1"},
            {"session_id": "s2", "id": "2"},
        ]
        filtered = manager.apply_session_filter(records, "s1")
        assert len(filtered) == 1


class TestSafetyProofs:
    def test_no_raw_secrets_in_export(
        self, manager: RetentionPrivacyManager, tmp_path: Path
    ) -> None:
        records = [{"api_key": "sk-abc123def456ghi789jkl012"}]
        config = ExportConfig(redact_enabled=True, include_metadata=False)
        result = manager.create_export_bundle(DataClass.SECURITY_AUTOPILOT_AUDIT, records, config)
        content = json.loads(result.export_path.read_text())
        assert "sk-" not in str(content)
        assert result.redaction_summary["secrets"] >= 1

    def test_no_raw_paths_in_export(self, manager: RetentionPrivacyManager, tmp_path: Path) -> None:
        records = [{"path": "/home/user/secret.txt"}]
        config = ExportConfig(redact_enabled=True, include_metadata=False)
        result = manager.create_export_bundle(DataClass.WORKBENCH_SESSION, records, config)
        content = json.loads(result.export_path.read_text())
        assert "/home/" not in str(content)

    def test_evidence_not_auto_deletable(self, manager: RetentionPrivacyManager) -> None:
        assert manager.can_delete(DataClass.SECURITY_AUTOPILOT_EVIDENCE) is False

    def test_warnings_for_redactions(
        self, manager: RetentionPrivacyManager, tmp_path: Path
    ) -> None:
        records = [{"api_key": "sk-abc123def456ghi789jkl012"}]
        config = ExportConfig(redact_enabled=True, include_metadata=False)
        result = manager.create_export_bundle(DataClass.SECURITY_AUTOPILOT_AUDIT, records, config)
        assert len(result.warnings) >= 1
