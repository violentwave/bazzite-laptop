"""Output formatters for code quality results.

Supports text (terminal), JSON, and HTML output formats.
"""

import json
import logging
from io import StringIO

from ai.code_quality.models import LintFinding, LintSummary
from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)


def format_results(summaries: list[LintSummary], fmt: str = "text") -> str:
    """Format lint results for display.

    Args:
        summaries: List of LintSummary from runner/analyzer.
        fmt: Output format — "text", "json", or "html".

    Returns:
        Formatted string.
    """
    if fmt == "json":
        return _format_json(summaries)
    if fmt == "html":
        return _format_html(summaries)
    return _format_text(summaries)


def _format_text(summaries: list[LintSummary]) -> str:
    """Plain text format for terminal output."""
    buf = StringIO()
    total_findings = sum(s.total_count for s in summaries)
    total_errors = sum(s.error_count for s in summaries)
    total_warnings = sum(s.warning_count for s in summaries)

    buf.write("=" * 60 + "\n")
    buf.write("CODE QUALITY REPORT\n")
    buf.write("=" * 60 + "\n\n")

    for summary in summaries:
        _write_tool_section(buf, summary)

    buf.write("-" * 60 + "\n")
    buf.write(f"TOTAL: {total_findings} findings ")
    buf.write(f"({total_errors} errors, {total_warnings} warnings)\n")

    return buf.getvalue()


def _write_tool_section(buf: StringIO, summary: LintSummary) -> None:
    """Write a single tool's section to the buffer."""
    buf.write(f"--- {summary.tool.upper()} ---\n")

    if summary.error_message:
        buf.write(f"  ERROR: {summary.error_message}\n\n")
        return

    if not summary.findings:
        buf.write("  No findings.\n\n")
        return

    buf.write(f"  {summary.total_count} findings ")
    buf.write(f"({summary.error_count}E / {summary.warning_count}W / {summary.info_count}I)")
    buf.write(f"  [{summary.runtime_seconds:.1f}s]\n\n")

    for finding in summary.findings:
        _write_finding(buf, finding)

    buf.write("\n")


def _write_finding(buf: StringIO, finding: LintFinding) -> None:
    """Write a single finding line."""
    sev_char = {"error": "E", "warning": "W", "info": "I"}.get(finding.severity.value, "?")
    buf.write(f"  [{sev_char}] {finding.file}:{finding.line}:{finding.column} ")
    buf.write(f"{finding.code}: {finding.message}\n")
    if finding.fix_suggestion:
        for line in finding.fix_suggestion.splitlines():
            buf.write(f"      FIX: {line}\n")


def _format_json(summaries: list[LintSummary]) -> str:
    """JSON format for programmatic consumption."""
    data = {
        "summaries": [_summary_to_dict(s) for s in summaries],
        "totals": {
            "findings": sum(s.total_count for s in summaries),
            "errors": sum(s.error_count for s in summaries),
            "warnings": sum(s.warning_count for s in summaries),
            "info": sum(s.info_count for s in summaries),
        },
    }
    return json.dumps(data, indent=2)


def _summary_to_dict(summary: LintSummary) -> dict:
    """Convert a LintSummary to a JSON-serializable dict."""
    return {
        "tool": summary.tool,
        "exit_code": summary.exit_code,
        "runtime_seconds": summary.runtime_seconds,
        "error_message": summary.error_message,
        "findings": [_finding_to_dict(f) for f in summary.findings],
        "counts": {
            "total": summary.total_count,
            "errors": summary.error_count,
            "warnings": summary.warning_count,
            "info": summary.info_count,
        },
    }


def _finding_to_dict(finding: LintFinding) -> dict:
    """Convert a LintFinding to a JSON-serializable dict."""
    return {
        "tool": finding.tool,
        "file": finding.file,
        "line": finding.line,
        "column": finding.column,
        "code": finding.code,
        "message": finding.message,
        "severity": finding.severity.value,
        "fix_suggestion": finding.fix_suggestion,
    }


def _format_html(summaries: list[LintSummary]) -> str:
    """Minimal HTML report with green (#16a34a) accent."""
    total = sum(s.total_count for s in summaries)
    errors = sum(s.error_count for s in summaries)

    buf = StringIO()
    buf.write("<!DOCTYPE html>\n<html><head>\n")
    buf.write("<meta charset='utf-8'>\n")
    buf.write("<title>Code Quality Report</title>\n")
    buf.write("<style>\n")
    buf.write(
        "body { font-family: monospace; margin: 2em;"
        " background: #0d1117; color: #c9d1d9; }\n"
    )
    buf.write("h1 { color: #16a34a; }\n")
    buf.write("h2 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 4px; }\n")
    buf.write(".error { color: #f85149; }\n")
    buf.write(".warning { color: #d29922; }\n")
    buf.write(".info { color: #8b949e; }\n")
    buf.write(".fix { color: #16a34a; margin-left: 2em; }\n")
    buf.write("table { border-collapse: collapse; width: 100%; margin: 1em 0; }\n")
    buf.write("th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid #30363d; }\n")
    buf.write("th { color: #16a34a; }\n")
    buf.write(".summary { font-size: 1.2em; margin: 1em 0; }\n")
    buf.write("</style>\n</head><body>\n")
    buf.write("<h1>Code Quality Report</h1>\n")
    buf.write(f"<p class='summary'>Total: {total} findings ({errors} errors)</p>\n")

    for summary in summaries:
        _write_html_tool(buf, summary)

    buf.write("</body></html>")
    return buf.getvalue()


def _write_html_tool(buf: StringIO, summary: LintSummary) -> None:
    """Write a single tool section in HTML."""
    buf.write(f"<h2>{summary.tool.upper()}</h2>\n")

    if summary.error_message:
        buf.write(f"<p class='error'>Error: {_html_escape(summary.error_message)}</p>\n")
        return

    if not summary.findings:
        buf.write("<p>No findings.</p>\n")
        return

    buf.write("<table>\n<tr><th>Sev</th><th>Location</th><th>Code</th><th>Message</th></tr>\n")
    for f in summary.findings:
        sev_class = f.severity.value
        buf.write(f"<tr class='{sev_class}'>")
        buf.write(f"<td>{f.severity.value.upper()}</td>")
        buf.write(f"<td>{_html_escape(f.file)}:{f.line}</td>")
        buf.write(f"<td>{_html_escape(f.code)}</td>")
        buf.write(f"<td>{_html_escape(f.message)}</td>")
        buf.write("</tr>\n")
        if f.fix_suggestion:
            buf.write(
                f"<tr><td colspan='4' class='fix'>"
                f"FIX: {_html_escape(f.fix_suggestion)}</td></tr>\n"
            )
    buf.write("</table>\n")


def _html_escape(text: str) -> str:
    """Basic HTML escaping for XSS prevention."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
