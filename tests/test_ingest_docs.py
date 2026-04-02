"""Tests for RAG document ingestion safety caps."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai.rag.constants import MAX_BYTES_PER_DOC, MAX_DOCS_PER_RUN, MAX_TOTAL_BYTES
from ai.rag.ingest_docs import ingest_files


def _make_md(tmp_path: Path, name: str, size_bytes: int) -> Path:
    """Create a .md file of the given byte size."""
    p = tmp_path / name
    # Fill with 'x ' repeated, prefixed with a ## header so chunking works
    content = f"## Section\n\n{'x ' * (size_bytes // 2)}"
    p.write_text(content[:size_bytes], encoding="utf-8")
    return p


@pytest.fixture()
def patched_deps():
    """Patch embedding and LanceDB so ingest_files runs without GPU/DB."""
    mock_store = MagicMock()
    mock_store.add_doc_chunks.return_value = 1

    with (
        patch("ai.rag.embedder.embed_texts", return_value=[[0.0] * 768]),
        patch("ai.rag.embedder.select_provider", return_value="ollama"),
        patch("ai.rag.store.get_store", return_value=mock_store),
        patch("ai.rag.ingest_docs._save_state"),
        patch("ai.rag.ingest_docs._load_state", return_value={}),
    ):
        yield mock_store


class TestFileSizeCap:
    def test_oversized_file_is_skipped(self, tmp_path, patched_deps, caplog):
        """Files larger than MAX_BYTES_PER_DOC are skipped with a warning."""
        import logging

        big = _make_md(tmp_path, "big.md", MAX_BYTES_PER_DOC + 1)
        small = _make_md(tmp_path, "small.md", 100)

        with caplog.at_level(logging.WARNING):
            result = ingest_files([big, small], force=True)

        assert result["skipped_size"] == 1
        assert result["processed"] == 1
        assert "big.md" in caplog.text
        assert "KB limit" in caplog.text

    def test_exactly_at_limit_is_allowed(self, tmp_path, patched_deps):
        """Files exactly at MAX_BYTES_PER_DOC are processed (not skipped)."""
        at_limit = _make_md(tmp_path, "atlimit.md", MAX_BYTES_PER_DOC)
        result = ingest_files([at_limit], force=True)
        assert result["skipped_size"] == 0
        assert result["processed"] == 1

    def test_summary_includes_skipped_size(self, tmp_path, patched_deps):
        """Return dict always contains skipped_size key."""
        f = _make_md(tmp_path, "a.md", 50)
        result = ingest_files([f], force=True)
        assert "skipped_size" in result


class TestDocCountCap:
    def test_stops_at_max_docs_per_run(self, tmp_path, patched_deps, caplog):
        """Processing stops after MAX_DOCS_PER_RUN files; rest are deferred."""
        import logging

        # Create MAX_DOCS_PER_RUN + 5 small files
        files = [_make_md(tmp_path, f"doc{i:04d}.md", 50) for i in range(MAX_DOCS_PER_RUN + 5)]

        with caplog.at_level(logging.INFO):
            result = ingest_files(files, force=True)

        assert result["processed"] == MAX_DOCS_PER_RUN
        assert result["skipped_deferred"] == 5
        assert "deferred" in caplog.text

    def test_deferred_count_in_summary(self, tmp_path, patched_deps):
        """skipped_deferred is always present in result."""
        f = _make_md(tmp_path, "a.md", 50)
        result = ingest_files([f], force=True)
        assert "skipped_deferred" in result


class TestTotalBytesCap:
    def test_stops_at_total_bytes_limit(self, tmp_path, patched_deps):
        """Processing stops once cumulative bytes would exceed MAX_TOTAL_BYTES."""
        # Files that together exceed the cap; each just under MAX_BYTES_PER_DOC
        chunk_size = MAX_BYTES_PER_DOC  # exactly at per-doc limit
        n_files = (MAX_TOTAL_BYTES // chunk_size) + 2  # enough to breach total cap

        files = [_make_md(tmp_path, f"doc{i:04d}.md", chunk_size) for i in range(n_files)]

        result = ingest_files(files, force=True)

        assert result["processed"] < n_files
        assert result["skipped_deferred"] > 0
        assert result["processed"] + result["skipped_deferred"] <= n_files


class TestSummaryDict:
    def test_all_expected_keys_present(self, tmp_path, patched_deps):
        """Return dict contains all required keys."""
        f = _make_md(tmp_path, "a.md", 50)
        result = ingest_files([f], force=True)

        assert set(result.keys()) == {
            "processed",
            "skipped_unchanged",
            "skipped_size",
            "skipped_deferred",
            "total_chunks",
        }

    def test_unchanged_files_counted(self, tmp_path):
        """Files with matching hash are counted in skipped_unchanged."""
        f = _make_md(tmp_path, "a.md", 50)
        from ai.rag.ingest_docs import _file_hash

        state = {str(f.resolve()): _file_hash(f)}

        mock_store = MagicMock()
        with (
            patch("ai.rag.embedder.embed_texts", return_value=[[0.0] * 768]),
            patch("ai.rag.embedder.select_provider", return_value="ollama"),
            patch("ai.rag.store.get_store", return_value=mock_store),
            patch("ai.rag.ingest_docs._save_state"),
            patch("ai.rag.ingest_docs._load_state", return_value=state),
        ):
            result = ingest_files([f], force=False)

        assert result["skipped_unchanged"] == 1
        assert result["processed"] == 0

    def test_non_md_files_not_counted(self, tmp_path, patched_deps):
        """Non-.md files generate a warning but don't affect any counter."""
        txt = tmp_path / "notes.txt"
        txt.write_text("hello")
        result = ingest_files([txt], force=True)
        assert result["processed"] == 0
        assert result["skipped_size"] == 0
        assert result["skipped_deferred"] == 0
        assert result["skipped_unchanged"] == 0


class TestSaveStateRetry:
    """Tests for _save_state I/O error retry logic."""

    def test_save_state_retries_on_io_error(self, tmp_path, monkeypatch):
        """_save_state should retry transient I/O errors."""
        import json
        import os

        from ai.rag.ingest_docs import _save_state

        # Save original before patching
        orig_rename = os.rename

        # Track call count
        call_count = 0

        def failing_rename(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Simulate Errno 5 (I/O error) on first attempts
                raise OSError(5, "Input/output error")
            # Succeed on second try
            return orig_rename(*args)

        # Use temp directory for state file
        test_state_file = tmp_path / ".test-doc-ingest-state.json"
        monkeypatch.setattr("ai.rag.ingest_docs._STATE_FILE", test_state_file)

        # Patch rename to fail then succeed
        monkeypatch.setattr(os, "rename", failing_rename)

        # Should succeed after retry (doesn't raise)
        _save_state({"file": "hash123"})

        # Should have retried at least once
        assert call_count >= 2

        # Verify file was written
        assert test_state_file.exists()
        data = json.loads(test_state_file.read_text())
        assert data == {"file": "hash123"}

    def test_save_state_succeeds_first_try(self, tmp_path, monkeypatch):
        """_save_state should work normally without retries on first success."""
        import json

        from ai.rag.ingest_docs import _save_state

        test_state_file = tmp_path / ".test-doc-ingest-state.json"
        monkeypatch.setattr("ai.rag.ingest_docs._STATE_FILE", test_state_file)

        _save_state({"test": "data"})

        assert test_state_file.exists()
        data = json.loads(test_state_file.read_text())
        assert data == {"test": "data"}
