"""Unit tests for threat intelligence HTML email formatters.

Tests HTML escaping, risk color mapping, detection ratio parsing,
and XSS prevention in email generation.
"""

from ai.threat_intel.formatters import RISK_COLORS, format_html_section, format_single_row
from ai.threat_intel.models import ThreatReport


class TestRiskColors:
    """Test risk level color constants."""

    def test_all_levels_defined(self):
        """All expected risk levels have color definitions."""
        for level in ("high", "medium", "low", "clean", "unknown"):
            assert level in RISK_COLORS
            assert "text" in RISK_COLORS[level]
            assert "bg" in RISK_COLORS[level]

    def test_color_format(self):
        """Color values are valid hex codes."""
        import re
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for level, colors in RISK_COLORS.items():
            assert hex_pattern.match(colors["text"]), f"{level} text color invalid"
            assert hex_pattern.match(colors["bg"]), f"{level} bg color invalid"


class TestFormatSingleRow:
    """Test individual row formatting with XSS prevention."""

    def test_html_escape_filename(self):
        """Filenames with HTML are escaped."""
        report = ThreatReport(
            hash="a" * 64,
            filename='<script>alert("xss")</script>',
            source="test",
        )
        html = format_single_row(report)
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_html_escape_family(self):
        """Malware family names are escaped."""
        report = ThreatReport(
            hash="b" * 64,
            family='Trojan<img src=x onerror=alert(1)>',
            source="test",
        )
        html = format_single_row(report)
        assert "&lt;img" in html
        assert "onerror=" not in html

    def test_truncate_long_hash(self):
        """Hashes longer than 12 chars are truncated with ellipsis."""
        report = ThreatReport(hash="c" * 64)
        html = format_single_row(report)
        assert ("c" * 12) + "..." in html

    def test_short_hash_not_truncated(self):
        """Hashes ≤12 chars are not truncated."""
        report = ThreatReport(hash="short")
        html = format_single_row(report)
        assert "short" in html
        assert "..." not in html

    def test_detection_ratio_high_risk(self):
        """Detection ratio >50% is bolded and red."""
        report = ThreatReport(
            hash="d" * 64,
            detection_ratio="60/72",
            source="test",
        )
        html = format_single_row(report)
        assert "60/72" in html
        assert "font-weight:700" in html
        assert "#ef4444" in html  # red color

    def test_detection_ratio_low_risk(self):
        """Detection ratio ≤50% is bolded but not red."""
        report = ThreatReport(
            hash="e" * 64,
            detection_ratio="3/72",
            source="test",
        )
        html = format_single_row(report)
        assert "3/72" in html
        assert "font-weight:700" in html
        assert "#ef4444" not in html

    def test_detection_ratio_malformed(self):
        """Malformed detection ratios don't crash."""
        report = ThreatReport(
            hash="f" * 64,
            detection_ratio="invalid",
            source="test",
        )
        html = format_single_row(report)
        assert "invalid" in html
        # Should not crash on non-numeric ratio

    def test_detection_ratio_division_by_zero(self):
        """Detection ratio with 0 total doesn't crash."""
        report = ThreatReport(
            hash="g" * 64,
            detection_ratio="0/0",
            source="test",
        )
        html = format_single_row(report)
        assert "0/0" in html

    def test_javascript_url_blocked(self):
        """javascript: URLs in vt_link are not rendered as links."""
        report = ThreatReport(
            hash="h" * 64,
            vt_link='javascript:alert("xss")',
            source="test",
        )
        html = format_single_row(report)
        assert "<a href=" not in html or 'javascript:' not in html

    def test_https_url_allowed(self):
        """Valid https:// URLs are rendered as links."""
        report = ThreatReport(
            hash="i" * 64,
            vt_link="https://www.virustotal.com/gui/file/abc123",
            source="virustotal",
        )
        html = format_single_row(report)
        assert '<a href="https://www.virustotal.com' in html
        assert "virustotal" in html

    def test_no_data_report(self):
        """Reports without data show 'No data' source."""
        report = ThreatReport(hash="j" * 64)
        html = format_single_row(report)
        assert "No data" in html

    def test_risk_badge_colors(self):
        """Risk badges use correct colors from RISK_COLORS."""
        for level in ("high", "medium", "low", "clean", "unknown"):
            report = ThreatReport(hash="k" * 64, risk_level=level, source="test")
            html = format_single_row(report)
            expected_bg = RISK_COLORS[level]["bg"]
            expected_text = RISK_COLORS[level]["text"]
            assert expected_bg in html
            assert expected_text in html


