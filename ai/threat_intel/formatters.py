"""HTML email generator for threat intelligence reports.

Generates an HTML section for injection into ClamAV alert emails.
Uses inline CSS only (email clients strip <style> blocks).
Blue accent (#3b82f6) distinguishes from ClamAV's red (#ef4444).

All dynamic content is HTML-escaped via html.escape() for XSS protection.
"""

import html

from ai.threat_intel.models import ThreatReport

RISK_COLORS: dict[str, dict[str, str]] = {
    "high": {"text": "#dc2626", "bg": "#fef2f2"},
    "medium": {"text": "#d97706", "bg": "#fffbeb"},
    "low": {"text": "#ca8a04", "bg": "#fefce8"},
    "clean": {"text": "#16a34a", "bg": "#f0fdf4"},
    "unknown": {"text": "#6b7280", "bg": "#f3f4f6"},
}

# Matches clamav-alert.sh header row style
_HEADER_STYLE = (
    "padding:10px 12px;font-size:12px;color:#f8fafc;text-align:left;"
    "text-transform:uppercase;letter-spacing:0.5px"
)

# Matches clamav-alert.sh cell style
_CELL_STYLE = "padding:10px 12px;font-size:13px;color:#1e293b"


def format_html_section(reports: list[ThreatReport]) -> str:
    """Generate complete HTML section for email injection.

    Returns empty string if no reports have data (email looks unchanged).
    Otherwise returns a <div> with blue left border containing a threat intel table.
    """
    if not any(r.has_data for r in reports):
        return ""

    rows = "".join(format_single_row(r) for r in reports)

    return (
        '<div style="margin:24px 0;padding:0 0 0 16px;border-left:4px solid #3b82f6">'
        '<h3 style="font-size:16px;color:#3b82f6;margin:0 0 8px 0">'
        "&#x1F50D; Threat Intelligence</h3>"
        '<p style="font-size:13px;color:#64748b;margin:0 0 16px 0">'
        "Cross-referenced with VirusTotal, OTX AlienVault, and MalwareBazaar</p>"
        '<table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0">'
        f'<tr style="background:#1e3a5f">'
        f'<th style="{_HEADER_STYLE}">File</th>'
        f'<th style="{_HEADER_STYLE}">Detection</th>'
        f'<th style="{_HEADER_STYLE}">Family</th>'
        f'<th style="{_HEADER_STYLE}">Risk</th>'
        f'<th style="{_HEADER_STYLE}">Source</th>'
        "</tr>"
        f"{rows}"
        "</table>"
        "</div>"
    )


def format_single_row(report: ThreatReport) -> str:
    """Generate one HTML table row for a single hash report."""
    # File column: filename or truncated hash
    if report.filename:
        file_display = html.escape(report.filename)
    elif len(report.hash) > 12:
        file_display = html.escape(report.hash[:12]) + "..."
    else:
        file_display = html.escape(report.hash)

    # Detection column
    if report.has_data and report.detection_ratio:
        detection = html.escape(report.detection_ratio)
        # Bold red if detection ratio > 50%
        parts = report.detection_ratio.split("/")
        try:
            ratio = int(parts[0]) / int(parts[1]) if len(parts) == 2 and int(parts[1]) > 0 else 0
        except (ValueError, ZeroDivisionError):
            ratio = 0
        if ratio > 0.5:
            detection_style = f"{_CELL_STYLE};font-weight:700;color:#ef4444"
        else:
            detection_style = f"{_CELL_STYLE};font-weight:700"
    else:
        detection = "N/A"
        detection_style = f"{_CELL_STYLE};color:#64748b"

    # Family column
    family = html.escape(report.family) if report.family else "Unknown"

    # Risk badge
    risk = report.risk_level if report.has_data else "unknown"
    colors = RISK_COLORS.get(risk, RISK_COLORS["unknown"])
    risk_badge = (
        f'<span style="background:{colors["bg"]};color:{colors["text"]};'
        f'padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">'
        f"{html.escape(risk.upper())}</span>"
    )

    # Source column (validate URL scheme to prevent javascript: XSS)
    if report.has_data and report.vt_link and report.vt_link.startswith("https://"):
        source_display = (
            f'<a href="{html.escape(report.vt_link)}" '
            f'style="color:#3b82f6;text-decoration:none">'
            f"{html.escape(report.source)}</a>"
        )
    elif report.has_data:
        source_display = html.escape(report.source)
    else:
        source_display = "No data"

    return (
        f'<tr style="border-bottom:1px solid #e2e8f0">'
        f'<td style="{_CELL_STYLE};font-family:\'Courier New\',monospace">{file_display}</td>'
        f'<td style="{detection_style}">{detection}</td>'
        f'<td style="{_CELL_STYLE}">{family}</td>'
        f'<td style="{_CELL_STYLE}">{risk_badge}</td>'
        f'<td style="{_CELL_STYLE}">{source_display}</td>'
        "</tr>"
    )
