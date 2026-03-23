"""Unit tests for ai/code_quality/runner.py, analyzer.py, formatter.py.

Tests parallel linter execution, result parsing, and AI-assisted fixes.
"""

import json
from unittest.mock import Mock, patch

from ai.code_quality.models import LintFinding, LintSummary, Severity


class TestLinterRunner:
    """Tests for ai/code_quality/runner.py parallel execution."""

    @patch("ai.code_quality.runner._run_ruff")
    @patch("ai.code_quality.runner._run_bandit")
    @patch("ai.code_quality.runner._run_shellcheck")
    def test_run_all_parallel_execution(self, mock_shell, mock_bandit, mock_ruff):
        """All linters run in parallel."""
        from ai.code_quality.runner import run_all

        # Mock each linter to return a summary
        mock_ruff.return_value = LintSummary(tool="ruff")
        mock_bandit.return_value = LintSummary(tool="bandit")
        mock_shell.return_value = LintSummary(tool="shellcheck")

        results = run_all()

        assert len(results) == 3
        assert {r.tool for r in results} == {"ruff", "bandit", "shellcheck"}

        # All three should have been called
        mock_ruff.assert_called_once()
        mock_bandit.assert_called_once()
        mock_shell.assert_called_once()

    @patch("ai.code_quality.runner._run_tool")
    def test_run_ruff_parses_json_output(self, mock_run_tool):
        """_run_ruff parses ruff JSON output correctly."""
        from ai.code_quality.runner import _run_ruff

        ruff_output = json.dumps([
            {
                "type": "E",
                "filename": "ai/test.py",
                "location": {"row": 10, "column": 5},
                "code": "E501",
                "message": "Line too long",
            },
        ])
        mock_run_tool.return_value = (ruff_output, "", 0, 0.5)

        summary = _run_ruff(["ai/"], timeout=120)

        assert summary.tool == "ruff"
        assert summary.total_count == 1
        assert summary.findings[0].file == "ai/test.py"
        assert summary.findings[0].line == 10
        assert summary.findings[0].code == "E501"
        assert summary.findings[0].severity == Severity.ERROR

    @patch("ai.code_quality.runner._run_tool")
    def test_run_bandit_parses_json_output(self, mock_run_tool):
        """_run_bandit parses bandit JSON output correctly."""
        from ai.code_quality.runner import _run_bandit

        bandit_output = json.dumps({
            "results": [
                {
                    "filename": "ai/test.py",
                    "line_number": 42,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "test_id": "B201",
                    "issue_text": "Use of unsafe function eval()",
                },
            ],
        })
        mock_run_tool.return_value = (bandit_output, "", 0, 1.2)

        summary = _run_bandit(["ai/"], timeout=120)

        assert summary.tool == "bandit"
        assert summary.total_count == 1
        assert summary.findings[0].code == "B201"
        assert summary.findings[0].severity == Severity.ERROR
        assert "eval()" in summary.findings[0].message

    @patch("ai.code_quality.runner._run_tool")
    def test_run_shellcheck_parses_json_output(self, mock_run_tool):
        """_run_shellcheck parses shellcheck JSON output correctly."""
        from ai.code_quality.runner import _run_shellcheck

        shellcheck_output = json.dumps([
            {
                "file": "scripts/test.sh",
                "line": 15,
                "column": 10,
                "level": "error",
                "code": 2086,
                "message": "Quote variable to prevent word splitting",
            },
        ])
        mock_run_tool.return_value = (shellcheck_output, "", 0, 0.8)

        summary = _run_shellcheck(["scripts/"], timeout=120)

        assert summary.tool == "shellcheck"
        assert summary.total_count == 1
        assert summary.findings[0].code == "SC2086"
        assert summary.findings[0].severity == Severity.ERROR

    @patch("ai.code_quality.runner._run_tool")
    def test_tool_not_found_handled(self, mock_run_tool):
        """Missing linter tool is handled gracefully."""
        from ai.code_quality.runner import _run_ruff

        mock_run_tool.return_value = ("", "Command not found: ruff", 127, 0.1)

        summary = _run_ruff(["ai/"], timeout=120)

        assert summary.error_message is not None
        assert "Command not found" in summary.error_message
        assert summary.total_count == 0

    @patch("ai.code_quality.runner._run_tool")
    def test_timeout_handled(self, mock_run_tool):
        """Linter timeout is handled gracefully."""
        from ai.code_quality.runner import _run_bandit

        mock_run_tool.return_value = ("", "Timeout after 120s", 124, 120.0)

        summary = _run_bandit(["ai/"], timeout=120)

        assert summary.error_message is not None
        assert "Timeout" in summary.error_message

    @patch("ai.code_quality.runner._run_ruff")
    def test_linter_exception_handled(self, mock_ruff):
        """Linter exceptions are captured in summary."""
        from ai.code_quality.runner import run_all

        mock_ruff.side_effect = RuntimeError("Unexpected linter crash")

        results = run_all()

        # Should return 3 summaries, ruff with error
        ruff_summary = next(r for r in results if r.tool == "ruff")
        assert ruff_summary.error_message is not None
        assert "Unexpected linter crash" in ruff_summary.error_message


