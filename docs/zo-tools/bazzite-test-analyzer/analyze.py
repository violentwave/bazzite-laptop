#!/usr/bin/env python3
"""
Bazzite Test Failure Analyzer

Parses pytest JUnit XML, categorizes failures, suggests fixes via LLM.
Tracks patterns over time for the bazzite-laptop test suite (~1951 tests).
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# JUnit parsing (try junitparser, fallback to stdlib)
try:
    from junitparser import JUnitXml, TestCase, TestSuite
    HAS_JUNITPARSER = True
except ImportError:
    HAS_JUNITPARSER = False

INTEL_DIR = Path.home() / "security" / "intel" / "tests"
ANALYZE_LOG = INTEL_DIR / ".analyzer.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(ANALYZE_LOG), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class Failure:
    test_name: str
    test_file: str
    error_type: str
    error_message: str
    stack_trace: str
    duration: float
    category: str = ""
    suggestion: str = ""
    fix_hash: str = ""


@dataclass
class AnalysisResult:
    run_id: str
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    categories: dict[str, int] = field(default_factory=dict)
    failures: list[Failure] = field(default_factory=list)


class TestAnalyzer:
    # Error patterns to categorize failures
    ERROR_PATTERNS = {
        "assertion_error": [
            r"assert\s+",
            r"AssertionError",
            r"assertEqual",
            r"assertTrue",
            r"assertFalse",
        ],
        "import_error": [
            r"ImportError",
            r"ModuleNotFoundError",
            r"No module named",
        ],
        "timeout_error": [
            r"Timeout",
            r"timed out",
            r"DeadlineExceeded",
        ],
        "mock_error": [
            r"Mock",
            r"mock",
            r"MagicMock",
            r"call_count",
            r"assert_called",
        ],
        "api_error": [
            r"ConnectionError",
            r"HTTPError",
            r"requests\.exceptions",
            r"httpx\.",
            r"APIError",
        ],
        "database_error": [
            r"DatabaseError",
            r"lancedb",
            r"sqlite3",
            r"OperationalError",
        ],
        "file_error": [
            r"FileNotFoundError",
            r"PermissionError",
            r"IsADirectoryError",
        ],
        "type_error": [
            r"TypeError",
            r"AttributeError",
        ],
        "key_error": [
            r"KeyError",
            r"IndexError",
        ],
    }

    FIX_TEMPLATES = {
        "assertion_error": "Check assertion logic; may need updated expected values or mocked dependencies",
        "import_error": "Missing dependency - add to requirements.txt or install with pip",
        "timeout_error": "Increase timeout or mock slow external calls",
        "mock_error": "Fix mock setup - verify patch target and call expectations",
        "api_error": "External API failure - mock this in tests or check network/credentials",
        "database_error": "Database state issue - ensure test isolation with fixtures",
        "file_error": "Missing test fixture - create expected files or mock file system",
        "type_error": "Type mismatch - check function signatures and return types",
        "key_error": "Missing dict key - check data structure or add default handling",
    }

    def __init__(self, junit_path: Path, project_root: Path | None = None):
        self.junit_path = junit_path
        self.project_root = project_root or junit_path.parent
        self.result = AnalysisResult(
            run_id=datetime.now(UTC).strftime("%Y%m%d_%H%M%S"),
            timestamp=datetime.now(UTC).isoformat(),
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            duration=0.0,
        )

    def analyze(self) -> AnalysisResult:
        """Parse JUnit XML and analyze failures."""
        logger.info(f"Analyzing {self.junit_path}")

        if HAS_JUNITPARSER:
            self._parse_with_junitparser()
        else:
            self._parse_with_stdlib()

        # Categorize and suggest fixes
        for failure in self.result.failures:
            failure.category = self._categorize(failure.error_message)
            failure.suggestion = self.FIX_TEMPLATES.get(
                failure.category, "Review error message and stack trace for root cause"
            )
            failure.fix_hash = hashlib.sha256(
                f"{failure.test_name}:{failure.error_message[:100]}".encode()
            ).hexdigest()[:16]

        # Count categories
        self.result.categories = {}
        for f in self.result.failures:
            self.result.categories[f.category] = \
                self.result.categories.get(f.category, 0) + 1

        return self.result

    def _parse_with_junitparser(self):
        """Parse using junitparser library."""
        xml = JUnitXml.fromfile(str(self.junit_path))

        for suite in xml:
            if isinstance(suite, TestSuite):
                for case in suite:
                    self._process_case(case)
            else:
                self._process_case(suite)

    def _parse_with_stdlib(self):
        """Fallback stdlib XML parsing."""
        tree = ET.parse(self.junit_path)
        root = tree.getroot()

        # Handle both <testsuites> and <testsuite> root
        if root.tag == "testsuites":
            for suite in root:
                self._process_suite_element(suite)
        else:
            self._process_suite_element(root)

    def _process_suite_element(self, suite: ET.Element):
        """Process a test suite element."""
        for case in suite.findall("testcase"):
            self._process_case_element(case)

    def _process_case_element(self, case: ET.Element):
        """Process a single test case element."""
        name = case.get("name", "unknown")
        classname = case.get("classname", "")
        time = float(case.get("time", 0))

        test_name = f"{classname}.{name}" if classname else name
        test_file = self._file_from_classname(classname)

        self.result.total_tests += 1

        # Check for failure/error
        failure_elem = case.find("failure")
        error_elem = case.find("error")
        skip_elem = case.find("skipped")

        if failure_elem is not None:
            self.result.failed += 1
            self.result.failures.append(Failure(
                test_name=test_name,
                test_file=test_file,
                error_type=failure_elem.get("type", "Failure"),
                error_message=failure_elem.get("message", ""),
                stack_trace=failure_elem.text or "",
                duration=time,
            ))
        elif error_elem is not None:
            self.result.errors += 1
            self.result.failures.append(Failure(
                test_name=test_name,
                test_file=test_file,
                error_type=error_elem.get("type", "Error"),
                error_message=error_elem.get("message", ""),
                stack_trace=error_elem.text or "",
                duration=time,
            ))
        elif skip_elem is not None:
            self.result.skipped += 1
        else:
            self.result.passed += 1

        self.result.duration += time

    def _process_case(self, case):
        """Process a junitparser TestCase."""
        if not isinstance(case, TestCase):
            return

        name = case.name
        classname = case.classname or ""
        time = case.time or 0

        test_name = f"{classname}.{name}" if classname else name
        test_file = self._file_from_classname(classname)

        self.result.total_tests += 1

        if case.is_passed:
            self.result.passed += 1
        elif case.result:
            result = case.result[0]
            if hasattr(result, 'type'):
                error_type = result.type
            else:
                error_type = type(result).__name__

            self.result.failed += 1
            self.result.failures.append(Failure(
                test_name=test_name,
                test_file=test_file,
                error_type=error_type,
                error_message=str(result)[:500],
                stack_trace=getattr(result, 'text', str(result)) or "",
                duration=time,
            ))
        else:
            self.result.passed += 1

        self.result.duration += time

    def _file_from_classname(self, classname: str) -> str:
        """Extract file path from test class name."""
        if not classname:
            return ""
        # Convert TestClass to test_class.py
        parts = classname.split(".")
        if parts:
            # Last part is class, rest is module path
            return parts[-1].lower().replace("test", "test_") + ".py"
        return ""

    def _categorize(self, error_message: str) -> str:
        """Categorize error based on message patterns."""
        error_lower = error_message.lower()

        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return category

        return "unknown_error"

    def save_report(self) -> Path:
        """Save analysis to JSON."""
        INTEL_DIR.mkdir(parents=True, exist_ok=True)

        report_path = INTEL_DIR / f"test_analysis_{self.result.run_id}.json"
        report_path.write_text(json.dumps(asdict(self.result), indent=2))

        # Update symlink
        latest = INTEL_DIR / "latest_analysis.json"
        if latest.exists():
            latest.unlink()
        latest.symlink_to(report_path.name)

        logger.info(f"Report saved: {report_path}")
        return report_path

    def compare_with_previous(self) -> dict:
        """Compare with previous run to detect regression."""
        latest = INTEL_DIR / "latest_analysis.json"
        if not latest.exists() or not latest.is_symlink():
            return {"is_regression": False, "previous_failures": 0}

        try:
            prev_path = INTEL_DIR / latest.readlink()
            if prev_path == INTEL_DIR / f"test_analysis_{self.result.run_id}.json":
                return {"is_regression": False, "previous_failures": 0}

            prev_data = json.loads(prev_path.read_text())
            prev_failures = prev_data.get("failed", 0)

            return {
                "is_regression": self.result.failed > prev_failures,
                "previous_failures": prev_failures,
                "current_failures": self.result.failed,
                "delta": self.result.failed - prev_failures,
            }
        except Exception as e:
            logger.warning(f"Could not compare with previous: {e}")
            return {"is_regression": False, "previous_failures": 0}


def print_summary(result: AnalysisResult, comparison: dict):
    """Print human-readable summary."""
    print(f"\n{'='*60}")
    print(f"TEST ANALYSIS: {result.run_id}")
    print(f"{'='*60}")
    print(f"Total tests: {result.total_tests}")
    print(f"  ✅ Passed:   {result.passed}")
    print(f"  ❌ Failed:   {result.failed}")
    print(f"  ⏭️  Skipped:  {result.skipped}")
    print(f"  ⚠️  Errors:   {result.errors}")
    print(f"Duration: {result.duration:.2f}s")

    if comparison.get("is_regression"):
        print(f"\n🔴 REGRESSION DETECTED: {comparison['delta']} more failures")
    elif comparison.get("previous_failures", 0) > 0:
        delta = comparison.get("delta", 0)
        if delta < 0:
            print(f"\n🟢 IMPROVEMENT: {abs(delta)} fewer failures")
        else:
            print("\n⚪ No change in failure count")

    if result.categories:
        print("\nFailure Categories:")
        for cat, count in sorted(result.categories.items(), key=lambda x: -x[1]):
            icon = "🔴" if cat in ["assertion_error", "api_error"] else "🟡"
            print(f"  {icon} {cat}: {count}")

    if result.failures:
        print("\nTop Failures (by duration):")
        sorted_failures = sorted(result.failures, key=lambda f: -f.duration)[:5]
        for f in sorted_failures:
            print(f"  - {f.test_name[:50]}... ({f.duration:.2f}s)")
            print(f"    {f.suggestion}")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze pytest test failures from JUnit XML"
    )
    parser.add_argument("junit_xml", help="Path to JUnit XML file")
    parser.add_argument("--project-root", help="Project root for file resolution")
    parser.add_argument("--dry-run", action="store_true", help="Analyze but don't save")
    args = parser.parse_args()

    junit_path = Path(args.junit_xml).expanduser().resolve()
    if not junit_path.exists():
        logger.error(f"File not found: {junit_path}")
        sys.exit(1)

    project_root = None
    if args.project_root:
        project_root = Path(args.project_root).expanduser().resolve()

    analyzer = TestAnalyzer(junit_path, project_root)
    result = analyzer.analyze()
    comparison = analyzer.compare_with_previous()

    print_summary(result, comparison)

    if not args.dry_run:
        report_path = analyzer.save_report()
        print(f"\nDetailed report: {report_path}")

        # Exit with error if regression
        if comparison.get("is_regression"):
            sys.exit(2)  # Special exit code for regression

    sys.exit(0 if result.failed == 0 else 1)


if __name__ == "__main__":
    main()
