"""Log intelligence ingestion pipeline.

Parses system health snapshots, ClamAV scan logs, and freshclam signature
updates into structured records.  Embeds text summaries via Ollama
(nomic-embed-text-v2-moe, 768-dim) and stores everything in LanceDB tables
under ~/security/vector-db/.

Tables created:
    health_records -- Parsed health snapshot metrics + embedding
    scan_records   -- Parsed ClamAV scan results + embedding
    sig_updates    -- freshclam signature version tracking

Usage:
    python -m ai.log_intel.ingest --all      # Catch-up: all new logs
    python -m ai.log_intel.ingest --health   # Health logs only
    python -m ai.log_intel.ingest --scan     # Scan logs only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ai.config import APP_NAME, VECTOR_DB_DIR

logger = logging.getLogger(APP_NAME)

# ── Constants ──────────────────────────────────────────────────

EMBEDDING_DIM = 768
HEALTH_LOG_DIR = Path("/var/log/system-health")
SCAN_LOG_DIR = Path("/var/log/clamav-scans")
FRESHCLAM_LOG = Path("/var/log/clamav-scans/freshclam.log")
INGEST_STATE_FILE = VECTOR_DB_DIR / ".ingest-state.json"


def _normalize_vector(vec: list[float], dim: int = EMBEDDING_DIM) -> list[float]:
    """Truncate or pad a vector to the expected dimension."""
    if len(vec) == dim:
        return vec
    if len(vec) > dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))


# ── PyArrow schemas (lazy to avoid sandbox segfault) ──────────


def _get_schemas() -> dict:
    """Lazy-load pyarrow schemas."""
    import pyarrow as pa  # noqa: PLC0415

    health_schema = pa.schema([
        pa.field("id", pa.utf8()),
        pa.field("timestamp", pa.utf8()),
        pa.field("gpu_temp_c", pa.float32()),
        pa.field("cpu_temp_c", pa.float32()),
        pa.field("disk_usage_pct", pa.float32()),
        pa.field("steam_usage_pct", pa.float32()),
        pa.field("ram_used_gb", pa.float32()),
        pa.field("swap_used_gb", pa.float32()),
        pa.field("smart_status", pa.utf8()),
        pa.field("services_ok", pa.int32()),
        pa.field("services_down", pa.int32()),
        pa.field("summary", pa.utf8()),
        pa.field("source_file", pa.utf8()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])

    scan_schema = pa.schema([
        pa.field("id", pa.utf8()),
        pa.field("timestamp", pa.utf8()),
        pa.field("scan_type", pa.utf8()),
        pa.field("files_scanned", pa.int32()),
        pa.field("threats_found", pa.int32()),
        pa.field("threat_names", pa.utf8()),
        pa.field("duration_s", pa.float32()),
        pa.field("quarantined", pa.int32()),
        pa.field("summary", pa.utf8()),
        pa.field("source_file", pa.utf8()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])

    sig_schema = pa.schema([
        pa.field("id", pa.utf8()),
        pa.field("timestamp", pa.utf8()),
        pa.field("sig_version", pa.utf8()),
        pa.field("sig_count", pa.int32()),
        pa.field("source_file", pa.utf8()),
    ])

    return {
        "health_records": health_schema,
        "scan_records": scan_schema,
        "sig_updates": sig_schema,
    }


# ── Ingest state persistence ─────────────────────────────────


def get_ingest_state(state_dir: Path | None = None) -> dict:
    """Read ingestion state from disk.  Returns empty dict on first run.

    *state_dir* overrides the default ``VECTOR_DB_DIR`` directory.
    """
    state_file = (state_dir or VECTOR_DB_DIR) / ".ingest-state.json"
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_ingest_state(state: dict, state_dir: Path | None = None) -> None:
    """Atomic write of ingestion state (tmp + rename).

    *state_dir* overrides the default ``VECTOR_DB_DIR`` directory.
    """
    state_file = (state_dir or VECTOR_DB_DIR) / ".ingest-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(state_file.parent),
        prefix=".ingest-state-",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.rename(tmp, str(state_file))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── File discovery ────────────────────────────────────────────


def find_new_files(
    log_dir: Path,
    pattern: str,
    last_processed: str | None = None,
    *,
    last_file: str | None = None,
) -> list[Path]:
    """Return log files newer than *last_processed*, sorted oldest-first.

    If *last_processed* is None every matching file is returned.
    *last_file* is accepted as a legacy alias for *last_processed*.
    """
    effective = last_processed if last_processed is not None else last_file
    if not log_dir.is_dir():
        return []

    candidates = sorted(log_dir.glob(pattern))  # lexicographic = chronological
    if effective is None:
        return candidates

    # Return only files whose name sorts after the last processed one
    return [p for p in candidates if p.name > effective]


# ── Parsers ───────────────────────────────────────────────────

# Timestamp patterns -- production format ("Monday March 21, 2026 ...") and
# simplified format ("Date: 2026-03-21 08:00:00")
_RE_TIMESTAMP = re.compile(
    r"^(?:System Health Snapshot\n)?"
    r"(\w+ \w+ \d{1,2}, \d{4} . \d{1,2}:\d{2}:\d{2} [AP]M \w+)",
    re.MULTILINE,
)
_RE_TIMESTAMP_ISO = re.compile(
    r"Date:\s*(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})",
    re.MULTILINE,
)

_RE_GPU_TEMP = re.compile(r"Temperature:\s+([\d.]+).C", re.MULTILINE)
# "Package temp: 62.0°C" or "Package id 0: +62.0°C"
_RE_PKG_TEMP = re.compile(
    r"(?:Package temp|Package id \d+):\s*\+?([\d.]+).C",
    re.MULTILINE,
)
# "Overall health: PASSED" or "/dev/sdX: PASSED/FAILED"
_RE_SMART = re.compile(r"Overall health:\s+(\w+)", re.MULTILINE)
_RE_SMART_DEV = re.compile(r"/dev/\S+:\s+(PASSED|FAILED)", re.MULTILINE)
_RE_SVC_OK = re.compile(r":\s+active$", re.MULTILINE)
_RE_SVC_DOWN = re.compile(
    r"(?:WARNING.*:\s+)?(inactive|unknown|failed)$",
    re.MULTILINE,
)
# Disk: "  · /dev/dm-0  31%  ..." or "/dev/dm-0: 31% (71G/237G)"
_RE_DISK_PCT = re.compile(r"\s(\d+)%\s*", re.MULTILINE)
_RE_DISK_LINE = re.compile(
    r"(/dev/\S+):\s+(\d+)%\s*\(",
    re.MULTILINE,
)
_RE_STATUS_LINE = re.compile(r"Status:\s+[^\n]+", re.MULTILINE)
_RE_RAM = re.compile(r"Mem:\s+([\d.]+)Gi?\s+([\d.]+)Gi?", re.MULTILINE)


def _safe_float(match: re.Match | None, group: int = 1) -> float:
    """Extract a float from a regex match, returning 0.0 on failure."""
    if match is None:
        return 0.0
    try:
        return float(match.group(group))
    except (ValueError, IndexError):
        return 0.0


def parse_health_log(
    source: Path | str,
    *,
    source_file: str | None = None,
) -> dict | None:
    """Parse a system-health-snapshot log into structured fields.

    *source* may be a ``Path`` (reads the file) or a ``str`` (uses the
    content directly).  The optional *source_file* kwarg overrides the
    recorded source filename.
    """
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8", errors="replace")
        source_file = source_file or str(source)
    else:
        text = source
        source_file = source_file or "<string>"

    if not text.strip():
        return None

    # Timestamp -- try production format, then ISO-style "Date: ..."
    timestamp = ""
    ts_match = _RE_TIMESTAMP.search(text)
    if ts_match:
        try:
            dt = datetime.strptime(ts_match.group(1), "%A %B %d, %Y %I:%M:%S %p %Z")
            timestamp = dt.isoformat()
        except ValueError:
            timestamp = ts_match.group(1)
    if not timestamp:
        ts_iso = _RE_TIMESTAMP_ISO.search(text)
        if ts_iso:
            raw = ts_iso.group(1).replace(" ", "T")
            timestamp = raw

    # GPU temperature
    gpu_match = _RE_GPU_TEMP.search(text)
    gpu_temp: float | None = float(gpu_match.group(1)) if gpu_match else None

    # CPU package temp (first match from sensors output)
    cpu_match = _RE_PKG_TEMP.search(text)
    cpu_temp: float | None = float(cpu_match.group(1)) if cpu_match else None

    # SMART overall health -- try "Overall health:" first, then per-device
    smart_match = _RE_SMART.search(text)
    if smart_match:
        smart_status = smart_match.group(1)
    else:
        smart_devs = _RE_SMART_DEV.findall(text)
        if smart_devs:
            smart_status = "FAILED" if "FAILED" in smart_devs else "PASSED"
        else:
            smart_status = "UNKNOWN"

    # Disk usage -- parse "/dev/X: NN% (used/total)" lines, or "· /..." lines
    disk_pct = 0.0
    steam_pct = 0.0
    disk_lines = _RE_DISK_LINE.findall(text)
    if disk_lines:
        for dev, pct_str in disk_lines:
            val = float(pct_str)
            if "sdb" in dev or "SteamLibrary" in dev:
                steam_pct = val
            elif disk_pct == 0.0:
                disk_pct = val
    else:
        # Fallback: production format with "· /" prefix
        for line in text.splitlines():
            if line.startswith("  ·   /"):
                pct_match = _RE_DISK_PCT.search(line)
                if pct_match:
                    val = float(pct_match.group(1))
                    stripped = line.strip()
                    if stripped.startswith("· /run/media") or "SteamLibrary" in stripped:
                        steam_pct = val
                    elif stripped.startswith("· / ") or "· /  " in stripped:
                        disk_pct = val
                    elif disk_pct == 0.0:
                        disk_pct = val

    # RAM -- look for free/top-style output
    ram_used = 0.0
    swap_used = 0.0
    ram_match = _RE_RAM.search(text)
    if ram_match:
        ram_used = _safe_float(ram_match, 2)

    # Swap
    swap_match = re.search(r"Swap:\s+([\d.]+)Gi?\s+([\d.]+)Gi?", text)
    if swap_match:
        swap_used = _safe_float(swap_match, 2)

    # Services
    services_ok = len(_RE_SVC_OK.findall(text))
    services_down = len(_RE_SVC_DOWN.findall(text))

    # Summary -- grab the status line from SUMMARY section
    status_match = _RE_STATUS_LINE.search(text)
    summary = status_match.group(0).strip() if status_match else "Health snapshot"

    return {
        "id": str(uuid4()),
        "timestamp": timestamp,
        "gpu_temp_c": gpu_temp,
        "cpu_temp_c": cpu_temp,
        "disk_usage_pct": disk_pct,
        "steam_usage_pct": steam_pct,
        "ram_used_gb": ram_used,
        "swap_used_gb": swap_used,
        "smart_status": smart_status,
        "services_ok": services_ok,
        "services_down": services_down,
        "summary": summary,
        "source_file": source_file,
    }


_RE_SCAN_SUMMARY_SEP = re.compile(r"-+\s*SCAN SUMMARY\s*-+")
_RE_SCANNED = re.compile(r"Scanned files:\s*(\d+)", re.IGNORECASE)
_RE_INFECTED = re.compile(r"Infected files:\s*(\d+)", re.IGNORECASE)
_RE_SCAN_TIME = re.compile(r"Time:\s*([\d.]+)\s*sec", re.IGNORECASE)
_RE_FOUND_LINE = re.compile(r"^(.+?):\s+(.+)\s+FOUND\s*$", re.MULTILINE)


def parse_scan_log(
    source: Path | str,
    *,
    source_file: str | None = None,
) -> dict | None:
    """Parse a ClamAV scan log into structured fields.

    *source* may be a ``Path`` (reads the file) or a ``str`` (uses the
    content directly).  The optional *source_file* kwarg overrides the
    recorded source filename.
    """
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8", errors="replace")
        source_file = source_file or str(source)
        fname = source.name
    else:
        text = source
        source_file = source_file or "<string>"
        fname = Path(source_file).name if source_file != "<string>" else "<string>"

    if not text.strip():
        return None

    # Derive timestamp from filename or "Start Date:" line
    timestamp = datetime.now(tz=UTC).isoformat()
    ts_match = re.search(r"scan-(\d{8})-(\d{6})", fname)
    if ts_match:
        raw = ts_match.group(1) + ts_match.group(2)
        try:
            dt = datetime.strptime(raw, "%Y%m%d%H%M%S")
            timestamp = dt.replace(tzinfo=UTC).isoformat()
        except ValueError:
            pass
    else:
        # Try "Start Date: YYYY:MM:DD HH:MM:SS"
        sd_match = re.search(r"Start Date:\s*(\d{4}:\d{2}:\d{2}\s+\d{2}:\d{2}:\d{2})", text)
        if sd_match:
            try:
                dt = datetime.strptime(sd_match.group(1), "%Y:%m:%d %H:%M:%S")
                timestamp = dt.replace(tzinfo=UTC).isoformat()
            except ValueError:
                pass

    # Detect scan type from filename or content
    scan_type = "quick"
    if "deep" in fname.lower() or "deep" in text[:200].lower():
        scan_type = "deep"
    elif "test" in fname.lower() or "EICAR" in text:
        scan_type = "test"
    elif "custom" in fname.lower():
        scan_type = "custom"

    # Parse summary section if present
    files_scanned = 0
    summary_match = _RE_SCAN_SUMMARY_SEP.search(text)
    summary_block = text[summary_match.end():] if summary_match else text

    scanned_m = _RE_SCANNED.search(summary_block)
    if scanned_m:
        files_scanned = int(scanned_m.group(1))

    infected_m = _RE_INFECTED.search(summary_block)
    threats_found = int(infected_m.group(1)) if infected_m else 0

    # If no formal summary, count FOUND lines
    if threats_found == 0:
        threats_found = len(_RE_FOUND_LINE.findall(text))

    # Threat names
    threat_names_list = []
    for _fpath, name in _RE_FOUND_LINE.findall(text):
        cleaned = name.strip()
        if cleaned and cleaned not in threat_names_list:
            threat_names_list.append(cleaned)
    threat_names = ", ".join(threat_names_list)

    # Duration
    duration_s = 0.0
    time_m = _RE_SCAN_TIME.search(summary_block)
    if time_m:
        duration_s = float(time_m.group(1))

    # Quarantined -- count "moved to" lines
    quarantined = text.lower().count("moved to")

    summary = (
        f"{scan_type.capitalize()} scan: {files_scanned} files, "
        f"{threats_found} threats"
    )
    if threats_found > 0:
        summary += f" ({threat_names})"

    return {
        "id": str(uuid4()),
        "timestamp": timestamp,
        "scan_type": scan_type,
        "files_scanned": files_scanned,
        "threats_found": threats_found,
        "threat_names": threat_names,
        "duration_s": duration_s,
        "quarantined": quarantined,
        "summary": summary,
        "source_file": source_file,
    }


_RE_SIG_VERSION = re.compile(
    r"(?:main|daily|bytecode)\.(?:cvd|cld)\s+(?:database\s+)?is\s+up[- ]to[- ]date\s*"
    r"\(version:\s*(\d+),\s*sigs:\s*(\d+)\)",
    re.IGNORECASE,
)
_RE_SIG_UPDATED = re.compile(
    r"(?:main|daily|bytecode)\.(?:cvd|cld)\s+updated\s*"
    r"\(version:\s*(\d+),\s*sigs:\s*(\d+)\)",
    re.IGNORECASE,
)
_RE_FRESHCLAM_TS = re.compile(
    r"ClamAV update process started at (.+)",
)


def parse_freshclam_log(path: Path) -> dict | None:
    """Extract the latest signature version and count from freshclam.log.

    Returns None if the file is missing or unparseable.
    """
    if not path.is_file():
        return None

    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return None

    # Walk backwards to find the latest session
    # Take the last occurrence of each pattern
    sig_version = ""
    sig_count = 0

    for match in _RE_SIG_VERSION.finditer(text):
        sig_version = match.group(1)
        sig_count = max(sig_count, int(match.group(2)))
    for match in _RE_SIG_UPDATED.finditer(text):
        sig_version = match.group(1)
        sig_count = max(sig_count, int(match.group(2)))

    if not sig_version:
        return None

    # Timestamp from last "ClamAV update process started at" line
    timestamp = datetime.now(tz=UTC).isoformat()
    for ts_m in _RE_FRESHCLAM_TS.finditer(text):
        raw_ts = ts_m.group(1).strip()
        try:
            dt = datetime.strptime(raw_ts, "%a %b %d %H:%M:%S %Y")
            timestamp = dt.replace(tzinfo=UTC).isoformat()
        except ValueError:
            pass

    return {
        "timestamp": timestamp,
        "sig_version": sig_version,
        "sig_count": sig_count,
        "source_file": str(path),
    }


# ── LanceDB helpers ──────────────────────────────────────────


def _connect_db():
    """Return a LanceDB connection to VECTOR_DB_DIR."""
    import lancedb  # noqa: PLC0415

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(VECTOR_DB_DIR))


def _ensure_table(db, name: str, schema):
    """Open or create a LanceDB table."""
    if name in db.table_names():
        return db.open_table(name)
    return db.create_table(name, schema=schema)


# ── Ingestion routines ───────────────────────────────────────


def ingest_health() -> int:
    """Ingest new health snapshot logs.  Returns count of records added."""
    from ai.rag.chunker import chunk_health_log  # noqa: PLC0415
    from ai.rag.embedder import embed_texts  # noqa: PLC0415
    from ai.rag.store import get_store  # noqa: PLC0415

    state = get_ingest_state()
    last_file = state.get("last_health_file")
    # Also pick up logrotated copies: health-*.log-YYYYMMDD (logrotate empties
    # the original .log and stores the real data with a date suffix).
    new_primary = find_new_files(HEALTH_LOG_DIR, "health-*.log", last_file)
    new_rotated = find_new_files(HEALTH_LOG_DIR, "health-*.log-*", last_file)
    new_files = sorted(
        {p for p in new_primary + new_rotated if p.stat().st_size > 0},
        key=lambda p: p.name,
    )

    if not new_files:
        logger.info("No new health logs to ingest")
        return 0

    schemas = _get_schemas()
    db = _connect_db()
    table = _ensure_table(db, "health_records", schemas["health_records"])

    records = []
    log_chunks_raw = []
    last_processed = last_file
    for path in new_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            parsed = parse_health_log(text, source_file=str(path))
            if parsed is not None:
                records.append(parsed)
                log_chunks_raw.extend(chunk_health_log(text, str(path)))
            last_processed = path.name
        except Exception:
            logger.exception("Failed to parse health log: %s", path)

    if not records:
        return 0

    # Embed summaries
    summaries = [r["summary"] for r in records]
    try:
        vectors = embed_texts(summaries)
    except RuntimeError:
        logger.error("Embedding providers unavailable, skipping health ingestion")
        return 0

    for rec, vec in zip(records, vectors, strict=True):
        rec["id"] = str(uuid4())
        rec["vector"] = _normalize_vector(vec)

    table.add(records)

    # Populate security_logs with raw chunked content for RAG queries
    if log_chunks_raw:
        chunk_texts = [c.content for c in log_chunks_raw]
        try:
            chunk_vectors = embed_texts(chunk_texts)
            chunk_dicts = [
                {
                    "source_file": c.source_file,
                    "section": c.section,
                    "content": c.content,
                    "log_type": c.log_type,
                    "timestamp": c.timestamp,
                    "vector": _normalize_vector(v),
                }
                for c, v in zip(log_chunks_raw, chunk_vectors, strict=False)
            ]
            get_store().add_log_chunks(chunk_dicts)
            logger.debug("Added %d health log chunks to security_logs", len(chunk_dicts))
        except RuntimeError:
            logger.error("Embedding providers unavailable, skipping security_logs population")
        except Exception:
            logger.exception("Failed to populate security_logs from health logs")

    state["last_health_file"] = last_processed
    state["last_health_ingest"] = datetime.now(tz=UTC).isoformat()
    save_ingest_state(state)

    logger.info("Ingested %d health record(s)", len(records))
    return len(records)


def ingest_scans() -> int:
    """Ingest new ClamAV scan logs (excluding test scans).  Returns count added."""
    from ai.rag.chunker import chunk_scan_log  # noqa: PLC0415
    from ai.rag.embedder import embed_texts  # noqa: PLC0415
    from ai.rag.store import get_store  # noqa: PLC0415

    state = get_ingest_state()
    last_file = state.get("last_scan_file")
    new_files = find_new_files(SCAN_LOG_DIR, "scan-*.log", last_file)

    if not new_files:
        logger.info("No new scan logs to ingest")
        return 0

    schemas = _get_schemas()
    db = _connect_db()
    table = _ensure_table(db, "scan_records", schemas["scan_records"])

    records = []
    log_chunks_raw = []
    last_processed = last_file
    for path in new_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            parsed = parse_scan_log(text, source_file=str(path))
            if parsed is None:
                last_processed = path.name
                continue
            # Exclude test scans from the knowledge base
            if parsed["scan_type"] == "test":
                logger.debug("Skipping test scan: %s", path.name)
                last_processed = path.name
                continue
            records.append(parsed)
            log_chunks_raw.extend(chunk_scan_log(text, str(path)))
            last_processed = path.name
        except Exception:
            logger.exception("Failed to parse scan log: %s", path)

    # Update state even if all were test scans
    if last_processed and last_processed != last_file:
        state["last_scan_file"] = last_processed
        state["last_scan_ingest"] = datetime.now(tz=UTC).isoformat()
        save_ingest_state(state)

    if not records:
        return 0

    summaries = [r["summary"] for r in records]
    try:
        vectors = embed_texts(summaries)
    except RuntimeError:
        logger.error("Embedding providers unavailable, skipping scan ingestion")
        return 0

    for rec, vec in zip(records, vectors, strict=True):
        rec["id"] = str(uuid4())
        rec["vector"] = _normalize_vector(vec)

    table.add(records)

    # Populate security_logs with raw chunked content for RAG queries
    if log_chunks_raw:
        chunk_texts = [c.content for c in log_chunks_raw]
        try:
            chunk_vectors = embed_texts(chunk_texts)
            chunk_dicts = [
                {
                    "source_file": c.source_file,
                    "section": c.section,
                    "content": c.content,
                    "log_type": c.log_type,
                    "timestamp": c.timestamp,
                    "vector": _normalize_vector(v),
                }
                for c, v in zip(log_chunks_raw, chunk_vectors, strict=False)
            ]
            get_store().add_log_chunks(chunk_dicts)
            logger.debug("Added %d log chunks to security_logs", len(chunk_dicts))
        except RuntimeError:
            logger.error("Embedding providers unavailable, skipping security_logs population")
        except Exception:
            logger.exception("Failed to populate security_logs from scan logs")

    logger.info("Ingested %d scan record(s)", len(records))
    return len(records)


def ingest_freshclam() -> int:
    """Ingest latest freshclam signature update.  Returns 1 if stored, 0 otherwise."""
    state = get_ingest_state()
    parsed = parse_freshclam_log(FRESHCLAM_LOG)

    if parsed is None:
        logger.info("No freshclam data to ingest")
        return 0

    # Skip if version unchanged
    if parsed["sig_version"] == state.get("last_sig_version"):
        logger.debug("Signature version unchanged (%s), skipping", parsed["sig_version"])
        return 0

    schemas = _get_schemas()
    db = _connect_db()
    table = _ensure_table(db, "sig_updates", schemas["sig_updates"])

    parsed["id"] = str(uuid4())
    table.add([parsed])

    state["last_sig_version"] = parsed["sig_version"]
    state["last_freshclam_ingest"] = datetime.now(tz=UTC).isoformat()
    save_ingest_state(state)

    logger.info(
        "Ingested signature update: version %s (%d sigs)",
        parsed["sig_version"],
        parsed["sig_count"],
    )
    return 1


def ingest_all() -> dict[str, int]:
    """Run all three ingestion routines.  Returns counts per category."""
    return {
        "health": ingest_health(),
        "scans": ingest_scans(),
        "freshclam": ingest_freshclam(),
    }


# ── CLI ───────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point with argparse."""
    from ai.config import setup_logging  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description="Ingest system logs into LanceDB for the AI layer.",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Ingest new health snapshot logs only",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Ingest new ClamAV scan logs only",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all new logs (health + scan + freshclam)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level)

    # Default to --all if no specific flag
    if not (args.health or args.scan or args.all):
        args.all = True

    if args.all:
        results = ingest_all()
        total = sum(results.values())
        logger.info(
            "Ingestion complete: %d total (%d health, %d scans, %d freshclam)",
            total,
            results["health"],
            results["scans"],
            results["freshclam"],
        )
    elif args.health:
        count = ingest_health()
        logger.info("Health ingestion complete: %d record(s)", count)
    elif args.scan:
        count = ingest_scans()
        logger.info("Scan ingestion complete: %d record(s)", count)


