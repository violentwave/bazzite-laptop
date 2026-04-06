"""Unit tests for the RAG vector store module.

All LanceDB operations are mocked -- LanceDB/pyarrow segfault in the VS Code
Flatpak sandbox, so no real database connections are made in tests.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Pre-populate sys.modules with mocks BEFORE importing store,
# so the lazy `import lancedb` and `import pyarrow` inside store.py
# get our mocks instead of the real (segfaulting) native extensions.
# Use setdefault return value so we share the same mock if another test file
# already installed one (e.g. test_log_intel.py), avoiding cross-file interference.
_mock_lancedb = sys.modules.setdefault("lancedb", MagicMock())
_mock_pyarrow = sys.modules.setdefault("pyarrow", MagicMock())

from ai.rag.store import VectorStore, get_store  # noqa: E402

# ── Fixtures ──


@pytest.fixture(autouse=True, scope="module")
def _cleanup_lancedb_mock_after_module():
    """Remove lancedb mock from sys.modules after this test module completes.

    test_store.py installs a MagicMock for lancedb at module level to prevent
    real LanceDB connections (which segfault in VS Code Flatpak). This fixture
    removes that mock after all tests in this module finish, so subsequent test
    modules (e.g. test_task_logger.py) can import the real lancedb.
    """
    yield
    sys.modules.pop("lancedb", None)


@pytest.fixture(autouse=True)
def _reset_lancedb_mock():
    """Reset the lancedb mock and singleton between tests."""
    import ai.rag.store as _store_mod
    _mock_lancedb.reset_mock(side_effect=True)
    # Replace connect with a fresh mock to clear accumulated calls from other test files.
    _mock_lancedb.connect = MagicMock(return_value=MagicMock())
    _store_mod._store_instance = None
    yield
    _store_mod._store_instance = None


@pytest.fixture()
def mock_db():
    """A mock LanceDB connection returned by lancedb.connect()."""
    db = MagicMock()
    _mock_lancedb.connect.return_value = db
    return db


@pytest.fixture()
def store(tmp_path, mock_db):
    """A VectorStore wired to a mock LanceDB connection."""
    return VectorStore(db_path=tmp_path / "test-vector-db")


@pytest.fixture()
def sample_log_chunk():
    """A single log chunk dict with all required fields."""
    return {
        "id": "chunk-001",
        "source_file": "/var/log/system-health/health-2026-03-15.log",
        "section": "GPU Status",
        "content": "GPU temp: 42C, fan: 30%, util: 0%",
        "log_type": "health",
        "timestamp": "2026-03-15T08:00:00+00:00",
        "vector": [0.1] * 768,
    }


@pytest.fixture()
def sample_threat_report():
    """A single threat report dict with all required fields."""
    return {
        "id": "threat-001",
        "hash": "a" * 64,
        "source": "virustotal",
        "family": "trojan.eicar/test",
        "risk_level": "high",
        "content": "VirusTotal: 62/72 detections for eicar test file",
        "timestamp": "2026-03-15T12:00:00+00:00",
        "vector": [0.2] * 768,
    }


# ── VectorStore Init ──


class TestVectorStoreInit:
    def test_default_path(self):
        """Uses VECTOR_DB_DIR when no path provided."""
        with patch("ai.rag.store.VECTOR_DB_DIR", Path("/home/lch/security/vector-db")):
            s = VectorStore()
            assert s._db_path == Path("/home/lch/security/vector-db")

    def test_custom_path(self, tmp_path):
        """Accepts a custom db_path."""
        custom = tmp_path / "custom-db"
        s = VectorStore(db_path=custom)
        assert s._db_path == custom

    def test_lazy_connection(self, tmp_path):
        """Does not connect on __init__."""
        VectorStore(db_path=tmp_path / "lazy-db")
        _mock_lancedb.connect.assert_not_called()

    def test_connect_called_once(self, store):
        """Calling _connect() twice reuses the same connection."""
        store._connect()
        store._connect()
        _mock_lancedb.connect.assert_called_once()


# ── Add Log Chunks ──


class TestAddLogChunks:
    def test_add_chunks(self, store, mock_db, sample_log_chunk):
        """Successfully adds chunks and returns count."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["security_logs"]
        mock_db.open_table.return_value = mock_table

        count = store.add_log_chunks([sample_log_chunk])

        assert count == 1
        mock_table.add.assert_called_once_with([sample_log_chunk])

    def test_add_multiple_chunks(self, store, mock_db, sample_log_chunk):
        """Adds multiple chunks in one call."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["security_logs"]
        mock_db.open_table.return_value = mock_table

        chunks = [sample_log_chunk.copy() for _ in range(3)]
        count = store.add_log_chunks(chunks)

        assert count == 3

    def test_add_empty_list(self, store):
        """Returns 0 for empty input without touching the database."""
        count = store.add_log_chunks([])
        assert count == 0

    def test_generates_id_if_missing(self, store, mock_db, sample_log_chunk):
        """Auto-generates UUID id when not provided in chunk."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = []
        mock_db.create_table.return_value = mock_table

        del sample_log_chunk["id"]
        store.add_log_chunks([sample_log_chunk])

        added = mock_table.add.call_args[0][0]
        assert "id" in added[0]
        assert len(added[0]["id"]) == 36  # UUID4 format

    def test_add_failure_returns_zero(self, store, mock_db, sample_log_chunk):
        """Returns 0 on LanceDB error instead of crashing."""
        mock_db.list_tables.side_effect = RuntimeError("disk full")

        count = store.add_log_chunks([sample_log_chunk])
        assert count == 0

    def test_creates_table_if_missing(self, store, mock_db, sample_log_chunk):
        """Creates the security_logs table when it does not exist."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = []
        mock_db.create_table.return_value = mock_table

        store.add_log_chunks([sample_log_chunk])

        mock_db.create_table.assert_called_once()
        assert mock_db.create_table.call_args[0][0] == "security_logs"


# ── Add Threat Reports ──


class TestAddThreatReports:
    def test_add_reports(self, store, mock_db, sample_threat_report):
        """Successfully adds threat reports and returns count."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["threat_intel"]
        mock_db.open_table.return_value = mock_table

        count = store.add_threat_reports([sample_threat_report])

        assert count == 1
        mock_table.add.assert_called_once_with([sample_threat_report])

    def test_add_empty_list(self, store):
        """Returns 0 for empty input."""
        count = store.add_threat_reports([])
        assert count == 0

    def test_generates_id_if_missing(self, store, mock_db, sample_threat_report):
        """Auto-generates UUID id when not provided."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["threat_intel"]
        mock_db.open_table.return_value = mock_table

        del sample_threat_report["id"]
        store.add_threat_reports([sample_threat_report])

        added = mock_table.add.call_args[0][0]
        assert "id" in added[0]

    def test_add_failure_returns_zero(self, store, mock_db, sample_threat_report):
        """Returns 0 on LanceDB error."""
        mock_db.list_tables.side_effect = RuntimeError("connection lost")

        count = store.add_threat_reports([sample_threat_report])
        assert count == 0

    def test_creates_table_if_missing(self, store, mock_db, sample_threat_report):
        """Creates the threat_intel table when it does not exist."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = []
        mock_db.create_table.return_value = mock_table

        store.add_threat_reports([sample_threat_report])

        mock_db.create_table.assert_called_once()
        assert mock_db.create_table.call_args[0][0] == "threat_intel"


