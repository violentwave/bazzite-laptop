"""Unit tests for ai/threat_intel/cve_scanner.py.

Covers:
  1. Package parsing (rpm, flatpak, pip)
  2. NVD response parsing
  3. OSV response parsing
  4. KEV overlay
  5. Report generation
  6. Graceful degradation (subprocess failures, API errors)
"""

import json
from unittest.mock import MagicMock, patch

import pytest  # noqa: I001

_MOD = "ai.threat_intel.cve_scanner"


# ══════════════════════════════════════════════════════════════════════════════
# 1. Package parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestEnumRpm:
    def test_parses_name_version(self):
        from ai.threat_intel.cve_scanner import _enum_rpm

        fake = MagicMock()
        fake.stdout = "bash 5.2.15\ncurl 7.85.0\n"
        with patch("subprocess.run", return_value=fake):
            pkgs = _enum_rpm()

        assert any(p.name == "bash" and p.version == "5.2.15" for p in pkgs)
        assert all(p.source == "rpm" for p in pkgs)

    def test_empty_output_returns_empty(self):
        from ai.threat_intel.cve_scanner import _enum_rpm

        fake = MagicMock()
        fake.stdout = ""
        with patch("subprocess.run", return_value=fake):
            assert _enum_rpm() == []

    def test_subprocess_failure_returns_empty(self):
        import subprocess

        from ai.threat_intel.cve_scanner import _enum_rpm

        with patch("subprocess.run", side_effect=subprocess.SubprocessError):
            assert _enum_rpm() == []


class TestEnumFlatpak:
    def test_parses_tab_separated(self):
        from ai.threat_intel.cve_scanner import _enum_flatpak

        fake = MagicMock()
        fake.stdout = "org.kde.konsole\t23.04.3\ncom.valvesoftware.Steam\t1.0.0\n"
        with patch("subprocess.run", return_value=fake):
            pkgs = _enum_flatpak()

        assert any(p.name == "org.kde.konsole" for p in pkgs)
        assert all(p.source == "flatpak" for p in pkgs)

    def test_missing_flatpak_returns_empty(self):
        from ai.threat_intel.cve_scanner import _enum_flatpak

        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert _enum_flatpak() == []


class TestEnumPip:
    def test_parses_json_output(self):
        from ai.threat_intel.cve_scanner import _enum_pip

        fake = MagicMock()
        fake.stdout = json.dumps([
            {"name": "requests", "version": "2.31.0"},
            {"name": "pydantic", "version": "2.0.0"},
        ])
        with patch("subprocess.run", return_value=fake):
            pkgs = _enum_pip()

        assert any(p.name == "requests" and p.version == "2.31.0" for p in pkgs)
        assert all(p.source == "pip" for p in pkgs)

    def test_invalid_json_returns_empty(self):
        from ai.threat_intel.cve_scanner import _enum_pip

        fake = MagicMock()
        fake.stdout = "not-json"
        with patch("subprocess.run", return_value=fake):
            assert _enum_pip() == []

    def test_subprocess_failure_returns_empty(self):
        import subprocess

        from ai.threat_intel.cve_scanner import _enum_pip

        with patch("subprocess.run", side_effect=subprocess.SubprocessError):
            assert _enum_pip() == []


# ══════════════════════════════════════════════════════════════════════════════
# 2. NVD response parsing
# ══════════════════════════════════════════════════════════════════════════════


_NVD_RESPONSE = {
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2023-12345",
                "descriptions": [
                    {"lang": "en", "value": "A critical vulnerability in bash."}
                ],
                "metrics": {
                    "cvssMetricV31": [
                        {
                            "cvssData": {
                                "baseScore": 9.8,
                                "baseSeverity": "CRITICAL",
                            }
                        }
                    ]
                },
            }
        }
    ]
}


