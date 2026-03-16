"""Tests for ai.code_quality.formatter module."""

import json

import pytest

from ai.code_quality.formatter import format_results
from ai.code_quality.models import LintFinding, LintSummary, Severity


# ── Fixtures ──


@pytest.fixture()
def sample_finding() -> LintFinding:
    """A single warning-level finding."""
    return LintFinding(
        tool="ruff",
        file="src/main.py",
        line=42,
        column=10,
        code="E501",
        message="Line too long",
        severity=Severity.WARNING,
    )


@pytest.fixture()
def finding_with_fix() -> LintFinding:
    """A finding that includes a fix suggestion."""
    return LintFinding(
        tool="ruff",
        file="src/main.py",
        line=10,
        column=1,
        code="F401",
        message="Unused import",
        severity=Severity.ERROR,
        fix_suggestion="Remove the unused import statement",
    )


@pytest.fixture()
def empty_summary() -> LintSummary:
    """A summary with no findings."""
    return LintSummary(tool="ruff", exit_code=0, runtime_seconds=0.5)


@pytest.fixture()
def error_summary() -> LintSummary:
    """A summary where the tool itself failed."""
    return LintSummary(
        tool="bandit",
        exit_code=2,
        error_message="bandit: command not found",
    )


@pytest.fixture()
def populated_summary(sample_finding: LintFinding, finding_with_fix: LintFinding) -> LintSummary:
    """A summary with mixed findings."""
    info_finding = LintFinding(
        tool="ruff",
        file="src/util.py",
        line=5,
        column=0,
        code="D100",
        message="Missing docstring",
        severity=Severity.INFO,
    )
    return LintSummary(
        tool="ruff",
        findings=[sample_finding, finding_with_fix, info_finding],
        exit_code=1,
        runtime_seconds=1.2,
    )


# ── Text Format Tests ──


class TestTextFormat:
    def test_text_format_header(self, empty_summary: LintSummary) -> None:
        result = format_results([empty_summary], fmt="text")
        assert "CODE QUALITY REPORT" in result

    def test_text_format_no_findings(self, empty_summary: LintSummary) -> None:
        result = format_results([empty_summary], fmt="text")
        assert "No findings." in result

    def test_text_format_with_findings(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="text")
        assert "src/main.py:42:10" in result
        assert "E501" in result
        assert "Line too long" in result

    def test_text_format_with_fix_suggestion(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="text")
        assert "FIX: Remove the unused import statement" in result

    def test_text_format_totals(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="text")
        assert "TOTAL: 3 findings" in result
        assert "1 errors" in result
        assert "1 warnings" in result

    def test_text_format_error_message(self, error_summary: LintSummary) -> None:
        result = format_results([error_summary], fmt="text")
        assert "ERROR: bandit: command not found" in result


# ── JSON Format Tests ──


class TestJsonFormat:
    def test_json_format_valid(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="json")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_format_structure(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="json")
        parsed = json.loads(result)
        assert "summaries" in parsed
        assert "totals" in parsed

    def test_json_format_finding_fields(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="json")
        parsed = json.loads(result)
        finding = parsed["summaries"][0]["findings"][0]
        expected_keys = {"tool", "file", "line", "column", "code", "message", "severity", "fix_suggestion"}
        assert set(finding.keys()) == expected_keys

    def test_json_totals_correct(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="json")
        parsed = json.loads(result)
        totals = parsed["totals"]
        assert totals["findings"] == 3
        assert totals["errors"] == 1
        assert totals["warnings"] == 1
        assert totals["info"] == 1


# ── HTML Format Tests ──


class TestHtmlFormat:
    def test_html_format_contains_title(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="html")
        assert "Code Quality Report" in result

    def test_html_format_green_accent(self, populated_summary: LintSummary) -> None:
        result = format_results([populated_summary], fmt="html")
        assert "#16a34a" in result

    def test_html_escape_xss(self) -> None:
        malicious_finding = LintFinding(
            tool="ruff",
            file="<script>alert('xss')</script>",
            line=1,
            column=0,
            code="<img onerror=alert(1)>",
            message='<script>alert("xss")</script>',
            severity=Severity.WARNING,
        )
        summary = LintSummary(
            tool="ruff",
            findings=[malicious_finding],
            exit_code=1,
            runtime_seconds=0.1,
        )
        result = format_results([summary], fmt="html")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# ── Edge Case Tests ──


class TestEdgeCases:
    def test_format_results_default_text(self, empty_summary: LintSummary) -> None:
        result = format_results([empty_summary])
        assert "CODE QUALITY REPORT" in result

    def test_empty_summaries(self) -> None:
        result = format_results([], fmt="text")
        assert "CODE QUALITY REPORT" in result
        assert "TOTAL: 0 findings" in result