# ── Search Logs ──


class TestSearchLogs:
    def test_search_returns_results(self, store, mock_db):
        """Vector search returns matching log entries."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["security_logs"]
        mock_db.open_table.return_value = mock_table

        result_list = [{
            "id": "chunk-001",
            "source_file": "/var/log/health.log",
            "section": "GPU Status",
            "content": "GPU temp: 42C",
            "log_type": "health",
            "timestamp": "2026-03-15T08:00:00+00:00",
            "vector": [0.1] * 768,
            "_distance": 0.05,
        }]
        mock_table.search.return_value.limit.return_value.to_list.return_value = result_list

        results = store.search_logs([0.1] * 768, limit=5)

        assert len(results) == 1
        assert results[0]["section"] == "GPU Status"
        mock_table.search.assert_called_once_with([0.1] * 768)
        mock_table.search.return_value.limit.assert_called_once_with(5)

    def test_search_empty_results(self, store, mock_db):
        """Returns empty list when no matches found."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["security_logs"]
        mock_db.open_table.return_value = mock_table

        mock_table.search.return_value.limit.return_value.to_list.return_value = []

        results = store.search_logs([0.1] * 768)
        assert results == []

    def test_search_failure_returns_empty(self, store, mock_db):
        """Returns empty list on search error."""
        mock_db.list_tables.side_effect = RuntimeError("broken")

        results = store.search_logs([0.1] * 768)
        assert results == []


