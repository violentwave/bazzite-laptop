"""Unit tests for ai/system/release_watch.py."""

import json
from unittest.mock import MagicMock, patch

_MOD = "ai.system.release_watch"


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════


def _make_rl(can_call=True):
    rl = MagicMock()
    rl.can_call.return_value = can_call
    return rl


def _gh_release_response(tag="v1.0.0", body="Release notes.", url="https://github.com/x"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "tag_name": tag,
        "published_at": "2026-03-20T09:00:00Z",
        "html_url": url,
        "body": body,
    }
    return resp


def _gh_advisories_response(count=0):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"id": f"GHSA-{i}"} for i in range(count)]
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# 1. GitHub release parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestFetchLatestRelease:
    def test_parses_tag_and_date(self):
        from ai.system.release_watch import _fetch_latest_release

        fake_resp = _gh_release_response("v4.0.1", "Changelog text here.")
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            result = _fetch_latest_release("ublue-os/bazzite", _make_rl())

        assert result is not None
        assert result["tag_name"] == "v4.0.1"
        assert result["published_at"] == "2026-03-20"
        assert result["summary"] == "Changelog text here."

    def test_404_returns_none(self):
        from ai.system.release_watch import _fetch_latest_release

        fake_resp = MagicMock()
        fake_resp.status_code = 404
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            result = _fetch_latest_release("nonexistent/repo", _make_rl())

        assert result is None

    def test_rate_limited_returns_none(self):
        from ai.system.release_watch import _fetch_latest_release

        with patch("requests.get") as mock_get:
            result = _fetch_latest_release("some/repo", _make_rl(can_call=False))

        mock_get.assert_not_called()
        assert result is None

    def test_request_error_returns_none(self):
        import requests as req_lib

        from ai.system.release_watch import _fetch_latest_release

        with (
            patch("requests.get", side_effect=req_lib.RequestException("timeout")),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            result = _fetch_latest_release("some/repo", _make_rl())

        assert result is None

    def test_summary_truncated_to_200_chars(self):
        from ai.system.release_watch import _fetch_latest_release

        long_body = "A" * 500
        fake_resp = _gh_release_response(body=long_body)
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            result = _fetch_latest_release("some/repo", _make_rl())

        assert len(result["summary"]) == 200

    def test_token_added_to_headers_when_set(self):
        from ai.system.release_watch import _fetch_latest_release

        fake_resp = _gh_release_response()
        with (
            patch("requests.get", return_value=fake_resp) as mock_get,
            patch(f"{_MOD}.get_key", return_value="ghp_mytoken"),
        ):
            _fetch_latest_release("some/repo", _make_rl())

        headers = mock_get.call_args[1]["headers"]
        assert headers.get("Authorization") == "Bearer ghp_mytoken"


# ══════════════════════════════════════════════════════════════════════════════
# 2. GHSA advisory overlay
# ══════════════════════════════════════════════════════════════════════════════


class TestFetchAdvisories:
    def test_returns_advisory_count(self):
        from ai.system.release_watch import _fetch_advisories

        fake_resp = _gh_advisories_response(count=3)
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            count = _fetch_advisories("some/repo", _make_rl())

        assert count == 3

    def test_404_returns_zero(self):
        from ai.system.release_watch import _fetch_advisories

        fake_resp = MagicMock()
        fake_resp.status_code = 404
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            count = _fetch_advisories("no-advisories/repo", _make_rl())

        assert count == 0

    def test_request_error_returns_zero(self):
        import requests as req_lib

        from ai.system.release_watch import _fetch_advisories

        with (
            patch("requests.get", side_effect=req_lib.RequestException),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            count = _fetch_advisories("some/repo", _make_rl())

        assert count == 0

    def test_advisory_count_in_check_releases_output(self, tmp_path):
        from ai.system.release_watch import check_releases

        release_resp = _gh_release_response("v1.0.0")
        advisory_resp = _gh_advisories_response(count=2)

        def side_effect(url, **kwargs):
            if "security-advisories" in url:
                return advisory_resp
            return release_resp

        with (
            patch("requests.get", side_effect=side_effect),
            patch(f"{_MOD}.get_key", return_value=None),
            patch(f"{_MOD}.RELEASE_WATCH_PATH", tmp_path / "release-watch.json"),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_releases(repos=["some/repo"], rate_limiter=_make_rl())

        data = json.loads((tmp_path / "release-watch.json").read_text())
        assert data["repos"]["some/repo"]["advisory_count"] == 2


# ══════════════════════════════════════════════════════════════════════════════
# 3. update_available detection
# ══════════════════════════════════════════════════════════════════════════════


class TestUpdateAvailableDetection:
    def test_update_available_when_tag_changed(self, tmp_path):
        from ai.system.release_watch import check_releases

        # Write cache with old tag
        cache = {"repos": {"some/repo": {"latest": "v0.9.0", "update_available": False}}}
        cache_path = tmp_path / "release-watch.json"
        cache_path.write_text(json.dumps(cache))

        release_resp = _gh_release_response("v1.0.0")
        advisory_resp = _gh_advisories_response()

        def side_effect(url, **kwargs):
            if "security-advisories" in url:
                return advisory_resp
            return release_resp

        with (
            patch("requests.get", side_effect=side_effect),
            patch(f"{_MOD}.get_key", return_value=None),
            patch(f"{_MOD}.RELEASE_WATCH_PATH", cache_path),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_releases(repos=["some/repo"], rate_limiter=_make_rl())

        data = json.loads(cache_path.read_text())
        assert data["repos"]["some/repo"]["update_available"] is True

    def test_no_update_when_tag_unchanged(self, tmp_path):
        from ai.system.release_watch import check_releases

        cache = {"repos": {"some/repo": {"latest": "v1.0.0", "update_available": False}}}
        cache_path = tmp_path / "release-watch.json"
        cache_path.write_text(json.dumps(cache))

        release_resp = _gh_release_response("v1.0.0")
        advisory_resp = _gh_advisories_response()

        def side_effect(url, **kwargs):
            if "security-advisories" in url:
                return advisory_resp
            return release_resp

        with (
            patch("requests.get", side_effect=side_effect),
            patch(f"{_MOD}.get_key", return_value=None),
            patch(f"{_MOD}.RELEASE_WATCH_PATH", cache_path),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_releases(repos=["some/repo"], rate_limiter=_make_rl())

        data = json.loads(cache_path.read_text())
        assert data["repos"]["some/repo"]["update_available"] is False

    def test_first_run_update_available_is_false(self, tmp_path):
        """First run (no cache) should baseline all repos as update_available=False."""
        from ai.system.release_watch import check_releases

        cache_path = tmp_path / "release-watch.json"
        # No cache file exists

        release_resp = _gh_release_response("v1.0.0")
        advisory_resp = _gh_advisories_response()

        def side_effect(url, **kwargs):
            if "security-advisories" in url:
                return advisory_resp
            return release_resp

        with (
            patch("requests.get", side_effect=side_effect),
            patch(f"{_MOD}.get_key", return_value=None),
            patch(f"{_MOD}.RELEASE_WATCH_PATH", cache_path),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            check_releases(repos=["some/repo"], rate_limiter=_make_rl())

        data = json.loads(cache_path.read_text())
        assert data["repos"]["some/repo"]["update_available"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. Graceful degradation
# ══════════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    def test_github_down_skips_repo_continues_others(self, tmp_path):
        """If GitHub is down for one repo, others still complete."""
        import requests as req_lib

        from ai.system.release_watch import check_releases

        call_count = 0

        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "security-advisories" in url:
                return _gh_advisories_response()
            if "repo-a" in url:
                raise req_lib.RequestException("timeout")
            return _gh_release_response("v1.0.0")

        cache_path = tmp_path / "release-watch.json"
        with (
            patch("requests.get", side_effect=side_effect),
            patch(f"{_MOD}.get_key", return_value=None),
            patch(f"{_MOD}.RELEASE_WATCH_PATH", cache_path),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            result = check_releases(
                repos=["owner/repo-a", "owner/repo-b"],
                rate_limiter=_make_rl(),
            )

        data = json.loads(cache_path.read_text())
        # repo-a skipped, repo-b succeeded
        assert "owner/repo-b" in data["repos"]
        assert result["repos_checked"] == 1

    def test_returns_summary_dict(self, tmp_path):
        from ai.system.release_watch import check_releases

        cache_path = tmp_path / "release-watch.json"
        with (
            patch(f"{_MOD}._fetch_latest_release", return_value=None),
            patch(f"{_MOD}.RELEASE_WATCH_PATH", cache_path),
            patch(f"{_MOD}.SECURITY_DIR", tmp_path),
        ):
            result = check_releases(repos=[], rate_limiter=_make_rl())

        assert "checked_at" in result
        assert "repos_checked" in result
        assert "updates_available" in result


# ══════════════════════════════════════════════════════════════════════════════
# 5. Rate limiter integration
# ══════════════════════════════════════════════════════════════════════════════


class TestRateLimiterIntegration:
    def test_rate_limiter_checked_before_request(self):
        from ai.system.release_watch import _fetch_latest_release

        rl = _make_rl(can_call=False)
        with patch("requests.get") as mock_get:
            _fetch_latest_release("some/repo", rl)

        rl.can_call.assert_called_once_with("github_releases")
        mock_get.assert_not_called()

    def test_record_call_after_successful_request(self):
        from ai.system.release_watch import _fetch_latest_release

        rl = _make_rl()
        fake_resp = _gh_release_response()
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            _fetch_latest_release("some/repo", rl)

        rl.record_call.assert_called_with("github_releases")


# ══════════════════════════════════════════════════════════════════════════════
# 6. CLI entry point
# ══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    def test_cli_calls_check_releases(self, tmp_path):
        from ai.system.release_watch import main

        with (
            patch(f"{_MOD}.check_releases", return_value={
                "checked_at": "2026-03-20T09:00:00Z",
                "repos_checked": 11,
                "updates_available": 0,
            }) as mock_check,
            patch(f"{_MOD}.load_keys"),
            patch(f"{_MOD}.setup_logging"),
            patch("sys.argv", ["release_watch", "--check"]),
        ):
            main()

        mock_check.assert_called_once()

    def test_cli_single_repo_flag(self, tmp_path):
        from ai.system.release_watch import main

        with (
            patch(f"{_MOD}.check_releases", return_value={
                "checked_at": "2026-03-20T09:00:00Z",
                "repos_checked": 1,
                "updates_available": 0,
            }) as mock_check,
            patch(f"{_MOD}.load_keys"),
            patch(f"{_MOD}.setup_logging"),
            patch("sys.argv", ["release_watch", "--repo", "ollama/ollama"]),
        ):
            main()

        _, kwargs = mock_check.call_args
        assert kwargs["repos"] == ["ollama/ollama"]
