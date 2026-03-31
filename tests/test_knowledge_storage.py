"""Unit tests for ai/agents/knowledge_storage.py."""

import json
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

_KS = "ai.agents.knowledge_storage"


class TestCheckLancedb:
    def test_nominal(self):
        fake_tbl = MagicMock()
        fake_tbl.count_rows.return_value = 42

        fake_db = MagicMock()
        fake_db.list_tables.return_value = ["security_logs", "docs"]
        fake_db.open_table.return_value = fake_tbl

        fake_lancedb = MagicMock()
        fake_lancedb.connect.return_value = fake_db

        with patch.dict("sys.modules", {"lancedb": fake_lancedb}):
            from ai.agents.knowledge_storage import _check_lancedb

            result = _check_lancedb()
        assert result["total_rows"] == 84
        assert result["tables"]["security_logs"] == 42
        assert result["error"] is None

    def test_lancedb_not_installed(self):
        with patch.dict("sys.modules", {"lancedb": None}):
            from ai.agents.knowledge_storage import _check_lancedb

            result = _check_lancedb()
        assert result["total_rows"] == 0
        assert result["error"] is not None

    def test_connect_exception(self):
        fake_lancedb = MagicMock()
        fake_lancedb.connect.side_effect = RuntimeError("disk error")

        with patch.dict("sys.modules", {"lancedb": fake_lancedb}):
            from ai.agents.knowledge_storage import _check_lancedb

            result = _check_lancedb()
        assert result["error"] == "disk error"
        assert result["total_rows"] == 0


class TestReadIngestState:
    def test_parses_last_ingest(self, tmp_path):
        state = {"last_ingest": "2026-03-21T09:00:00+00:00"}
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        with patch(f"{_KS}._DOC_STATE_FILE", state_file):
            from ai.agents.knowledge_storage import _read_ingest_state

            result = _read_ingest_state(state_file)
        assert result["last_ingest"] is not None
        assert result["hours_ago"] is not None
        assert result["hours_ago"] >= 0

    def test_missing_file_returns_none(self, tmp_path):
        from ai.agents.knowledge_storage import _read_ingest_state

        result = _read_ingest_state(tmp_path / "nonexistent.json")
        assert result["last_ingest"] is None
        assert result["hours_ago"] is None

    def test_no_timestamp_key(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"other_key": "value"}))

        from ai.agents.knowledge_storage import _read_ingest_state

        result = _read_ingest_state(state_file)
        assert result["last_ingest"] is None