class TestLintAnalyzer:
    """Tests for ai/code_quality/analyzer.py AI-assisted analysis."""

    @patch("ai.code_quality.analyzer.route_query")
    def test_analyze_findings_with_llm(self, mock_router):
        """Analyzer sends findings to LLM for fix suggestions."""
        from ai.code_quality.analyzer import analyze_findings

        finding = LintFinding(
            tool="ruff",
            file="ai/test.py",
            line=10,
            code="E501",
            message="Line too long",
            severity=Severity.ERROR,
        )
        summaries = [LintSummary(tool="ruff", findings=[finding])]

        mock_router.return_value = "This line exceeds PEP 8's 88-char limit. Consider breaking it."

        result = analyze_findings(summaries)

        # Verify router was called with "fast" task type
        mock_router.assert_called_once()
        call_args = mock_router.call_args[0]
        assert call_args[0] == "fast"
        assert "E501" in call_args[1]

        # Verify result is list of summaries with fix populated
        assert isinstance(result, list)
        assert result[0].findings[0].fix_suggestion != ""

    @patch("ai.code_quality.analyzer.route_query")
    def test_analyze_empty_findings(self, mock_router):
        """Analyzer handles empty summaries list."""
        from ai.code_quality.analyzer import analyze_findings

        result = analyze_findings([])

        # Should not call router for empty list
        mock_router.assert_not_called()
        assert isinstance(result, list)
        assert result == []

    @patch("ai.code_quality.analyzer.route_query")
    def test_analyze_findings_router_error(self, mock_router):
        """Analyzer handles router errors gracefully."""
        from ai.code_quality.analyzer import analyze_findings

        finding = LintFinding(
            tool="bandit",
            file="ai/test.py",
            line=5,
            code="B201",
            message="Use of eval",
            severity=Severity.ERROR,
        )
        summaries = [LintSummary(tool="bandit", findings=[finding])]

        mock_router.side_effect = RuntimeError("LLM unavailable")

        result = analyze_findings(summaries)

        # Should return summaries (router error is caught internally)
        assert isinstance(result, list)


