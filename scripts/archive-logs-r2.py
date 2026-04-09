#!/usr/bin/env python3
"""Compress and archive old log files to Cloudflare R2.

# ROOT CAUSE — stale uploads since 2026-03-22
#
# Diagnosis:
#   local_retention_days = 7 (already correct — not the cause)
#   Scan dirs: /var/log/system-health, /var/log/clamav-scans,
#              ~/security/{audit,perf,storage,code,cve}-reports
#
#   The service runs as User=lch (log-archive.service). Log files in
#   /var/log/system-health/ and /var/log/clamav-scans/ are owned by root
#   (written by system-health.service and clamav, both running as root).
#   User lch can READ them (world-readable 644) but cannot UNLINK them.
#
#   The original upload_file() called filepath.unlink() inside the same
#   try/except as s3_client.put_object(). A PermissionError from unlink()
#   was caught and the whole operation was counted as FAILED and returned
#   False — even though R2 had already received the data. archive-log.txt
#   showed only FAILED entries, giving the appearance of zero uploads.
#
# Fix applied here:
#   - upload_file() now returns (success, r2_key, compressed_size) and
#     does NOT delete the local file.
#   - archive_logs() handles deletion separately, with its own except block
#     that logs a warning but does not fail the upload counter.
#   - Ingest gate: local deletion is only attempted after verifying the file
#     appears in .ingest-state.json (LanceDB ingested it).
#   - Archive state is tracked in .archive-state.json for auditability.
"""

import gzip
import io
import json
import logging
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import boto3
import yaml

_LOG = logging.getLogger(__name__)

HOME = Path.home()
PROJECT_ROOT = Path(__file__).parent.parent

CONFIG_FILE = PROJECT_ROOT / "configs" / "r2-config.yaml"
KEYS_FILE = HOME / ".config" / "bazzite-ai" / "keys.env"
ARCHIVE_LOG = HOME / "security" / "archive-log.txt"

VECTOR_DB_DIR = HOME / "security" / "vector-db"
ARCHIVE_STATE_FILE = VECTOR_DB_DIR / ".archive-state.json"
INGEST_STATE_FILE = VECTOR_DB_DIR / ".ingest-state.json"

# Ingest pipeline only tracks files from these two directories.
_HEALTH_LOG_DIR = Path("/var/log/system-health")
_SCAN_LOG_DIR = Path("/var/log/clamav-scans")


# ── Key / config loading ───────────────────────────────────────────


def load_keys_env(keys_file: Path) -> dict[str, str]:
    """Parse key=value pairs from a keys env file. Returns empty dict on error."""
    result: dict[str, str] = {}
    try:
        for raw_line in keys_file.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return result


def load_config(config_file: Path) -> dict:
    """Load R2 config from YAML. Returns empty dict if file is missing or unreadable."""
    try:
        with config_file.open() as f:
            return yaml.safe_load(f) or {}
    except OSError:
        return {}


# ── Archive state ──────────────────────────────────────────────────────────────────────────────


def load_archive_state() -> dict:
    """Load archive state from disk. Returns an empty state dict on first run."""
    try:
        return json.loads(ARCHIVE_STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {
            "archived_files": {},
            "last_archive_run": "",
            "total_archived": 0,
            "total_bytes_archived": 0,
        }


def save_archive_state(state: dict) -> None:
    """Atomically write archive state using tempfile + os.replace."""
    ARCHIVE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(ARCHIVE_STATE_FILE.parent),
        suffix=".json.tmp",
        prefix=".archive-state-",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, str(ARCHIVE_STATE_FILE))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Ingest verification ─────────────────────────────────────────────────────────────────────────


