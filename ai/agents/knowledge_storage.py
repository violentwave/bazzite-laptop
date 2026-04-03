"""Storage and knowledge base health agent for Bazzite.

Checks LanceDB health, ingestion freshness, disk usage, and Ollama status.
Generates hardcoded rule-based recommendations (no cloud LLM calls).
Writes a structured JSON report to ~/security/storage-reports/.

Includes automatic corruption detection and repair capabilities.

Usage:
    python -m ai.agents.knowledge_storage
    from ai.agents.knowledge_storage import run_storage_check
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from ai.config import APP_NAME, SECURITY_DIR, VECTOR_DB_DIR
from ai.rag.constants import EMBEDDING_DIM

logger = logging.getLogger(APP_NAME)

STEAM_MOUNT = Path("/var/mnt/ext-ssd")
STORAGE_REPORTS_DIR = SECURITY_DIR / "storage-reports"

_DOC_STATE_FILE = VECTOR_DB_DIR / ".doc-ingest-state.json"
_LOG_STATE_FILE = VECTOR_DB_DIR / ".ingest-state.json"

_OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
_EMBED_MODEL = "nomic-embed-text"

_MAX_BACKUPS = 3


# ── Collectors ─────────────────────────────────────────────────────────────────


def _check_lancedb() -> dict:
    """Connect to LanceDB, list tables, and count rows. Returns dict or error."""
    try:
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(VECTOR_DB_DIR))
        tables_result = db.list_tables()

        if hasattr(tables_result, "tables"):
            tables = list(tables_result.tables)
        elif isinstance(tables_result, (list, tuple)):
            tables = list(tables_result)
        else:
            tables = []

        row_counts: dict[str, int] = {}
        for name in tables:
            try:
                tbl = db.open_table(name)
                row_counts[name] = tbl.count_rows()
            except Exception as e:
                logger.debug("Could not count rows in table %s: %s", name, e)
                row_counts[name] = -1
        total = sum(v for v in row_counts.values() if v >= 0)
        return {"tables": row_counts, "total_rows": total, "error": None}
    except ImportError:
        return {"tables": {}, "total_rows": 0, "error": "lancedb not installed"}
    except Exception as e:
        logger.debug("LanceDB connect error: %s", e)
        return {"tables": {}, "total_rows": 0, "error": str(e)}


def _read_ingest_state(state_file: Path) -> dict:
    """Parse ingest state JSON and return {last_ingest, hours_ago}."""
    try:
        data = json.loads(state_file.read_text())

        # Try multiple timestamp keys in order of preference
        raw_ts = (
            data.get("last_ingest")
            or data.get("timestamp")
            or data.get("last_doc_ingest")
            or data.get("last_health_ingest")
            or data.get("last_scan_ingest")
        )

        if not raw_ts:
            # For doc state file which uses file->hash mapping, use file mtime
            # Find most recent file modification time from state
            if state_file.exists():
                mtime = state_file.stat().st_mtime
                dt = datetime.fromtimestamp(mtime, tz=UTC)
                hours_ago = round((datetime.now(UTC) - dt).total_seconds() / 3600, 1)
                return {"last_ingest": dt.isoformat(), "hours_ago": hours_ago}
            return {"last_ingest": None, "hours_ago": None}

        dt = datetime.fromisoformat(raw_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        hours_ago = round((datetime.now(UTC) - dt).total_seconds() / 3600, 1)
        return {"last_ingest": dt.isoformat(), "hours_ago": hours_ago}
    except FileNotFoundError:
        return {"last_ingest": None, "hours_ago": None}
    except Exception as e:
        logger.debug("Ingest state read error (%s): %s", state_file, e)
        return {"last_ingest": None, "hours_ago": None}


def _get_vector_db_size() -> tuple[int, str]:
    """Return (size_bytes, size_human) for VECTOR_DB_DIR using du -sb."""
    try:
        result = subprocess.run(
            ["du", "-sb", str(VECTOR_DB_DIR)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("\t", 1)
            size_bytes = int(parts[0])
            size_human = _human_bytes(size_bytes)
            return size_bytes, size_human
    except Exception as e:
        logger.debug("du error: %s", e)
    return 0, "unknown"


def _human_bytes(n: int) -> str:
    """Format bytes as a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} TB"


