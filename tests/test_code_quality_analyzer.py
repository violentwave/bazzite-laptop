"""Unit tests for ai/code_quality/analyzer.py."""

from unittest.mock import MagicMock, patch

import pytest

from ai.code_quality.analyzer import (
    _build_fix_prompt,
    _read_source_context,
    analyze_findings,
)
from ai.code_quality.models import LintFinding, LintSummary, Severity


def _make_finding(
    severity: Severity = Severity.ERROR,
    tool: str = "ruff",
    file: str = "/tmp/test.py",
    line: int = 10,
    code: str = "E501",
    message: str = "Line too long",
) -> LintFinding:
    """Helper to build a LintFinding with sensible defaults."""
    return LintFinding(
        tool=tool, file=file, line=line, code=code,
        message=message, severity=severity,
    )


def _make_summary(findings: list[LintFinding] | None = None, tool: str = "ruff") -> LintSummary:
    """Helper to build a LintSummary."""
    return LintSummary(tool=tool, findings=findings or [])


@patch("ai.code_quality.analyzer.RateLimiter")
@patch("ai.code_quality.analyzer.route_query")
class TestAnalyzeFindings:
    """Tests for analyze_findings (router and rate limiter always mocked)."""

    def test_analyze_no_findings(self, mock_route, mock_rl):
        """Empty summaries returns unchanged."""
        summaries = [_make_summary()]
        result = analyze_findings(summaries, rate_limiter=MagicMock())
        assert result is summaries
        mock_route.assert_not_called()

    def test_analyze_skips_info_severity(self, mock_route, mock_rl):
        """INFO findings do not get fix suggestions."""
        finding = _make_finding(severity=Severity.INFO)
        summaries = [_make_summary([finding])]
        result = analyze_findings(summaries, rate_limiter=MagicMock())
        assert result[0].findings[0].fix_suggestion == ""
        mock_route.assert_not_called()

    @patch("ai.code_quality.analyzer.Path")
    def test_analyze_enriches_error_findings(self, mock_path, mock_route, mock_rl):
        """ERROR finding gets fix_suggestion set from router response."""
        mock_route.return_value = "fixed_code()"
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = "line1\nline2\nbad_code()\nline4"

        finding = _make_finding(severity=Severity.ERROR, line=3)
        summaries = [_make_summary([finding])]
        analyze_findings(summaries, rate_limiter=MagicMock())

        assert finding.fix_suggestion == "fixed_code()"
        mock_route.assert_called_once()
        assert mock_route.call_args[0][0] == "fast"

    @patch("ai.code_quality.analyzer.Path")
    def test_analyze_enriches_warning_findings(self, mock_path, mock_route, mock_rl):
        """WARNING finding gets fix_suggestion set from router response."""
        mock_route.return_value = "fixed_warning()"
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = "code_here"

        finding = _make_finding(severity=Severity.WARNING, line=1)
        summaries = [_make_summary([finding])]
        analyze_findings(summaries, rate_limiter=MagicMock())

        assert finding.fix_suggestion == "fixed_warning()"

    @patch("ai.code_quality.analyzer.Path")
    def test_max_suggestions_limit(self, mock_path, mock_route, mock_rl):
        """With 15 fixable findings and max=5, only 5 get suggestions."""
        mock_route.return_value = "fix"
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = "source"

        findings = [_make_finding(line=i) for i in range(15)]
        summaries = [_make_summary(findings)]
        analyze_findings(summaries, rate_limiter=MagicMock(), max_suggestions=5)

        assert mock_route.call_count == 5
        enriched = [f for f in findings if f.fix_suggestion != ""]
        assert len(enriched) == 5

    @patch("ai.code_quality.analyzer.Path")
    def test_errors_prioritized_over_warnings(self, mock_path, mock_route, mock_rl):
        """Errors are processed before warnings when limited."""
        call_order: list[str] = []

        def track_route(tier, prompt):
            # Extract severity from the prompt text
            if "error" in prompt:
                call_order.append("error")
            elif "warning" in prompt:
                call_order.append("warning")
            return "fix"

        mock_route.side_effect = track_route
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = "source"

        warnings = [_make_finding(severity=Severity.WARNING, line=i) for i in range(3)]
        errors = [_make_finding(severity=Severity.ERROR, line=i) for i in range(3)]
        # Put warnings first in the list to verify sorting
        summaries = [_make_summary(warnings + errors)]
        analyze_findings(summaries, rate_limiter=MagicMock(), max_suggestions=6)

        # All errors should come before all warnings
        assert call_order == ["error", "error", "error", "warning", "warning", "warning"]

    @patch("ai.code_quality.analyzer.Path")
    def test_scaffold_response_returns_empty(self, mock_path, mock_route, mock_rl):
        """Router returning '[SCAFFOLD]...' results in empty fix_suggestion."""
        mock_route.return_value = "[SCAFFOLD] Would route 'fast' query to LiteLLM."
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = "source"

        finding = _make_finding()
        summaries = [_make_summary([finding])]
        analyze_findings(summaries, rate_limiter=MagicMock())

        assert finding.fix_suggestion == ""

    @patch("ai.code_quality.analyzer.Path")
    def test_router_exception_graceful(self, mock_path, mock_route, mock_rl):
        """Router raising RuntimeError does not crash; fix_suggestion stays empty."""
        mock_route.side_effect = RuntimeError("provider down")
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = "source"

        finding = _make_finding()
        summaries = [_make_summary([finding])]
        # Should not raise
        result = analyze_findings(summaries, rate_limiter=MagicMock())

        assert finding.fix_suggestion == ""
        assert result is summaries


class TestReadSourceContext:
    """Tests for _read_source_context (file system mocked)."""

    @patch("ai.code_quality.analyzer.Path")
    def test_source_context_read(self, mock_path_cls):
        """Reads source and returns numbered lines around the target."""
        source = "\n".join(f"line {i}" for i in range(1, 21))
        mock_path_inst = MagicMock()
        mock_path_cls.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = True
        mock_path_inst.read_text.return_value = source

        result = _read_source_context("/tmp/example.py", 10)

        # Should contain numbered lines around line 10
        assert "  10 |" in result
        # Context should include lines before and after
        assert "   5 |" in result
        assert "  14 |" in result

    @patch("ai.code_quality.analyzer.Path")
    def test_file_not_found_graceful(self, mock_path_cls):
        """Nonexistent file returns empty string without crashing."""
        mock_path_inst = MagicMock()
        mock_path_cls.return_value = mock_path_inst
        mock_path_inst.is_file.return_value = False

        result = _read_source_context("/nonexistent/file.py", 5)
        assert result == ""


class TestBuildFixPrompt:
    """Tests for _build_fix_prompt."""

    def test_build_fix_prompt_structure(self):
        """Prompt contains tool, rule, message, file, and severity."""
        finding = _make_finding(
            tool="bandit",
            code="B101",
            message="Use of assert detected",
            file="/src/app.py",
            line=42,
            severity=Severity.WARNING,
        )
        prompt = _build_fix_prompt(finding, "  42 | assert x > 0")

        assert "Tool: bandit" in prompt
        assert "Rule: B101" in prompt
        assert "Message: Use of assert detected" in prompt
        assert "File: /src/app.py:42" in prompt
        assert "Severity: warning" in prompt
        assert "42 | assert x > 0" in prompt
