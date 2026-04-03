"""Test coverage for ai/code_quality/models.py."""

from ai.code_quality.models import LintFinding, LintSummary, Severity


class TestSeverityEnum:
    """Test Severity enum."""

    def test_severity_values(self):
        """Severity enum has correct string values."""
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"


class TestLintFinding:
    """Test LintFinding dataclass."""

    def test_lint_finding_creation_minimal(self):
        """Create LintFinding with required fields only."""
        finding = LintFinding(
            tool="ruff",
            file="test.py",
            line=10,
            code="E501",
            message="Line too long",
        )

        assert finding.tool == "ruff"
        assert finding.file == "test.py"
        assert finding.line == 10
        assert finding.code == "E501"
        assert finding.message == "Line too long"
        assert finding.severity == Severity.WARNING  # default
        assert finding.column == 0  # default
        assert finding.end_line is None  # default
        assert finding.fix_suggestion == ""  # default

    def test_lint_finding_with_all_fields(self):
        """Create LintFinding with all optional fields."""
        finding = LintFinding(
            tool="bandit",
            file="app.py",
            line=50,
            code="B101",
            message="Use of assert detected",
            severity=Severity.ERROR,
            column=5,
            end_line=52,
            fix_suggestion="Replace assert with proper exception",
        )

        assert finding.severity == Severity.ERROR
        assert finding.column == 5
        assert finding.end_line == 52
        assert finding.fix_suggestion == "Replace assert with proper exception"

    def test_lint_finding_severity_types(self):
        """LintFinding accepts all severity levels."""
        for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO]:
            finding = LintFinding(
                tool="test",
                file="test.py",
                line=1,
                code="T001",
                message="test",
                severity=severity,
            )
            assert finding.severity == severity


class TestLintSummary:
    """Test LintSummary dataclass."""

    def test_lint_summary_creation_minimal(self):
        """Create LintSummary with required fields only."""
        summary = LintSummary(tool="ruff")

        assert summary.tool == "ruff"
        assert summary.findings == []  # default
        assert summary.exit_code == 0  # default
        assert summary.runtime_seconds == 0.0  # default
        assert summary.error_message == ""  # default

    def test_lint_summary_with_findings(self):
        """LintSummary with multiple findings."""
        findings = [
            LintFinding(
                tool="ruff",
                file="a.py",
                line=1,
                code="E001",
                message="error",
                severity=Severity.ERROR,
            ),
            LintFinding(
                tool="ruff",
                file="b.py",
                line=2,
                code="W001",
                message="warning",
                severity=Severity.WARNING,
            ),
            LintFinding(
                tool="ruff",
                file="c.py",
                line=3,
                code="I001",
                message="info",
                severity=Severity.INFO,
            ),
        ]

        summary = LintSummary(
            tool="ruff",
            findings=findings,
            exit_code=1,
            runtime_seconds=2.5,
            error_message="",
        )

        assert len(summary.findings) == 3
        assert summary.exit_code == 1
        assert summary.runtime_seconds == 2.5

    def test_error_count_property(self):
        """error_count returns only ERROR severity findings."""
        findings = [
            LintFinding(tool="test", file="a.py", line=1, code="E001",
                        message="e", severity=Severity.ERROR),
            LintFinding(tool="test", file="b.py", line=2, code="E002",
                        message="e", severity=Severity.ERROR),
            LintFinding(tool="test", file="c.py", line=3, code="W001",
                        message="w", severity=Severity.WARNING),
            LintFinding(tool="test", file="d.py", line=4, code="I001",
                        message="i", severity=Severity.INFO),
        ]

        summary = LintSummary(tool="test", findings=findings)

        assert summary.error_count == 2

    def test_warning_count_property(self):
        """warning_count returns only WARNING severity findings."""
        findings = [
            LintFinding(tool="test", file="a.py", line=1, code="E001",
                        message="e", severity=Severity.ERROR),
            LintFinding(tool="test", file="b.py", line=2, code="W001",
                        message="w", severity=Severity.WARNING),
            LintFinding(tool="test", file="c.py", line=3, code="W002",
                        message="w", severity=Severity.WARNING),
            LintFinding(tool="test", file="d.py", line=4, code="W003",
                        message="w", severity=Severity.WARNING),
        ]

        summary = LintSummary(tool="test", findings=findings)

        assert summary.warning_count == 3

    def test_info_count_property(self):
        """info_count returns only INFO severity findings."""
        findings = [
            LintFinding(tool="test", file="a.py", line=1, code="I001",
                        message="i", severity=Severity.INFO),
            LintFinding(tool="test", file="b.py", line=2, code="W001",
                        message="w", severity=Severity.WARNING),
        ]

        summary = LintSummary(tool="test", findings=findings)

        assert summary.info_count == 1

    def test_total_count_property(self):
        """total_count returns all findings regardless of severity."""
        findings = [
            LintFinding(
                tool="test", file=f"{i}.py", line=i, code=f"X{i:03d}",
                message="x", severity=Severity.ERROR,
            )
            for i in range(10)
        ]

        summary = LintSummary(tool="test", findings=findings)

        assert summary.total_count == 10

    def test_empty_summary_counts(self):
        """Empty summary returns 0 for all count properties."""
        summary = LintSummary(tool="test")

        assert summary.error_count == 0
        assert summary.warning_count == 0
        assert summary.info_count == 0
        assert summary.total_count == 0

    def test_summary_with_error_message(self):
        """LintSummary can store tool execution errors."""
        summary = LintSummary(
            tool="broken-tool",
            exit_code=127,
            error_message="Command not found",
        )

        assert summary.exit_code == 127
        assert summary.error_message == "Command not found"
        assert summary.total_count == 0  # No findings on error
