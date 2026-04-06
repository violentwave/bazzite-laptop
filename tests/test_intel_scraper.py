"""Tests for ai.intel_scraper module."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestStateRoundtrip:
    """Test state load/save round-trip."""

    def test_state_roundtrip(self, temp_output_dir):
        """Save state then load returns same dict."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()
        scraper.output_dir = temp_output_dir
        scraper.state = {
            "github_releases": "2024-01-15T10:00:00Z",
            "cisa_kev": "2024-01-16T10:00:00Z",
            "nvd_cves": "2024-01-17T10:00:00Z",
            "fedora_rss": "2024-01-18T10:00:00Z",
        }

        scraper._save_state()

        loaded = scraper._load_state(temp_output_dir)
        assert loaded == scraper.state


class TestAtomicWrite:
    """Test atomic write and deduplication."""

    def test_atomic_write_dedup(self, temp_output_dir):
        """Adding same URL twice writes only once."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()
        filepath = temp_output_dir / "test.jsonl"

        items = [
            {"url": "https://example.com/1", "title": "Item 1"},
            {"url": "https://example.com/1", "title": "Item 1 duplicate"},
            {"url": "https://example.com/2", "title": "Item 2"},
        ]

        scraper._atomic_write_jsonl(filepath, items)

        with open(filepath) as f:
            lines = f.readlines()

        assert len(lines) == 2

        parsed = [json.loads(line) for line in lines]
        urls = [item["url"] for item in parsed]
        assert "https://example.com/1" in urls
        assert "https://example.com/2" in urls
        assert urls.count("https://example.com/1") == 1


class TestCisaKev:
    """Test CISA KEV timezone-aware comparison."""

    def test_cisa_kev_tz_aware(self):
        """Items older than since_days are filtered."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()

        now = datetime.now(UTC)
        old_date = (now - timedelta(days=10)).strftime("%Y-%m-%d")
        recent_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vulnerabilities": [
                {"dateAdded": old_date, "cveID": "CVE-2024-0001"},
                {"dateAdded": recent_date, "cveID": "CVE-2024-0002"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.client, "get", return_value=mock_response):
            results = scraper.scrape_cisa_kev(since_days=7)

        dates = [r["date_added"] for r in results]
        assert recent_date in dates
        assert old_date not in dates


class TestNvdParams:
    """Test NVD URL params dict."""

    def test_nvd_params_dict(self):
        """NVD request uses params dict not URL string."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()

        mock_response = MagicMock()
        mock_response.json.return_value = {"vulnerabilities": []}
        mock_response.raise_for_status = MagicMock()

        captured_request = {}

        def capture_request(url, params=None):
            captured_request["url"] = url
            captured_request["params"] = params
            return mock_response

        with patch.object(scraper.client, "get", side_effect=capture_request):
            scraper.scrape_nvd_cves(days=7)

        assert "params" in captured_request
        assert captured_request["params"]["keywordSearch"] == "python linux fedora nvidia node npm"
        assert captured_request["params"]["resultsPerPage"] == 20
        assert "lastModStartDate" in captured_request["params"]


class TestPerSourceIsolation:
    """Test per-source error isolation."""

    def test_per_source_isolation(self, temp_output_dir):
        """One source raising does not abort others."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()

        def mock_get(url, **kwargs):
            if "cisa.gov" in url:
                raise Exception("CISA network error")
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"vulnerabilities": []}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch.object(scraper.client, "get", side_effect=mock_get):
            with patch.object(scraper, "scrape_github_releases", return_value=[]):
                with patch.object(scraper, "scrape_fedora_rss", return_value=[]):
                    summary = scraper.run_all(str(temp_output_dir))

        assert summary["total_new"] == 0


class TestImportNoSideEffects:
    """Test module import has no side effects."""

    def test_import_no_side_effects(self, capsys):
        """Importing module produces no output."""
        import sys

        if "ai.intel_scraper" in sys.modules:
            del sys.modules["ai.intel_scraper"]

        import ai.intel_scraper  # noqa: F401

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


class TestRunAllSummary:
    """Test run_all returns proper summary."""

    def test_run_all_summary_keys(self, temp_output_dir):
        """run_all returns dict with scraped_at/counts/total_new."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()

        mock_response = MagicMock()
        mock_response.json.return_value = {"vulnerabilities": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.client, "get", return_value=mock_response):
            with patch.object(scraper, "scrape_github_releases", return_value=[]):
                with patch.object(scraper, "scrape_fedora_rss", return_value=[]):
                    summary = scraper.run_all(str(temp_output_dir))

        assert "scraped_at" in summary
        assert "counts" in summary
        assert "total_new" in summary
        assert isinstance(summary["scraped_at"], str)
        assert isinstance(summary["counts"], dict)
        assert isinstance(summary["total_new"], int)


class TestGithubReleases:
    """Test GitHub releases filtering."""

    def test_github_releases_filters_old(self):
        """Releases older than since_days excluded."""
        from ai.intel_scraper import IntelScraper

        scraper = IntelScraper()

        now = datetime.now(UTC)
        old_date = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_date = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"published_at": old_date, "tag_name": "v1.0.0", "html_url": "https://example.com/1"},
            {
                "published_at": recent_date,
                "tag_name": "v1.1.0",
                "html_url": "https://example.com/2",
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.client, "get", return_value=mock_response):
            results = scraper.scrape_github_releases("owner", "repo", since_days=7)

        tags = [r["tag"] for r in results]
        assert "v1.1.0" in tags
        assert "v1.0.0" not in tags
