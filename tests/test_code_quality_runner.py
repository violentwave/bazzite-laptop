"""Tests for ai.code_quality.runner — all subprocess calls are mocked."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from ai.code_quality.models import LintSummary, Severity
from ai.code_quality.runner import (
    _run_bandit,
    _run_ruff,
    _run_shellcheck,
    run_all,
)

# ── Sample JSON payloads ──

RUFF_JSON = json.dumps([
    {
        "code": "F401",
        "message": "os imported but unused",
        "filename": "ai/config.py",
        "type": "F",
        "location": {"row": 3, "column": 1},
        "end_location": {"row": 3, "column": 10},
    },
    {
        "code": "E501",
        "message": "Line too long",
        "filename": "ai/router.py",
        "type": "E",
        "location": {"row": 42, "column": 89},
        "end_location": {"row": 42, "column": 130},
    },
])

BANDIT_JSON = json.dumps({
    "results": [
        {
            "test_id": "B101",
            "issue_text": "Use of assert detected.",
            "issue_severity": "LOW",
            "filename": "tests/test_config.py",
            "line_number": 10,
        },
        {
            "test_id": "B608",
            "issue_text": "Possible SQL injection.",
            "issue_severity": "HIGH",
            "filename": "ai/router.py",
            "line_number": 55,
        },
        {
            "test_id": "B105",
            "issue_text": "Possible hardcoded password.",
            "issue_severity": "MEDIUM",
            "filename": "ai/config.py",
            "line_number": 20,
        },
    ],
})

SHELLCHECK_JSON = json.dumps([
    {
        "file": "scripts/backup.sh",
        "line": 12,
        "endLine": 12,
        "column": 5,
        "code": 2086,
        "level": "warning",
        "message": "Double quote to prevent globbing.",
    },
    {
        "file": "scripts/deploy.sh",
        "line": 30,
        "endLine": 31,
        "column": 1,
        "code": 2034,
        "level": "error",
        "message": "Variable unused.",
    },
    {
        "file": "scripts/deploy.sh",
        "line": 45,
        "endLine": 45,
        "column": 10,
        "code": 1091,
        "level": "info",
        "message": "Not following sourced file.",
    },
])


# ── Helpers ──

def _make_proc(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock CompletedProcess."""
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


# ── Tests ──


class TestRunAll:
    """Tests for run_all orchestration."""

    @patch("ai.code_quality.runner._run_tool")
    def test_run_all_returns_three_summaries(self, mock_run_tool):
        """run_all returns exactly 3 LintSummary objects sorted by tool name."""
        mock_run_tool.return_value = ("", "", 0, 0.1)

        results = run_all(
            python_targets=["/fake/py"],
            shell_targets=["/fake/sh"],
        )

        assert len(results) == 3
        assert all(isinstance(r, LintSummary) for r in results)
        tools = [r.tool for r in results]
        assert tools == sorted(tools), "Results must be sorted by tool name"
        assert tools == ["bandit", "ruff", "shellcheck"]

    @patch("ai.code_quality.runner._run_tool")
    def test_run_all_tool_exception(self, mock_run_tool):
        """If one tool raises an exception, others still complete."""

        def side_effect(cmd, timeout):
            if cmd[0] == "ruff":
                raise RuntimeError("ruff crashed")
            return ("", "", 0, 0.05)

        mock_run_tool.side_effect = side_effect

        results = run_all(
            python_targets=["/fake/py"],
            shell_targets=["/fake/sh"],
        )

        assert len(results) == 3
        ruff_result = next(r for r in results if r.tool == "ruff")
        assert ruff_result.error_message == "ruff crashed"
        assert ruff_result.findings == []

        other_results = [r for r in results if r.tool != "ruff"]
        for r in other_results:
            assert r.error_message == ""


class TestRuffParsing:
    """Tests for _run_ruff JSON parsing."""

    @patch("ai.code_quality.runner._run_tool")
    def test_ruff_json_parsing(self, mock_run_tool):
        """Ruff JSON output is parsed into correct LintFinding fields."""
        mock_run_tool.return_value = (RUFF_JSON, "", 1, 0.5)

        summary = _run_ruff(["/fake/dir"], timeout=60)

        assert summary.tool == "ruff"
        assert summary.exit_code == 1
        assert len(summary.findings) == 2

        f0 = summary.findings[0]
        assert f0.tool == "ruff"
        assert f0.file == "ai/config.py"
        assert f0.line == 3
        assert f0.column == 1
        assert f0.code == "F401"
        assert f0.message == "os imported but unused"
        assert f0.severity == Severity.WARNING
        assert f0.end_line == 3

        f1 = summary.findings[1]
        assert f1.severity == Severity.ERROR  # type "E" maps to ERROR
        assert f1.code == "E501"

    @patch("ai.code_quality.runner._run_tool")
    def test_ruff_exit_code_1_no_error_message(self, mock_run_tool):
        """Ruff rc=1 (findings exist) should produce empty error_message."""
        mock_run_tool.return_value = (RUFF_JSON, "some stderr", 1, 0.3)

        summary = _run_ruff(["/fake"], timeout=60)

        assert summary.exit_code == 1
        assert summary.error_message == ""


