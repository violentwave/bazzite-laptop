"""Unit tests for ai/threat_intel/ioc_lookup.py.

Covers: input validation, provider parsing, cascade logic,
CIRCL enrichment, graceful degradation, and rate-limiter integration.
All network calls are mocked — no real HTTP traffic.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai.threat_intel.ioc_lookup import (
    IOCReport,
    _enrich_circl,
    _lookup_threatfox,
    _lookup_urlhaus,
    _validate_url,
    lookup_url,
)

# Patch target shortcuts
_UH = "ai.threat_intel.ioc_lookup._lookup_urlhaus"
_TF = "ai.threat_intel.ioc_lookup._lookup_threatfox"
_CIRCL = "ai.threat_intel.ioc_lookup._enrich_circl"

# Minimal URLhaus hit dict
_UH_HIT = {
    "threat_type": "malware_download",
    "malware_family": "Trojan.Generic",
    "tags": ["exe", "trojan"],
    "payload_hashes": [],
    "risk_level": "high",
    "raw": {},
}

# Minimal ThreatFox hit dict
_TF_HIT = {
    "threat_type": "botnet_cc",
    "malware_family": "Mirai",
    "tags": ["botnet"],
    "confidence": 85,
    "risk_level": "high",
    "raw": {},
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_limiter():
    """RateLimiter mock that allows all calls."""
    limiter = MagicMock()
    limiter.can_call.return_value = True
    limiter.wait_time.return_value = 0.0
    return limiter


@pytest.fixture()
def blocked_limiter():
    """RateLimiter mock that blocks all calls."""
    limiter = MagicMock()
    limiter.can_call.return_value = False
    return limiter


def _mock_resp(json_data: dict, status_code: int = 200):
    """Build a minimal requests.Response mock."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from requests.exceptions import HTTPError  # noqa: PLC0415
        resp.raise_for_status.side_effect = HTTPError(response=resp)
    return resp


# ── Input Validation ──────────────────────────────────────────────────────────


class TestValidateURL:
    def test_valid_http(self):
        assert _validate_url("http://example.com") == "http://example.com"

    def test_valid_https_with_path(self):
        url = "https://evil.example.com/malware.exe"
        assert _validate_url(url) == url

    def test_valid_ftp(self):
        assert _validate_url("ftp://files.example.com/bad.bin") is not None

    def test_strips_whitespace(self):
        assert _validate_url("  http://example.com  ") == "http://example.com"

    def test_empty_rejected(self):
        assert _validate_url("") is None

    def test_no_scheme_rejected(self):
        assert _validate_url("example.com") is None

    def test_file_scheme_rejected(self):
        assert _validate_url("file:///etc/passwd") is None

    def test_javascript_scheme_rejected(self):
        assert _validate_url("javascript:alert(1)") is None

    def test_no_netloc_rejected(self):
        assert _validate_url("http://") is None


# ── URLhaus Provider ──────────────────────────────────────────────────────────


class TestLookupURLhaus:
    def test_returns_dict_on_hit(self, mock_limiter):
        payload = {
            "query_status": "is_host",
            "threat": "malware_download",
            "tags": ["exe"],
            "payloads": [],
        }
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp(payload),
        ):
            result = _lookup_urlhaus("http://example.com", mock_limiter)

        assert result is not None
        assert result["threat_type"] == "malware_download"
        assert result["risk_level"] == "high"

    def test_returns_none_on_no_results(self, mock_limiter):
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp({"query_status": "no_results"}),
        ):
            result = _lookup_urlhaus("http://clean.example.com", mock_limiter)

        assert result is None

    def test_returns_none_on_invalid_url_status(self, mock_limiter):
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp({"query_status": "invalid_url"}),
        ):
            result = _lookup_urlhaus("http://x", mock_limiter)

        assert result is None

    def test_extracts_payload_hashes(self, mock_limiter):
        payload = {
            "query_status": "is_host",
            "threat": "malware_download",
            "tags": [],
            "payloads": [
                {"sha256_hash": "abc123" + "a" * 58, "signature": "Trojan.X"},
                {"sha256_hash": "def456" + "b" * 58, "signature": ""},
            ],
        }
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp(payload),
        ):
            result = _lookup_urlhaus("http://example.com", mock_limiter)

        assert len(result["payload_hashes"]) == 2
        assert result["malware_family"] == "Trojan.X"

    def test_returns_none_when_rate_limited(self, blocked_limiter):
        result = _lookup_urlhaus("http://example.com", blocked_limiter)
        assert result is None

    def test_returns_none_on_request_error(self, mock_limiter):
        from requests.exceptions import ConnectionError as ConnError  # noqa: PLC0415

        with patch(
            "ai.threat_intel.ioc_lookup.requests.post", side_effect=ConnError()
        ):
            result = _lookup_urlhaus("http://example.com", mock_limiter)

        assert result is None

    def test_records_call_on_success(self, mock_limiter):
        payload = {"query_status": "is_host", "threat": "malware_download",
                   "tags": [], "payloads": []}
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp(payload),
        ):
            _lookup_urlhaus("http://example.com", mock_limiter)

        mock_limiter.record_call.assert_called_once_with("urlhaus")


