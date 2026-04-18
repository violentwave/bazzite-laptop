"""Tests for deployment profiles (P137)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai.deployment_profiles import (
    CheckStatus,
    ProfileMode,
    _check_env_var,
    _check_key_presence,
    _check_port,
    _check_project_root,
    _check_service,
    _check_workbench_config,
    get_profile_summary,
    load_profile,
    validate_all_profiles,
)


class TestProfileLoading:
    def test_load_local_only_profile(self) -> None:
        profile = load_profile(ProfileMode.LOCAL_ONLY)
        assert profile is not None
        assert profile.mode == ProfileMode.LOCAL_ONLY
        assert profile.name == "Local Only (Laptop)"
        assert "bazzite-llm-proxy" in profile.required_services
        assert "bazzite-mcp-bridge" in profile.required_services

    def test_load_security_autopilot_profile(self) -> None:
        profile = load_profile(ProfileMode.SECURITY_AUTOPILOT)
        assert profile is not None
        assert profile.mode == ProfileMode.SECURITY_AUTOPILOT
        assert "keys" in profile.required_checks

    def test_load_agent_workbench_profile(self) -> None:
        profile = load_profile(ProfileMode.AGENT_WORKBENCH)
        assert profile is not None
        assert profile.mode == ProfileMode.AGENT_WORKBENCH
        assert "workbench-config" in profile.required_checks


class TestProfileValidation:
    @pytest.mark.parametrize("mode", ProfileMode)
    def test_all_profiles_load(self, mode: ProfileMode) -> None:
        profile = load_profile(mode)
        assert profile is not None

    def test_local_only_checks_mcp_health(self) -> None:
        profile = load_profile(ProfileMode.LOCAL_ONLY)
        assert profile is not None
        assert "mcp-health" in profile.required_checks

    def test_local_only_checks_llm_health(self) -> None:
        profile = load_profile(ProfileMode.LOCAL_ONLY)
        assert profile is not None
        assert "llm-health" in profile.required_checks


class TestFailClosed:
    @patch("ai.deployment_profiles._run_command")
    def test_missing_service_fails(self, mock_run) -> None:
        mock_run.return_value = (4, "inactive", "inactive")
        status, msg = _check_service("bazzite-nonexistent")
        assert status == CheckStatus.FAIL

    @patch("ai.deployment_profiles._run_command")
    def test_missing_port_fails(self, mock_run) -> None:
        mock_run.return_value = (1, "", "")
        status, msg = _check_port(9999)
        assert status == CheckStatus.FAIL

    @patch("ai.deployment_profiles.os.environ", {})
    def test_missing_env_var_fails(self) -> None:
        status, msg = _check_env_var("NONEXISTENT_VAR_XYZ")
        assert status == CheckStatus.FAIL

    def test_missing_project_root_fails(self, tmp_path: Path) -> None:
        with patch("ai.deployment_profiles._get_repo_root", return_value=tmp_path / "nonexistent"):
            status, msg = _check_project_root(tmp_path / "nonexistent")
            assert status == CheckStatus.FAIL


class TestKeyPresence:
    def test_missing_keys_env_fails(self, tmp_path: Path) -> None:
        keys_file = tmp_path / "keys.env"
        status, msg = _check_key_presence("OPENAI_API_KEY", keys_file)
        assert status == CheckStatus.FAIL

    def test_present_key_passes(self, tmp_path: Path) -> None:
        keys_file = tmp_path / "keys.env"
        keys_file.write_text("OPENAI_API_KEY=sk-test123\nANTHROPIC_API_KEY=sk-ant123\n")
        status, msg = _check_key_presence("OPENAI_API_KEY", keys_file)
        assert status == CheckStatus.OK


class TestWorkbenchConfig:
    def test_missing_config_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        status, msg = _check_workbench_config(config_file)
        assert status == CheckStatus.FAIL

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid}")
        status, msg = _check_workbench_config(config_file)
        assert status == CheckStatus.FAIL

    def test_valid_config_passes(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        config_file.write_text('{"projects": [{"id": "test"}]}')
        status, msg = _check_workbench_config(config_file)
        assert status == CheckStatus.OK


class TestSummary:
    def test_summary_counts_correct(self) -> None:
        profile = load_profile(ProfileMode.LOCAL_ONLY)
        assert profile is not None

        profile.checks = [
            type("Check", (), {"name": "c1", "status": CheckStatus.OK, "critical": True})(),
            type("Check", (), {"name": "c2", "status": CheckStatus.OK, "critical": True})(),
            type("Check", (), {"name": "c3", "status": CheckStatus.FAIL, "critical": True})(),
            type("Check", (), {"name": "c4", "status": CheckStatus.WARN, "critical": False})(),
        ]

        summary = get_profile_summary(profile)
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["warned"] == 1
        assert summary["critical_failed"] == ["c3"]
        assert summary["all_critical_passed"] is False


class TestSafetyProofs:
    def test_no_secret_values_exposed(self, tmp_path: Path) -> None:
        keys_file = tmp_path / "keys.env"
        keys_file.write_text("OPENAI_API_KEY=sk-VERY_SECRET_VALUE_12345678901234567890\n")

        import ai.deployment_profiles as dp

        with patch.object(dp, "_get_keys_env_path", return_value=keys_file):
            status, msg = _check_key_presence("OPENAI_API_KEY", keys_file)

        assert status == CheckStatus.OK
        assert "sk-VERY_SECRET" not in msg
        assert "sk-" not in msg.lower() or "hidden" in msg.lower()

    def test_fail_closed_on_missing_critical(self) -> None:
        profile = load_profile(ProfileMode.SECURITY_AUTOPILOT)
        assert profile is not None
        assert "keys" in profile.required_checks

        with patch("ai.deployment_profiles._get_keys_env_path") as mock_keys:
            mock_keys.return_value = Path("/nonexistent/keys.env")

            from ai.deployment_profiles import _check_key_presence

            status, msg = _check_key_presence("ANY_KEY", Path("/nonexistent/keys.env"))

        assert status == CheckStatus.FAIL

    def test_validate_all_profiles_returns_results(self) -> None:
        results = validate_all_profiles()
        assert len(results) == 3
        for mode in ProfileMode:
            assert mode in results