if __name__ == "__main__":
    main()


# ── Lazy embed_texts reference (patchable in tests) ──────────


def _get_embed_texts():
    """Return the embed_texts function, importing lazily."""
    from ai.rag.embedder import embed_texts as _et  # noqa: PLC0415

    return _et


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Thin wrapper around ``ai.rag.embedder.embed_texts``.

    Exists at module level so tests can ``patch("ai.log_intel.ingest.embed_texts", ...)``.
    """
    fn = _get_embed_texts()
    return fn(texts)


# ── Re-exports from queries (tests import these from ingest) ──


def health_trend(limit: int = 7, *, db_path: str | None = None) -> list[dict]:
    """Proxy to :func:`ai.log_intel.queries.health_trend`."""
    from ai.log_intel.queries import health_trend as _ht  # noqa: PLC0415

    return _ht(limit=limit, db_path=db_path)


def scan_history(limit: int = 10, *, db_path: str | None = None) -> list[dict]:
    """Proxy to :func:`ai.log_intel.queries.scan_history`."""
    from ai.log_intel.queries import scan_history as _sh  # noqa: PLC0415

    return _sh(limit=limit, db_path=db_path)


def get_anomalies(*, db_path: str | None = None) -> list[dict]:
    """Proxy to :func:`ai.log_intel.queries.get_anomalies`."""
    from ai.log_intel.queries import get_anomalies as _ga  # noqa: PLC0415

    return _ga(db_path=db_path)


def search_logs(
    query: str,
    limit: int = 5,
    *,
    db_path: str | None = None,
) -> list[dict]:
    """Semantic search using the module-level :func:`embed_texts` (patchable).

    Wraps :func:`ai.log_intel.queries.search_logs` but uses *this* module's
    ``embed_texts`` so that tests can inject a mock or a side-effect.
    """
    try:
        vectors = embed_texts([query])
    except (RuntimeError, Exception):
        return []

    if not vectors or not vectors[0]:
        return []

    from ai.log_intel.queries import _search_logs_with_vector  # noqa: PLC0415

    return _search_logs_with_vector(vectors[0], limit=limit, db_path=db_path)


def pipeline_stats(*, db_path: str | None = None) -> dict:
    """Proxy to :func:`ai.log_intel.queries.pipeline_stats`."""
    from ai.log_intel.queries import pipeline_stats as _ps  # noqa: PLC0415

    return _ps(db_path=db_path)
