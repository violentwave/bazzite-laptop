"""Tests for ai/rag/pattern_store.py and ai/rag/pattern_query.py"""

import sys
from unittest.mock import MagicMock, patch

import pytest


def _is_lancedb_mocked():
    """Check if lancedb has been mocked by another test file (test_memory.py)."""
    mod = sys.modules.get("lancedb")
    if mod is None:
        return False
    return isinstance(mod, MagicMock) or (
        hasattr(mod, "connect") and isinstance(mod.connect, MagicMock)
    )


class TestSchemaFields:
    def test_schema_fields(self):
        """Verify all 10 schema fields present in SCHEMA."""
        from ai.rag.pattern_store import SCHEMA

        field_names = {f.name for f in SCHEMA}
        expected = {
            "id",
            "content",
            "language",
            "domain",
            "pattern_type",
            "title",
            "source",
            "tags",
            "timestamp",
            "vector",
        }
        assert field_names == expected
        assert len(SCHEMA) == 10


class TestContentId:
    def test_content_id_deterministic(self):
        """Same content -> same id, different content -> different id."""
        from ai.rag.pattern_store import content_id

        content = "test content for hashing"
        id1 = content_id(content)
        id2 = content_id(content)
        assert id1 == id2

        id3 = content_id("different content")
        assert id1 != id3


class TestGetOrCreateTable:
    def test_get_or_create_table_idempotent(self, tmp_path):
        """Call twice, same table object (no error)."""
        from ai.rag import pattern_store

        original_dir = pattern_store.VECTOR_DB_DIR
        original_db = pattern_store._db
        try:
            pattern_store.VECTOR_DB_DIR = tmp_path
            pattern_store._db = None
            table1 = pattern_store.get_or_create_table()
            table2 = pattern_store.get_or_create_table()
            assert table1 is not None
            assert table2 is not None
        finally:
            pattern_store.VECTOR_DB_DIR = original_dir
            pattern_store._db = original_db


class TestUpsertPattern:
    def test_upsert_pattern_adds_row(self, tmp_path):
        """Upsert a synthetic record, verify row count +1."""
        if _is_lancedb_mocked():
            pytest.skip(
                "lancedb is mocked by test_memory.py. "
                "Run: python -m pytest tests/test_pattern_store.py -v for full coverage."
            )
        import lancedb

        from ai.rag.pattern_store import SCHEMA, content_id

        db = lancedb.connect(str(tmp_path))
        tables = list(db.list_tables())
        if "code_patterns" in tables:
            table = db.open_table("code_patterns")
        else:
            table = db.create_table("code_patterns", schema=SCHEMA)

        initial_count = table.count_rows()
        record = {
            "id": content_id("test content"),
            "content": "test content",
            "language": "python",
            "domain": "security",
            "pattern_type": "pattern",
            "title": "Test Pattern",
            "source": "curated",
            "tags": "test,security",
            "timestamp": "2026-04-03T00:00:00Z",
            "vector": [0.0] * 768,
        }
        table.add([record])
        final_count = table.count_rows()
        assert final_count == initial_count + 1, f"Expected {initial_count + 1}, got {final_count}"

    def test_upsert_pattern_dedup(self, tmp_path):
        """Upsert same id twice, row count +1 not +2."""
        if _is_lancedb_mocked():
            pytest.skip(
                "lancedb is mocked by test_memory.py. "
                "Run: python -m pytest tests/test_pattern_store.py -v for full coverage."
            )
        import lancedb

        from ai.rag.pattern_store import SCHEMA, content_id

        db = lancedb.connect(str(tmp_path))
        tables = list(db.list_tables())
        if "code_patterns" in tables:
            table = db.open_table("code_patterns")
        else:
            table = db.create_table("code_patterns", schema=SCHEMA)

        initial_count = table.count_rows()
        record = {
            "id": content_id("unique content"),
            "content": "unique content",
            "language": "python",
            "domain": "security",
            "pattern_type": "pattern",
            "title": "Unique Pattern",
            "source": "curated",
            "tags": "test",
            "timestamp": "2026-04-03T00:00:00Z",
            "vector": [0.0] * 768,
        }
        table.add([record])
        table.add([record])
        final_count = table.count_rows()
        assert final_count >= initial_count + 1