class TestLintFormatter:
    """Tests for ai/code_quality/analyzer.py AI-assisted fix generation."""

    @patch("ai.code_quality.analyzer.route_query")
    def test_generate_fix_for_finding(self, mock_router):
        """Analyzer generates AI fix suggestions for a single finding."""
        from ai.code_quality.analyzer import _generate_fix

        finding = LintFinding(
            tool="ruff",
            file="ai/test.py",
            line=10,
            code="E501",
            message="Line too long (95 > 88)",
            severity=Severity.ERROR,
        )

        mock_router.return_value = (
            "Split the line at logical break points:\n"
            "result = function(\n    arg1, arg2\n)"
        )

        from ai.rate_limiter import RateLimiter
        fix = _generate_fix(finding, RateLimiter())

        assert "Split the line" in fix or "arg1, arg2" in fix
        mock_router.assert_called_once()

    @patch("ai.code_quality.analyzer.route_query")
    def test_generate_fix_for_security_issue(self, mock_router):
        """Analyzer suggests secure alternatives."""
        from ai.code_quality.analyzer import _generate_fix

        finding = LintFinding(
            tool="bandit",
            file="ai/test.py",
            line=42,
            code="B201",
            message="Use of eval() detected",
            severity=Severity.ERROR,
        )

        mock_router.return_value = "Replace eval() with ast.literal_eval() for safe evaluation."

        from ai.rate_limiter import RateLimiter
        fix = _generate_fix(finding, RateLimiter())

        assert "ast.literal_eval" in fix or "safe" in fix

    @patch("ai.code_quality.analyzer.route_query")
    def test_batch_fix_generation(self, mock_router):
        """Analyzer can batch-process multiple findings via analyze_findings."""
        from ai.code_quality.analyzer import analyze_findings

        findings = [
            LintFinding(tool="ruff", file="a.py", line=1, code="E501",
                        message="Line too long", severity=Severity.ERROR),
            LintFinding(tool="ruff", file="b.py", line=2, code="E501",
                        message="Line too long", severity=Severity.ERROR),
        ]
        summaries = [LintSummary(tool="ruff", findings=findings)]

        mock_router.return_value = "Fix suggestion for all findings."

        result = analyze_findings(summaries)

        # Should return summaries with fix suggestions populated
        assert len(result) == 1
        fixed_findings = result[0].findings
        assert len(fixed_findings) == 2


class TestIntegrationScenarios:
    """Integration tests for complete code quality workflows."""

    @patch("subprocess.run")
    def test_full_lint_analyze_fix_pipeline(self, mock_subprocess):
        """Full pipeline: lint → analyze → suggest fixes."""
        from ai.code_quality.analyzer import analyze_findings
        from ai.code_quality.runner import run_all

        # Mock subprocess to return ruff findings
        ruff_output = json.dumps([
            {
                "type": "E",
                "filename": "ai/test.py",
                "location": {"row": 10, "column": 1},
                "code": "E501",
                "message": "Line too long",
            },
        ])

        mock_subprocess.return_value = Mock(
            stdout=ruff_output,
            stderr="",
            returncode=0,
        )

        with patch("ai.code_quality.analyzer.route_query") as mock_analyze:

            mock_analyze.return_value = "Analysis of issues"

            # Run linters
            summaries = run_all(python_targets=["ai/"], shell_targets=[])

            # Analyze findings (takes summaries, returns summaries)
            analyzed = analyze_findings(summaries)

            # Verify pipeline executed
            assert len(summaries) == 3  # ruff, bandit, shellcheck
            assert isinstance(analyzed, list)
            assert len(analyzed) == len(summaries)


class TestEdgeCases:
    """Edge case tests for code quality tools."""

    @patch("ai.code_quality.runner._run_tool")
    def test_malformed_json_output(self, mock_run_tool):
        """Malformed JSON from linter is handled."""
        from ai.code_quality.runner import _run_ruff

        mock_run_tool.return_value = ("not valid json{", "", 0, 0.5)

        summary = _run_ruff(["ai/"], timeout=120)

        # Should not crash, should report error
        assert summary.error_message is not None or summary.total_findings == 0

    def test_severity_mapping_all_levels(self):
        """Severity enum covers all linter levels."""
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"
        # All three distinct levels exist
        assert len({Severity.ERROR, Severity.WARNING, Severity.INFO}) == 3

    @patch("ai.code_quality.runner._run_tool")
    def test_empty_targets_handled(self, mock_run_tool):
        """Empty target directories are handled."""
        from ai.code_quality.runner import run_all

        results = run_all(python_targets=[], shell_targets=[])

        # Should still run all 3 linters (with default targets or gracefully skip)
        assert len(results) == 3