class TestLookupNvd:
    def _make_rate_limiter(self, can_call=True):
        rl = MagicMock()
        rl.can_call.return_value = can_call
        return rl

    def test_parses_cve_id_and_severity(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_nvd

        pkg = PackageInfo("bash", "5.2.15", "rpm")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = _NVD_RESPONSE

        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            cves = _lookup_nvd(pkg, self._make_rate_limiter())

        assert len(cves) == 1
        assert cves[0].cve_id == "CVE-2023-12345"
        assert cves[0].severity == "CRITICAL"
        assert cves[0].cvss_score == pytest.approx(9.8)
        assert cves[0].source == "nvd"

    def test_rate_limited_returns_empty(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_nvd

        pkg = PackageInfo("bash", "5.2.15", "rpm")
        with patch("requests.get") as mock_get:
            cves = _lookup_nvd(pkg, self._make_rate_limiter(can_call=False))
        mock_get.assert_not_called()
        assert cves == []

    def test_request_error_returns_empty(self):
        import requests as req_lib

        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_nvd

        pkg = PackageInfo("curl", "7.85.0", "rpm")
        with (
            patch("requests.get", side_effect=req_lib.RequestException("timeout")),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            cves = _lookup_nvd(pkg, self._make_rate_limiter())
        assert cves == []

    def test_404_returns_empty(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_nvd

        pkg = PackageInfo("unknown-pkg", "1.0", "rpm")
        fake_resp = MagicMock()
        fake_resp.status_code = 404
        with (
            patch("requests.get", return_value=fake_resp),
            patch(f"{_MOD}.get_key", return_value=None),
        ):
            cves = _lookup_nvd(pkg, self._make_rate_limiter())
        assert cves == []

    def test_api_key_included_in_headers(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_nvd

        pkg = PackageInfo("bash", "5.2.15", "rpm")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"vulnerabilities": []}

        with (
            patch("requests.get", return_value=fake_resp) as mock_get,
            patch(f"{_MOD}.get_key", return_value="my-nvd-key"),
        ):
            _lookup_nvd(pkg, self._make_rate_limiter())

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["headers"].get("apiKey") == "my-nvd-key"


# ══════════════════════════════════════════════════════════════════════════════
# 3. OSV response parsing
# ══════════════════════════════════════════════════════════════════════════════


_OSV_RESPONSE = {
    "vulns": [
        {
            "id": "GHSA-abcd-efgh-1234",
            "aliases": ["CVE-2023-54321"],
            "details": "SQL injection in requests library.",
            "severity": [{"type": "CVSS_V3", "score": "7.5"}],
        }
    ]
}


class TestLookupOsv:
    def test_parses_cve_alias(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_osv

        pkg = PackageInfo("requests", "2.31.0", "pip")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = _OSV_RESPONSE

        with patch("requests.post", return_value=fake_resp):
            cves = _lookup_osv(pkg)

        assert len(cves) == 1
        assert cves[0].cve_id == "CVE-2023-54321"
        assert cves[0].severity == "HIGH"
        assert cves[0].cvss_score == pytest.approx(7.5)
        assert cves[0].source == "osv"

    def test_uses_ghsa_id_when_no_cve_alias(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_osv

        pkg = PackageInfo("somelib", "1.0", "pip")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "vulns": [{"id": "GHSA-xxxx", "aliases": [], "details": "Bug."}]
        }
        with patch("requests.post", return_value=fake_resp):
            cves = _lookup_osv(pkg)

        assert cves[0].cve_id == "GHSA-xxxx"

    def test_request_error_returns_empty(self):
        import requests as req_lib

        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_osv

        pkg = PackageInfo("requests", "2.31.0", "pip")
        with patch("requests.post", side_effect=req_lib.RequestException):
            assert _lookup_osv(pkg) == []

    def test_empty_vulns_returns_empty(self):
        from ai.threat_intel.cve_scanner import PackageInfo, _lookup_osv

        pkg = PackageInfo("requests", "2.31.0", "pip")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"vulns": []}
        with patch("requests.post", return_value=fake_resp):
            assert _lookup_osv(pkg) == []


# ══════════════════════════════════════════════════════════════════════════════
# 4. KEV overlay
# ══════════════════════════════════════════════════════════════════════════════


class TestKevOverlay:
    def test_kev_flag_set_for_matching_cve(self, tmp_path):
        from ai.threat_intel.cve_scanner import _load_kev_cache

        kev_data = {
            "vulnerabilities": [
                {"cveID": "CVE-2023-12345"},
                {"cveID": "CVE-2022-99999"},
            ]
        }
        cache = tmp_path / "kev-cache.json"
        cache.write_text(json.dumps(kev_data))

        with (
            patch(f"{_MOD}._KEV_CACHE_PATH", cache),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
            patch("time.time", return_value=cache.stat().st_mtime + 1),
        ):
            kev_ids = _load_kev_cache()

        assert "CVE-2023-12345" in kev_ids
        assert "CVE-2022-99999" in kev_ids

    def test_stale_cache_triggers_fetch(self, tmp_path):
        from ai.threat_intel.cve_scanner import _load_kev_cache

        old_data = {"vulnerabilities": [{"cveID": "CVE-2020-00001"}]}
        cache = tmp_path / "kev-cache.json"
        cache.write_text(json.dumps(old_data))

        new_data = {"vulnerabilities": [{"cveID": "CVE-2024-99999"}]}
        fake_resp = MagicMock()
        fake_resp.json.return_value = new_data

        stale_mtime = cache.stat().st_mtime - (170 * 3600)  # 170h ago (> 7d TTL)
        with (
            patch(f"{_MOD}._KEV_CACHE_PATH", cache),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
            patch("time.time", return_value=stale_mtime + 170 * 3600),
        ):
            # Simulate stale by patching mtime
            import os

            os.utime(cache, (stale_mtime, stale_mtime))
            with patch("requests.get", return_value=fake_resp):
                kev_ids = _load_kev_cache()

        assert "CVE-2024-99999" in kev_ids

    def test_fetch_failure_uses_stale_cache(self, tmp_path):
        import requests as req_lib

        from ai.threat_intel.cve_scanner import _load_kev_cache

        old_data = {"vulnerabilities": [{"cveID": "CVE-2020-00001"}]}
        cache = tmp_path / "kev-cache.json"
        cache.write_text(json.dumps(old_data))

        import os

        stale_mtime = cache.stat().st_mtime - (25 * 3600)
        os.utime(cache, (stale_mtime, stale_mtime))

        with (
            patch(f"{_MOD}._KEV_CACHE_PATH", cache),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
            patch("requests.get", side_effect=req_lib.RequestException("down")),
        ):
            kev_ids = _load_kev_cache()

        assert "CVE-2020-00001" in kev_ids

    def test_no_cache_no_network_returns_empty(self, tmp_path):
        import requests as req_lib

        from ai.threat_intel.cve_scanner import _load_kev_cache

        cache = tmp_path / "kev-cache.json"
        with (
            patch(f"{_MOD}._KEV_CACHE_PATH", cache),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
            patch("requests.get", side_effect=req_lib.RequestException("down")),
        ):
            kev_ids = _load_kev_cache()

        assert kev_ids == {}


# ══════════════════════════════════════════════════════════════════════════════
# 5. Report generation
# ══════════════════════════════════════════════════════════════════════════════


class TestWriteReport:
    def test_report_written_atomically(self, tmp_path):
        from ai.threat_intel.cve_scanner import CVEEntry, ScanReport, _write_report

        report = ScanReport(
            packages_scanned=10,
            total_cves=2,
            high_severity=1,
            kev_cves=1,
            cves=[
                CVEEntry(
                    cve_id="CVE-2023-12345",
                    description="Test CVE",
                    severity="HIGH",
                    cvss_score=7.5,
                    package_name="bash",
                    package_version="5.2.15",
                    source="nvd",
                    in_kev=True,
                )
            ],
        )

        with patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path):
            path = _write_report(report)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["packages_scanned"] == 10
        assert data["total_cves"] == 2
        assert data["kev_cves"] == 1
        assert data["cves"][0]["in_kev"] is True
        assert data["cves"][0]["cve_id"] == "CVE-2023-12345"

    def test_report_filename_contains_today(self, tmp_path):
        from datetime import date

        from ai.threat_intel.cve_scanner import ScanReport, _write_report

        report = ScanReport()
        with patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path):
            path = _write_report(report)

        assert date.today().isoformat() in path.name


# ══════════════════════════════════════════════════════════════════════════════
# 6. Graceful degradation
# ══════════════════════════════════════════════════════════════════════════════


class TestScanCvesGraceful:
    def _make_rl(self):
        rl = MagicMock()
        rl.can_call.return_value = True
        return rl

    def test_returns_summary_dict(self, tmp_path):
        from ai.threat_intel.cve_scanner import scan_cves

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=[]),
            patch(f"{_MOD}._load_kev_cache", return_value=set()),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        assert "packages_scanned" in result
        assert "total_cves" in result
        assert "high_severity" in result
        assert "kev_cves" in result

    def test_no_packages_no_cves(self, tmp_path):
        from ai.threat_intel.cve_scanner import scan_cves

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=[]),
            patch(f"{_MOD}._load_kev_cache", return_value=set()),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        assert result["packages_scanned"] == 0
        assert result["total_cves"] == 0

    def test_kev_cves_counted(self, tmp_path):
        from ai.threat_intel.cve_scanner import PackageInfo, scan_cves

        packages = [PackageInfo("requests", "2.31.0", "pip")]
        nvd_cves = []
        osv_resp = MagicMock()
        osv_resp.status_code = 200
        osv_resp.json.return_value = {
            "vulns": [{
                "id": "GHSA-abc",
                "aliases": ["CVE-2023-12345"],
                "details": "Bug",
                "severity": [],
            }]
        }

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache", return_value={"CVE-2023-12345": "2024-01-17"}),
            patch(f"{_MOD}._lookup_nvd", return_value=nvd_cves),
            patch("requests.post", return_value=osv_resp),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        assert result["kev_cves"] == 1

    def test_report_write_failure_does_not_raise(self, tmp_path):
        from ai.threat_intel.cve_scanner import scan_cves

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=[]),
            patch(f"{_MOD}._load_kev_cache", return_value=set()),
            patch(f"{_MOD}._write_report", side_effect=OSError("disk full")),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        # Should still return summary without raising
        assert "packages_scanned" in result

    def test_deduplicates_cves(self, tmp_path):
        from ai.threat_intel.cve_scanner import CVEEntry, PackageInfo, scan_cves

        packages = [PackageInfo("bash", "5.2.15", "rpm")]
        duplicate_cves = [
            CVEEntry("CVE-2023-0001", "desc", "HIGH", 7.0, "bash", "5.2.15", "nvd"),
            CVEEntry("CVE-2023-0001", "desc", "HIGH", 7.0, "bash", "5.2.15", "nvd"),
        ]

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache", return_value={}),
            patch(f"{_MOD}._lookup_nvd", return_value=duplicate_cves),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        assert result["total_cves"] == 1

    def test_summary_includes_kev_matches_and_osv_flag(self, tmp_path):
        from ai.threat_intel.cve_scanner import scan_cves

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=[]),
            patch(f"{_MOD}._load_kev_cache", return_value={}),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        assert "kev_matches" in result
        assert "osv_fallback_used" in result


