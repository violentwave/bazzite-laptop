"""Unit tests for ai/threat_intel/sandbox.py.

Covers:
  1. Path validation (traversal, missing file, valid path)
  2. Hash-first: returns cached result when hash found
  3. Submission flow: submits when no cached result
  4. Rate limiter enforcement
  5. Graceful degradation (missing key, API errors, submit rejection)
"""

from unittest.mock import MagicMock, patch

_MOD = "ai.threat_intel.sandbox"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _make_rl(can_call=True):
    rl = MagicMock()
    rl.can_call.return_value = can_call
    return rl


def _make_real_file(tmp_path, name="sample.exe", content=b"MZ\x90\x00"):
    f = tmp_path / name
    f.write_bytes(content)
    return f


# ══════════════════════════════════════════════════════════════════════════════
# 1. Path validation
# ══════════════════════════════════════════════════════════════════════════════


class TestValidatePath:
    def test_valid_file_in_quarantine(self, tmp_path):
        from ai.threat_intel.sandbox import _validate_path

        sample = tmp_path / "sample.exe"
        sample.write_bytes(b"MZ")

        with patch(f"{_MOD}._QUARANTINE_DIR", tmp_path):
            result = _validate_path(str(sample))

        assert result == sample.resolve()

    def test_rejects_traversal(self, tmp_path):
        from ai.threat_intel.sandbox import _validate_path

        outside = tmp_path.parent / "evil.exe"
        outside.write_bytes(b"MZ")

        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        with patch(f"{_MOD}._QUARANTINE_DIR", quarantine):
            result = _validate_path(str(outside))

        assert result is None

    def test_rejects_missing_file(self, tmp_path):
        from ai.threat_intel.sandbox import _validate_path

        missing = tmp_path / "does-not-exist.exe"
        with patch(f"{_MOD}._QUARANTINE_DIR", tmp_path):
            result = _validate_path(str(missing))

        assert result is None

    def test_rejects_directory(self, tmp_path):
        from ai.threat_intel.sandbox import _validate_path

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch(f"{_MOD}._QUARANTINE_DIR", tmp_path):
            result = _validate_path(str(subdir))

        assert result is None

    def test_dotdot_in_path_rejected(self, tmp_path):
        from ai.threat_intel.sandbox import _validate_path

        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        traversal = str(quarantine / ".." / ".." / "etc" / "passwd")
        with patch(f"{_MOD}._QUARANTINE_DIR", quarantine):
            result = _validate_path(traversal)

        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 2. Hash-first: cached result
# ══════════════════════════════════════════════════════════════════════════════


class TestHashFirst:
    def test_returns_cached_when_hash_found(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)

        cached = {
            "verdict": "malicious",
            "threat_score": 85,
            "threat_level_human": "high",
            "analysis_start_time": "2026-03-22T00:00:00",
        }
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [cached]

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", return_value=fake_resp),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        assert report.status == "cached"
        assert report.verdict == "malicious"
        assert report.threat_score == 85
        assert report.threat_level == "high"
        assert report.sha256 != ""

    def test_cached_does_not_submit(self, tmp_path):
        """When hash found, no second POST (submission) is made."""
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [{"verdict": "benign"}]

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", return_value=fake_resp) as mock_post,
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        # Only one POST for hash search, none for submission
        assert mock_post.call_count == 1
        assert report.status == "cached"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Submission flow
# ══════════════════════════════════════════════════════════════════════════════