class TestBanditParsing:
    """Tests for _run_bandit JSON parsing."""

    @patch("ai.code_quality.runner._run_tool")
    def test_bandit_json_parsing(self, mock_run_tool):
        """Bandit severity mapping: HIGH->ERROR, MEDIUM->WARNING, LOW->INFO."""
        mock_run_tool.return_value = (BANDIT_JSON, "", 1, 0.8)

        summary = _run_bandit(["/fake"], timeout=60)

        assert summary.tool == "bandit"
        assert len(summary.findings) == 3

        sev_by_code = {f.code: f.severity for f in summary.findings}
        assert sev_by_code["B101"] == Severity.INFO       # LOW
        assert sev_by_code["B608"] == Severity.ERROR      # HIGH
        assert sev_by_code["B105"] == Severity.WARNING    # MEDIUM

        b608 = next(f for f in summary.findings if f.code == "B608")
        assert b608.file == "ai/router.py"
        assert b608.line == 55
        assert b608.message == "Possible SQL injection."


class TestShellcheckParsing:
    """Tests for _run_shellcheck JSON parsing."""

    @patch("ai.code_quality.runner._run_tool")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("pathlib.Path.is_file", return_value=False)
    @patch("pathlib.Path.glob")
    def test_shellcheck_json_parsing(
        self, mock_glob, mock_is_file, mock_is_dir, mock_run_tool
    ):
        """Shellcheck codes are prefixed with 'SC' and severity maps correctly."""
        from pathlib import Path

        mock_glob.return_value = [Path("/fake/scripts/backup.sh")]
        mock_run_tool.return_value = (SHELLCHECK_JSON, "", 1, 0.4)

        summary = _run_shellcheck(["/fake/scripts"], timeout=60)

        assert summary.tool == "shellcheck"
        assert len(summary.findings) == 3

        f0 = summary.findings[0]
        assert f0.code == "SC2086"
        assert f0.severity == Severity.WARNING
        assert f0.file == "scripts/backup.sh"
        assert f0.line == 12
        assert f0.column == 5

        f1 = summary.findings[1]
        assert f1.code == "SC2034"
        assert f1.severity == Severity.ERROR

        f2 = summary.findings[2]
        assert f2.code == "SC1091"
        assert f2.severity == Severity.INFO
        assert f2.end_line == 45

    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("pathlib.Path.is_file", return_value=False)
    @patch("pathlib.Path.glob", return_value=[])
    @patch("ai.code_quality.runner._run_tool")
    def test_shellcheck_no_sh_files(
        self, mock_run_tool, mock_glob, mock_is_file, mock_is_dir
    ):
        """No .sh files found returns empty summary without running subprocess."""
        summary = _run_shellcheck(["/empty/dir"], timeout=60)

        assert summary.tool == "shellcheck"
        assert summary.findings == []
        assert summary.runtime_seconds == 0.0
        mock_run_tool.assert_not_called()


class TestToolErrors:
    """Tests for tool-not-found, timeout, and malformed output."""

    @patch("ai.code_quality.runner.subprocess.run")
    def test_tool_not_found(self, mock_subprocess_run):
        """FileNotFoundError produces rc=127 and descriptive error_message."""
        mock_subprocess_run.side_effect = FileNotFoundError("No such file")

        from ai.code_quality.runner import _run_tool

        stdout, stderr, rc, elapsed = _run_tool(["nonexistent", "--version"], 60)

        assert rc == 127
        assert "Command not found: nonexistent" in stderr
        assert stdout == ""

    @patch("ai.code_quality.runner.subprocess.run")
    def test_tool_timeout(self, mock_subprocess_run):
        """TimeoutExpired produces rc=124 and timeout message."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd=["slow-tool"], timeout=10
        )

        from ai.code_quality.runner import _run_tool

        stdout, stderr, rc, elapsed = _run_tool(["slow-tool"], 10)

        assert rc == 124
        assert "Timeout after 10s" in stderr
        assert stdout == ""

    @patch("ai.code_quality.runner._run_tool")
    def test_invalid_json_output(self, mock_run_tool):
        """Malformed JSON produces empty findings without raising."""
        mock_run_tool.return_value = ("not valid json {{{", "", 1, 0.1)

        summary = _run_ruff(["/fake"], timeout=60)

        assert summary.tool == "ruff"
        assert summary.findings == []
        assert summary.exit_code == 1

    @patch("ai.code_quality.runner._run_tool")
    def test_empty_output(self, mock_run_tool):
        """Empty stdout produces empty findings list."""
        mock_run_tool.return_value = ("", "", 0, 0.05)

        summary = _run_ruff(["/fake"], timeout=60)

        assert summary.tool == "ruff"
        assert summary.findings == []
        assert summary.exit_code == 0
        assert summary.error_message == ""

    @patch("ai.code_quality.runner._run_tool")
    def test_empty_output_bandit(self, mock_run_tool):
        """Bandit with empty stdout also produces empty findings."""
        mock_run_tool.return_value = ("", "", 0, 0.05)

        summary = _run_bandit(["/fake"], timeout=60)

        assert summary.findings == []
        assert summary.tool == "bandit"
