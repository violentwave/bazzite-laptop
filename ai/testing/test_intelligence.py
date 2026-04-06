"""Testing intelligence module for test stability tracking and analysis."""

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("ai.testing")

_TEST_DB_PATH = Path.home() / ".config" / "bazzite-ai" / "test-stability.db"


def _ensure_db_dir() -> None:
    """Ensure the config directory exists."""
    _TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class TestStabilityTracker:
    """Track test results and detect flaky tests."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        if project_root is not None:
            self._db_path = project_root / "test-stability.db"
        else:
            _ensure_db_dir()
            self._db_path = _TEST_DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database for test tracking."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                test_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                passed INTEGER NOT NULL,
                duration REAL,
                worker TEXT DEFAULT 'main',
                run_id INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_quarantine (
                test_id TEXT PRIMARY KEY,
                reason TEXT,
                quarantined_at TEXT NOT NULL,
                consecutive_passes INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results_test_id
            ON test_results(test_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results_timestamp
            ON test_results(timestamp)
        """)

        conn.commit()
        conn.close()

    def record_result(
        self, test_id: str, passed: bool, duration: float, worker: str = "main"
    ) -> None:
        """Record a test result."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        timestamp = datetime.now(UTC).isoformat()
        cursor.execute(
            "INSERT INTO test_results (test_id, timestamp, passed, duration, worker) "
            "VALUES (?, ?, ?, ?, ?)",
            (test_id, timestamp, 1 if passed else 0, duration, worker),
        )

        conn.commit()
        conn.close()

    def get_flaky_tests(
        self, min_runs: int = 5, min_pass_rate: float = 0.1, max_pass_rate: float = 0.99
    ) -> list[dict]:
        """Find tests that pass intermittently."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT test_id, COUNT(*) as runs,
                   SUM(passed) as passes,
                   AVG(duration) as avg_duration
            FROM test_results
            GROUP BY test_id
            HAVING runs >= ? AND passes > 0 AND passes < runs
            ORDER BY runs DESC
        """,
            (min_runs,),
        )

        results = []
        for row in cursor.fetchall():
            test_id, runs, passes, avg_duration = row
            pass_rate = passes / runs if runs > 0 else 0
            if min_pass_rate <= pass_rate <= max_pass_rate:
                results.append(
                    {
                        "test_id": test_id,
                        "runs": runs,
                        "passes": passes,
                        "pass_rate": pass_rate,
                        "avg_duration": avg_duration or 0,
                    }
                )

        conn.close()
        return results

    def quarantine_test(self, test_id: str, reason: str = "auto-detected flaky") -> None:
        """Add a test to the quarantine list."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        timestamp = datetime.now(UTC).isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO test_quarantine "
            "(test_id, reason, quarantined_at) VALUES (?, ?, ?)",
            (test_id, reason, timestamp),
        )

        conn.commit()
        conn.close()

    def check_unquarantine(self, consecutive_passes_needed: int = 10) -> list[str]:
        """Find quarantined tests that have enough recent passes to unquarantine."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT tr.test_id
            FROM test_results tr
            INNER JOIN test_quarantine tq ON tr.test_id = tq.test_id
            WHERE tr.passed = 1
            ORDER BY tr.timestamp DESC
        """)

        test_pass_counts: dict[str, int] = {}
        for row in cursor.fetchall():
            test_id = row[0]
            if test_id not in test_pass_counts:
                test_pass_counts[test_id] = 0
            test_pass_counts[test_id] += 1

        to_unquarantine = [
            test_id
            for test_id, count in test_pass_counts.items()
            if count >= consecutive_passes_needed
        ]

        for test_id in to_unquarantine:
            cursor.execute("DELETE FROM test_quarantine WHERE test_id = ?", (test_id,))

        conn.commit()
        conn.close()
        return to_unquarantine

    def get_affected_tests(self, changed_files: list[str]) -> list[str]:
        """Find tests affected by changed files using import heuristics."""
        test_files = list(self.project_root.glob("tests/test_*.py"))

        affected = []
        changed_modules = set()
        for f in changed_files:
            f = Path(f)
            if f.suffix == ".py":
                if "ai/" in str(f):
                    module = str(f).replace("/", ".").replace(".py", "")
                    changed_modules.add(module)

        for test_file in test_files:
            try:
                content = test_file.read_text()
                for module in changed_modules:
                    if module.split(".")[-1] in content:
                        affected.append(f"{test_file.stem}::*")
                        break
            except Exception as e:
                logger.warning(f"Failed to read {test_file}: {e}")

        return affected

    def get_coverage_map(self) -> dict:
        """Read .coverage SQLite and build source-to-test mapping."""
        coverage_file = self.project_root / ".coverage"
        if not coverage_file.exists():
            return {}

        try:
            conn = sqlite3.connect(str(coverage_file))
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='coverage_python'"
            )
            if not cursor.fetchone():
                conn.close()
                return {}

            cursor.execute("""
                SELECT file, name FROM coverage_python
                WHERE function_name IS NOT NULL
            """)

            coverage_map = {}
            for row in cursor.fetchall():
                file_path, test_name = row
                if file_path not in coverage_map:
                    coverage_map[file_path] = []
                coverage_map[file_path].append(test_name)

            conn.close()
            return coverage_map
        except Exception as e:
            logger.warning(f"Failed to read coverage data: {e}")
            return {}

    def get_test_stats(self) -> dict:
        """Get summary statistics about tests."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(DISTINCT test_id) FROM test_results")
        total_tests = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM test_quarantine")
        quarantined_count = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(DISTINCT test_id) FROM test_results
            WHERE passed = 0
            GROUP BY test_id
            HAVING COUNT(*) > 1
        """)
        flaky_count = len(cursor.fetchall())

        cursor.execute("SELECT AVG(duration) FROM test_results WHERE duration IS NOT NULL")
        avg_duration = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT test_id, duration FROM test_results
            WHERE duration IS NOT NULL
            ORDER BY duration DESC
            LIMIT 10
        """)
        slowest = [{"test_id": r[0], "duration": r[1]} for r in cursor.fetchall()]

        conn.close()
        return {
            "total_tests": total_tests,
            "quarantined_count": quarantined_count,
            "flaky_count": flaky_count,
            "avg_duration": avg_duration,
            "slowest_10": slowest,
        }


_test_intel_instance: TestStabilityTracker | None = None


def get_test_intel() -> TestStabilityTracker:
    """Get singleton TestIntelligence instance."""
    global _test_intel_instance
    if _test_intel_instance is None:
        _test_intel_instance = TestStabilityTracker()
    return _test_intel_instance
