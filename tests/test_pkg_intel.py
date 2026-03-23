"""Unit tests for ai/system/pkg_intel.py."""

import json
from unittest.mock import MagicMock, patch

_MOD = "ai.system.pkg_intel"

# Sample deps.dev API responses
_PKG_RESPONSE = {
    "versions": [
        {"versionKey": {"version": "0.31.0"}, "isDefault": True},
        {"versionKey": {"version": "0.29.0"}, "isDefault": False},
    ]
}

_VER_RESPONSE = {
    "licenses": [{"spdxExpression": "Apache-2.0"}],
    "advisoryKeys": [],
    "slsaProvenance": None,
    "links": [
        {"label": "SOURCE_REPO", "url": "https://github.com/lancedb/lancedb"}
    ],
}

_VER_WITH_ADVISORY = {
    "licenses": [{"spdxExpression": "MIT"}],
    "advisoryKeys": [{"sourceId": "GHSA-test-0001"}, {"sourceId": "CVE-2024-1234"}],
    "slsaProvenance": {"builder": "GitHub Actions"},
    "links": [],
}


def _make_rl(can_call=True):
    rl = MagicMock()
    rl.can_call.return_value = can_call
    return rl


def _fake_resp(data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# 1. deps.dev response parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestExtractPackageInfo:
    def test_latest_version_detected(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(_PKG_RESPONSE, _VER_RESPONSE, "lancedb", "0.31.0")
        assert info["is_latest"] is True
        assert info["latest_version"] == "0.31.0"

    def test_outdated_version_detected(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(_PKG_RESPONSE, _VER_RESPONSE, "lancedb", "0.29.0")
        assert info["is_latest"] is False
        assert info["latest_version"] == "0.31.0"

    def test_license_extracted(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(_PKG_RESPONSE, _VER_RESPONSE, "lancedb", "0.31.0")
        assert "Apache-2.0" in info["licenses"]

    def test_source_repo_extracted(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(_PKG_RESPONSE, _VER_RESPONSE, "lancedb", "0.31.0")
        assert "lancedb" in info["source_repo"]

    def test_no_advisories(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(_PKG_RESPONSE, _VER_RESPONSE, "lancedb", "0.31.0")
        assert info["advisory_count"] == 0
        assert info["advisories"] == []

    def test_none_data_returns_safe_defaults(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(None, None, "unknown", "1.0.0")
        assert info["latest_version"] == ""
        assert info["licenses"] == []
        assert info["advisory_count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 2. Advisory cross-reference extraction
# ══════════════════════════════════════════════════════════════════════════════


class TestAdvisoryExtraction:
    def test_advisory_keys_extracted(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(None, _VER_WITH_ADVISORY, "requests", "2.28.0")
        assert info["advisory_count"] == 2
        assert "GHSA-test-0001" in info["advisories"]
        assert "CVE-2024-1234" in info["advisories"]

    def test_provenance_detected(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(None, _VER_WITH_ADVISORY, "requests", "2.28.0")
        assert info["has_provenance"] is True

    def test_no_provenance_when_absent(self):
        from ai.system.pkg_intel import _extract_package_info

        info = _extract_package_info(None, _VER_RESPONSE, "requests", "2.28.0")
        assert info["has_provenance"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 3. Scan mode — requirements.txt parsing + deps.dev queries
# ══════════════════════════════════════════════════════════════════════════════


class TestScanMode:
    def test_parses_pinned_requirements(self, tmp_path):
        from ai.system.pkg_intel import _parse_requirements

        req = tmp_path / "requirements.txt"
        req.write_text(
            "lancedb==0.29.0\nrequests>=2.28.0\n# comment\n-r other.txt\n"
        )
        packages = _parse_requirements(req)
        names = [p[0] for p in packages]
        assert "lancedb" in names
        assert "requests" in names

    def test_ignores_comments_and_options(self, tmp_path):
        from ai.system.pkg_intel import _parse_requirements

        req = tmp_path / "requirements.txt"
        req.write_text("# header\n-r other.txt\n--index-url https://pypi.org\npydantic==2.0.0\n")
        packages = _parse_requirements(req)
        assert all(n == "pydantic" for n, _ in packages)

    def test_scan_queries_each_package(self, tmp_path):
        from ai.system.pkg_intel import scan_requirements

        req = tmp_path / "requirements.txt"
        req.write_text("lancedb==0.29.0\nrequests==2.31.0\n")

        def fake_get(url, **kwargs):
            if "versions" in url:
                return _fake_resp(_VER_RESPONSE)
            return _fake_resp(_PKG_RESPONSE)

        with (
            patch("requests.get", side_effect=fake_get),
            patch(f"{_MOD}.PKG_INTEL_DIR", tmp_path),
        ):
            summary = scan_requirements(req, rate_limiter=_make_rl())

        assert summary["total_packages"] == 2

    def test_scan_report_written(self, tmp_path):
        from ai.system.pkg_intel import scan_requirements

        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.31.0\n")

        with (
            patch("requests.get", return_value=_fake_resp(_VER_RESPONSE)),
            patch(f"{_MOD}.PKG_INTEL_DIR", tmp_path),
        ):
            scan_requirements(req, rate_limiter=_make_rl())

        reports = list(tmp_path.glob("pkg-intel-*.json"))
        assert len(reports) == 1
        data = json.loads(reports[0].read_text())
        assert "packages" in data
        assert "summary" in data


# ══════════════════════════════════════════════════════════════════════════════
# 4. Graceful degradation
# ══════════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    def test_deps_dev_down_skips_package(self, tmp_path):
        import requests as req_lib

        from ai.system.pkg_intel import scan_requirements

        req = tmp_path / "requirements.txt"
        req.write_text("lancedb==0.29.0\n")

        with (
            patch("requests.get", side_effect=req_lib.RequestException("down")),
            patch(f"{_MOD}.PKG_INTEL_DIR", tmp_path),
        ):
            summary = scan_requirements(req, rate_limiter=_make_rl())

        # Both package + version fetch fail → package skipped → 0 results
        assert summary["total_packages"] == 0

    def test_404_returns_none(self):
        from ai.system.pkg_intel import _fetch_package

        with patch("requests.get", return_value=_fake_resp({}, 404)):
            result = _fetch_package("pypi", "nonexistent", _make_rl())
        assert result is None

    def test_rate_limited_skips_fetch(self):
        from ai.system.pkg_intel import _fetch_package

        with patch("requests.get") as mock_get:
            result = _fetch_package("pypi", "lancedb", _make_rl(can_call=False))
        mock_get.assert_not_called()
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. Rate limiter integration
# ══════════════════════════════════════════════════════════════════════════════


class TestRateLimiterIntegration:
    def test_can_call_checked_before_request(self):
        from ai.system.pkg_intel import _fetch_version

        rl = _make_rl(can_call=False)
        with patch("requests.get") as mock_get:
            _fetch_version("pypi", "lancedb", "0.29.0", rl)
        rl.can_call.assert_called_with("deps_dev")
        mock_get.assert_not_called()

    def test_record_call_after_success(self):
        from ai.system.pkg_intel import _fetch_version

        rl = _make_rl()
        with patch("requests.get", return_value=_fake_resp(_VER_RESPONSE)):
            _fetch_version("pypi", "lancedb", "0.29.0", rl)
        rl.record_call.assert_called_with("deps_dev")


# ══════════════════════════════════════════════════════════════════════════════
# 6. MCP handler
# ══════════════════════════════════════════════════════════════════════════════


class TestMcpHandler:
    def test_returns_latest_report(self, tmp_path):
        from ai.system.pkg_intel import mcp_handler

        report = {"scanned_at": "2026-03-22T09:00:00Z", "packages": {}, "summary": {}}
        (tmp_path / "pkg-intel-2026-03-22.json").write_text(json.dumps(report))

        with patch(f"{_MOD}.PKG_INTEL_DIR", tmp_path):
            result = mcp_handler()

        assert result["scanned_at"] == "2026-03-22T09:00:00Z"

    def test_no_report_returns_error_dict(self, tmp_path):
        from ai.system.pkg_intel import mcp_handler

        with patch(f"{_MOD}.PKG_INTEL_DIR", tmp_path):
            result = mcp_handler()

        assert "error" in result


# ══════════════════════════════════════════════════════════════════════════════
# 7. CLI entry points
# ══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    def test_single_package_cli(self):
        from ai.system.pkg_intel import main

        with (
            patch(f"{_MOD}.lookup_package", return_value={"version": "0.29.0"}) as mock_lp,
            patch(f"{_MOD}.load_keys"),
            patch(f"{_MOD}.setup_logging"),
            patch("sys.argv", ["pkg_intel", "--package", "lancedb", "--version", "0.29.0"]),
        ):
            main()

        mock_lp.assert_called_once()

    def test_scan_cli(self, tmp_path):
        from ai.system.pkg_intel import main

        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.31.0\n")

        with (
            patch(f"{_MOD}.scan_requirements", return_value={"total_packages": 1}) as mock_scan,
            patch(f"{_MOD}.load_keys"),
            patch(f"{_MOD}.setup_logging"),
            patch("sys.argv", ["pkg_intel", "--scan", str(req)]),
        ):
            main()

        mock_scan.assert_called_once()
