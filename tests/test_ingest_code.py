"""Tests for the Python code ingestion module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai.rag.constants import MAX_BYTES_PER_DOC, MAX_DOCS_PER_RUN
from ai.rag.ingest_code import (
    _EXCLUDE_DIRS,
    chunk_python_file,
    discover_python_files,
    ingest_files,
)


# ── Helpers ──

def _write_py(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _big_py(tmp_path: Path, name: str) -> Path:
    """Create a .py file just over the per-doc size cap."""
    content = "# filler\n" + ("x = 1\n" * ((MAX_BYTES_PER_DOC // 6) + 1))
    p = tmp_path / name
    p.write_bytes(content.encode()[:MAX_BYTES_PER_DOC + 1])
    return p


@pytest.fixture()
def patched_deps():
    """Patch embedding and LanceDB so ingest_files runs without GPU/DB."""
    mock_store = MagicMock()
    mock_store.add_code_chunks.return_value = 1

    with (
        patch("ai.rag.embedder.embed_texts", return_value=[[0.0] * 768]),
        patch("ai.rag.embedder.select_provider", return_value="ollama"),
        patch("ai.rag.store.get_store", return_value=mock_store),
        patch("ai.rag.ingest_code._save_state"),
        patch("ai.rag.ingest_code._load_state", return_value={}),
    ):
        yield mock_store


# ── File discovery ──

class TestDiscoverPythonFiles:
    def test_finds_py_files(self, tmp_path):
        _write_py(tmp_path, "a.py", "x = 1")
        _write_py(tmp_path, "b.py", "y = 2")
        (tmp_path / "notes.txt").write_text("ignore me")

        found = discover_python_files(tmp_path)
        names = {p.name for p in found}
        assert names == {"a.py", "b.py"}

    def test_excludes_venv(self, tmp_path):
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        _write_py(venv, "hidden.py", "x = 1")
        _write_py(tmp_path, "visible.py", "y = 2")

        found = discover_python_files(tmp_path)
        names = {p.name for p in found}
        assert "hidden.py" not in names
        assert "visible.py" in names

    def test_excludes_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        _write_py(cache, "cached.py", "x = 1")
        _write_py(tmp_path, "real.py", "y = 2")

        found = discover_python_files(tmp_path)
        names = {p.name for p in found}
        assert "cached.py" not in names
        assert "real.py" in names

    def test_exclude_dirs_constant_covers_expected_dirs(self):
        for d in (".venv", "__pycache__", ".git", "node_modules"):
            assert d in _EXCLUDE_DIRS

    def test_returns_sorted(self, tmp_path):
        for name in ("z.py", "a.py", "m.py"):
            _write_py(tmp_path, name, "x = 1")
        found = discover_python_files(tmp_path)
        assert found == sorted(found)


# ── Code chunking ──

class TestChunkPythonFile:
    def test_module_with_no_defs(self):
        src = "X = 1\nY = 2\n"
        chunks = chunk_python_file(src, "mod.py", "/repo")
        assert len(chunks) == 1
        assert chunks[0]["symbol_name"] == "__module__"
        assert chunks[0]["line_start"] == 1
        assert "relative_path" in chunks[0]
        assert chunks[0]["relative_path"] == "mod.py"
        assert chunks[0]["language"] == "python"

    def test_splits_on_functions(self):
        src = "import os\n\ndef foo():\n    pass\n\ndef bar():\n    return 1\n"
        chunks = chunk_python_file(src, "f.py", "/repo")
        names = [c["symbol_name"] for c in chunks]
        assert "foo" in names
        assert "bar" in names

    def test_splits_on_class(self):
        src = "class Foo:\n    pass\n\nclass Bar:\n    pass\n"
        chunks = chunk_python_file(src, "c.py", "/repo")
        names = [c["symbol_name"] for c in chunks]
        assert "Foo" in names
        assert "Bar" in names

    def test_header_prepended_to_chunks(self):
        src = "import os\n\ndef myfunc():\n    pass\n"
        chunks = chunk_python_file(src, "h.py", "/repo")
        func_chunk = next(c for c in chunks if c["symbol_name"] == "myfunc")
        assert "import os" in func_chunk["content"]

    def test_line_numbers_are_1_indexed(self):
        src = "import os\n\ndef foo():\n    pass\n"
        chunks = chunk_python_file(src, "ln.py", "/repo")
        foo = next(c for c in chunks if c["symbol_name"] == "foo")
        assert foo["line_start"] == 3  # 'def foo():' is line 3

    def test_oversized_chunk_is_truncated(self):
        # Build a function with many words
        big_body = "def big():\n" + "    # " + " ".join(f"word{i}" for i in range(2000)) + "\n"
        chunks = chunk_python_file(big_body, "big.py", "/repo")
        assert chunks[0]["content"].endswith("...[truncated]")

    def test_all_chunks_have_required_metadata_keys(self):
        src = "def f():\n    pass\n"
        chunks = chunk_python_file(src, "meta.py", "/repo")
        required = {"relative_path", "repo_root", "language", "symbol_name",
                    "line_start", "line_end", "content", "id"}
        for chunk in chunks:
            assert required <= set(chunk.keys())

    def test_indented_methods_not_split(self):
        src = "class Foo:\n    def method(self):\n        pass\n"
        chunks = chunk_python_file(src, "nested.py", "/repo")
        # Only one top-level symbol: Foo
        names = [c["symbol_name"] for c in chunks]
        assert names == ["Foo"]
        assert "method" not in names


# ── Ingestion ──

class TestIngestFiles:
    def test_processes_py_file(self, tmp_path, patched_deps):
        f = _write_py(tmp_path, "app.py", "def hello():\n    pass\n")
        result = ingest_files([f], tmp_path, force=True)
        assert result["processed"] == 1

    def test_oversized_file_skipped(self, tmp_path, patched_deps, caplog):
        import logging
        big = _big_py(tmp_path, "big.py")
        small = _write_py(tmp_path, "small.py", "x = 1\n")

        with caplog.at_level(logging.WARNING):
            result = ingest_files([big, small], tmp_path, force=True)

        assert result["skipped_size"] == 1
        assert result["processed"] == 1
        assert "big.py" in caplog.text

    def test_unchanged_file_skipped_by_mtime(self, tmp_path):
        f = _write_py(tmp_path, "a.py", "x = 1\n")
        mtime = f.stat().st_mtime
        rel = str(f.relative_to(tmp_path))
        state = {rel: mtime}

        mock_store = MagicMock()
        with (
            patch("ai.rag.embedder.embed_texts", return_value=[[0.0] * 768]),
            patch("ai.rag.embedder.select_provider", return_value="ollama"),
            patch("ai.rag.store.get_store", return_value=mock_store),
            patch("ai.rag.ingest_code._save_state"),
            patch("ai.rag.ingest_code._load_state", return_value=state),
        ):
            result = ingest_files([f], tmp_path, force=False)

        assert result["skipped_unchanged"] == 1
        assert result["processed"] == 0

    def test_doc_count_cap(self, tmp_path, patched_deps):
        files = [_write_py(tmp_path, f"f{i:04d}.py", "x = 1\n")
                 for i in range(MAX_DOCS_PER_RUN + 3)]
        result = ingest_files(files, tmp_path, force=True)
        assert result["processed"] == MAX_DOCS_PER_RUN
        assert result["skipped_deferred"] == 3

    def test_summary_dict_keys(self, tmp_path, patched_deps):
        f = _write_py(tmp_path, "a.py", "x = 1\n")
        result = ingest_files([f], tmp_path, force=True)
        assert set(result.keys()) == {
            "processed", "skipped_unchanged", "skipped_size",
            "skipped_deferred", "total_chunks",
        }

    def test_non_py_files_ignored(self, tmp_path, patched_deps):
        txt = tmp_path / "notes.txt"
        txt.write_text("hello")
        result = ingest_files([txt], tmp_path, force=True)
        assert result["processed"] == 0
        assert result["skipped_size"] == 0
        assert result["skipped_unchanged"] == 0
        assert result["skipped_deferred"] == 0
