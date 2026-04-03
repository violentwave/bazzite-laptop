"""LanceDB vector store for security logs and threat intelligence.

Tables:
    security_logs -- Chunked scan/health log sections with embeddings
    threat_intel  -- Enriched threat reports with embeddings

All table operations use LanceDB's native Python API. The store is
initialized lazily on first access to avoid import-time side effects.
"""

import logging
from pathlib import Path
from uuid import uuid4

from ai.config import APP_NAME, VECTOR_DB_DIR
from ai.rag.constants import CODE_TABLE, EMBEDDING_DIM

logger = logging.getLogger(APP_NAME)


def _get_schemas() -> dict:
    """Lazy-load pyarrow schemas to avoid import-time segfault in Flatpak sandbox."""
    import pyarrow as pa  # noqa: PLC0415

    security_log_schema = pa.schema(
        [
            pa.field("id", pa.utf8()),
            pa.field("source_file", pa.utf8()),
            pa.field("section", pa.utf8()),
            pa.field("content", pa.utf8()),
            pa.field("log_type", pa.utf8()),
            pa.field("timestamp", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        ]
    )

    threat_intel_schema = pa.schema(
        [
            pa.field("id", pa.utf8()),
            pa.field("hash", pa.utf8()),
            pa.field("source", pa.utf8()),
            pa.field("family", pa.utf8()),
            pa.field("risk_level", pa.utf8()),
            pa.field("content", pa.utf8()),
            pa.field("timestamp", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        ]
    )

    docs_schema = pa.schema(
        [
            pa.field("id", pa.utf8()),
            pa.field("source_file", pa.utf8()),
            pa.field("section_title", pa.utf8()),
            pa.field("doc_type", pa.utf8()),
            pa.field("content", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        ]
    )

    code_files_schema = pa.schema(
        [
            pa.field("id", pa.utf8()),
            pa.field("relative_path", pa.utf8()),
            pa.field("repo_root", pa.utf8()),
            pa.field("language", pa.utf8()),
            pa.field("symbol_name", pa.utf8()),
            pa.field("line_start", pa.int32()),
            pa.field("line_end", pa.int32()),
            pa.field("content", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        ]
    )

    return {
        "security_logs": security_log_schema,
        "threat_intel": threat_intel_schema,
        "docs": docs_schema,
        CODE_TABLE: code_files_schema,
    }


# ── Store ──


class VectorStore:
    """Manages LanceDB tables for security data.

    Args:
        db_path: Path to the LanceDB directory. Defaults to VECTOR_DB_DIR.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or VECTOR_DB_DIR
        self._db = None

    def _connect(self):
        """Return a lazy-initialized LanceDB connection, creating the dir if needed."""
        if self._db is not None:
            return self._db
        try:
            import lancedb  # noqa: PLC0415

            self._db_path.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self._db_path))
        except (OSError, PermissionError) as e:
            logger.error("Failed to connect to LanceDB at %s: %s", self._db_path, e)
            raise
        return self._db

    def _ensure_table(self, name: str, schema):
        """Open a table by name, creating it from schema if it does not exist."""
        db = self._connect()
        try:
            _r = db.list_tables()
            existing = _r.tables if hasattr(_r, "tables") else list(_r)
            if name in existing:
                table = db.open_table(name)
            else:
                try:
                    table = db.create_table(name, schema=schema)
                except Exception as e:
                    if "already exists" in str(e).lower():
                        table = db.open_table(name)
                    else:
                        raise

            # Add FTS index for text columns after table creation/opening
            self._ensure_fts_index(table, name)
            return table
        except Exception:
            logger.exception("Failed to ensure table '%s'", name)
            raise

    def _ensure_fts_index(self, table, table_name: str) -> None:
        """Create FTS index if not already present. Silently skip on error."""
        try:
            # Define text columns to index per table
            text_columns = {
                "security_logs": "content",
                "docs": "content",
                "health_records": "summary",
                "scan_records": "summary",
                "threat_intel": "content",
                "conversations": "query",
                CODE_TABLE: "content",
            }

            column = text_columns.get(table_name)
            if column:
                try:
                    table.create_fts_index(column, replace=True)
                except Exception as e:
                    logger.debug("Could not create FTS index for %s.%s: %s", table_name, column, e)
        except Exception:  # noqa: S110
            pass

    def add_log_chunks(self, chunks: list[dict]) -> int:
        """Add embedded log chunks to security_logs table. Returns count added."""
        if not chunks:
            return 0
        try:
            for chunk in chunks:
                chunk.setdefault("id", str(uuid4()))
            schemas = _get_schemas()
            table = self._ensure_table("security_logs", schemas["security_logs"])
            table.add(chunks)
            return len(chunks)
        except Exception:
            logger.exception("Failed to add %d log chunks", len(chunks))
            return 0

    def add_doc_chunks(self, chunks: list[dict]) -> int:
        """Add embedded doc chunks to docs table. Returns count added."""
        if not chunks:
            return 0
        try:
            for chunk in chunks:
                chunk.setdefault("id", str(uuid4()))
                vec = chunk.get("vector", [])
                if not isinstance(vec, list):
                    raise ValueError(f"Vector must be a list, got {type(vec)}")
                if len(vec) != EMBEDDING_DIM:
                    raise ValueError(
                        f"Vector dimension {len(vec)} != expected {EMBEDDING_DIM}. "
                        "Embedding model mismatch — check embedder provider."
                    )
            schemas = _get_schemas()
            table = self._ensure_table("docs", schemas["docs"])
            table.add(chunks)
            return len(chunks)
        except Exception:
            logger.exception("Failed to add %d doc chunks", len(chunks))
            return 0

    def add_code_chunks(self, chunks: list[dict]) -> int:
        """Add embedded code chunks to code_files table. Returns count added."""
        if not chunks:
            return 0
        try:
            for chunk in chunks:
                chunk.setdefault("id", str(uuid4()))
                vec = chunk.get("vector", [])
                if not isinstance(vec, list):
                    raise ValueError(f"Vector must be a list, got {type(vec)}")
                if len(vec) != EMBEDDING_DIM:
                    raise ValueError(
                        f"Vector dimension {len(vec)} != expected {EMBEDDING_DIM}. "
                        "Embedding model mismatch — check embedder provider."
                    )
            schemas = _get_schemas()
            table = self._ensure_table(CODE_TABLE, schemas[CODE_TABLE])
            table.add(chunks)
            return len(chunks)
        except Exception:
            logger.exception("Failed to add %d code chunks", len(chunks))
            return 0

    def search_code(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        """Search code_files by vector similarity. Returns list of result dicts."""
        schemas = _get_schemas()
        return self._search(CODE_TABLE, schemas[CODE_TABLE], query_vector, limit)

    def add_threat_reports(self, reports: list[dict]) -> int:
        """Add embedded threat reports to threat_intel table. Returns count added."""
        if not reports:
            return 0
        try:
            for report in reports:
                report.setdefault("id", str(uuid4()))
            schemas = _get_schemas()
            table = self._ensure_table("threat_intel", schemas["threat_intel"])
            table.add(reports)
            return len(reports)
        except Exception:
            logger.exception("Failed to add %d threat reports", len(reports))
            return 0

    def search_logs(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        """Search security_logs by vector similarity. Returns list of result dicts."""
        schemas = _get_schemas()
        return self._search("security_logs", schemas["security_logs"], query_vector, limit)

    def search_docs(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        """Search docs by vector similarity. Returns list of result dicts."""
        schemas = _get_schemas()
        return self._search("docs", schemas["docs"], query_vector, limit)

    def search_threats(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        """Search threat_intel by vector similarity. Returns list of result dicts."""
        schemas = _get_schemas()
        return self._search("threat_intel", schemas["threat_intel"], query_vector, limit)

    def _search(
        self,
        table_name: str,
        schema,
        query_vector: list[float],
        limit: int,
    ) -> list[dict]:
        """Run a vector similarity search on the given table."""
        try:
            table = self._ensure_table(table_name, schema)
            results = table.search(query_vector).limit(limit).to_list()
            return results
        except Exception:
            logger.exception("Vector search failed on table '%s'", table_name)
            return []

    def count(self, table_name: str) -> int:
        """Return row count for a table. Returns 0 if table doesn't exist."""
        try:
            db = self._connect()
            if table_name not in db.list_tables():
                return 0
            table = db.open_table(table_name)
            return table.count_rows()
        except Exception:
            logger.exception("Failed to count rows in table '%s'", table_name)
            return 0


# ── Singleton ──

_store_instance: VectorStore | None = None


def get_store(db_path: Path | None = None) -> VectorStore:
    """Get or create the singleton VectorStore instance."""
    global _store_instance  # noqa: PLW0603
    if _store_instance is None:
        _store_instance = VectorStore(db_path=db_path)
    return _store_instance