# ── ThreatFox Provider ────────────────────────────────────────────────────────


class TestLookupThreatFox:
    def test_returns_dict_on_hit(self, mock_limiter):
        payload = {
            "query_status": "ok",
            "data": [{"threat_type": "botnet_cc", "malware": "Mirai",
                      "confidence_level": 80, "tags": ["mirai"]}],
        }
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp(payload),
        ):
            result = _lookup_threatfox("http://evil.com", mock_limiter)

        assert result is not None
        assert result["threat_type"] == "botnet_cc"
        assert result["malware_family"] == "Mirai"

    def test_returns_none_on_no_results(self, mock_limiter):
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp({"query_status": "no_results"}),
        ):
            result = _lookup_threatfox("http://clean.com", mock_limiter)

        assert result is None

    def test_returns_none_on_empty_data(self, mock_limiter):
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp({"query_status": "ok", "data": []}),
        ):
            result = _lookup_threatfox("http://clean.com", mock_limiter)

        assert result is None

    @pytest.mark.parametrize("conf,expected", [
        (90, "high"),
        (75, "high"),
        (74, "medium"),
        (50, "medium"),
        (49, "low"),
        (0, "low"),
    ])
    def test_confidence_risk_mapping(self, mock_limiter, conf, expected):
        payload = {
            "query_status": "ok",
            "data": [{"threat_type": "x", "malware": "y",
                      "confidence_level": conf, "tags": []}],
        }
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp(payload),
        ):
            result = _lookup_threatfox("http://x.com", mock_limiter)

        assert result["risk_level"] == expected

    def test_returns_none_when_rate_limited(self, blocked_limiter):
        result = _lookup_threatfox("http://x.com", blocked_limiter)
        assert result is None

    def test_returns_none_on_request_error(self, mock_limiter):
        from requests.exceptions import ConnectionError as ConnError  # noqa: PLC0415

        with patch(
            "ai.threat_intel.ioc_lookup.requests.post", side_effect=ConnError()
        ):
            result = _lookup_threatfox("http://x.com", mock_limiter)

        assert result is None

    def test_records_call_on_success(self, mock_limiter):
        payload = {
            "query_status": "ok",
            "data": [{"threat_type": "x", "malware": "y",
                      "confidence_level": 80, "tags": []}],
        }
        with patch(
            "ai.threat_intel.ioc_lookup.requests.post",
            return_value=_mock_resp(payload),
        ):
            _lookup_threatfox("http://x.com", mock_limiter)

        mock_limiter.record_call.assert_called_once_with("threatfox")


# ── CIRCL Hashlookup Enrichment ───────────────────────────────────────────────


class TestEnrichCIRL:
    def test_returns_dict_on_hit(self):
        payload = {"FileName": "evil.exe", "hashlookup:trust": 95}
        with patch(
            "ai.threat_intel.ioc_lookup.requests.get",
            return_value=_mock_resp(payload),
        ):
            result = _enrich_circl("a" * 64)

        assert result["filename"] == "evil.exe"
        assert result["trust"] == 95
        assert result["sha256"] == "a" * 64

    def test_returns_empty_on_404(self):
        resp = _mock_resp({}, status_code=404)
        resp.raise_for_status = MagicMock()
        with patch("ai.threat_intel.ioc_lookup.requests.get", return_value=resp):
            result = _enrich_circl("a" * 64)

        assert result == {}

    def test_returns_empty_on_request_error(self):
        from requests.exceptions import ConnectionError as ConnError  # noqa: PLC0415

        with patch(
            "ai.threat_intel.ioc_lookup.requests.get", side_effect=ConnError()
        ):
            result = _enrich_circl("a" * 64)

        assert result == {}

    def test_handles_missing_fields_gracefully(self):
        with patch(
            "ai.threat_intel.ioc_lookup.requests.get",
            return_value=_mock_resp({}),
        ):
            result = _enrich_circl("a" * 64)

        assert result["filename"] == ""
        assert result["trust"] == -1


# ── Cascade Orchestration ─────────────────────────────────────────────────────


