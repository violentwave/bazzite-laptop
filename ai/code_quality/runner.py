"""Parallel linter runner for the code quality pipeline.

Runs ruff, bandit, and shellcheck concurrently, parses JSON output
into LintFinding/LintSummary dataclasses.
"""

import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ai.code_quality.models import LintFinding, LintSummary, Severity
from ai.config import APP_NAME, PROJECT_ROOT

logger = logging.getLogger(APP_NAME)

# Default target directories
PYTHON_TARGETS = [str(PROJECT_ROOT / "ai"), str(PROJECT_ROOT / "tests")]
SHELL_TARGETS = [str(PROJECT_ROOT / "scripts")]


def run_all(
    python_targets: list[str] | None = None,
    shell_targets: list[str] | None = None,
    timeout: int = 120,
) -> list[LintSummary]:
    """Run all linters in parallel and return summaries.

    Args:
        python_targets: Directories for ruff/bandit. Defaults to ai/ and tests/.
        shell_targets: Directories for shellcheck. Defaults to scripts/.
        timeout: Per-tool timeout in seconds.

    Returns:
        List of LintSummary, one per tool.
    """
    py_targets = python_targets or PYTHON_TARGETS
    sh_targets = shell_targets or SHELL_TARGETS

    tasks = {
        "ruff": lambda: _run_ruff(py_targets, timeout),
        "bandit": lambda: _run_bandit(py_targets, timeout),
        "shellcheck": lambda: _run_shellcheck(sh_targets, timeout),
    }

    results: list[LintSummary] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            tool = futures[future]
            try:
                summary = future.result()
                results.append(summary)
            except Exception as e:
                logger.exception("Linter '%s' raised an exception", tool)
                results.append(LintSummary(tool=tool, error_message=str(e)))

    results.sort(key=lambda s: s.tool)
    return results


def _run_tool(cmd: list[str], timeout: int) -> tuple[str, str, int, float]:
    """Run a subprocess, capture output, return (stdout, stderr, returncode, seconds)."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        return proc.stdout, proc.stderr, proc.returncode, elapsed
    except FileNotFoundError:
        elapsed = time.monotonic() - start
        return "", f"Command not found: {cmd[0]}", 127, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return "", f"Timeout after {timeout}s", 124, elapsed


def _run_ruff(targets: list[str], timeout: int) -> LintSummary:
    """Run ruff check with JSON output."""
    cmd = ["ruff", "check", "--output-format=json", "--no-fix", *targets]
    stdout, stderr, rc, elapsed = _run_tool(cmd, timeout)

    findings: list[LintFinding] = []
    if stdout.strip():
        try:
            for item in json.loads(stdout):
                sev = Severity.ERROR if item.get("type") == "E" else Severity.WARNING
                findings.append(LintFinding(
                    tool="ruff",
                    file=item.get("filename", ""),
                    line=item.get("location", {}).get("row", 0),
                    column=item.get("location", {}).get("column", 0),
                    code=item.get("code", ""),
                    message=item.get("message", ""),
                    severity=sev,
                    end_line=item.get("end_location", {}).get("row"),
                ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse ruff JSON: %s", e)

    return LintSummary(
        tool="ruff",
        findings=findings,
        exit_code=rc,
        runtime_seconds=elapsed,
        error_message=stderr if rc not in (0, 1) else "",
    )


def _run_bandit(targets: list[str], timeout: int) -> LintSummary:
    """Run bandit with JSON output."""
    cmd = [
        "bandit", "-r", "-f", "json",
        "-c", str(PROJECT_ROOT / "pyproject.toml"),
        *targets,
    ]
    stdout, stderr, rc, elapsed = _run_tool(cmd, timeout)

    findings: list[LintFinding] = []
    if stdout.strip():
        try:
            data = json.loads(stdout)
            for item in data.get("results", []):
                sev_map = {
                    "HIGH": Severity.ERROR,
                    "MEDIUM": Severity.WARNING,
                    "LOW": Severity.INFO,
                }
                findings.append(LintFinding(
                    tool="bandit",
                    file=item.get("filename", ""),
                    line=item.get("line_number", 0),
                    code=item.get("test_id", ""),
                    message=item.get("issue_text", ""),
                    severity=sev_map.get(
                        item.get("issue_severity", ""), Severity.WARNING
                    ),
                ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse bandit JSON: %s", e)

    return LintSummary(
        tool="bandit",
        findings=findings,
        exit_code=rc,
        runtime_seconds=elapsed,
        error_message=stderr if rc not in (0, 1) else "",
    )


def _run_shellcheck(targets: list[str], timeout: int) -> LintSummary:
    """Run shellcheck with JSON output on all .sh files in targets."""
    sh_files: list[str] = []
    for target in targets:
        p = Path(target)
        if p.is_file() and p.suffix == ".sh":
            sh_files.append(str(p))
        elif p.is_dir():
            sh_files.extend(str(f) for f in p.glob("*.sh"))

    if not sh_files:
        return LintSummary(tool="shellcheck", runtime_seconds=0.0)

    cmd = ["shellcheck", "-f", "json", *sh_files]
    stdout, stderr, rc, elapsed = _run_tool(cmd, timeout)

    findings: list[LintFinding] = []
    if stdout.strip():
        try:
            for item in json.loads(stdout):
                sev_map = {
                    "error": Severity.ERROR,
                    "warning": Severity.WARNING,
                    "info": Severity.INFO,
                    "style": Severity.INFO,
                }
                findings.append(LintFinding(
                    tool="shellcheck",
                    file=item.get("file", ""),
                    line=item.get("line", 0),
                    column=item.get("column", 0),
                    code=f"SC{item.get('code', '')}",
                    message=item.get("message", ""),
                    severity=sev_map.get(
                        item.get("level", ""), Severity.WARNING
                    ),
                    end_line=item.get("endLine"),
                ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse shellcheck JSON: %s", e)

    return LintSummary(
        tool="shellcheck",
        findings=findings,
        exit_code=rc,
        runtime_seconds=elapsed,
        error_message=stderr if rc not in (0, 1) else "",
    )
