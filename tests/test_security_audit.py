"""Unit tests for ai/agents/security_audit.py."""

import json
import os
import time
from unittest.mock import MagicMock, patch


class TestRanRecently:
    def test_no_files_returns_false(self, tmp_path):
        from ai.agents.security_audit import _ran_recently

        assert not _ran_recently(tmp_path, "*.log")

    def test_recent_file_returns_true(self, tmp_path):
        (tmp_path / "scan-2026-03-21.log").write_text("test data")

        from ai.agents.security_audit import _ran_recently

        assert _ran_recently(tmp_path, "scan-*.log", within_s=3600)

    def test_old_file_returns_false(self, tmp_path):
        f = tmp_path / "scan-old.log"
        f.write_text("test data")
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(f, (old_time, old_time))

        from ai.agents.security_audit import _ran_recently

        assert not _ran_recently(tmp_path, "scan-*.log", within_s=3600)

    def test_picks_most_recent_file(self, tmp_path):
        old = tmp_path / "scan-old.log"
        old.write_text("old")
        old_time = time.time() - 7200
        os.utime(old, (old_time, old_time))

        recent = tmp_path / "scan-new.log"
        recent.write_text("new")  # mtime = now

        from ai.agents.security_audit import _ran_recently

        assert _ran_recently(tmp_path, "scan-*.log", within_s=3600)


class TestTriggerSystemctl:
    def test_success_returns_true(self):
        with patch("ai.agents.security_audit.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            from ai.agents.security_audit import _trigger_systemctl

            assert _trigger_systemctl("clamav-quick.service")
            mock_run.assert_called_once_with(
                ["systemctl", "start", "clamav-quick.service"],
                capture_output=True,
                timeout=10,
            )

    def test_nonzero_exit_returns_false(self):
        with patch("ai.agents.security_audit.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr=b"access denied"
            )

            from ai.agents.security_audit import _trigger_systemctl

            assert not _trigger_systemctl("clamav-quick.service")

    def test_exception_returns_false(self):
        with patch("ai.agents.security_audit.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("systemctl not found")

            from ai.agents.security_audit import _trigger_systemctl

            assert not _trigger_systemctl("clamav-quick.service")


class TestRunAudit:
    def _mock_rag(self, answer: str) -> MagicMock:
        mock = MagicMock(return_value=answer)
        return mock

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=False)
    @patch("ai.agents.security_audit._trigger_systemctl", return_value=True)
    def test_triggers_when_stale(
        self, mock_trigger, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.return_value = {"health": 1, "scans": 1, "freshclam": 0}
        mock_rag.return_value = "System is clean. No issues found in the last 24 hours."

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", tmp_path / "reports"):
            from ai.agents.security_audit import run_audit

            result = run_audit()

        assert result["scan_triggered"] is True
        assert result["health_triggered"] is True
        assert result["logs_ingested"] is True
        assert result["status"] == "clean"
        assert "timestamp" in result

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=True)
    def test_skips_triggers_when_recent(
        self, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.return_value = {"health": 0, "scans": 0, "freshclam": 0}
        mock_rag.return_value = "No issues found."

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", tmp_path / "reports"):
            from ai.agents.security_audit import run_audit

            result = run_audit()

        assert result["scan_triggered"] is False
        assert result["health_triggered"] is False

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=True)
    def test_status_issues_on_threat_keywords(
        self, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.return_value = {}
        mock_rag.return_value = "Threat detected: malware found in /tmp/evil"

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", tmp_path / "reports"):
            from ai.agents.security_audit import run_audit

            result = run_audit()

        assert result["status"] == "issues"

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=True)
    def test_status_warnings_on_warning_keywords(
        self, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.return_value = {}
        mock_rag.return_value = "Temperature warning: CPU spike at 88°C"

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", tmp_path / "reports"):
            from ai.agents.security_audit import run_audit

            result = run_audit()

        assert result["status"] == "warnings"

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=True)
    def test_report_written_atomically(
        self, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.return_value = {}
        mock_rag.return_value = "All clear."
        reports_dir = tmp_path / "reports"

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", reports_dir):
            from ai.agents.security_audit import run_audit

            run_audit()

        files = list(reports_dir.glob("audit-*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert set(data.keys()) == {
            "timestamp", "scan_triggered", "health_triggered",
            "logs_ingested", "rag_summary", "status",
        }

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=True)
    def test_ingest_failure_sets_flag_false(
        self, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.side_effect = RuntimeError("LanceDB unavailable")
        mock_rag.return_value = "No data."

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", tmp_path / "reports"):
            from ai.agents.security_audit import run_audit

            result = run_audit()

        assert result["logs_ingested"] is False

    @patch("ai.agents.security_audit._do_ingest")
    @patch("ai.agents.security_audit._do_rag_query")
    @patch("ai.agents.security_audit._ran_recently", return_value=True)
    def test_rag_failure_sets_fallback_message(
        self, mock_ran, mock_rag, mock_ingest, tmp_path
    ):
        mock_ingest.return_value = {}
        mock_rag.side_effect = RuntimeError("embedding unavailable")

        with patch("ai.agents.security_audit.AUDIT_REPORTS_DIR", tmp_path / "reports"):
            from ai.agents.security_audit import run_audit

            result = run_audit()

        assert "RAG unavailable" in result["rag_summary"]
        assert result["status"] == "clean"  # no threat keywords in fallback message