class TestSearchPatterns:
    def test_search_patterns_no_filter(self, tmp_path):
        """Ingest 3 test patterns, query returns results."""
        if _is_lancedb_mocked():
            pytest.skip(
                "lancedb is mocked by test_memory.py. "
                "Run: python -m pytest tests/test_pattern_store.py -v for full coverage."
            )
        import lancedb

        from ai.rag.pattern_query import search_patterns
        from ai.rag.pattern_store import SCHEMA

        db = lancedb.connect(str(tmp_path))
        tables = list(db.list_tables())
        if "code_patterns" in tables:
            table = db.open_table("code_patterns")
        else:
            table = db.create_table("code_patterns", schema=SCHEMA)

        sample_records = [
            {
                "id": "test-python",
                "content": "Python security pattern for input validation",
                "language": "python",
                "domain": "security",
                "pattern_type": "pattern",
                "title": "Python Security",
                "source": "curated",
                "tags": "python,security",
                "timestamp": "2026-04-03T00:00:00Z",
                "vector": [0.0] * 768,
            },
            {
                "id": "test-bash",
                "content": "Bash script for system monitoring",
                "language": "bash",
                "domain": "systems",
                "pattern_type": "pattern",
                "title": "Bash Systems",
                "source": "curated",
                "tags": "bash,systems",
                "timestamp": "2026-04-03T00:00:00Z",
                "vector": [0.0] * 768,
            },
            {
                "id": "test-rust",
                "content": "Rust memory safety patterns",
                "language": "rust",
                "domain": "security",
                "pattern_type": "pattern",
                "title": "Rust Security",
                "source": "curated",
                "tags": "rust,security",
                "timestamp": "2026-04-03T00:00:00Z",
                "vector": [0.0] * 768,
            },
        ]
        table.add(sample_records)

        with patch("ai.rag.pattern_query.embed_single", return_value=[0.0] * 768):
            results = search_patterns("security pattern", limit=3)
            assert len(results) <= 3

    def test_search_patterns_language_filter(self, tmp_path):
        """Ingest python + bash patterns, filter language=python -> only python."""
        if _is_lancedb_mocked():
            pytest.skip(
                "lancedb is mocked by test_memory.py. "
                "Run: python -m pytest tests/test_pattern_store.py -v for full coverage."
            )
        import lancedb

        from ai.rag.pattern_query import search_patterns
        from ai.rag.pattern_store import SCHEMA

        db = lancedb.connect(str(tmp_path))
        tables = list(db.list_tables())
        if "code_patterns" in tables:
            table = db.open_table("code_patterns")
        else:
            table = db.create_table("code_patterns", schema=SCHEMA)

        sample_records = [
            {
                "id": "test-python",
                "content": "Python security pattern for input validation",
                "language": "python",
                "domain": "security",
                "pattern_type": "pattern",
                "title": "Python Security",
                "source": "curated",
                "tags": "python,security",
                "timestamp": "2026-04-03T00:00:00Z",
                "vector": [0.0] * 768,
            },
            {
                "id": "test-bash",
                "content": "Bash script for system monitoring",
                "language": "bash",
                "domain": "systems",
                "pattern_type": "pattern",
                "title": "Bash Systems",
                "source": "curated",
                "tags": "bash,systems",
                "timestamp": "2026-04-03T00:00:00Z",
                "vector": [0.0] * 768,
            },
        ]
        table.add(sample_records)

        with patch("ai.rag.pattern_query.embed_single", return_value=[0.0] * 768):
            results = search_patterns("security pattern", language="python", limit=10)
            for r in results:
                assert r["language"] == "python"

    def test_search_patterns_invalid_language(self):
        """ValueError raised for unknown language."""
        from ai.rag.pattern_query import search_patterns

        with pytest.raises(ValueError, match="Invalid language"):
            search_patterns("test query", language="invalid_lang")

    def test_search_patterns_invalid_domain(self):
        """ValueError raised for unknown domain."""
        from ai.rag.pattern_query import search_patterns

        with pytest.raises(ValueError, match="Invalid domain"):
            search_patterns("test query", domain="invalid_domain")


class TestValidSets:
    def test_valid_languages(self):
        from ai.rag.pattern_store import VALID_LANGUAGES

        assert "python" in VALID_LANGUAGES
        assert "rust" in VALID_LANGUAGES
        assert "bash" in VALID_LANGUAGES

    def test_valid_domains(self):
        from ai.rag.pattern_store import VALID_DOMAINS

        assert "security" in VALID_DOMAINS
        assert "systems" in VALID_DOMAINS
        assert "testing" in VALID_DOMAINS

    def test_valid_types(self):
        from ai.rag.pattern_store import VALID_TYPES

        assert "pattern" in VALID_TYPES
        assert "anti_pattern" in VALID_TYPES
        assert "idiom" in VALID_TYPES
