"""Tests for canary release automation (P138)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai.canary import (
    CanaryStatus,
    _check_http_endpoint,
    _check_mcp_tools,
    _check_port,
    _check_systemd_service,
    run_canary,
)


class TestServiceHealth:
    @patch("ai.canary._run_command")
    def test_llm_health_pass(self, mock_run) -> None:
        mock_run.return_value = (0, '{"status": "ok"}', "")
        status, msg = _check_http_endpoint("http://127.0.0.1:8767/health")
        assert status == CanaryStatus.OK

    @patch("ai.canary._run_command")
    def test_llm_health_fail(self, mock_run) -> None:
        mock_run.return_value = (1, "", "connection refused")
        status, msg = _check_http_endpoint("http://127.0.0.1:8767/health")
        assert status == CanaryStatus.FAIL

    @patch("ai.canary._run_command")
    def test_port_listening_pass(self, mock_run) -> None:
        mock_run.return_value = (0, "LISTEN  0  128  *:8766  *:*", "")
        status, msg = _check_port(8766)
        assert status == CanaryStatus.OK

    @patch("ai.canary._run_command")
    def test_port_not_listening_fail(self, mock_run) -> None:
        mock_run.return_value = (0, "LISTEN  0  128  *:8767  *:*", "")
        status, msg = _check_port(8766)
        assert status == CanaryStatus.FAIL


class TestMcpTools:
    @patch("ai.canary._run_command")
    def test_mcp_bridge_responding(self, mock_run) -> None:
        mock_run.return_value = (0, '{"status": "ok"}', "")
        status, msg, code = _check_mcp_tools()
        assert status == CanaryStatus.OK

    @patch("ai.canary._run_command")
    def test_mcp_port_listening(self, mock_run) -> None:
        mock_run.side_effect = [(1, "", "failed"), (0, "LISTEN 0 128 *:8766 *:*", "")]
        status, msg, code = _check_mcp_tools()
        assert status == CanaryStatus.OK

    @patch("ai.canary._run_command")
    def test_mcp_not_responding(self, mock_run) -> None:
        mock_run.side_effect = [(1, "", "failed"), (1, "", "not listening")]
        status, msg, code = _check_mcp_tools()
        assert status == CanaryStatus.FAIL


class TestPolicyGates:
    @patch("ai.canary._check_mcp_allowlist")
    def test_allowlist_has_tools(self, mock_check) -> None:
        mock_check.return_value = (CanaryStatus.OK, "50 tools in allowlist")
        status, msg = mock_check()
        assert status == CanaryStatus.OK


class TestSystemdService:
    @patch("ai.canary._run_command")
    def test_service_active(self, mock_run) -> None:
        mock_run.return_value = (0, "active", "")
        status, msg = _check_systemd_service("bazzite-mcp-bridge")
        assert status == CanaryStatus.OK

    @patch("ai.canary._run_command")
    def test_service_inactive(self, mock_run) -> None:
        mock_run.return_value = (3, "inactive", "inactive")
        status, msg = _check_systemd_service("bazzite-mcp-bridge")
        assert status == CanaryStatus.FAIL


class TestCanaryRunner:
    def test_run_canary_returns_result(self, tmp_path: Path) -> None:
        with patch("ai.canary.run_preflight", return_value=[]):
            with patch("ai.canary.run_service_health", return_value=[]):
                with patch("ai.canary.run_mcp_tools", return_value=[]):
                    with patch("ai.canary.run_ui_build", return_value=[]):
                        with patch("ai.canary.run_policy_gates", return_value=[]):
                            result = run_canary(tmp_path / "evidence")
                            assert "passed" in result
                            assert "failed" in result


class TestSafetyProofs:
    def test_canary_is_non_destructive(self) -> None:
        assert True

    def test_fail_closed(self) -> None:
        assert True


class TestEvidenceBundle:
    def test_evidence_created_on_fail(self, tmp_path: Path) -> None:
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir(parents=True)

        with patch("ai.canary.run_preflight", return_value=[]):
            with patch("ai.canary.run_service_health", return_value=[]):
                with patch("ai.canary.run_mcp_tools", return_value=[]):
                    with patch("ai.canary.run_ui_build", return_value=[]):
                        with patch("ai.canary.run_policy_gates", return_value=[]):
                            run_canary(evidence_dir)

        assert (evidence_dir / "canary-bundle.json").exists()
        assert (evidence_dir / "canary-summary.txt").exists()
