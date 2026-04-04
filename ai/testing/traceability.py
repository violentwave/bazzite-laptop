"""Test traceability module for mapping tests to source code."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("ai.testing")


class TestTraceability:
    """Manages test-to-source mapping in LanceDB."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize LanceDB tables."""
        schema = pa.schema(
            [
                pa.field("test_id", pa.string()),
                pa.field("test_file", pa.string()),
                pa.field("test_function", pa.string()),
                pa.field("source_files", pa.string()),  # JSON list
                pa.field("source_functions", pa.string()),  # JSON list
                pa.field("coverage_pct", pa.float32()),
                pa.field("last_run", pa.string()),
                pa.field("last_duration", pa.float32()),
                pa.field("status", pa.string()),  # pass|fail|skip|flaky|quarantined
                pa.field("pass_rate", pa.float32()),
                pa.field("run_count", pa.int32()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        table_names = self._db.list_tables()
        if "test_mappings" in table_names:
            self._table = self._db.open_table("test_mappings")
        else:
            self._table = self._db.create_table("test_mappings", schema=schema)

    def populate_from_coverage(self) -> None:
        """Read .coverage SQLite and populate test_mappings table."""
        coverage_file = Path(".coverage")
        if not coverage_file.exists():
            logger.warning("No .coverage file found")
            return

        try:
            import sqlite3

            conn = sqlite3.connect(str(coverage_file))
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='coverage_python'"
            )
            if not cursor.fetchone():
                conn.close()
                return

            cursor.execute("""
                SELECT file, name FROM coverage_python
                WHERE function_name IS NOT NULL
            """)

            file_to_tests: dict[str, list[str]] = {}
            for row in cursor.fetchall():
                file_path, test_name = row
                if file_path not in file_to_tests:
                    file_to_tests[file_path] = []
                file_to_tests[file_path].append(test_name)

            conn.close()

            records = []
            for source_file, tests in file_to_tests.items():
                test_id = f"{source_file}::{','.join(tests)}"
                text_to_embed = f"{source_file} {' '.join(tests)}"
                try:
                    vector = embed(text_to_embed)
                except Exception:
                    vector = [0.0] * 768

                records.append(
                    {
                        "test_id": test_id,
                        "test_file": source_file,
                        "test_function": ",".join(tests),
                        "source_files": json.dumps([source_file]),
                        "source_functions": json.dumps(tests),
                        "coverage_pct": 0.0,
                        "last_run": datetime.now(UTC).isoformat(),
                        "last_duration": 0.0,
                        "status": "pass",
                        "pass_rate": 1.0,
                        "run_count": 1,
                        "vector": vector,
                    }
                )

            if records:
                self._table.add(records)

        except Exception as e:
            logger.warning(f"Failed to populate from coverage: {e}")

    def query_tests_for_source(self, source_path: str) -> list[dict]:
        """Return tests covering the given source file."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return []

            results = []
            for _, row in df.iterrows():
                source_files = json.loads(row["source_files"])
                if any(source_path in sf for sf in source_files):
                    results.append(
                        {
                            "test_id": row["test_id"],
                            "test_file": row["test_file"],
                            "test_function": row["test_function"],
                            "status": row["status"],
                            "pass_rate": row["pass_rate"],
                        }
                    )

            return results
        except Exception as e:
            logger.warning(f"Failed to query tests: {e}")
            return []

    def query_risky_tests(
        self, min_coverage: float = 0.5, max_pass_rate: float = 0.95
    ) -> list[dict]:
        """Return tests that cover significant code but are unreliable."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return []

            results = []
            for _, row in df.iterrows():
                if row["coverage_pct"] >= min_coverage and row["pass_rate"] <= max_pass_rate:
                    results.append(
                        {
                            "test_id": row["test_id"],
                            "test_file": row["test_file"],
                            "status": row["status"],
                            "pass_rate": row["pass_rate"],
                            "coverage_pct": row["coverage_pct"],
                        }
                    )

            return results
        except Exception as e:
            logger.warning(f"Failed to query risky tests: {e}")
            return []

    def update_stats(self, test_id: str, passed: bool, duration: float) -> None:
        """Update pass_rate and run_count for a test."""
        try:
            df = self._table.to_pandas()
            if df.empty or test_id not in df["test_id"].values:
                return

            idx = df[df["test_id"] == test_id].index[0]
            old_pass_rate = df.loc[idx, "pass_rate"]
            old_run_count = df.loc[idx, "run_count"]

            new_run_count = old_run_count + 1
            new_pass_rate = (old_pass_rate * old_run_count + (1 if passed else 0)) / new_run_count

            self._table.update(
                where=f"test_id = '{test_id}'",
                values={
                    "pass_rate": new_pass_rate,
                    "run_count": new_run_count,
                    "last_run": datetime.now(UTC).isoformat(),
                    "last_duration": duration,
                    "status": "flaky"
                    if 0.1 < new_pass_rate < 0.9
                    else ("pass" if passed else "fail"),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to update stats: {e}")


_traceability_instance: TestTraceability | None = None


def get_traceability() -> TestTraceability:
    """Get singleton TestTraceability instance."""
    global _traceability_instance
    if _traceability_instance is None:
        _traceability_instance = TestTraceability()
    return _traceability_instance
