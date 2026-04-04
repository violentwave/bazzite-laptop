"""Tests for ai.security.alerts.SecurityAlertEvaluator."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import ai.security.alerts as alerts_mod
from ai.security.alerts import SecurityAlertEvaluator


class TestEvaluateEmpty:
    def test_empty_dir_returns_zero_counts(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            result = ev.evaluate()

        assert result["critical"] == 0
        assert result["high"] == 0
        assert result["medium"] == 0
        assert result["alerts"] == []

    def test_result_has_stale_scans_key(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            result = ev.evaluate()

        assert "stale_scans" in result


class TestCVEResults:
    def _write_cve_file(self, security_dir: Path, vulnerabilities: list) -> None:
        cve_file = security_dir / "cve-scan-results.json"
        cve_file.write_text(json.dumps({"vulnerabilities": vulnerabilities}))

    def test_critical_cvss_mapped(self, tmp_path: Path) -> None:
        self._write_cve_file(
            tmp_path,
            [
                {
                    "id": "CVE-2024-001",
                    "package": "foo",
                    "cvss_score": 9.8,
                    "summary": "Critical vuln",
                }
            ],
        )
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_cve_results()

        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"

    def test_high_cvss_mapped(self, tmp_path: Path) -> None:
        self._write_cve_file(
            tmp_path,
            [{"id": "CVE-2024-002", "package": "bar", "cvss_score": 7.5, "summary": "High vuln"}],
        )
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_cve_results()

        assert len(alerts) == 1
        assert alerts[0]["severity"] == "high"

    def test_low_cvss_mapped(self, tmp_path: Path) -> None:
        self._write_cve_file(
            tmp_path,
            [{"id": "CVE-2024-003", "package": "baz", "cvss_score": 2.1, "summary": "Low vuln"}],
        )
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_cve_results()

        assert len(alerts) == 1
        assert alerts[0]["severity"] == "low"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_cve_results()

        assert alerts == []

    def test_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        cve_file = tmp_path / "cve-scan-results.json"
        cve_file.write_text("NOT VALID JSON {{{{")
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_cve_results()

        assert alerts == []


class TestReleaseAlerts:
    def _write_release_file(self, security_dir: Path, releases: list) -> None:
        release_file = security_dir / "release-watch.json"
        release_file.write_text(json.dumps({"releases": releases}))

    def test_security_keyword_triggers_alert(self, tmp_path: Path) -> None:
        self._write_release_file(
            tmp_path,
            [
                {
                    "tag_name": "v1.2.3",
                    "repo": "example/pkg",
                    "description": "This release includes a security fix",
                    "published_at": datetime.now(UTC).isoformat(),
                }
            ],
        )
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_release_alerts()

        assert len(alerts) == 1
        assert alerts[0]["severity"] == "high"

    def test_non_security_release_not_triggered(self, tmp_path: Path) -> None:
        self._write_release_file(
            tmp_path,
            [
                {
                    "tag_name": "v1.2.4",
                    "repo": "example/pkg",
                    "description": "Bug fixes and performance improvements",
                    "published_at": datetime.now(UTC).isoformat(),
                }
            ],
        )
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_release_alerts()

        assert alerts == []

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            alerts = ev._check_release_alerts()

        assert alerts == []


class TestDeduplication:
    def _make_alert(self, cve_id: str = "CVE-2024-X", package: str = "foo") -> dict:
        return {
            "cve_id": cve_id,
            "package": package,
            "severity": "high",
            "description": "Test alert",
            "recommended_action": "Update",
            "first_seen": datetime.now(UTC).isoformat(),
            "source": "cve-scanner",
        }

    def test_new_alert_passes_through(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            result = ev._deduplicate([self._make_alert()])

        assert len(result) == 1

    def test_recent_duplicate_suppressed(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        recent_ts = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            ev.dedup_state = {"CVE-2024-X:foo": recent_ts}
            result = ev._deduplicate([self._make_alert()])

        assert result == []

    def test_old_alert_passes_through(self, tmp_path: Path) -> None:
        dedup_file = tmp_path / ".alert-dedup.json"
        old_ts = (datetime.now(UTC) - timedelta(days=8)).isoformat()
        with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
            ev = SecurityAlertEvaluator(security_dir=tmp_path)
            ev.dedup_state = {"CVE-2024-X:foo": old_ts}
            result = ev._deduplicate([self._make_alert()])

        assert len(result) == 1


class TestSaveResults:
    def test_results_written_to_file(self, tmp_path: Path) -> None:
        alerts_file = tmp_path / "alerts.json"
        dedup_file = tmp_path / ".alert-dedup.json"
        payload = {"timestamp": "2026-01-01T00:00:00+00:00", "critical": 0, "high": 1}
        with patch.object(alerts_mod, "ALERTS_FILE", alerts_file):
            with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
                ev = SecurityAlertEvaluator(security_dir=tmp_path)
                ev._save_results(payload)

        assert alerts_file.exists()
        written = json.loads(alerts_file.read_text())
        assert written["high"] == 1

    def test_no_tmp_file_left_behind(self, tmp_path: Path) -> None:
        alerts_file = tmp_path / "alerts.json"
        dedup_file = tmp_path / ".alert-dedup.json"
        payload = {"timestamp": "2026-01-01T00:00:00+00:00", "critical": 0}
        with patch.object(alerts_mod, "ALERTS_FILE", alerts_file):
            with patch.object(alerts_mod, "DEDUP_FILE", dedup_file):
                ev = SecurityAlertEvaluator(security_dir=tmp_path)
                ev._save_results(payload)

        tmp_file = alerts_file.with_suffix(".tmp")
        assert not tmp_file.exists()
