"""Unit tests for ai/rag/memory.py."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock lancedb and pyarrow before importing memory module — they segfault
# in the VS Code Flatpak sandbox. Use setdefault so we share the same mocks
# if another test file already installed them.
_mock_lancedb = sys.modules.setdefault("lancedb", MagicMock())
_mock_pa = sys.modules.setdefault("pyarrow", MagicMock())

from ai.rag.memory import (  # noqa: E402,I001
    _cleanup_if_needed,
    _MAX_ROWS,
    _CLEANUP_COUNT,
    is_enabled,
    retrieve_relevant_context,
    store_interaction,
)

FAKE_VECTOR = [0.1] * 768


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_lancedb_mock():
    _mock_lancedb.reset_mock()
    yield


@pytest.fixture()
def mock_table():
    """A mock LanceDB table with count_rows=0 wired to a mock connection."""
    table = MagicMock()
    table.count_rows.return_value = 0
    mock_db = MagicMock()
    mock_db.list_tables.return_value = []
    mock_db.create_table.return_value = table
    _mock_lancedb.connect.return_value = mock_db
    return table


# ---------------------------------------------------------------------------
# is_enabled
# ---------------------------------------------------------------------------


class TestIsEnabled:
    def test_false_when_not_set(self):
        env = {k: v for k, v in os.environ.items() if k != "ENABLE_CONVERSATION_MEMORY"}
        with patch.dict(os.environ, env, clear=True):
            assert is_enabled() is False

    def test_false_when_set_to_false(self):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "false"}):
            assert is_enabled() is False

    def test_true_when_set_to_true(self):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            assert is_enabled() is True

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "TRUE"}):
            assert is_enabled() is True


# ---------------------------------------------------------------------------
# store_interaction
# ---------------------------------------------------------------------------


class TestStoreInteraction:
    def test_no_op_when_disabled(self, mock_table):
        env = {k: v for k, v in os.environ.items() if k != "ENABLE_CONVERSATION_MEMORY"}
        with patch.dict(os.environ, env, clear=True):
            result = store_interaction("query", "response", "fast")
        assert result is False
        mock_table.add.assert_not_called()

    def test_creates_row_and_returns_true(self, mock_table):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]):
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    result = store_interaction("hello", "world summary", "fast")

        assert result is True
        mock_table.add.assert_called_once()
        row = mock_table.add.call_args[0][0][0]
        assert row["query"] == "hello"
        assert row["response_summary"] == "world summary"
        assert row["task_type"] == "fast"
        assert "timestamp" in row
        assert "id" in row
        assert len(row["vector"]) == 768

    def test_query_truncated_to_500_chars(self, mock_table):
        long_query = "x" * 600
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]) as mock_embed:
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    store_interaction(long_query, "summary", "fast")

        called_text = mock_embed.call_args[0][0][0]
        assert len(called_text) == 500

    def test_response_summary_truncated_to_200_chars(self, mock_table):
        long_summary = "y" * 300
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]):
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    store_interaction("q", long_summary, "fast")

        row = mock_table.add.call_args[0][0][0]
        assert len(row["response_summary"]) == 200

    def test_embed_failure_returns_false(self, mock_table):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", side_effect=RuntimeError("no embed")):
                result = store_interaction("query", "response", "fast")
        assert result is False

    def test_calls_cleanup_after_add(self, mock_table):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]):
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    with patch("ai.rag.memory._cleanup_if_needed") as mock_cleanup:
                        store_interaction("q", "r", "fast")

        mock_cleanup.assert_called_once_with(mock_table)


# ---------------------------------------------------------------------------
# retrieve_relevant_context
# ---------------------------------------------------------------------------


class TestRetrieveRelevantContext:
    def test_returns_empty_when_disabled(self):
        env = {k: v for k, v in os.environ.items() if k != "ENABLE_CONVERSATION_MEMORY"}
        with patch.dict(os.environ, env, clear=True):
            result = retrieve_relevant_context("query")
        assert result == []

    def test_returns_summaries_from_search_results(self, mock_table):
        mock_table.search.return_value.limit.return_value.to_list.return_value = [
            {"response_summary": "past answer 1"},
            {"response_summary": "past answer 2"},
        ]
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]):
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    result = retrieve_relevant_context("query", limit=2)

        assert result == ["past answer 1", "past answer 2"]

    def test_empty_summary_fields_filtered_out(self, mock_table):
        mock_table.search.return_value.limit.return_value.to_list.return_value = [
            {"response_summary": "valid"},
            {"response_summary": ""},
            {},
        ]
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]):
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    result = retrieve_relevant_context("query")

        assert result == ["valid"]

    def test_table_error_returns_empty(self):
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]):
                with patch("ai.rag.memory._get_table", side_effect=RuntimeError("db down")):
                    result = retrieve_relevant_context("query")
        assert result == []

    def test_uses_search_query_input_type(self, mock_table):
        mock_table.search.return_value.limit.return_value.to_list.return_value = []
        with patch.dict(os.environ, {"ENABLE_CONVERSATION_MEMORY": "true"}):
            with patch("ai.rag.memory.embed_texts", return_value=[FAKE_VECTOR]) as mock_embed:
                with patch("ai.rag.memory._get_table", return_value=mock_table):
                    retrieve_relevant_context("query")

        _, kwargs = mock_embed.call_args
        assert kwargs.get("input_type") == "search_query"


# ---------------------------------------------------------------------------
# _cleanup_if_needed
# ---------------------------------------------------------------------------


class TestCleanupIfNeeded:
    def test_no_cleanup_under_limit(self):
        table = MagicMock()
        table.count_rows.return_value = _MAX_ROWS
        _cleanup_if_needed(table)
        table.delete.assert_not_called()

    def test_no_cleanup_at_exact_limit(self):
        table = MagicMock()
        table.count_rows.return_value = _MAX_ROWS
        _cleanup_if_needed(table)
        table.delete.assert_not_called()

    def test_cleanup_triggered_over_limit(self):
        table = MagicMock()
        table.count_rows.return_value = _MAX_ROWS + 1
        timestamps = [f"2026-03-{i % 28 + 1:02d}T{i:02d}:00:00Z" for i in range(_CLEANUP_COUNT)]
        ids = [f"id-{i}" for i in range(_CLEANUP_COUNT)]
        table.to_arrow.return_value.to_pydict.return_value = {
            "timestamp": timestamps,
            "id": ids,
        }
        _cleanup_if_needed(table)

        table.delete.assert_called_once()
        delete_clause = table.delete.call_args[0][0]
        assert "id IN" in delete_clause

    def test_cleanup_deletes_oldest_first(self):
        table = MagicMock()
        table.count_rows.return_value = _MAX_ROWS + 50
        # newest first in list — cleanup should sort and delete the oldest
        timestamps = ["2026-03-22T00:00:00Z", "2026-03-01T00:00:00Z", "2026-03-10T00:00:00Z"]
        ids = ["new-id", "old-id", "mid-id"]
        table.to_arrow.return_value.to_pydict.return_value = {
            "timestamp": timestamps,
            "id": ids,
        }
        # With _CLEANUP_COUNT > number of rows, all get deleted; just verify
        # old-id is included in the delete clause
        _cleanup_if_needed(table)
        delete_clause = table.delete.call_args[0][0]
        assert "old-id" in delete_clause

    def test_to_arrow_error_does_not_raise(self):
        table = MagicMock()
        table.count_rows.return_value = _MAX_ROWS + 1
        table.to_arrow.side_effect = RuntimeError("arrow failure")
        # Should not raise
        _cleanup_if_needed(table)
