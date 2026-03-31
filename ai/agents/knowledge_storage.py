"""Storage and knowledge base health agent for Bazzite.

Checks LanceDB health, ingestion freshness, disk usage, and Ollama status.
Generates hardcoded rule-based recommendations (no cloud LLM calls).
Writes a structured JSON report to ~/security/storage-reports/.

Usage:
    python -m ai.agents.knowledge_storage
    from ai.agents.knowledge_storage import run_storage_check
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ai.config import APP_NAME, SECURITY_DIR, VECTOR_DB_DIR

logger = logging.getLogger(APP_NAME)

STEAM_MOUNT = Path("/var/mnt/ext-ssd")
STORAGE_REPORTS_DIR = SECURITY_DIR / "storage-reports"

_DOC_STATE_FILE = VECTOR_DB_DIR / ".doc-ingest-state.json"
_LOG_STATE_FILE = VECTOR_DB_DIR / ".ingest-state.json"

_OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
_EMBED_MODEL = "nomic-embed-text"


# ── Collectors ─────────────────────────────────────────────────────────────────


def _check_lancedb() -> dict:
    """Connect to LanceDB, list tables, and count rows. Returns dict or error."""
    try:
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(VECTOR_DB_DIR))
        tables = db.list_tables()
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
        raw_ts = data.get("last_ingest") or data.get("timestamp")
        if not raw_ts:
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


def run_storage_check() -> dict:
    """Run storage and knowledge base health check.

    Checks LanceDB tables, ingestion freshness, disk usage, and Ollama status.
    No cloud API calls. Results written atomically to ~/security/storage-reports/.

    Returns:
        dict with keys: timestamp, vector_db, ingestion, disk, ollama,
        recommendations, status.
    """
    now = datetime.now(UTC)
    timestamp = now.isoformat()

    # Collect data
    db_info = _check_lancedb()
    size_bytes, size_human = _get_vector_db_size()
    db_info["size_bytes"] = size_bytes
    db_info["size_human"] = size_human

    doc_state = _read_ingest_state(_DOC_STATE_FILE)
    log_state = _read_ingest_state(_LOG_STATE_FILE)
    disk = _collect_disk()
    ollama = _check_ollama()

    # Recommendations
    recs, status = _build_recommendations(db_info, doc_state, log_state, disk, ollama)

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
    return report


if __name__ == "__main__":
    import sys

    from ai.config import setup_logging

    setup_logging()
    result = run_storage_check()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] in ("healthy", "stale") else 1)