# ══════════════════════════════════════════════════════════════════════════════
# 7. OSV fallback behaviour
# ══════════════════════════════════════════════════════════════════════════════


class TestOsvFallback:
    def _make_rl(self):
        rl = MagicMock()
        rl.can_call.return_value = True
        return rl

    def test_osv_called_when_nvd_empty_for_pip(self, tmp_path):
        """OSV fallback triggered when NVD returns 0 results for a pip package."""
        from ai.threat_intel.cve_scanner import PackageInfo, scan_cves

        packages = [PackageInfo("lancedb", "0.29.0", "pip")]
        osv_resp = MagicMock()
        osv_resp.status_code = 200
        osv_resp.json.return_value = {
            "vulns": [{
                "id": "GHSA-osv-test",
                "aliases": ["CVE-2024-00001"],
                "details": "OSV fallback test.",
                "severity": [],
            }]
        }

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache", return_value={}),
            patch(f"{_MOD}._lookup_nvd", return_value=[]),
            patch("requests.post", return_value=osv_resp) as mock_post,
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        mock_post.assert_called_once()
        assert result["osv_fallback_used"] is True
        assert result["total_cves"] == 1

    def test_osv_not_called_when_nvd_has_results_for_pip(self, tmp_path):
        """OSV skipped when NVD already found CVEs for the package."""
        from ai.threat_intel.cve_scanner import CVEEntry, PackageInfo, scan_cves

        packages = [PackageInfo("requests", "2.31.0", "pip")]
        nvd_cve = CVEEntry(
            "CVE-2023-99999", "NVD result", "HIGH", 7.0,
            "requests", "2.31.0", "nvd",
        )

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache", return_value={}),
            patch(f"{_MOD}._lookup_nvd", return_value=[nvd_cve]),
            patch("requests.post") as mock_post,
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        mock_post.assert_not_called()
        assert result["osv_fallback_used"] is False

    def test_osv_skipped_for_rpm_packages(self, tmp_path):
        """OSV is never called for RPM packages regardless of NVD result."""
        from ai.threat_intel.cve_scanner import PackageInfo, scan_cves

        packages = [PackageInfo("bash", "5.2.15", "rpm")]

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache", return_value={}),
            patch(f"{_MOD}._lookup_nvd", return_value=[]),
            patch("requests.post") as mock_post,
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            scan_cves(rate_limiter=self._make_rl())

        mock_post.assert_not_called()

    def test_osv_down_skips_gracefully(self, tmp_path):
        """OSV request failure does not abort the scan."""
        import requests as req_lib

        from ai.threat_intel.cve_scanner import PackageInfo, scan_cves

        packages = [PackageInfo("somelib", "1.0", "pip")]

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache", return_value={}),
            patch(f"{_MOD}._lookup_nvd", return_value=[]),
            patch("requests.post", side_effect=req_lib.RequestException("osv down")),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            result = scan_cves(rate_limiter=self._make_rl())

        assert "packages_scanned" in result
        assert result["osv_fallback_used"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 8. KEV exploited_in_wild and kev_due_date overlay
# ══════════════════════════════════════════════════════════════════════════════


class TestKevReportFields:
    def _make_rl(self):
        rl = MagicMock()
        rl.can_call.return_value = True
        return rl

    def test_kev_sets_exploited_in_wild_and_due_date(self, tmp_path):
        """KEV overlay sets exploited_in_wild and kev_due_date on matching CVEs."""
        from ai.threat_intel.cve_scanner import PackageInfo, scan_cves

        packages = [PackageInfo("requests", "2.31.0", "pip")]
        osv_resp = MagicMock()
        osv_resp.status_code = 200
        osv_resp.json.return_value = {
            "vulns": [{
                "id": "GHSA-kev-test",
                "aliases": ["CVE-2023-12345"],
                "details": "KEV test.",
                "severity": [],
            }]
        }

        with (
            patch(f"{_MOD}.enumerate_packages", return_value=packages),
            patch(f"{_MOD}._load_kev_cache",
                  return_value={"CVE-2023-12345": "2024-03-01"}),
            patch(f"{_MOD}._lookup_nvd", return_value=[]),
            patch("requests.post", return_value=osv_resp),
            patch(f"{_MOD}.CVE_REPORTS_DIR", tmp_path),
        ):
            scan_cves(rate_limiter=self._make_rl())

        report_path = next(tmp_path.glob("cve-*.json"))
        report_data = json.loads(report_path.read_text())
        cve = report_data["cves"][0]
        assert cve["exploited_in_wild"] is True
        assert cve["kev_due_date"] == "2024-03-01"
        assert report_data["kev_matches"] == 1
        assert report_data["osv_fallback_used"] is True
