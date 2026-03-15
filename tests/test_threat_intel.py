"""Unit tests for Phase 1 threat intelligence modules.

Covers: ThreatReport model, VT/OTX/MB provider lookups, cascading logic,
and HTML formatter. All API calls are mocked — no real network traffic.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai.threat_intel.formatters import RISK_COLORS, format_html_section, format_single_row
from ai.threat_intel.models import ThreatReport

# ── Fixtures ──


@pytest.fixture()
def mock_limiter():
    """RateLimiter mock that allows all calls."""
    limiter = MagicMock()
    limiter.can_call.return_value = True
    limiter.wait_time.return_value = 0.0
    return limiter


@pytest.fixture()
def sample_report():
    """A ThreatReport with realistic VT data."""
    return ThreatReport(
        hash="a" * 64,
        filename="eicar-test.txt",
        source="virustotal",
        family="trojan.eicar/test",
        category="trojan",
        detection_ratio="62/72",
        risk_level="high",
        description="VirusTotal: 62/72 detections",
        tags=["eicar", "test-file"],
        vt_link="https://www.virustotal.com/gui/file/" + "a" * 64,
        timestamp="2026-03-15T12:00:00+00:00",
        raw_data={"last_analysis_stats": {"malicious": 62}},
    )


@pytest.fixture()
def no_data_report():
    """A ThreatReport with no provider data."""
    return ThreatReport(hash="b" * 64, source="none")


# ── ThreatReport Model Tests ──


class TestThreatReportModel:
    def test_defaults(self):
        r = ThreatReport(hash="c" * 64)
        assert r.source == ""
        assert r.risk_level == "unknown"
        assert r.tags == []
        assert r.raw_data == {}

    def test_has_data_true(self, sample_report):
        assert sample_report.has_data is True

    def test_has_data_false_empty(self):
        r = ThreatReport(hash="d" * 64, source="")
        assert r.has_data is False

    def test_has_data_false_none_source(self, no_data_report):
        assert no_data_report.has_data is False

    def test_to_jsonl_valid_json(self, sample_report):
        jsonl = sample_report.to_jsonl()
        data = json.loads(jsonl)
        assert data["hash"] == "a" * 64
        assert data["source"] == "virustotal"
        assert data["detection_ratio"] == "62/72"
        assert data["family"] == "trojan.eicar/test"

    def test_to_jsonl_excludes_raw_data(self, sample_report):
        data = json.loads(sample_report.to_jsonl())
        assert "raw_data" not in data


# ── VirusTotal Lookup Tests ──


class TestVirusTotalLookup:
    @patch("ai.threat_intel.lookup.get_key", return_value="fake-vt-key")
    @patch("ai.threat_intel.lookup.vt")
    def test_vt_found(self, mock_vt, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_virustotal

        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default=None: {
            "last_analysis_stats": {"malicious": 62, "undetected": 8, "harmless": 2},
            "popular_threat_classification": {
                "suggested_threat_label": "trojan.eicar/test",
                "popular_threat_category": [{"value": "trojan"}],
            },
            "tags": ["eicar"],
            "meaningful_name": "eicar-test.txt",
        }.get(key, default)
        mock_vt.Client.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_vt.Client.return_value.__enter__.return_value.get_object.return_value = mock_file
        mock_vt.Client.return_value.__exit__ = MagicMock(return_value=False)

        result = _lookup_virustotal("a" * 64, mock_limiter)
        assert result is not None
        assert result.source == "virustotal"
        assert result.detection_ratio == "62/72"
        assert result.risk_level == "high"
        assert result.vt_link.endswith("a" * 64)
        mock_limiter.record_call.assert_called_with("virustotal")

    @patch("ai.threat_intel.lookup.get_key", return_value="fake-vt-key")
    @patch("ai.threat_intel.lookup.vt")
    def test_vt_not_found(self, mock_vt, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_virustotal

        mock_vt.error.APIError = type("APIError", (Exception,), {})
        mock_vt.Client.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_vt.Client.return_value.__enter__.return_value.get_object.side_effect = (
            mock_vt.error.APIError("NotFoundError")
        )
        mock_vt.Client.return_value.__exit__ = MagicMock(return_value=False)

        result = _lookup_virustotal("a" * 64, mock_limiter)
        assert result is None

    def test_vt_rate_limited(self, mock_limiter):
        from ai.threat_intel.lookup import _lookup_virustotal

        mock_limiter.can_call.return_value = False
        result = _lookup_virustotal("a" * 64, mock_limiter)
        assert result is None

    @patch("ai.threat_intel.lookup.get_key", return_value=None)
    def test_vt_no_key(self, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_virustotal

        result = _lookup_virustotal("a" * 64, mock_limiter)
        assert result is None

    @patch("ai.threat_intel.lookup.get_key", return_value="fake-vt-key")
    @patch("ai.threat_intel.lookup.vt")
    def test_vt_no_classification(self, mock_vt, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_virustotal

        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default=None: {
            "last_analysis_stats": {"malicious": 1, "undetected": 70, "harmless": 1},
        }.get(key, default)
        mock_vt.Client.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_vt.Client.return_value.__enter__.return_value.get_object.return_value = mock_file
        mock_vt.Client.return_value.__exit__ = MagicMock(return_value=False)

        result = _lookup_virustotal("a" * 64, mock_limiter)
        assert result is not None
        assert result.family == ""
        assert result.risk_level == "low"


# ── OTX Lookup Tests ──


class TestOTXLookup:
    @patch("ai.threat_intel.lookup.get_key", return_value="fake-otx-key")
    @patch("ai.threat_intel.lookup.requests")
    def test_otx_found(self, mock_requests, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_otx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "pulse_info": {
                "count": 5,
                "pulses": [
                    {
                        "malware_families": [{"display_name": "Emotet"}],
                        "tags": ["banking", "trojan"],
                    },
                    {"malware_families": [], "tags": ["malware"]},
                ],
            },
            "general": {"description": "Known banking trojan"},
        }
        mock_requests.get.return_value = mock_resp

        result = _lookup_otx("a" * 64, mock_limiter)
        assert result is not None
        assert result.source == "otx"
        assert result.family == "Emotet"
        assert result.risk_level == "medium"
        assert "banking" in result.tags

    @patch("ai.threat_intel.lookup.get_key", return_value="fake-otx-key")
    @patch("ai.threat_intel.lookup.requests")
    def test_otx_no_pulses(self, mock_requests, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_otx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"pulse_info": {"count": 0, "pulses": []}}
        mock_requests.get.return_value = mock_resp

        result = _lookup_otx("a" * 64, mock_limiter)
        assert result is None

    @patch("ai.threat_intel.lookup.get_key", return_value="fake-otx-key")
    @patch("ai.threat_intel.lookup.requests")
    def test_otx_timeout(self, mock_requests, _mock_key, mock_limiter):
        import requests as real_requests

        from ai.threat_intel.lookup import _lookup_otx

        mock_requests.get.side_effect = real_requests.exceptions.Timeout("timed out")
        mock_requests.exceptions = real_requests.exceptions

        result = _lookup_otx("a" * 64, mock_limiter)
        assert result is None

    @patch("ai.threat_intel.lookup.get_key", return_value=None)
    def test_otx_no_key(self, _mock_key, mock_limiter):
        from ai.threat_intel.lookup import _lookup_otx

        result = _lookup_otx("a" * 64, mock_limiter)
        assert result is None


# ── MalwareBazaar Lookup Tests ──


class TestMalwareBazaarLookup:
    @patch("ai.threat_intel.lookup.requests")
    def test_mb_found(self, mock_requests, mock_limiter):
        from ai.threat_intel.lookup import _lookup_malwarebazaar

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "query_status": "ok",
            "data": [
                {
                    "signature": "Emotet",
                    "file_name": "malware.exe",
                    "tags": ["emotet", "banker"],
                    "file_type": "exe",
                }
            ],
        }
        mock_requests.post.return_value = mock_resp

        result = _lookup_malwarebazaar("a" * 64, mock_limiter)
        assert result is not None
        assert result.source == "malwarebazaar"
        assert result.family == "Emotet"
        assert result.risk_level == "high"

    @patch("ai.threat_intel.lookup.requests")
    def test_mb_not_found(self, mock_requests, mock_limiter):
        from ai.threat_intel.lookup import _lookup_malwarebazaar

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"query_status": "hash_not_found"}
        mock_requests.post.return_value = mock_resp

        result = _lookup_malwarebazaar("a" * 64, mock_limiter)
        assert result is None

    @patch("ai.threat_intel.lookup.requests")
    def test_mb_uses_form_encoding(self, mock_requests, mock_limiter):
        from ai.threat_intel.lookup import _lookup_malwarebazaar

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"query_status": "hash_not_found"}
        mock_requests.post.return_value = mock_resp

        _lookup_malwarebazaar("a" * 64, mock_limiter)

        call_kwargs = mock_requests.post.call_args
        assert "data" in call_kwargs.kwargs, "MalwareBazaar must use form-encoded data= not json="
        assert "json" not in call_kwargs.kwargs or call_kwargs.kwargs["json"] is None


# ── Cascading Logic Tests ──


class TestCascadingLogic:
    @patch("ai.threat_intel.lookup._lookup_malwarebazaar")
    @patch("ai.threat_intel.lookup._lookup_otx")
    @patch("ai.threat_intel.lookup._lookup_virustotal")
    def test_vt_hit_stops(self, mock_vt, mock_otx, mock_mb, mock_limiter, sample_report, tmp_path):
        from ai.threat_intel.lookup import lookup_hash

        mock_vt.return_value = sample_report

        with patch("ai.threat_intel.lookup.ENRICHED_HASHES", tmp_path / "enriched.jsonl"):
            result = lookup_hash("a" * 64, rate_limiter=mock_limiter)

        assert result.source == "virustotal"
        mock_otx.assert_not_called()
        mock_mb.assert_not_called()

    @patch("ai.threat_intel.lookup._lookup_malwarebazaar")
    @patch("ai.threat_intel.lookup._lookup_otx")
    @patch("ai.threat_intel.lookup._lookup_virustotal")
    def test_vt_miss_otx_hit(self, mock_vt, mock_otx, mock_mb, mock_limiter, tmp_path):
        from ai.threat_intel.lookup import lookup_hash

        mock_vt.return_value = None
        mock_otx.return_value = ThreatReport(
            hash="a" * 64, source="otx", family="Emotet", risk_level="medium"
        )

        with patch("ai.threat_intel.lookup.ENRICHED_HASHES", tmp_path / "enriched.jsonl"):
            result = lookup_hash("a" * 64, rate_limiter=mock_limiter)

        assert result.source == "otx"
        mock_mb.assert_not_called()

    @patch("ai.threat_intel.lookup._lookup_malwarebazaar", return_value=None)
    @patch("ai.threat_intel.lookup._lookup_otx", return_value=None)
    @patch("ai.threat_intel.lookup._lookup_virustotal", return_value=None)
    def test_all_miss(self, _vt, _otx, _mb, mock_limiter, tmp_path):
        from ai.threat_intel.lookup import lookup_hash

        with patch("ai.threat_intel.lookup.ENRICHED_HASHES", tmp_path / "enriched.jsonl"):
            result = lookup_hash("a" * 64, rate_limiter=mock_limiter)

        assert result.source == "none"
        assert result.has_data is False

    @patch("ai.threat_intel.lookup._lookup_malwarebazaar")
    @patch("ai.threat_intel.lookup._lookup_otx")
    @patch("ai.threat_intel.lookup._lookup_virustotal")
    def test_vt_rate_limited_skips_to_otx(self, mock_vt, mock_otx, mock_mb, mock_limiter, tmp_path):
        from ai.threat_intel.lookup import lookup_hash

        # VT returns None (rate limited internally), OTX returns data
        mock_vt.return_value = None
        mock_otx.return_value = ThreatReport(
            hash="a" * 64, source="otx", family="TestFamily", risk_level="low"
        )

        with patch("ai.threat_intel.lookup.ENRICHED_HASHES", tmp_path / "enriched.jsonl"):
            result = lookup_hash("a" * 64, rate_limiter=mock_limiter)

        assert result.source == "otx"

    def test_invalid_hash(self, mock_limiter):
        from ai.threat_intel.lookup import lookup_hash

        result = lookup_hash("not-a-hash", rate_limiter=mock_limiter)
        assert result.source == "none"
        assert "Invalid" in result.description


# ── HTML Formatter Tests ──


class TestHTMLFormatter:
    def test_single_report(self, sample_report):
        html = format_html_section([sample_report])
        assert "<div" in html
        assert "Threat Intelligence" in html
        assert "62/72" in html
        assert "trojan.eicar/test" in html

    def test_multiple_reports(self, sample_report):
        reports = [sample_report, sample_report, sample_report]
        html = format_html_section(reports)
        assert html.count("<tr") == 4  # 1 header + 3 data rows

    def test_no_data_returns_empty(self, no_data_report):
        result = format_html_section([no_data_report])
        assert result == ""

    def test_all_no_data_returns_empty(self):
        reports = [
            ThreatReport(hash="a" * 64, source="none"),
            ThreatReport(hash="b" * 64, source=""),
        ]
        assert format_html_section(reports) == ""

    def test_risk_badge_colors(self):
        for level, colors in RISK_COLORS.items():
            report = ThreatReport(
                hash="a" * 64, source="virustotal", risk_level=level
            )
            row = format_single_row(report)
            assert colors["bg"] in row
            assert colors["text"] in row
            assert level.upper() in row

    def test_xss_protection(self):
        report = ThreatReport(
            hash="a" * 64,
            filename='<script>alert("xss")</script>',
            source="virustotal",
            family='<img src=x onerror="alert(1)">',
            risk_level="high",
        )
        row = format_single_row(report)
        assert "<script>" not in row
        assert "&lt;script&gt;" in row
        assert "<img" not in row
        assert "&lt;img" in row

    def test_detection_ratio_display(self, sample_report):
        row = format_single_row(sample_report)
        assert "62/72" in row

    def test_detection_na_when_empty(self, no_data_report):
        row = format_single_row(no_data_report)
        assert "N/A" in row

    def test_high_detection_ratio_red(self):
        report = ThreatReport(
            hash="a" * 64,
            source="virustotal",
            detection_ratio="60/72",
            risk_level="high",
        )
        row = format_single_row(report)
        assert "#ef4444" in row  # red color for >50% detection

    def test_low_detection_ratio_not_red(self):
        report = ThreatReport(
            hash="a" * 64,
            source="virustotal",
            detection_ratio="2/72",
            risk_level="low",
        )
        row = format_single_row(report)
        assert "2/72" in row
        # The detection cell should NOT have the red danger color
        # Extract the detection <td> (second td in the row)
        tds = row.split("</td>")
        detection_td = tds[1] if len(tds) > 1 else ""
        assert "#ef4444" not in detection_td

    def test_vt_link_rendered(self, sample_report):
        row = format_single_row(sample_report)
        assert "href=" in row
        assert "virustotal" in row

    def test_no_vt_link_shows_source_text(self):
        report = ThreatReport(
            hash="a" * 64, source="otx", risk_level="medium"
        )
        row = format_single_row(report)
        assert "href=" not in row
        assert "otx" in row