def _collect_disk() -> dict:
    """Return disk usage for /home and Steam drive."""
    targets = ["/home"]
    steam_mounted = STEAM_MOUNT.exists()
    if steam_mounted:
        targets.append(str(STEAM_MOUNT))

    result: dict = {"home_used_pct": None, "steam_used_pct": None, "steam_mounted": steam_mounted}
    try:
        out = subprocess.run(
            ["df", "-B1"] + targets,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return result
        for line in out.stdout.splitlines()[1:]:
            fields = line.split()
            if len(fields) < 6:
                continue
            mount = fields[5]
            try:
                use_pct = float(fields[4].rstrip("%"))
            except (ValueError, IndexError):
                continue
            if mount == "/home":
                result["home_used_pct"] = use_pct
            elif mount == str(STEAM_MOUNT):
                result["steam_used_pct"] = use_pct
    except Exception as e:
        logger.debug("df error: %s", e)
    return result


def _check_ollama() -> dict:
    """Check if Ollama is running and nomic-embed-text is available."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "5", _OLLAMA_URL],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {"running": False, "nomic_available": False}
        data = json.loads(result.stdout)
        models = data.get("models", [])
        nomic_available = any(_EMBED_MODEL in m.get("name", "").lower() for m in models)
        return {"running": True, "nomic_available": nomic_available}
    except Exception as e:
        logger.debug("Ollama check error: %s", e)
        return {"running": False, "nomic_available": False}


# ── Corruption detection and repair ─────────────────────────────────────────


def _check_permissions(path: Path) -> dict:
    """Check read/write permissions for a path."""
    result = {"readable": False, "writable": False, "error": None}
    try:
        result["readable"] = os.access(path, os.R_OK)
        result["writable"] = os.access(path, os.W_OK)
    except Exception as e:
        result["error"] = str(e)
    return result


def _validate_table_vectors(table_name: str, sample_size: int = 10) -> dict:
    """Validate vectors in a table by sampling entries."""
    result = {"valid": True, "issues": [], "sample_size": sample_size}
    try:
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(VECTOR_DB_DIR))
        table = db.open_table(table_name)

        df = table.to_pandas()
        if df.empty:
            result["valid"] = True
            result["issues"].append("empty_table")
            return result

        vector_col = "vector"
        if vector_col not in df.columns:
            result["valid"] = False
            result["issues"].append("no_vector_column")
            return result

        sample = df.head(sample_size)
        for row_idx, row in sample.iterrows():
            row_key = str(row_idx)
            vec = row.get(vector_col)
            if vec is None:
                result["valid"] = False
                result["issues"].append(f"row_{row_key}_null_vector")
                continue

            # Handle numpy arrays from LanceDB
            import numpy as np

            if isinstance(vec, np.ndarray):
                vec = vec.tolist()

            if not isinstance(vec, (list, tuple)):
                result["valid"] = False
                result["issues"].append(f"row_{row_key}_unhashable_type_{type(vec).__name__}")
                continue
            if len(vec) != EMBEDDING_DIM:
                result["valid"] = False
                result["issues"].append(
                    f"row_{row_key}_wrong_dimension_{len(vec)}_expected_{EMBEDDING_DIM}"
                )
            for v in vec:
                if not isinstance(v, (int, float, np.integer, np.floating)):
                    result["valid"] = False
                    result["issues"].append(f"row_{row_key}_non_numeric_value")
                    break
                if v != v or abs(v) == float("inf"):
                    result["valid"] = False
                    result["issues"].append(f"row_{row_key}_nan_or_inf")
                    break

    except Exception as e:
        result["valid"] = False
        result["issues"].append(f"validation_error_{type(e).__name__}")
        logger.debug("Vector validation error for %s: %s", table_name, e)

    return result


def _detect_corruption() -> dict:
    """Full corruption scan of LanceDB tables."""
    corruption = {
        "corrupted_tables": {},
        "total_issues": 0,
        "can_repair": True,
        "permissions_ok": True,
        "error": None,
    }

    perms = _check_permissions(VECTOR_DB_DIR)
    if not perms["readable"]:
        corruption["error"] = f"Vector DB not readable: {perms.get('error')}"
        corruption["can_repair"] = False
        return corruption

    if not perms["writable"]:
        corruption["permissions_ok"] = False
        corruption["can_repair"] = False
        corruption["error"] = "Vector DB not writable - repair not possible"
        logger.warning("Vector DB is read-only, repair disabled")

    try:
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(VECTOR_DB_DIR))
        tables_result = db.list_tables()

        if hasattr(tables_result, "tables"):
            tables = list(tables_result.tables)
        elif isinstance(tables_result, (list, tuple)):
            tables = list(tables_result)
        else:
            tables = []

        for table_name in tables:
            lance_path = VECTOR_DB_DIR / f"{table_name}.lance"
            if not lance_path.exists():
                corruption["corrupted_tables"][table_name] = {
                    "issue": "missing_lance_directory",
                    "repairable": False,
                }
                corruption["total_issues"] += 1
                continue

            table_issues = []
            is_corrupted = False

            try:
                tbl = db.open_table(table_name)
                row_count = tbl.count_rows()
                if row_count < 0:
                    table_issues.append("cannot_count_rows")
                    is_corrupted = True

                if "vector" in tbl.schema.names:
                    validation = _validate_table_vectors(table_name)
                    if not validation["valid"]:
                        table_issues.extend(validation["issues"][:5])
                        is_corrupted = True

            except Exception as e:
                table_issues.append(f"open_error_{type(e).__name__}")
                is_corrupted = True
                logger.debug("Table %s corruption: %s", table_name, e)

            if is_corrupted:
                corruption["corrupted_tables"][table_name] = {
                    "issue": "; ".join(table_issues[:3]),
                    "repairable": True,
                }
                corruption["total_issues"] += 1

    except Exception as e:
        corruption["error"] = str(e)
        logger.warning("Corruption detection error: %s (this may be recoverable)", e)

    return corruption


def _create_backup() -> tuple[bool, Path | None]:
    """Create timestamped backup of vector DB. Returns (success, backup_path)."""
    if not VECTOR_DB_DIR.exists():
        return False, None

    backup_name = f"vector-db-backup-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    backup_path = SECURITY_DIR / backup_name

    try:
        shutil.copytree(VECTOR_DB_DIR, backup_path, symlinks=True, dirs_exist_ok=False)
        logger.info("Created backup at %s", backup_path)
        return True, backup_path
    except Exception as e:
        logger.error("Backup failed: %s", e)
        return False, None


def _prune_old_backups() -> int:
    """Remove oldest backups beyond _MAX_BACKUPS. Returns count deleted."""
    deleted = 0
    try:
        backups = sorted(
            [p for p in SECURITY_DIR.iterdir() if p.name.startswith("vector-db-backup-")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_backup in backups[_MAX_BACKUPS:]:
            try:
                shutil.rmtree(old_backup)
                logger.info("Pruned old backup: %s", old_backup)
                deleted += 1
            except Exception as e:
                logger.warning("Failed to prune %s: %s", old_backup, e)
    except Exception as e:
        logger.debug("Backup pruning error: %s", e)
    return deleted


def repair_database() -> dict:
    """Attempt automatic repair of corrupted LanceDB tables."""
    result = {
        "repaired": False,
        "backed_up": False,
        "tables_repaired": [],
        "error": None,
    }

    corruption = _detect_corruption()
    if not corruption["can_repair"]:
        result["error"] = corruption.get("error", "Repair not possible due to permissions")
        return result

    if corruption["total_issues"] == 0:
        result["repaired"] = True
        return result

    logger.info("Corruption detected in %d tables, attempting repair", corruption["total_issues"])

    success, backup_path = _create_backup()
    result["backed_up"] = success
    if not success:
        result["error"] = "Failed to create backup, aborting repair"
        return result

    _prune_old_backups()

    try:
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(VECTOR_DB_DIR))

        for table_name, info in corruption["corrupted_tables"].items():
            if not info.get("repairable", False):
                continue

            try:
                old_table = db.open_table(table_name)
                good_rows = []

                df = old_table.to_pandas()
                vector_col = "vector"

                for _idx, row in df.iterrows():
                    if vector_col not in row:
                        continue
                    vec = row[vector_col]

                    if not isinstance(vec, (list, tuple)):
                        continue
                    if len(vec) != EMBEDDING_DIM:
                        continue
                    if any(v != v or abs(v) == float("inf") for v in vec):
                        continue

                    good_rows.append(row.to_dict())

                db.drop_table(table_name)
                logger.info("Dropped corrupted table: %s", table_name)

                if good_rows:
                    new_table = db.create_table(table_name, schema=old_table.schema)
                    new_table.add(good_rows)
                    logger.info("Recreated table %s with %d valid rows", table_name, len(good_rows))
                    result["tables_repaired"].append(table_name)

            except Exception as e:
                logger.error("Failed to repair table %s: %s", table_name, e)
                result["error"] = f"Failed to repair {table_name}: {e}"
                continue

        result["repaired"] = len(result["tables_repaired"]) > 0

    except Exception as e:
        logger.error("Repair failed: %s", e)
        result["error"] = str(e)

    return result


# ── Recommendation engine ──────────────────────────────────────────────────────


def _build_recommendations(
    db: dict,
    doc_state: dict,
    log_state: dict,
    disk: dict,
    ollama: dict,
) -> tuple[list[str], str]:
    """Apply threshold rules and return (recommendations, status).

    Status levels:
        attention_needed — at least one hard issue
        stale            — embeddings are out of date
        healthy          — all nominal
    """
    recs: list[str] = []
    hard_issues = 0
    stale_issues = 0

    # LanceDB state
    if db.get("error"):
        recs.append(f"LanceDB unavailable: {db['error']}")
        hard_issues += 1
    else:
        total_rows = db.get("total_rows", 0)
        if total_rows == 0:
            recs.append("Vector DB is empty — run initial ingestion")
            hard_issues += 1
        security_rows = db.get("tables", {}).get("security_logs", 0)
        if total_rows > 0 and security_rows == 0:
            recs.append("No security logs ingested yet — needs investigation")
            hard_issues += 1

    # Ingestion freshness
    docs_hours = doc_state.get("hours_ago")
    if docs_hours is None:
        recs.append("Document ingest state not found — run knowledge.ingest_docs")
        stale_issues += 1
    elif docs_hours > 48:
        recs.append(f"Document embeddings are stale ({docs_hours:.0f}h ago), consider re-ingesting")
        stale_issues += 1

    logs_hours = log_state.get("hours_ago")
    if logs_hours is None:
        recs.append("Log ingest state not found — run security.run_ingest")
        stale_issues += 1
    elif logs_hours > 48:
        recs.append(f"Log embeddings are stale ({logs_hours:.0f}h ago), run security.run_ingest")
        stale_issues += 1

    # Vector DB size
    size_bytes = db.get("size_bytes", 0)
    if size_bytes and size_bytes > 500 * 1024 * 1024:
        recs.append(f"Vector DB getting large ({_human_bytes(size_bytes)}), consider cleanup")
        stale_issues += 1

    # Disk usage
    home_pct = disk.get("home_used_pct")
    if home_pct is not None and home_pct > 85:
        recs.append("Home disk nearly full")
        hard_issues += 1

    # Ollama
    if not ollama.get("running"):
        recs.append("Ollama is down — RAG queries will fail")
        hard_issues += 1
    elif not ollama.get("nomic_available"):
        recs.append("nomic-embed-text not pulled — run: ollama pull nomic-embed-text")
        hard_issues += 1

    if not recs:
        recs.append("Knowledge base healthy")

    if hard_issues > 0:
        status = "attention_needed"
    elif stale_issues > 0:
        status = "stale"
    else:
        status = "healthy"

    return recs, status


# ── Main workflow ──────────────────────────────────────────────────────────────


def run_storage_check(auto_repair: bool = True) -> dict:
    """Run storage and knowledge base health check.

    Checks LanceDB tables, ingestion freshness, disk usage, and Ollama status.
    Includes automatic corruption detection and optional repair.
    No cloud API calls. Results written atomically to ~/security/storage-reports/.

    Args:
        auto_repair: If True, automatically repair detected corruption.

    Returns:
        dict with keys: timestamp, vector_db, ingestion, disk, ollama,
        recommendations, status, corruption, repair.
    """
    now = datetime.now(UTC)
    timestamp = now.isoformat()
    start_time = time.time()

    # Collect data
    db_info = _check_lancedb()
    size_bytes, size_human = _get_vector_db_size()
    db_info["size_bytes"] = size_bytes
    db_info["size_human"] = size_human

    # Corruption detection
    corruption = _detect_corruption()
    repair_result = {"attempted": False, "success": False}

    if corruption["total_issues"] > 0 and auto_repair:
        logger.warning(
            "Corruption detected: %d issues in %s",
            corruption["total_issues"],
            list(corruption["corrupted_tables"].keys()),
        )
        repair_result = repair_database()
        repair_result["attempted"] = True

    doc_state = _read_ingest_state(_DOC_STATE_FILE)
    log_state = _read_ingest_state(_LOG_STATE_FILE)
    disk = _collect_disk()
    ollama = _check_ollama()

    # Build recommendations with corruption awareness
    recs, status = _build_recommendations(db_info, doc_state, log_state, disk, ollama)

    # Add corruption-related recommendations
    if corruption["total_issues"] > 0:
        for table, info in corruption["corrupted_tables"].items():
            recs.append(f"Corrupted table: {table} - {info.get('issue', 'unknown')}")
        status = "attention_needed"

    if repair_result.get("attempted") and not repair_result.get("repaired"):
        recs.append(f"Repair failed: {repair_result.get('error', 'unknown error')}")
        recs.append("Manual database re-initialization required - see morning briefing")
        status = "attention_needed"

    report: dict = {
        "timestamp": timestamp,
        "vector_db": {
            "tables": db_info.get("tables", {}),
            "total_rows": db_info.get("total_rows", 0),
            "size_bytes": size_bytes,
            "size_human": size_human,
            "error": db_info.get("error"),
        },
        "ingestion": {
            "docs_last_ingest": doc_state.get("last_ingest"),
            "docs_hours_ago": doc_state.get("hours_ago"),
            "logs_last_ingest": log_state.get("last_ingest"),
            "logs_hours_ago": log_state.get("hours_ago"),
        },
        "disk": disk,
        "ollama": ollama,
        "corruption": {
            "detected": corruption["total_issues"] > 0,
            "corrupted_tables": corruption.get("corrupted_tables", {}),
            "can_repair": corruption.get("can_repair", False),
        },
        "repair": repair_result,
        "recommendations": recs,
        "status": status,
    }

    # Atomic write
    STORAGE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"storage-{now.strftime('%Y-%m-%d-%H%M')}.json"
    report_path = STORAGE_REPORTS_DIR / filename

    fd, tmp_path = tempfile.mkstemp(dir=STORAGE_REPORTS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(report, f, indent=2)
        os.rename(tmp_path, report_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Storage report written to %s", report_path)

    # Record outcome for learning hooks
    try:
        from ai.hooks import record_task_outcome

        quality = 1.0 if status == "healthy" else (0.7 if status == "stale" else 0.4)
        record_task_outcome(
            task_id="agents.knowledge_storage",
            quality=quality,
            success=status in ("healthy", "stale"),
            duration_seconds=time.time() - start_time,
            agent_type="knowledge",
        )
    except Exception:
        pass  # Best-effort, non-blocking

    return report


if __name__ == "__main__":
    import sys

    from ai.config import setup_logging

    setup_logging()
    result = run_storage_check()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] in ("healthy", "stale") else 1)
