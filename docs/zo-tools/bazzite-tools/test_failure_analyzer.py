#!/usr/bin/env python3
"""
test_failure_analyzer.py - Analyzes pytest output and provides actionable failure summaries.

Parses both text output and JSON reports, categorizes failures, generates fix hints.
"""

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class Failure:
    test_id: str
    module: str
    class_: str
    function: str
    error_type: str
    error_message: str
    traceback_lines: list[str]
    duration_ms: int


@dataclass
class CollectionError:
    error_type: str
    location: str
    message: str


@dataclass
class AnalysisResult:
    total: int
    passed: int
    failed: int
    error: int
    skipped: int
    duration_s: float
    failures: list[Failure]
    collection_errors: list[CollectionError]
    failure_categories: dict[str, list[str]] = field(default_factory=dict)
    fix_hints: dict[str, str] = field(default_factory=dict)
    repeat_offenders: list[str] = field(default_factory=list)


class TestFailureAnalyzer:
    """Analyzes pytest output and provides structured failure summaries."""

    ERROR_PATTERNS = {
        "ImportError": [
            r"ImportError",
            r"ModuleNotFoundError",
            r"No module named",
        ],
        "AssertionError": [
            r"AssertionError",
            r"assert\s+",
            r"assertEqual",
            r"assertTrue",
            r"assertFalse",
            r"assertion",
        ],
        "TimeoutError": [
            r"Timeout",
            r"timed out",
            r"DeadlineExceeded",
            r"concurrent.futures.TimeoutError",
        ],
        "AttributeError": [
            r"AttributeError",
            r"has no attribute",
            r"NoneType",
        ],
        "KeyError": [
            r"KeyError",
        ],
        "ValueError": [
            r"ValueError",
        ],
        "TypeError": [
            r"TypeError",
        ],
        "FileNotFoundError": [
            r"FileNotFoundError",
        ],
        "PermissionError": [
            r"PermissionError",
        ],
        "ConnectionError": [
            r"ConnectionError",
            r"HTTPError",
            r"requests\.exceptions",
            r"httpx\.",
            r"Connection refused",
        ],
    }

    MODULE_PATTERNS = {
        "ai": r"ai[/\\][\w/\\]+",
        "tests": r"tests[/\\][\w/\\]+",
        "systemd": r"systemd[/\\][\w/\\]+",
        "security": r"security|threat|intel",
    }

    def __init__(self):
        self.history: dict = {}

    def parse_pytest_output(self, raw_output: str) -> AnalysisResult:
        """
        Parse the text output of `pytest -v` (not JSON).
        Extracts failed tests and errors with full details.
        """
        failures: list[Failure] = []
        collection_errors: list[CollectionError] = []
        summary = {"total": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0, "duration": 0.0}

        # Extract summary stats
        summary_patterns = [
            r"=+\s*(\d+)\s*passed",
            r"=+\s*(\d+)\s*failed",
            r"=+\s*(\d+)\s*error",
            r"=+\s*(\d+)\s*skipped",
            r"passed.*failed.*error.*skipped",
            r"passed.*skipped",
            r"passed.*failed",
            r"failed.*error",
        ]

        for line in raw_output.split("\n"):
            if "passed" in line.lower() or "failed" in line.lower():
                m = re.search(r"(\d+)\s+passed", line, re.IGNORECASE)
                if m:
                    summary["passed"] = int(m.group(1))
                m = re.search(r"(\d+)\s+failed", line, re.IGNORECASE)
                if m:
                    summary["failed"] = int(m.group(1))
                m = re.search(r"(\d+)\s+error", line, re.IGNORECASE)
                if m:
                    summary["error"] = int(m.group(1))
                m = re.search(r"(\d+)\s+skipped", line, re.IGNORECASE)
                if m:
                    summary["skipped"] = int(m.group(1))

                # Duration
                m = re.search(r"in\s+([\d.]+)\s*s", line)
                if m:
                    summary["duration"] = float(m.group(1))

        summary["total"] = summary["passed"] + summary["failed"] + summary["error"] + summary["skipped"]

        # Parse failed tests
        # Pattern: FAILED path/to/test::Class::test_function - ErrorType: message
        failed_pattern = r"FAILED\s+(\S+)\s*::\s*([^\s-]+)\s*(?:-\s*([^:]+):\s*(.+))?"

        for match in re.finditer(failed_pattern, raw_output):
            test_path = match.group(1)
            test_name = match.group(2)
            error_type = match.group(3) or "Unknown"
            error_msg = match.group(4) or ""

            # Parse module/class/function
            parts = test_name.split("::")
            class_name = ""
            func_name = test_name
            if len(parts) >= 2:
                class_name = parts[0]
                func_name = "::".join(parts[1:])

            # Extract traceback (lines after the failure until next test or end)
            start_pos = match.end()
            traceback_end = raw_output.find("\nFAILED", start_pos)
            if traceback_end == -1:
                traceback_end = len(raw_output)

            raw_traceback = raw_output[start_pos:traceback_end].strip()
            traceback_lines = [l for l in raw_traceback.split("\n") if l.strip()]

            failures.append(Failure(
                test_id=f"{test_path}::{test_name}",
                module=test_path.replace("/", ".").replace("\\", ".").replace(".py", ""),
                class_=class_name,
                function=func_name,
                error_type=error_type.strip() if error_type else "Unknown",
                error_message=error_msg.strip()[:500],
                traceback_lines=traceback_lines[:20],  # Limit lines
                duration_ms=0,
            ))

        # Parse collection errors
        collect_pattern = r"ERROR\s+collecting\s+(\S+)\s*-\s*([^:]+):\s*(.+)"
        for match in re.finditer(collect_pattern, raw_output):
            collection_errors.append(CollectionError(
                error_type=match.group(2).strip(),
                location=match.group(1),
                message=match.group(3).strip()[:500],
            ))

        return AnalysisResult(
            total=summary["total"],
            passed=summary["passed"],
            failed=summary["failed"],
            error=summary["error"],
            skipped=summary["skipped"],
            duration_s=summary["duration"],
            failures=failures,
            collection_errors=collection_errors,
        )

    def parse_pytest_json(self, json_path: str) -> AnalysisResult:
        """
        Parse output from `pytest --json-report` (pytest-json-report plugin).
        Same output structure as parse_pytest_output.
        """
        with open(json_path) as f:
            data = json.load(f)

        failures = []
        collection_errors = []

        for test in data.get("tests", []):
            outcome = test.get("outcome", "")
            if outcome not in ("failed", "error"):
                continue

            nodeid = test.get("nodeid", "")
            parts = nodeid.split("::")
            module = parts[0] if parts else ""
            class_ = parts[1] if len(parts) > 2 else ""
            func = parts[-1] if parts else ""

            call = test.get("call", {})
            error_type = ""
            error_msg = ""
            traceback = []

            if "crash" in call:
                crash = call["crash"]
                error_type = crash.get("cls", "Unknown")
                error_msg = crash.get("message", "")[:500]
                traceback = crash.get("tb", [])[:20]

            duration_ms = test.get("duration", 0) * 1000

            failures.append(Failure(
                test_id=nodeid,
                module=module.replace(".py", "").replace("/", "."),
                class_=class_,
                function=func,
                error_type=error_type,
                error_message=error_msg,
                traceback_lines=traceback,
                duration_ms=int(duration_ms),
            ))

        for error in data.get("collectors", []):
            if error.get("outcome") == "error" and "error" in error:
                err = error["error"]
                collection_errors.append(CollectionError(
                    error_type=err.get("cls", "Unknown"),
                    location=error.get("nodeid", ""),
                    message=err.get("message", "")[:500],
                ))

        summary = data.get("summary", {})
        return AnalysisResult(
            total=sum(summary.values()),
            passed=summary.get("passed", 0),
            failed=summary.get("failed", 0),
            error=summary.get("error", 0),
            skipped=summary.get("skipped", 0),
            duration_s=data.get("duration", 0),
            failures=failures,
            collection_errors=collection_errors,
        )

    def categorize_failures(self, failures: list[Failure]) -> dict[str, list[str]]:
        """
        Groups failures by error_type, module, and pattern.
        Returns {category: [test_ids]} dict.
        """
        categories: dict[str, list[str]] = {
            "error_type": {},
            "module": {},
            "pattern": {},
        }

        for failure in failures:
            # By error type
            error_type = failure.error_type
            if error_type not in categories["error_type"]:
                categories["error_type"][error_type] = []
            categories["error_type"][error_type].append(failure.test_id)

            # By module
            module = failure.module.split(".")[0] if "." in failure.module else failure.module
            if module not in categories["module"]:
                categories["module"][module] = []
            categories["module"][module].append(failure.test_id)

            # By pattern (error message analysis)
            msg = (failure.error_message or "").lower()
            patterns = []

            if "import" in msg or "module" in msg:
                patterns.append("import")
            if "mock" in msg or "patch" in msg:
                patterns.append("mock")
            if "file" in msg and "not found" in msg:
                patterns.append("file_not_found")
            if "network" in msg or "http" in msg or "api" in msg:
                patterns.append("network_call")
            if "timeout" in msg:
                patterns.append("timeout")
            if "fixture" in msg:
                patterns.append("fixture")

            for pattern in patterns:
                if pattern not in categories["pattern"]:
                    categories["pattern"][pattern] = []
                categories["pattern"][pattern].append(failure.test_id)

        # Flatten for return (just category -> list)
        flat: dict[str, list[str]] = {}
        for cat_type, groups in categories.items():
            for key, test_ids in groups.items():
                flat[f"{cat_type}:{key}"] = test_ids

        return flat

    def generate_fix_hints(self, categorized: dict[str, list[str]]) -> dict[str, str]:
        """
        For each category, produces a short actionable hint string.
        """
        hints: dict[str, str] = {}

        for category, test_ids in categorized.items():
            if not test_ids:
                continue

            if "error_type:ImportError" in category:
                hints[category] = "Check venv activation and requirements-ai.txt"
            elif "error_type:ModuleNotFoundError" in category:
                hints[category] = "Check venv activation and requirements-ai.txt"
            elif "pattern:network_call" in category:
                hints[category] = "Add @pytest.mark.skipif or mock the HTTP client"
            elif "pattern:file_not_found" in category:
                hints[category] = "Check test fixtures or tmp_path usage"
            elif "pattern:mock" in category:
                hints[category] = "Mock return value may be None, check patch target"
            elif "error_type:AttributeError" in category:
                hints[category] = "Mock return value is None, check patch target"
            elif "pattern:timeout" in category:
                hints[category] = "Increase timeout or use @pytest.mark.slow decorator"
            elif "pattern:fixture" in category:
                hints[category] = "Check fixture dependencies and conftest.py setup"
            elif "error_type:AssertionError" in category:
                hints[category] = "Check expected vs actual values, verify data mocks"
            elif "error_type:KeyError" in category:
                hints[category] = "Verify dict keys exist, add .get() with default"
            elif "error_type:ValueError" in category:
                hints[category] = "Check input validation and type conversions"
            else:
                hints[category] = "Review test logic and error traceback for details"

        return hints

    def generate_report(
        self,
        analysis: AnalysisResult,
        output_path: str,
        history_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Write JSON report with:
        - analyzed_at, summary, failure_categories
        - top_failures[:10], fix_hints, repeat_offenders
        Atomic write.
        """
        # Categorize
        categorized = self.categorize_failures(analysis.failures)
        hints = self.generate_fix_hints(categorized)

        # Find repeat offenders from history
        repeat_offenders: list[str] = []
        if history_path and Path(history_path).exists():
            with open(history_path) as f:
                self.history = json.load(f)

            current_fails = {f.test_id for f in analysis.failures}
            prev_fails = set(self.history.get("failed_tests", []))
            repeat_offenders = list(current_fails & prev_fails)

        # Top 10 failures by error severity
        top_failures = sorted(
            analysis.failures,
            key=lambda f: (f.error_type in ("ImportError", "ModuleNotFoundError"), len(f.error_message)),
            reverse=True,
        )[:10]

        report: dict[str, Any] = {
            "analyzed_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total": analysis.total,
                "passed": analysis.passed,
                "failed": analysis.failed,
                "error": analysis.error,
                "skipped": analysis.skipped,
                "pass_rate": analysis.passed / max(analysis.total, 1) * 100,
                "duration_s": analysis.duration_s,
            },
            "failure_categories": categorized,
            "top_failures": [
                {
                    "test_id": f.test_id,
                    "error_type": f.error_type,
                    "error_message": f.error_message[:200] if len(f.error_message) > 200 else f.error_message,
                    "module": f.module,
                }
                for f in top_failures
            ],
            "fix_hints": hints,
            "repeat_offenders": repeat_offenders,
            "collection_errors": [
                {"error_type": e.error_type, "location": e.location, "message": e.message}
                for e in analysis.collection_errors
            ],
        }

        # Atomic write
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = output_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(report, f, indent=2)
        os.replace(tmp_file, output_file)

        # Update history
        self.history["failed_tests"] = [f.test_id for f in analysis.failures]
        if history_path:
            tmp_hist = Path(history_path).with_suffix(".tmp")
            with open(tmp_hist, "w") as f:
                json.dump(self.history, f)
            os.replace(tmp_hist, history_path)

        return report

    def compare_runs(self, report_a_path: str, report_b_path: str) -> dict[str, Any]:
        """
        Diff two reports, returns:
        {newly_failing, newly_passing, still_failing, fixed_count, regressed_count}
        """
        with open(report_a_path) as f:
            a = json.load(f)
        with open(report_b_path) as f:
            b = json.load(f)

        a_fails = {f["test_id"] for f in a.get("top_failures", [])}
        b_fails = {f["test_id"] for f in b.get("top_failures", [])}

        newly_failing = list(b_fails - a_fails)
        newly_passing = list(a_fails - b_fails)
        still_failing = list(a_fails & b_fails)

        a_total = a["summary"]["failed"] + a["summary"]["error"]
        b_total = b["summary"]["failed"] + b["summary"]["error"]

        return {
            "newly_failing": newly_failing,
            "newly_passing": newly_passing,
            "still_failing": still_failing,
            "fixed_count": len(newly_passing),
            "regressed_count": len(newly_failing),
            "comparison": f"A={a_total} failures, B={b_total} failures",
        }

    def run(self, input_source: str, output_dir: str) -> str:
        """
        input_source is either a file path (pytest JSON report) or raw string.
        Auto-detects format.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / f"test_analysis_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        history_file = output_path / ".test_history.json"

        # Auto-detect format
        input_path = Path(input_source)
        if input_path.exists():
            # Check if JSON
            try:
                with open(input_path) as f:
                    content = f.read()
                    data = json.loads(content)
                    # If valid pytest JSON structure
                    if "tests" in data or "summary" in data:
                        analysis = self.parse_pytest_json(input_source)
                    else:
                        # Treat as text
                        analysis = self.parse_pytest_output(content)
            except json.JSONDecodeError:
                # Treat as raw text output
                with open(input_path) as f:
                    analysis = self.parse_pytest_output(f.read())
        else:
            # Treat as raw output string
            analysis = self.parse_pytest_output(input_source)

        # Generate report
        self.generate_report(analysis, str(report_file), str(history_file))

        return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="Test Failure Analyzer")
    parser.add_argument("--input", "-i", help="Input file or raw pytest output string")
    parser.add_argument("--output-dir", "-o", default="~/security/intel/tests", help="Output directory")
    parser.add_argument("--compare", help="Compare with previous report")

    args = parser.parse_args()

    if not args.input:
        # Read from stdin
        args.input = sys.stdin.read()

    output_dir = Path(args.output_dir).expanduser()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    analyzer = TestFailureAnalyzer()

    if args.compare:
        result = analyzer.compare_runs(args.compare, str(output_dir / f"test_analysis_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"))
        print(json.dumps(result, indent=2))
    else:
        report_path = analyzer.run(args.input, str(output_dir))
        print(f"Report written to: {report_path}")

        # Print summary
        with open(report_path) as f:
            report = json.load(f)
        s = report["summary"]
        print("\n=== Test Summary ===")
        print(f"Total: {s['total']}, Passed: {s['passed']}, Failed: {s['failed']}, Error: {s['error']}")
        print(f"Pass rate: {s['pass_rate']:.1f}%")
        if report["repeat_offenders"]:
            print(f"Repeat offenders: {len(report['repeat_offenders'])}")


if __name__ == "__main__":
    main()