class TestSubmissionFlow:
    def test_submits_when_not_cached(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)

        # First POST (hash search): returns empty list (not found)
        # Second POST (submit): returns job_id
        hash_resp = MagicMock()
        hash_resp.status_code = 200
        hash_resp.json.return_value = []

        submit_resp = MagicMock()
        submit_resp.status_code = 200
        submit_resp.json.return_value = {"job_id": "abc-123"}

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", side_effect=[hash_resp, submit_resp]),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        assert report.status == "submitted"
        assert report.job_id == "abc-123"

    def test_submission_includes_environment_id(self, tmp_path):
        from ai.threat_intel.sandbox import _ENVIRONMENT_ID, submit_file

        sample = _make_real_file(tmp_path)
        hash_resp = MagicMock()
        hash_resp.status_code = 200
        hash_resp.json.return_value = []

        submit_resp = MagicMock()
        submit_resp.status_code = 200
        submit_resp.json.return_value = {"job_id": "xyz"}

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", side_effect=[hash_resp, submit_resp]),
        ):
            submit_file(str(sample), rate_limiter=_make_rl())

        assert _ENVIRONMENT_ID == 120

    def test_submission_uses_falcon_sandbox_useragent(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        hash_resp = MagicMock()
        hash_resp.status_code = 200
        hash_resp.json.return_value = []

        submit_resp = MagicMock()
        submit_resp.status_code = 200
        submit_resp.json.return_value = {"job_id": "xyz"}

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", side_effect=[hash_resp, submit_resp]) as mock_post,
        ):
            submit_file(str(sample), rate_limiter=_make_rl())

        first_call_headers = mock_post.call_args_list[0][1]["headers"]
        assert first_call_headers["User-Agent"] == "Falcon Sandbox"
        assert first_call_headers["api-key"] == "test-key"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Rate limiter enforcement
# ══════════════════════════════════════════════════════════════════════════════


class TestRateLimiter:
    def test_rate_limited_returns_rate_limited_status(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post") as mock_post,
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl(can_call=False))

        mock_post.assert_not_called()
        assert report.status == "rate_limited"

    def test_rate_limit_checked_before_network(self, tmp_path):
        """Rate limit check must happen before any requests.post call."""
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        rl = _make_rl(can_call=False)

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post") as mock_post,
        ):
            submit_file(str(sample), rate_limiter=rl)

        mock_post.assert_not_called()

    def test_record_call_on_hash_search(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        rl = _make_rl()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [{"verdict": "benign"}]

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", return_value=fake_resp),
        ):
            submit_file(str(sample), rate_limiter=rl)

        rl.record_call.assert_called_with("hybrid_analysis")


# ══════════════════════════════════════════════════════════════════════════════
# 5. Graceful degradation
# ══════════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    def test_missing_api_key_returns_error(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        assert report.status == "error"
        assert "HYBRID_ANALYSIS_KEY" in report.description

    def test_invalid_path_returns_error(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        outside = tmp_path / "evil.exe"
        outside.write_bytes(b"MZ")

        with patch(f"{_MOD}._QUARANTINE_DIR", quarantine):
            report = submit_file(str(outside), rate_limiter=_make_rl())

        assert report.status == "error"

    def test_hash_search_request_error_falls_through(self, tmp_path):
        """If hash search fails with network error, proceed to submit."""
        import requests as req_lib

        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        submit_resp = MagicMock()
        submit_resp.status_code = 200
        submit_resp.json.return_value = {"job_id": "fallback-job"}

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch(
                "requests.post",
                side_effect=[req_lib.RequestException("timeout"), submit_resp],
            ),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        # Hash search returned None (network error), so file was submitted
        assert report.status == "submitted"

    def test_submission_rejected_400_returns_error(self, tmp_path):
        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        hash_resp = MagicMock()
        hash_resp.status_code = 200
        hash_resp.json.return_value = []

        bad_resp = MagicMock()
        bad_resp.status_code = 400
        bad_resp.text = "Bad request"

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", side_effect=[hash_resp, bad_resp]),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        assert report.status == "error"

    def test_sha256_computed_for_valid_file(self, tmp_path):
        import hashlib

        from ai.threat_intel.sandbox import submit_file

        content = b"Hello, World!"
        sample = _make_real_file(tmp_path, content=content)
        expected = hashlib.sha256(content).hexdigest()

        # Use a key so we reach the SHA256 step; hash search returns cached result
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [{"verdict": "benign"}]

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch("requests.post", return_value=fake_resp),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        assert report.sha256 == expected

    def test_submit_network_error_returns_error(self, tmp_path):
        import requests as req_lib

        from ai.threat_intel.sandbox import submit_file

        sample = _make_real_file(tmp_path)
        hash_resp = MagicMock()
        hash_resp.status_code = 200
        hash_resp.json.return_value = []

        with (
            patch(f"{_MOD}._QUARANTINE_DIR", tmp_path),
            patch(f"{_MOD}.get_key", return_value="test-key"),
            patch(
                "requests.post",
                side_effect=[hash_resp, req_lib.RequestException("down")],
            ),
        ):
            report = submit_file(str(sample), rate_limiter=_make_rl())

        assert report.status == "error"