class TestLookupURL:
    def test_urlhaus_hit_returns_urlhaus_source(self, mock_limiter):
        with (
            patch(_UH, return_value=_UH_HIT),
            patch(_CIRCL, return_value={}),
        ):
            report = lookup_url("http://evil.example.com", mock_limiter)

        assert report.source == "urlhaus"
        assert report.risk_level == "high"
        assert report.threat_type == "malware_download"
        assert report.has_data is True

    def test_urlhaus_miss_calls_threatfox(self, mock_limiter):
        with (
            patch(_UH, return_value=None),
            patch(_TF, return_value=_TF_HIT) as mock_tf,
        ):
            report = lookup_url("http://unknown.example.com", mock_limiter)

        mock_tf.assert_called_once()
        assert report.source == "threatfox"
        assert report.malware_family == "Mirai"

    def test_urlhaus_hit_skips_threatfox(self, mock_limiter):
        with (
            patch(_UH, return_value=_UH_HIT),
            patch(_TF) as mock_tf,
            patch(_CIRCL, return_value={}),
        ):
            lookup_url("http://evil.example.com", mock_limiter)

        mock_tf.assert_not_called()

    def test_circl_enrichment_when_urlhaus_has_hashes(self, mock_limiter):
        uh_with_hashes = {**_UH_HIT, "payload_hashes": ["a" * 64, "b" * 64]}
        circl_hit = {"sha256": "a" * 64, "filename": "evil.exe", "trust": 90}
        with (
            patch(_UH, return_value=uh_with_hashes),
            patch(_CIRCL, return_value=circl_hit) as mock_circl,
        ):
            report = lookup_url("http://evil.example.com", mock_limiter)

        assert mock_circl.call_count == 2
        assert len(report.circl_hits) == 2
        assert "circl" in report.source

    def test_circl_capped_at_3_hashes(self, mock_limiter):
        hashes = ["a" * 64, "b" * 64, "c" * 64, "d" * 64]
        uh_with_hashes = {**_UH_HIT, "payload_hashes": hashes}
        with (
            patch(_UH, return_value=uh_with_hashes),
            patch(_CIRCL, return_value={"sha256": "a", "filename": "", "trust": 1})
            as mock_circl,
        ):
            lookup_url("http://evil.example.com", mock_limiter)

        assert mock_circl.call_count == 3  # capped at 3

    def test_circl_miss_excludes_from_source(self, mock_limiter):
        uh_with_hashes = {**_UH_HIT, "payload_hashes": ["a" * 64]}
        with (
            patch(_UH, return_value=uh_with_hashes),
            patch(_CIRCL, return_value={}),
        ):
            report = lookup_url("http://evil.example.com", mock_limiter)

        assert "circl" not in report.source

    def test_both_miss_returns_none_report(self, mock_limiter):
        with (
            patch(_UH, return_value=None),
            patch(_TF, return_value=None),
        ):
            report = lookup_url("http://clean.example.com", mock_limiter)

        assert report.source == "none"
        assert report.has_data is False

    def test_invalid_url_returns_immediately(self, mock_limiter):
        with (
            patch(_UH) as mock_uh,
            patch(_TF) as mock_tf,
        ):
            report = lookup_url("not-a-url", mock_limiter)

        mock_uh.assert_not_called()
        mock_tf.assert_not_called()
        assert report.source == "none"
        assert "Invalid" in report.description

    def test_circl_failure_doesnt_block_report(self, mock_limiter):
        uh_with_hashes = {**_UH_HIT, "payload_hashes": ["a" * 64]}
        with (
            patch(_UH, return_value=uh_with_hashes),
            patch(_CIRCL, return_value={}),
        ):
            report = lookup_url("http://evil.example.com", mock_limiter)

        assert report.has_data is True
        assert report.circl_hits == []

    def test_threatfox_failure_graceful_degradation(self, mock_limiter):
        with (
            patch(_UH, return_value=None),
            patch(_TF, return_value=None),
        ):
            report = lookup_url("http://example.com", mock_limiter)

        assert report.source == "none"

    def test_tags_deduplicated(self, mock_limiter):
        uh_with_dups = {**_UH_HIT, "tags": ["exe", "malware", "exe"]}
        with (
            patch(_UH, return_value=uh_with_dups),
            patch(_CIRCL, return_value={}),
        ):
            report = lookup_url("http://evil.example.com", mock_limiter)

        assert report.tags.count("exe") == 1

    def test_to_json_excludes_raw_data(self, mock_limiter):
        with (
            patch(_UH, return_value=_UH_HIT),
            patch(_CIRCL, return_value={}),
        ):
            report = lookup_url("http://evil.example.com", mock_limiter)

        data = json.loads(report.to_json())
        assert "raw_data" not in data
        assert data["risk_level"] == "high"
        assert data["ioc"] == "http://evil.example.com"

    def test_rate_limiter_blocks_urlhaus(self):
        blocked = MagicMock()
        blocked.can_call.return_value = False
        with patch(_TF, return_value=None):
            report = lookup_url("http://evil.example.com", blocked)

        assert report.source == "none"


# ── IOCReport Model ───────────────────────────────────────────────────────────


class TestIOCReport:
    def test_has_data_true_with_source(self):
        r = IOCReport(ioc="http://x.com", source="urlhaus")
        assert r.has_data is True

    def test_has_data_false_when_source_none(self):
        r = IOCReport(ioc="http://x.com", source="none")
        assert r.has_data is False

    def test_has_data_false_when_source_empty(self):
        r = IOCReport(ioc="http://x.com")
        assert r.has_data is False

    def test_to_json_valid(self):
        r = IOCReport(
            ioc="http://evil.com",
            source="urlhaus",
            threat_type="malware_download",
            risk_level="high",
        )
        data = json.loads(r.to_json())
        assert data["ioc"] == "http://evil.com"
        assert data["source"] == "urlhaus"
        assert data["risk_level"] == "high"

    def test_to_json_has_timestamp(self):
        r = IOCReport(ioc="http://x.com", source="urlhaus")
        data = json.loads(r.to_json())
        assert "timestamp" in data
        assert data["timestamp"]
