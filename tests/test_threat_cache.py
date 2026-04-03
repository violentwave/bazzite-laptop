"""Tests for disk-based caching in the threat intel lookup pipeline.

Verifies cache miss (API called, result stored) and cache hit (API bypassed).
All network calls are mocked — no real HTTP traffic.
"""

from unittest.mock import MagicMock, patch

from ai.threat_intel.lookup import lookup_hash
from ai.threat_intel.models import ThreatReport

SHA256 = "a" * 64

_REPORT_DICT = {
    "hash": SHA256,
    "filename": "evil.exe",
    "source": "malwarebazaar",
    "family": "Trojan.Agent",
    "category": "exe",
    "detection_ratio": "",
    "risk_level": "high",
    "description": "MalwareBazaar: Trojan.Agent",
    "tags": ["trojan"],
    "vt_link": "",
    "timestamp": "2026-01-01T00:00:00+00:00",
}


class TestLookupHashCaching:
    def test_cache_miss_calls_provider_and_stores_result(self):
        """On a cache miss the provider chain runs and the result is written to cache."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # miss

        mb_report = ThreatReport(**_REPORT_DICT)

        with (
            patch("ai.threat_intel.lookup._threat_cache", mock_cache),
            patch(
                "ai.threat_intel.lookup._lookup_malwarebazaar",
                return_value=mb_report,
            ) as mock_mb,
            patch("ai.threat_intel.lookup._append_enriched"),
        ):
            result = lookup_hash(SHA256)

        mock_cache.get.assert_called_once_with(f"hash:{SHA256}")
        mock_mb.assert_called_once()
        mock_cache.set.assert_called_once()
        stored_key, stored_val = mock_cache.set.call_args[0]
        assert stored_key == f"hash:{SHA256}"
        assert stored_val["source"] == "malwarebazaar"
        assert result.source == "malwarebazaar"

    def test_cache_hit_skips_providers(self):
        """On a cache hit the provider chain is never called and cached data is returned."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = _REPORT_DICT  # hit

        with (
            patch("ai.threat_intel.lookup._threat_cache", mock_cache),
            patch("ai.threat_intel.lookup._lookup_malwarebazaar") as mock_mb,
            patch("ai.threat_intel.lookup._lookup_otx") as mock_otx,
            patch("ai.threat_intel.lookup._lookup_virustotal") as mock_vt,
        ):
            result = lookup_hash(SHA256)

        mock_cache.get.assert_called_once_with(f"hash:{SHA256}")
        mock_mb.assert_not_called()
        mock_otx.assert_not_called()
        mock_vt.assert_not_called()
        mock_cache.set.assert_not_called()
        assert result.source == "malwarebazaar"
        assert result.family == "Trojan.Agent"
        assert result.risk_level == "high"
