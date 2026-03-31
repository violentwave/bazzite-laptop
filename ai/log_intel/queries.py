"""Query layer for the log intelligence pipeline.

Provides read-only functions called by MCP bridge tools.
All functions are defensive: missing tables return empty results.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import lancedb

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger("ai.log_intel.queries")

_INGEST_STATE = VECTOR_DB_DIR / ".ingest-state.json"


def _connect(db_path: str | None = None) -> lancedb.DBConnection:
    """Open a LanceDB connection.

    *db_path* overrides the default ``VECTOR_DB_DIR``.
    """
    return lancedb.connect(db_path or str(VECTOR_DB_DIR))


def _table_exists(db: lancedb.DBConnection, name: str) -> bool:
    """Check whether a table exists in the database."""
    try:
        return name in db.list_tables()
    except Exception:
        return False


def health_trend(
    limit: int = 7,
    *,
    db_path: str | None = None,
) -> list[dict]:
    """Return last *limit* health snapshots with delta annotations.

    For each consecutive pair of records, compute deltas for numeric
    fields (gpu_temp_c, cpu_temp_c, disk_usage_pct, ram_used_gb).
    """
    db = _connect(db_path)
    if not _table_exists(db, "health_records"):
        return []

    table = db.open_table("health_records")
    try:
        rows = table.search().limit(limit).to_list()
    except Exception:
        return []
    if not rows:
        return []

    # Sort newest-first
    rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    records = [{k: v for k, v in r.items() if k != "vector"} for r in rows]

    # Compute deltas (records are newest-first)
    delta_fields = ["gpu_temp_c", "cpu_temp_c", "disk_usage_pct", "ram_used_gb"]
    for i in range(len(records) - 1):
        newer = records[i]
        older = records[i + 1]
        deltas = {}
        for field in delta_fields:
            if field in newer and field in older:
                try:
                    diff = float(newer[field]) - float(older[field])
                    deltas[field] = round(diff, 2)
                except (TypeError, ValueError):
                    pass
        newer["_deltas"] = deltas

    return records


def scan_history(
    limit: int = 10,
    *,
    db_path: str | None = None,
) -> list[dict]:
    """Return last *limit* ClamAV scan records, newest first."""
    db = _connect(db_path)
    if not _table_exists(db, "scan_records"):
        return []

    table = db.open_table("scan_records")
    try:
        rows = table.search().limit(limit).to_list()
    except Exception:
        return []
    if not rows:
        return []

    rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return [{k: v for k, v in r.items() if k != "vector"} for r in rows]


def get_anomalies(*, db_path: str | None = None) -> list[dict]:
    """Return all unacknowledged anomaly records."""
    db = _connect(db_path)
    if not _table_exists(db, "anomalies"):
        return []

    table = db.open_table("anomalies")
    df = table.to_pandas()
    if df.empty:
        return []

    df = df[df["acknowledged"] == False]  # noqa: E712 — pandas bool filter
    return df.to_dict("records")


def search_logs(
    query: str,
    limit: int = 5,
    *,
    db_path: str | None = None,
) -> list[dict]:
    """Semantic search across health and scan log tables.

    Embeds *query* via Ollama nomic-embed-text, then searches each table
    and merges results by distance score.
    """
    from ai.rag.embedder import embed_texts  # noqa: PLC0415

    try:
        vectors = embed_texts([query])
    except (RuntimeError, Exception):
        return []

    if not vectors or not vectors[0]:
        return []

    return _search_logs_with_vector(vectors[0], limit=limit, db_path=db_path)


def _search_logs_with_vector(
    query_vector: list[float],
    limit: int = 5,
    *,
    db_path: str | None = None,
) -> list[dict]:
    """Search health and scan tables using a pre-computed embedding vector."""
    db = _connect(db_path)
    results: list[dict] = []

    for table_name in ("health_records", "scan_records"):
        if not _table_exists(db, table_name):
            continue
        try:
            table = db.open_table(table_name)
            hits = table.search(query_vector).limit(limit).to_list()
            for hit in hits:
                hit.pop("vector", None)
                hit["_source_table"] = table_name
                results.append(hit)
        except Exception as exc:
            logger.warning("Search failed on %s: %s", table_name, exc)

    # Sort by distance (lower is better); LanceDB returns _distance
    results.sort(key=lambda r: r.get("_distance", float("inf")))
    return results[:limit]


def pipeline_stats(*, db_path: str | None = None) -> dict:
    """Return record counts per table, last ingestion time, and DB size."""
    db = _connect(db_path)
    tables = db.list_tables() if hasattr(db, "list_tables") else []
    table_names = ("health_records", "scan_records", "sig_updates", "anomalies")
    counts: dict[str, int] = {}

    for name in table_names:
        if name in tables:
            try:
                table = db.open_table(name)
                counts[name] = table.count_rows()
            except Exception:
                counts[name] = 0
        else:
            counts[name] = 0

    # Last ingestion time from state file
    last_ingestion = None
    if _INGEST_STATE.exists():
        try:
            state = json.loads(_INGEST_STATE.read_text())
            last_ingestion = state.get("last_run")
        except Exception:
            logger.debug("Failed to read ingest state: %s", _INGEST_STATE)

    # DB directory size on disk
    db_size_bytes = 0
    db_dir = Path(db_path) if db_path else Path(VECTOR_DB_DIR)
    if db_dir.is_dir():
        db_size_bytes = sum(f.stat().st_size for f in db_dir.rglob("*") if f.is_file())

    return {
        "health_records": counts.get("health_records", 0),
        "scan_records": counts.get("scan_records", 0),
        "anomalies": counts.get("anomalies", 0),
        "sig_updates": counts.get("sig_updates", 0),
        "table_counts": counts,
        "last_ingestion": last_ingestion,
        "db_size_bytes": db_size_bytes,
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
    }
