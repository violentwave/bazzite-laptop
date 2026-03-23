"""Unit tests for ai/system/fedora_updates.py."""

import json
from unittest.mock import MagicMock, patch

_MOD = "ai.system.fedora_updates"

_BODHI_RESPONSE = {
    "updates": [
        {
            "alias": "FEDORA-2026-abcd1234",
            "title": "curl-8.0.1-1.fc41",
            "type": "security",
            "severity": "high",
            "status": "stable",
            "date_submitted": "2026-03-18T10:00:00",
            "builds": [{"name": "curl"}],
        },
        {
            "alias": "FEDORA-2026-bug5678",
            "title": "bash-5.2.15-2.fc41",
            "type": "bugfix",
            "severity": "unspecified",
            "status": "testing",
            "date_submitted": "2026-03-19T08:00:00",
            "builds": [{"name": "bash"}],
        },
        {
            "alias": "FEDORA-2026-enh9999",
            "title": "vim-9.0-1.fc41",
            "type": "enhancement",
            "severity": "unspecified",
            "status": "stable",
            "date_submitted": "2026-03-20T12:00:00",
            "builds": [{"name": "vim"}],
        },
    ]
}


def _make_rl(can_call=True):
    rl = MagicMock()
    rl.can_call.return_value = can_call
    return rl


def _fake_resp(data=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data or {"updates": []}
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# 1. Bodhi response parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestParseUpdate:
    def test_extracts_alias_and_type(self):
        from ai.system.fedora_updates import _parse_update

        raw = _BODHI_RESPONSE["updates"][0]
        parsed = _parse_update(raw)
        assert parsed["alias"] == "FEDORA-2026-abcd1234"
        assert parsed["type"] == "security"
        assert parsed["severity"] == "high"

    def test_date_truncated_to_10_chars(self):
        from ai.system.fedora_updates import _parse_update

        raw = _BODHI_RESPONSE["updates"][0]
        parsed = _parse_update(raw)
        assert parsed["date_submitted"] == "2026-03-18"

    def test_url_constructed_from_alias(self):
        from ai.system.fedora_updates import _parse_update

        raw = _BODHI_RESPONSE["updates"][0]
        parsed = _parse_update(raw)
        assert "FEDORA-2026-abcd1234" in parsed["url"]

    def test_packages_extracted_from_builds(self):
        from ai.system.fedora_updates import _parse_update

        raw = _BODHI_RESPONSE["updates"][0]
        parsed = _parse_update(raw)
        assert "curl" in parsed["packages"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. Security update filtering
# ══════════════════════════════════════════════════════════════════════════════


class TestSecurityFilter:
    def test_security_updates_separated(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", return_value=_fake_resp(_BODHI_RESPONSE)),
            patch(f"{_MOD}._get_installed_rpms", return_value={"bash", "curl"}),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            summary = check_updates(rate_limiter=_make_rl())

        # Both testing + stable queries return same mock → duplicates possible
        # but security filter should catch the curl entry
        assert summary["security_count"] >= 1

    def test_non_security_not_in_security_list(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", return_value=_fake_resp(_BODHI_RESPONSE)),
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_updates(rate_limiter=_make_rl())

        data = json.loads((tmp_path / "fedora-updates.json").read_text())
        for u in data["security_updates"]:
            assert u["type"] == "security"

    def test_critical_count_accurate(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        bodhi_data = {
            "updates": [
                {
                    "alias": "FEDORA-2026-crit0001",
                    "title": "openssl-3.0.0-1.fc41",
                    "type": "security",
                    "severity": "critical",
                    "status": "stable",
                    "date_submitted": "2026-03-20T00:00:00",
                    "builds": [{"name": "openssl"}],
                }
            ]
        }
        with (
            patch("requests.get", return_value=_fake_resp(bodhi_data)),
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            summary = check_updates(rate_limiter=_make_rl())

        assert summary["critical_count"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 3. RPM package matching
# ══════════════════════════════════════════════════════════════════════════════


class TestRpmMatching:
    def test_relevant_updates_match_installed_rpms(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", return_value=_fake_resp(_BODHI_RESPONSE)),
            patch(f"{_MOD}._get_installed_rpms", return_value={"bash"}),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_updates(rate_limiter=_make_rl())

        data = json.loads((tmp_path / "fedora-updates.json").read_text())
        relevant_pkgs = [p for u in data["relevant_updates"] for p in u["packages"]]
        assert "bash" in relevant_pkgs

    def test_uninstalled_non_security_excluded(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", return_value=_fake_resp(_BODHI_RESPONSE)),
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_updates(rate_limiter=_make_rl())

        data = json.loads((tmp_path / "fedora-updates.json").read_text())
        assert data["summary"]["relevant_count"] == 0

    def test_rpm_failure_returns_empty_set(self):
        import subprocess

        from ai.system.fedora_updates import _get_installed_rpms

        with patch("subprocess.run", side_effect=subprocess.SubprocessError):
            result = _get_installed_rpms()

        assert result == set()


# ══════════════════════════════════════════════════════════════════════════════
# 4. Graceful degradation
# ══════════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    def test_bodhi_down_returns_empty_report(self, tmp_path):
        import requests as req_lib

        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", side_effect=req_lib.RequestException("down")),
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            summary = check_updates(rate_limiter=_make_rl())

        assert summary["security_count"] == 0
        assert summary["relevant_count"] == 0

    def test_rate_limited_skips_fetch(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get") as mock_get,
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_updates(rate_limiter=_make_rl(can_call=False))

        mock_get.assert_not_called()

    def test_404_returns_empty_updates(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", return_value=_fake_resp(status_code=404)),
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            summary = check_updates(rate_limiter=_make_rl())

        assert summary["security_count"] == 0

    def test_report_written_atomically(self, tmp_path):
        from ai.system.fedora_updates import check_updates

        with (
            patch("requests.get", return_value=_fake_resp()),
            patch(f"{_MOD}._get_installed_rpms", return_value=set()),
            patch(f"{_MOD}.FEDORA_UPDATES_PATH", tmp_path / "fedora-updates.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_updates(rate_limiter=_make_rl())

        report_path = tmp_path / "fedora-updates.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert "checked_at" in data
        assert data["fedora_release"] == "F41"


# ══════════════════════════════════════════════════════════════════════════════
# 5. CLI
# ══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    def test_cli_calls_check_updates(self):
        from ai.system.fedora_updates import main

        with (
            patch(f"{_MOD}.check_updates", return_value={
                "security_count": 0, "relevant_count": 0, "critical_count": 0,
            }) as mock_check,
            patch(f"{_MOD}.load_keys"),
            patch(f"{_MOD}.setup_logging"),
            patch("sys.argv", ["fedora_updates", "--check"]),
        ):
            main()

        mock_check.assert_called_once()
