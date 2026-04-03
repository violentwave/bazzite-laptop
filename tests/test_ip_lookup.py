"""Unit tests for ai/threat_intel/ip_lookup.py.

Covers: input validation, provider parsing, tiebreaker logic, cascade
orchestration, graceful degradation, and rate-limiter integration.
All network calls are mocked — no real HTTP traffic.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai.threat_intel.ip_lookup import (
    _enrich_shodan,
    _lookup_abuseipdb,
    _lookup_greynoise,
    _make_recommendation,
    _validate_ip,
    lookup_ip,
)

_EMPTY_SHODAN = {"ports": [], "vulns": []}
_ENRICH_EMPTY = "ai.threat_intel.ip_lookup._enrich_shodan"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_ip_cache():
    """Prevent disk-based cache from polluting tests."""
    with patch("ai.threat_intel.ip_lookup._ip_cache.get", return_value=None):
        yield


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


def _mock_response(json_data: dict, status_code: int = 200):
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


class TestValidateIP:
    def test_valid_public_ipv4(self):
        assert _validate_ip("1.2.3.4") == "1.2.3.4"

    def test_valid_public_ipv6(self):
        # 2606:4700:4700::1111 is Cloudflare's public DNS (genuinely public IPv6)
        assert _validate_ip("2606:4700:4700::1111") is not None

    def test_private_ipv4_rejected(self):
        assert _validate_ip("192.168.1.1") is None

    def test_private_10_block_rejected(self):
        assert _validate_ip("10.0.0.1") is None

    def test_loopback_rejected(self):
        assert _validate_ip("127.0.0.1") is None

    def test_loopback_ipv6_rejected(self):
        assert _validate_ip("::1") is None

    def test_malformed_rejected(self):
        assert _validate_ip("not-an-ip") is None

    def test_empty_string_rejected(self):
        assert _validate_ip("") is None

    def test_strips_whitespace(self):
        assert _validate_ip("  8.8.8.8  ") == "8.8.8.8"

    def test_link_local_rejected(self):
        assert _validate_ip("169.254.0.1") is None


# ── AbuseIPDB Provider ────────────────────────────────────────────────────────


class TestLookupAbuseIPDB:
    def test_returns_score_on_success(self, mock_limiter):
        payload = {"data": {"abuseConfidenceScore": 85}}
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(payload)),
        ):
            result = _lookup_abuseipdb("1.2.3.4", mock_limiter)

        assert result == 85

    def test_returns_zero_score(self, mock_limiter):
        payload = {"data": {"abuseConfidenceScore": 0}}
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(payload)),
        ):
            result = _lookup_abuseipdb("1.2.3.4", mock_limiter)

        assert result == 0

    def test_returns_none_when_rate_limited(self, blocked_limiter):
        result = _lookup_abuseipdb("1.2.3.4", blocked_limiter)
        assert result is None

    def test_returns_none_when_no_key(self, mock_limiter):
        with patch("ai.threat_intel.ip_lookup.get_key", return_value=None):
            result = _lookup_abuseipdb("1.2.3.4", mock_limiter)
        assert result is None

    def test_returns_none_on_request_error(self, mock_limiter):
        from requests.exceptions import ConnectionError as ConnError  # noqa: PLC0415

        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", side_effect=ConnError()),
        ):
            result = _lookup_abuseipdb("1.2.3.4", mock_limiter)

        assert result is None

    def test_returns_none_when_score_missing(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch(
                "ai.threat_intel.ip_lookup.requests.get",
                return_value=_mock_response({"data": {}}),
            ),
        ):
            result = _lookup_abuseipdb("1.2.3.4", mock_limiter)

        assert result is None

    def test_records_call_on_success(self, mock_limiter):
        payload = {"data": {"abuseConfidenceScore": 10}}
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(payload)),
        ):
            _lookup_abuseipdb("1.2.3.4", mock_limiter)

        mock_limiter.record_call.assert_called_once_with("abuseipdb")


# ── GreyNoise Provider ────────────────────────────────────────────────────────


class TestLookupGreyNoise:
    def test_returns_malicious_classification(self, mock_limiter):
        payload = {"classification": "malicious", "noise": True}
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(payload)),
        ):
            result = _lookup_greynoise("1.2.3.4", mock_limiter)

        assert result == "malicious"

    def test_returns_benign_classification(self, mock_limiter):
        payload = {"classification": "benign", "noise": True}
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(payload)),
        ):
            result = _lookup_greynoise("1.2.3.4", mock_limiter)

        assert result == "benign"

    def test_returns_unknown_on_404(self, mock_limiter):
        resp = _mock_response({}, status_code=404)
        resp.raise_for_status = MagicMock()  # 404 should not raise in our logic
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=resp),
        ):
            result = _lookup_greynoise("1.2.3.4", mock_limiter)

        assert result == "unknown"

    def test_returns_none_when_rate_limited(self, blocked_limiter):
        result = _lookup_greynoise("1.2.3.4", blocked_limiter)
        assert result is None

    def test_returns_none_when_no_key(self, mock_limiter):
        with patch("ai.threat_intel.ip_lookup.get_key", return_value=None):
            result = _lookup_greynoise("1.2.3.4", mock_limiter)
        assert result is None

    def test_returns_none_on_request_error(self, mock_limiter):
        from requests.exceptions import ConnectionError as ConnError  # noqa: PLC0415

        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="fakekey"),
            patch("ai.threat_intel.ip_lookup.requests.get", side_effect=ConnError()),
        ):
            result = _lookup_greynoise("1.2.3.4", mock_limiter)

        assert result is None


# ── Shodan InternetDB Enrichment ──────────────────────────────────────────────


class TestEnrichShodan:
    def test_returns_ports_and_vulns(self):
        payload = {"ports": [80, 443, 8080], "vulns": ["CVE-2021-44228"]}
        with patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(payload)):
            result = _enrich_shodan("1.2.3.4")

        assert result["ports"] == [80, 443, 8080]
        assert "CVE-2021-44228" in result["vulns"]

    def test_returns_empty_on_404(self):
        resp = _mock_response({}, status_code=404)
        resp.raise_for_status = MagicMock()
        with patch("ai.threat_intel.ip_lookup.requests.get", return_value=resp):
            result = _enrich_shodan("1.2.3.4")

        assert result == {"ports": [], "vulns": []}

    def test_returns_empty_on_request_error(self):
        from requests.exceptions import ConnectionError as ConnError  # noqa: PLC0415

        with patch("ai.threat_intel.ip_lookup.requests.get", side_effect=ConnError()):
            result = _enrich_shodan("1.2.3.4")

        assert result == {"ports": [], "vulns": []}

    def test_handles_missing_keys_gracefully(self):
        with patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response({})):
            result = _enrich_shodan("1.2.3.4")

        assert result["ports"] == []
        assert result["vulns"] == []


# ── Recommendation Logic ──────────────────────────────────────────────────────


class TestMakeRecommendation:
    def test_score_80_block(self):
        assert _make_recommendation(80, None) == "block on firewall"

    def test_score_100_block(self):
        assert _make_recommendation(100, None) == "block on firewall"

    def test_score_50_malicious_greynoise(self):
        assert _make_recommendation(50, "malicious") == "likely malicious"

    def test_score_79_malicious_greynoise(self):
        assert _make_recommendation(79, "malicious") == "likely malicious"

    def test_score_50_benign_greynoise(self):
        assert _make_recommendation(50, "benign") == "known scanner"

    def test_score_79_benign_greynoise(self):
        assert _make_recommendation(79, "benign") == "known scanner"

    def test_score_50_no_greynoise_defaults_likely_malicious(self):
        assert _make_recommendation(50, None) == "likely malicious"

    def test_score_30_suspicious(self):
        assert _make_recommendation(30, None) == "suspicious"

    def test_score_49_suspicious(self):
        assert _make_recommendation(49, None) == "suspicious"

    def test_score_29_low_risk(self):
        assert _make_recommendation(29, None) == "low risk"

    def test_score_0_low_risk(self):
        assert _make_recommendation(0, None) == "low risk"


# ── Tiebreaker Logic ──────────────────────────────────────────────────────────


class TestTiebreakerLogic:
    """GreyNoise is only called when AbuseIPDB score is in the 30-70 range."""

    def _make_mocks(self, abuse_score, gn_class, shodan_data=None):
        """Build patched provider mocks."""
        shodan_data = shodan_data or {"ports": [], "vulns": []}
        abuse_resp = {"data": {"abuseConfidenceScore": abuse_score}}
        gn_resp = {"classification": gn_class}

        return (
            _mock_response(abuse_resp),
            _mock_response(gn_resp),
            shodan_data,
        )

    def test_score_55_triggers_greynoise_and_applies(self, mock_limiter):
        # Score 55 is in both the tiebreaker range (30-70) and the greynoise-
        # dependent range (50-79), so classification changes the recommendation.
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="key"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(
                {"data": {"abuseConfidenceScore": 55}}
            )),
            patch(
                "ai.threat_intel.ip_lookup._lookup_greynoise", return_value="benign"
            ) as mock_gn,
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        mock_gn.assert_called_once()
        assert report.recommendation == "known scanner"

    def test_score_29_skips_greynoise(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="key"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(
                {"data": {"abuseConfidenceScore": 29}}
            )),
            patch("ai.threat_intel.ip_lookup._lookup_greynoise") as mock_gn,
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        mock_gn.assert_not_called()
        assert report.recommendation == "low risk"

    def test_score_71_skips_greynoise(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="key"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(
                {"data": {"abuseConfidenceScore": 71}}
            )),
            patch("ai.threat_intel.ip_lookup._lookup_greynoise") as mock_gn,
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        mock_gn.assert_not_called()
        assert report.recommendation == "likely malicious"

    def test_score_70_triggers_greynoise(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup.get_key", return_value="key"),
            patch("ai.threat_intel.ip_lookup.requests.get", return_value=_mock_response(
                {"data": {"abuseConfidenceScore": 70}}
            )),
            patch(
                "ai.threat_intel.ip_lookup._lookup_greynoise", return_value="malicious"
            ) as mock_gn,
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            lookup_ip("1.2.3.4", mock_limiter)

        mock_gn.assert_called_once()


# ── Full Cascade ──────────────────────────────────────────────────────────────


class TestLookupIP:
    def test_valid_ip_with_all_providers(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=85),
            patch("ai.threat_intel.ip_lookup._lookup_greynoise", return_value=None),
            patch(_ENRICH_EMPTY, return_value={"ports": [80], "vulns": []}),
        ):
            report = lookup_ip("8.8.8.8", mock_limiter)

        assert report.ip == "8.8.8.8"
        assert report.abuse_score == 85
        assert report.recommendation == "block on firewall"
        assert report.ports == [80]
        assert report.has_data is True

    def test_private_ip_returns_none_report(self, mock_limiter):
        report = lookup_ip("192.168.1.1", mock_limiter)
        assert report.source == "none"
        assert report.has_data is False
        assert "private" in report.description.lower() or "invalid" in report.description.lower()

    def test_invalid_ip_returns_none_report(self, mock_limiter):
        report = lookup_ip("not-an-ip", mock_limiter)
        assert report.source == "none"
        assert report.has_data is False

    def test_abuseipdb_failure_graceful_degradation(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=None),
            patch(_ENRICH_EMPTY, return_value={"ports": [22], "vulns": []}),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        assert report.source == "none"
        assert report.ports == [22]  # Shodan enrichment still included
        assert report.has_data is False

    def test_greynoise_failure_doesnt_block_report(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=50),
            patch("ai.threat_intel.ip_lookup._lookup_greynoise", return_value=None),
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        assert report.has_data is True
        assert report.recommendation == "likely malicious"  # default for empty greynoise
        assert report.greynoise_classification == ""

    def test_shodan_failure_doesnt_block_report(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=20),
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        assert report.has_data is True
        assert report.recommendation == "low risk"

    def test_report_includes_shodan_vulns(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=10),
            patch("ai.threat_intel.ip_lookup._enrich_shodan", return_value={
                "ports": [80, 443],
                "vulns": ["CVE-2021-44228"],
            }),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        assert "CVE-2021-44228" in report.vulns
        assert 80 in report.ports

    def test_source_includes_greynoise_when_queried(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=45),
            patch("ai.threat_intel.ip_lookup._lookup_greynoise", return_value="benign"),
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("1.2.3.4", mock_limiter)

        assert "greynoise" in report.source
        assert "abuseipdb" in report.source

    def test_to_json_valid_and_no_raw_data(self, mock_limiter):
        with (
            patch("ai.threat_intel.ip_lookup._lookup_abuseipdb", return_value=90),
            patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN),
        ):
            report = lookup_ip("8.8.8.8", mock_limiter)

        data = json.loads(report.to_json())
        assert "raw_data" not in data
        assert data["ip"] == "8.8.8.8"
        assert data["recommendation"] == "block on firewall"

    def test_rate_limiter_respected(self):
        blocked = MagicMock()
        blocked.can_call.return_value = False

        with patch(_ENRICH_EMPTY, return_value=_EMPTY_SHODAN):
            report = lookup_ip("1.2.3.4", blocked)

        assert report.source == "none"
