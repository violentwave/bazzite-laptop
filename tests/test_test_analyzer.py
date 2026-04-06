"""Tests for ai.system.test_analyzer module."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestParseFailed:
    """Test parse_pytest_output extracts failure details."""

    def test_parse_failed_line(self):
        """Regex extracts nodeid/error_type/message correctly."""
        from ai.system.test_analyzer import TestFailureAnalyzer

        analyzer = TestFailureAnalyzer()
        output = """============================= test session starts ==============================
tests/test_example.py::TestClass::test_foo FAILED - ValueError: invalid value

=========================== 1 failed in 0.5s ==========================="""

        result = analyzer.parse_pytest_output(output)

        assert result.failed == 1
        assert len(result.failures) == 1

        f = result.failures[0]
        assert "test_foo" in f.function
        assert f.error_type == "ValueError"
        assert "invalid value" in f.error_message


class TestAllPassing:
    """Test all passing output handling."""

    def test_parse_all_passing(self):
        """Returns 0 failures without error."""
        from ai.system.test_analyzer import TestFailureAnalyzer

        analyzer = TestFailureAnalyzer()
        output = """============================= test session starts ==============================
tests/test_example.py::test_one PASSED
tests/test_example.py::test_two PASSED
=========================== 2 passed in 0.5s ==========================="""

        result = analyzer.parse_pytest_output(output)

        assert result.failed == 0
        assert result.passed == 2


class TestCategorize:
    """Test failure categorization."""

    def test_categorize_by_error_type(self):
        """Groups failures under correct keys."""
        from ai.system.test_analyzer import Failure, TestFailureAnalyzer

        analyzer = TestFailureAnalyzer()
        failures = [
            Failure(
                test_id="tests/a.py::test_1",
                module="tests.a",
                class_="",
                function="test_1",
                error_type="ImportError",
                error_message="No module named 'foo'",
                traceback_lines=[],
                duration_ms=0,
            ),
            Failure(
                test_id="tests/b.py::test_2",
                module="tests.b",
                class_="",
                function="test_2",
                error_type="ValueError",
                error_message="Invalid value",
                traceback_lines=[],
                duration_ms=0,
            ),
        ]

        categories = analyzer.categorize_failures(failures)

        key1 = "error_type:ImportError"
        key2 = "error_type:ValueError"
        assert key1 in categories
        assert key2 in categories
        assert "tests/a.py::test_1" in categories[key1]
        assert "tests/b.py::test_2" in categories[key2]


class TestCompareRuns:
    """Test compare_runs uses all failures not just top 10."""

    def test_compare_runs_all_failures(self, temp_output_dir):
        """Uses all failures not just top 10."""
        from ai.system.test_analyzer import TestFailureAnalyzer

        analyzer = TestFailureAnalyzer()

        a_path = temp_output_dir / "a.json"
        b_path = temp_output_dir / "b.json"

        a_path.write_text(
            json.dumps(
                {
                    "summary": {"failed": 15, "error": 5},
                    "failure_categories": {
                        "error_type:ImportError": ["t1", "t2", "t3"],
                        "error_type:ValueError": ["t4", "t5", "t6"],
                        "error_type:TimeoutError": ["t7", "t8", "t9"],
                    },
                }
            )
        )

        b_path.write_text(
            json.dumps(
                {
                    "summary": {"failed": 10, "error": 3},
                    "failure_categories": {
                        "error_type:ImportError": ["t1", "t2"],
                        "error_type:ValueError": ["t4", "t5", "t6", "t7"],
                    },
                }
            )
        )

        result = analyzer.compare_runs(str(a_path), str(b_path))

        a_fails = {"t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"}
        b_fails = {"t1", "t2", "t4", "t5", "t6", "t7"}

        assert set(result["newly_failing"]) == b_fails - a_fails
        assert set(result["newly_passing"]) == a_fails - b_fails


class TestAtomicWrite:
    """Test atomic write functionality."""

    def test_generate_report_atomic_write(self, temp_output_dir):
        """Tmp file created then replaced."""
        from ai.system.test_analyzer import AnalysisResult, TestFailureAnalyzer

        analyzer = TestFailureAnalyzer()
        analysis = AnalysisResult(
            total=1,
            passed=0,
            failed=1,
            error=0,
            skipped=0,
            duration_s=0.5,
            failures=[],
            collection_errors=[],
        )

        report_path = temp_output_dir / "report.json"
        analyzer.generate_report(analysis, str(report_path))

        assert report_path.exists()

        tmp_file = report_path.with_suffix(".tmp")
        assert not tmp_file.exists()


class TestAutoDetect:
    """Test run auto-detects JSON vs plain text."""

    def test_run_autodetects_json(self, temp_output_dir):
        """Detects JSON report vs plain text."""
        from ai.system.test_analyzer import TestFailureAnalyzer

        json_report = {
            "tests": [
                {"nodeid": "tests/a.py::test_1", "outcome": "passed", "duration": 0.1},
                {"nodeid": "tests/b.py::test_2", "outcome": "failed", "duration": 0.2},
            ],
            "summary": {"passed": 1, "failed": 1},
            "duration": 1.5,
        }

        json_path = temp_output_dir / "report.json"
        json_path.write_text(json.dumps(json_report))

        analyzer = TestFailureAnalyzer()
        result = analyzer.parse_pytest_json(str(json_path))

        assert result.passed == 1
        assert result.failed == 1