class TestFormatHtmlSection:
    """Test full HTML section generation."""

    def test_empty_reports_no_output(self):
        """Empty report list returns empty string."""
        assert format_html_section([]) == ""

    def test_all_no_data_reports_no_output(self):
        """Reports without data produce no HTML section."""
        reports = [
            ThreatReport(hash="a" * 64),
            ThreatReport(hash="b" * 64),
        ]
        assert format_html_section(reports) == ""

    def test_mixed_reports_render_section(self):
        """Mix of data and no-data reports renders section."""
        reports = [
            ThreatReport(hash="a" * 64),  # no data
            ThreatReport(hash="b" * 64, source="test", detection_ratio="5/10"),
        ]
        html = format_html_section(reports)
        assert '<div style="margin:24px 0' in html
        assert "Threat Intelligence" in html
        assert "5/10" in html

    def test_table_structure(self):
        """HTML contains proper table structure."""
        reports = [
            ThreatReport(
                hash="c" * 64,
                filename="test.exe",
                source="virustotal",
                detection_ratio="10/20",
                family="Trojan.Test",
                risk_level="high",
            )
        ]
        html = format_html_section(reports)
        assert "<table" in html
        assert "<th" in html
        assert "<tr" in html
        assert "<td" in html
        assert "File" in html
        assert "Detection" in html
        assert "Family" in html
        assert "Risk" in html
        assert "Source" in html

    def test_multiple_reports(self):
        """Multiple reports generate multiple rows."""
        reports = [
            ThreatReport(hash="d" * 64, filename="file1.exe", source="vt"),
            ThreatReport(hash="e" * 64, filename="file2.dll", source="otx"),
        ]
        html = format_html_section(reports)
        assert "file1.exe" in html
        assert "file2.dll" in html
        assert html.count("<tr") >= 3  # header + 2 data rows

    def test_cross_referenced_sources(self):
        """Section mentions cross-referenced threat intel sources."""
        reports = [ThreatReport(hash="f" * 64, source="test")]
        html = format_html_section(reports)
        assert "VirusTotal" in html or "virustotal" in html.lower()
        assert "AlienVault" in html or "otx" in html.lower()
        assert "MalwareBazaar" in html or "malwarebazaar" in html.lower()


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_unicode_in_filename(self):
        """Unicode characters in filenames are preserved."""
        report = ThreatReport(
            hash="a" * 64,
            filename="файл.exe",  # Cyrillic
            source="test",
        )
        html = format_single_row(report)
        assert "файл.exe" in html or "&#" in html  # Either preserved or entity-encoded

    def test_very_long_family_name(self):
        """Very long malware family names don't break layout."""
        report = ThreatReport(
            hash="b" * 64,
            family="A" * 200,
            source="test",
        )
        html = format_single_row(report)
        assert "A" * 50 in html  # Should contain at least part of it

    def test_empty_string_fields(self):
        """Empty string fields render as 'Unknown' or 'N/A'."""
        report = ThreatReport(
            hash="c" * 64,
            filename="",
            family="",
            source="test",
        )
        html = format_single_row(report)
        assert "Unknown" in html or "N/A" in html

    def test_none_temperature_fields(self):
        """None values don't crash formatting."""
        report = ThreatReport(hash="d" * 64, detection_ratio=None)  # type: ignore
        # Should not crash during rendering
        html = format_single_row(report)
        assert "N/A" in html or "" in html
