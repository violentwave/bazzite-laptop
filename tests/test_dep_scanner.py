"""Tests for ai.system.dep_scanner module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_venv():
    """Create a mock venv structure with METADATA files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir)
        lib_path = venv_path / "lib" / "python3.12" / "site-packages"
        lib_path.mkdir(parents=True)

        (lib_path / "requests-2.31.0.dist-info").mkdir()
        (lib_path / "requests-2.31.0.dist-info" / "METADATA").write_text(
            "Name: requests\nVersion: 2.31.0\n"
        )

        (lib_path / "flask-3.0.0.dist-info").mkdir()
        (lib_path / "flask-3.0.0.dist-info" / "METADATA").write_text(
            "Name: Flask\nVersion: 3.0.0\n"
        )

        yield venv_path


class TestGetPackages:
    """Test get_installed_packages reads METADATA files."""

    def test_get_packages_reads_dist_info(self, mock_venv):
        """Reads METADATA files correctly."""
        from ai.system.dep_scanner import DepVulnScanner

        scanner = DepVulnScanner()
        packages = scanner.get_installed_packages(str(mock_venv))

        names = {name for name, _ in packages}
        assert "requests" in names
        assert "flask" in names

        versions = {version for name, version in packages if name == "requests"}
        assert "2.31.0" in versions


class TestOsvBatch:
    """Test OSV batch query structure."""

    def test_osv_batch_structure(self):
        """Queries list has correct PyPI ecosystem entries."""
        from ai.system.dep_scanner import DepVulnScanner

        scanner = DepVulnScanner()
        packages = [("requests", "2.31.0"), ("flask", "3.0.0")]

        captured = {}

        def mock_post(url, json=None, **kwargs):
            captured["url"] = url
            captured["json"] = json
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"results": []}
            return mock_resp

        with patch.object(scanner.client, "post", side_effect=mock_post):
            scanner.check_osv(packages)

        assert "queries" in captured["json"]
        queries = captured["json"]["queries"]
        assert len(queries) == 2
        assert queries[0]["package"]["ecosystem"] == "PyPI"
        assert queries[0]["package"]["name"] == "requests"


class TestOsvRetry:
    """Test OSV retry path parses response correctly."""

    def test_osv_retry_parses_response(self):
        """Retry path builds Vulnerability objects."""
        from ai.system.dep_scanner import DepVulnScanner

        scanner = DepVulnScanner()
        packages = [("requests", "2.31.0")]

        import httpx

        mock_response_normal = MagicMock(spec=httpx.Response)
        mock_response_normal.status_code = 429

        mock_response_retry = MagicMock(spec=httpx.Response)
        mock_response_retry.status_code = 200
        mock_response_retry.json.return_value = {
            "results": [
                {
                    "vulns": [
                        {
                            "id": "VULN-001",
                            "summary": "Test vulnerability",
                            "database_specific": {"severity": "HIGH"},
                            "affected": [{"ranges": [{"events": [{"fixed": "2.31.1"}]}]}],
                            "aliases": ["CVE-2024-1234"],
                        }
                    ]
                }
            ]
        }

        responses = [mock_response_normal, mock_response_retry]
        idx = 0

        def mock_post(url, json=None, **kwargs):
            nonlocal idx
            resp = responses[idx]
            idx += 1
            if resp.status_code == 429:
                raise httpx.HTTPStatusError("429", request=MagicMock(), response=resp)
            return resp

        with patch.object(scanner.client, "post", side_effect=mock_post):
            results = scanner.check_osv(packages)

        assert "requests" in results
        assert len(results["requests"]) == 1
        assert results["requests"][0].id == "VULN-001"


class TestVersionTracking:
    """Test version is tracked in report."""

    def test_version_in_report(self, temp_output_dir):
        """Report output has non-empty version per package."""
        from ai.system.dep_scanner import DepVulnScanner

        scanner = DepVulnScanner()

        with patch.object(scanner, "get_installed_packages", return_value=[("requests", "2.31.0")]):
            with patch.object(scanner, "check_osv", return_value={"requests": []}):
                report = scanner.generate_report(
                    {"requests": []},
                    1,
                    str(temp_output_dir / "report.json"),
                    pkg_versions={"requests": "2.31.0"},
                )

        assert report["packages"][0]["version"] == "2.31.0"


class TestAtomicWrite:
    """Test atomic write functionality."""

    def test_generate_report_atomic_write(self, temp_output_dir):
        """Tmp file created then replaced."""
        from ai.system.dep_scanner import DepVulnScanner

        scanner = DepVulnScanner()

        report_path = temp_output_dir / "report.json"
        scanner.generate_report({}, 0, str(report_path))

        assert report_path.exists()

        tmp_file = report_path.with_suffix(".tmp")
        assert not tmp_file.exists()


class TestImportNoSideEffects:
    """Test module import has no side effects."""

    def test_import_no_side_effects(self, capsys):
        """Import produces no output or logging."""
        import sys

        if "ai.system.dep_scanner" in sys.modules:
            del sys.modules["ai.system.dep_scanner"]

        import ai.system.dep_scanner  # noqa: F401

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