class TestGetVectorDbSize:
    def test_parses_du_output(self):
        with patch(f"{_KS}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="12345678\t/home/lch/security/vector-db\n"
            )
            from ai.agents.knowledge_storage import _get_vector_db_size

            size, human = _get_vector_db_size()
        assert size == 12345678
        assert "MB" in human or "KB" in human or "B" in human

    def test_failure_returns_zeros(self):
        with patch(f"{_KS}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            from ai.agents.knowledge_storage import _get_vector_db_size

            size, human = _get_vector_db_size()
        assert size == 0
        assert human == "unknown"


class TestCheckOllama:
    def test_running_with_nomic(self):
        response = json.dumps({"models": [{"name": "nomic-embed-text:latest"}]})
        with patch(f"{_KS}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=response)
            from ai.agents.knowledge_storage import _check_ollama

            result = _check_ollama()
        assert result["running"] is True
        assert result["nomic_available"] is True

    def test_running_without_nomic(self):
        response = json.dumps({"models": [{"name": "llama3:latest"}]})
        with patch(f"{_KS}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=response)
            from ai.agents.knowledge_storage import _check_ollama

            result = _check_ollama()
        assert result["running"] is True
        assert result["nomic_available"] is False

    def test_not_running(self):
        with patch(f"{_KS}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            from ai.agents.knowledge_storage import _check_ollama

            result = _check_ollama()
        assert result["running"] is False
        assert result["nomic_available"] is False


class TestBuildRecommendations:
    def _call(self, **kwargs):
        defaults = {
            "db": {"tables": {"security_logs": 10, "docs": 5}, "total_rows": 15, "error": None},
            "doc_state": {"last_ingest": "2026-03-21T09:00:00+00:00", "hours_ago": 5.0},
            "log_state": {"last_ingest": "2026-03-21T08:30:00+00:00", "hours_ago": 4.0},
            "disk": {"home_used_pct": 60.0, "steam_used_pct": 50.0, "steam_mounted": True},
            "ollama": {"running": True, "nomic_available": True},
        }
        defaults.update(kwargs)
        from ai.agents.knowledge_storage import _build_recommendations

        return _build_recommendations(**defaults)

    def test_all_nominal_returns_healthy(self):
        recs, status = self._call()
        assert status == "healthy"
        assert any("healthy" in r.lower() for r in recs)

    def test_empty_db_returns_attention(self):
        db = {"tables": {}, "total_rows": 0, "error": None}
        recs, status = self._call(db=db)
        assert status == "attention_needed"
        assert any("empty" in r.lower() for r in recs)

    def test_stale_docs_returns_stale(self):
        doc_state = {"last_ingest": "2026-03-19T09:00:00+00:00", "hours_ago": 60.0}
        recs, status = self._call(doc_state=doc_state)
        assert status == "stale"
        assert any("stale" in r.lower() for r in recs)

    def test_stale_logs_returns_stale(self):
        log_state = {"last_ingest": "2026-03-19T09:00:00+00:00", "hours_ago": 72.0}
        recs, status = self._call(log_state=log_state)
        assert status == "stale"

    def test_ollama_down_returns_attention(self):
        recs, status = self._call(ollama={"running": False, "nomic_available": False})
        assert status == "attention_needed"
        assert any("ollama" in r.lower() for r in recs)

    def test_nomic_missing_returns_attention(self):
        recs, status = self._call(ollama={"running": True, "nomic_available": False})
        assert status == "attention_needed"
        assert any("nomic" in r.lower() for r in recs)

    def test_lancedb_error_returns_attention(self):
        db = {"tables": {}, "total_rows": 0, "error": "connection refused"}
        recs, status = self._call(db=db)
        assert status == "attention_needed"


def _run_storage_patched(tmp_path, **overrides):
    """Helper: run run_storage_check with all collectors mocked."""
    defaults = {
        f"{_KS}._check_lancedb": {
            "tables": {"security_logs": 30, "docs": 12},
            "total_rows": 42,
            "error": None,
            "size_bytes": 5 * 1024 * 1024,
            "size_human": "5.0 MB",
        },
        f"{_KS}._get_vector_db_size": (5 * 1024 * 1024, "5.0 MB"),
        f"{_KS}._read_ingest_state": {"last_ingest": "2026-03-21T09:00:00+00:00", "hours_ago": 5.0},
        f"{_KS}._collect_disk": {
            "home_used_pct": 65.0,
            "steam_used_pct": 50.0,
            "steam_mounted": True,
        },
        f"{_KS}._check_ollama": {"running": True, "nomic_available": True},
        f"{_KS}.STORAGE_REPORTS_DIR": tmp_path / "reports",
    }
    defaults.update(overrides)

    patches = [
        patch(f"{_KS}._check_lancedb", return_value=defaults[f"{_KS}._check_lancedb"]),
        patch(f"{_KS}._get_vector_db_size", return_value=defaults[f"{_KS}._get_vector_db_size"]),
        patch(
            f"{_KS}._read_ingest_state",
            return_value=defaults[f"{_KS}._read_ingest_state"],
        ),
        patch(f"{_KS}._collect_disk", return_value=defaults[f"{_KS}._collect_disk"]),
        patch(f"{_KS}._check_ollama", return_value=defaults[f"{_KS}._check_ollama"]),
        patch(f"{_KS}.STORAGE_REPORTS_DIR", defaults[f"{_KS}.STORAGE_REPORTS_DIR"]),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from ai.agents.knowledge_storage import run_storage_check

        return run_storage_check()


class TestRunStorageCheck:
    def test_full_workflow_writes_report(self, tmp_path):
        result = _run_storage_patched(tmp_path)

        assert result["status"] in ("healthy", "stale", "attention_needed")
        assert "timestamp" in result
        assert "vector_db" in result
        assert "ingestion" in result
        assert "disk" in result
        assert "ollama" in result
        assert "recommendations" in result

        files = list((tmp_path / "reports").glob("storage-*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["status"] == result["status"]

    def test_report_keys_complete(self, tmp_path):
        result = _run_storage_patched(tmp_path)

        expected_keys = {
            "timestamp",
            "vector_db",
            "ingestion",
            "disk",
            "ollama",
            "recommendations",
            "status",
        }
        assert set(result.keys()) == expected_keys

    def test_healthy_when_all_nominal(self, tmp_path):
        result = _run_storage_patched(tmp_path)
        assert result["status"] == "healthy"