def load_ingest_state() -> dict:
    """Load LanceDB ingest state. Returns empty dict if not yet initialised."""
    try:
        return json.loads(INGEST_STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _file_is_ingested(filepath: Path, ingest_state: dict) -> bool:
    """Return True if the file has been processed by the LanceDB ingest pipeline.

    Only health logs and scan logs are tracked by ingest. All other categories
    (report dirs, etc.) are considered ingest-exempt and can be deleted freely.

    Uses lexicographic filename comparison: ingest.py processes files in
    alphabetical order and records the last filename ingested. Any file whose
    name sorts at or before that marker has already been ingested.
    """
    parent = filepath.parent
    name = filepath.name

    if parent == _HEALTH_LOG_DIR:
        last_health = ingest_state.get("last_health_file", "")
        if not last_health:
            return False
        return name <= last_health

    if parent == _SCAN_LOG_DIR:
        last_scan = ingest_state.get("last_scan_file", "")
        if not last_scan:
            return False
        return name <= last_scan

    # Report dirs and other paths have no ingest tracking — allow deletion.
    return True


# ── File discovery ───────────────────────────────────────────────


def find_old_files(directory: Path, age_seconds: float) -> list[Path]:
    """Return non-symlink files in directory whose mtime is older than age_seconds."""
    if not directory.exists():
        return []
    cutoff = time.time() - age_seconds
    return [
        p
        for p in directory.iterdir()
        if not p.is_symlink() and p.is_file() and p.stat().st_mtime < cutoff
    ]


# ── Compression / upload ──────────────────────────────────────────


def compress_bytes(data: bytes) -> bytes:
    """Return gzip-compressed copy of data (in-memory, original untouched)."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(data)
    return buf.getvalue()


def _append_archive_log(archive_log: Path, message: str) -> None:
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    archive_log.parent.mkdir(parents=True, exist_ok=True)
    with archive_log.open("a") as f:
        f.write(f"{timestamp} {message}\n")


def upload_file(
    s3_client,
    bucket: str,
    category: str,
    filepath: Path,
    archive_log: Path,
) -> tuple[bool, str, int]:
    """Compress and upload *filepath* to R2. Does NOT delete the local file.

    Returns (success, r2_key, compressed_size_bytes).
    Deletion is handled by the caller so a permission error on unlink
    cannot mask a successful upload.
    """
    try:
        compressed = compress_bytes(filepath.read_bytes())
        key = f"{category}/{filepath.name}.gz"
        s3_client.put_object(Bucket=bucket, Key=key, Body=compressed)
        msg = f"UPLOADED {filepath.name} -> {key} ({len(compressed)} bytes)"
        _append_archive_log(archive_log, msg)
        _LOG.info("Uploaded %s to R2 (%d bytes compressed)", filepath.name, len(compressed))
        return True, key, len(compressed)
    except Exception:  # noqa: BLE001
        _append_archive_log(archive_log, f"FAILED {filepath.name}")
        _LOG.warning("Upload failed for %s", filepath.name, exc_info=False)
        return False, "", 0


# ── Directory helpers ─────────────────────────────────────────────


def _build_scan_dirs(config: dict) -> list[tuple[Path, str]]:
    """Derive (directory, category) pairs from archive config."""
    archive_cfg = config.get("archive", {})
    result: list[tuple[Path, str]] = []
    for raw in archive_cfg.get("local_log_dirs", []):
        p = Path(raw)
        result.append((p, p.name))
    for raw in archive_cfg.get("report_dirs", []):
        p = Path(raw).expanduser()
        result.append((p, p.name))
    return result


# ── Main archival routine ─────────────────────────────────────────


def archive_logs(
    config_file: Path = CONFIG_FILE,
    keys_file: Path = KEYS_FILE,
    archive_log: Path = ARCHIVE_LOG,
    scan_dirs: list[tuple[Path, str]] | None = None,
) -> dict:
    """Run log archiving. Returns a summary dict. Never raises."""
    config = load_config(config_file)
    r2_cfg = config.get("r2", {})
    archive_cfg = config.get("archive", {})
    keys_cfg = config.get("keys", {})

    endpoint = r2_cfg.get("endpoint", "")
    if not endpoint:
        _LOG.info("R2 endpoint not configured — skipping.")
        return {"skipped": True, "reason": "no_endpoint"}

    access_key_env = keys_cfg.get("access_key_env", "R2_ACCESS_KEY_ID")
    secret_key_env = keys_cfg.get("secret_key_env", "R2_SECRET_ACCESS_KEY")

    keys = load_keys_env(keys_file)
    access_key = keys.get(access_key_env) or os.environ.get(access_key_env, "")
    secret_key = keys.get(secret_key_env) or os.environ.get(secret_key_env, "")

    if not access_key:
        _LOG.warning("R2 access key not set — skipping R2 archiving.")
        return {"skipped": True, "reason": "no_access_key"}
    if not secret_key:
        _LOG.warning("R2 secret key not set — skipping R2 archiving.")
        return {"skipped": True, "reason": "no_secret_key"}

    bucket = r2_cfg.get("bucket", "bazzite-logs")
    region = r2_cfg.get("region", "auto")
    retention_days = archive_cfg.get("local_retention_days", 7)
    age_seconds = retention_days * 24 * 3600

    if scan_dirs is None:
        scan_dirs = _build_scan_dirs(config)

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    archive_state = load_archive_state()
    ingest_state = load_ingest_state()
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    uploaded = 0
    failed = 0
    bytes_this_run = 0

    for directory, category in scan_dirs:
        for filepath in find_old_files(directory, age_seconds):
            success, r2_key, compressed_size = upload_file(
                s3, bucket, category, filepath, archive_log
            )

            if not success:
                failed += 1
                continue

            uploaded += 1
            bytes_this_run += compressed_size

            # Always record successful upload in archive state (before ingest check).
            archive_state["archived_files"][filepath.name] = {
                "r2_key": r2_key,
                "archived_at": now_iso,
                "size_bytes": compressed_size,
            }

            # Ingest gate: only delete local copy once LanceDB has processed it.
            if not _file_is_ingested(filepath, ingest_state):
                _LOG.warning(
                    "Skipping deletion of %s — not yet ingested by LanceDB",
                    filepath.name,
                )
                continue

            try:
                filepath.unlink()
            except OSError as exc:
                _LOG.warning("Could not delete %s after upload: %s", filepath.name, exc)

    # Persist archive state atomically.
    archive_state["last_archive_run"] = now_iso
    archive_state["total_archived"] = archive_state.get("total_archived", 0) + uploaded
    archive_state["total_bytes_archived"] = (
        archive_state.get("total_bytes_archived", 0) + bytes_this_run
    )
    try:
        save_archive_state(archive_state)
    except OSError:
        _LOG.warning("Could not save archive state to %s", ARCHIVE_STATE_FILE)

    _LOG.info("Archive run complete: %d uploaded, %d failed.", uploaded, failed)
    return {"skipped": False, "uploaded": uploaded, "failed": failed}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = archive_logs()
    if result.get("skipped"):
        _LOG.info("Skipped: %s", result.get("reason"))


if __name__ == "__main__":
    main()