# ── Search Threats ──


class TestSearchThreats:
    def test_search_returns_results(self, store, mock_db):
        """Vector search returns matching threat reports."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["threat_intel"]
        mock_db.open_table.return_value = mock_table

        result_list = [{
            "id": "threat-001",
            "hash": "a" * 64,
            "source": "virustotal",
            "family": "trojan.eicar/test",
            "risk_level": "high",
            "content": "62/72 detections",
            "timestamp": "2026-03-15T12:00:00+00:00",
            "vector": [0.2] * 768,
            "_distance": 0.03,
        }]
        mock_table.search.return_value.limit.return_value.to_list.return_value = result_list

        results = store.search_threats([0.2] * 768, limit=3)

        assert len(results) == 1
        assert results[0]["source"] == "virustotal"
        mock_table.search.return_value.limit.assert_called_once_with(3)

    def test_search_respects_limit(self, store, mock_db):
        """Passes limit parameter through to LanceDB search."""
        mock_table = MagicMock()
        mock_db.list_tables.return_value = ["threat_intel"]
        mock_db.open_table.return_value = mock_table
        mock_table.search.return_value.limit.return_value.to_list.return_value = []

        store.search_threats([0.1] * 768, limit=10)

        mock_table.search.return_value.limit.assert_called_once_with(10)

    def test_search_failure_returns_empty(self, store, mock_db):
        """Returns empty list on search error."""
        mock_db.list_tables.side_effect = RuntimeError("broken")

        results = store.search_threats([0.1] * 768)
        assert results == []


# ── Count ──


class TestCount:
    def test_count_existing_table(self, store, mock_db):
        """Returns row count for an existing table."""
        mock_table = MagicMock()
        mock_table.count_rows.return_value = 42
        mock_db.list_tables.return_value = ["security_logs"]
        mock_db.open_table.return_value = mock_table

        assert store.count("security_logs") == 42

    def test_count_missing_table(self, store, mock_db):
        """Returns 0 for a table that does not exist."""
        mock_db.list_tables.return_value = []

        assert store.count("security_logs") == 0

    def test_count_failure_returns_zero(self, store, mock_db):
        """Returns 0 on error instead of crashing."""
        mock_db.list_tables.side_effect = RuntimeError("broken")

        assert store.count("security_logs") == 0


# ── Singleton ──


class TestGetStore:
    def test_returns_vector_store(self, tmp_path):
        """get_store() returns a VectorStore instance."""
        with patch("ai.rag.store._store_instance", None):
            s = get_store(db_path=tmp_path / "singleton-db")
            assert isinstance(s, VectorStore)

    def test_singleton_same_instance(self, tmp_path):
        """Repeated calls return the same instance."""
        with patch("ai.rag.store._store_instance", None):
            s1 = get_store(db_path=tmp_path / "singleton-db")
            with patch("ai.rag.store._store_instance", s1):
                s2 = get_store()
                assert s1 is s2
