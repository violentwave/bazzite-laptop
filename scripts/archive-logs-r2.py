#!/usr/bin/env python3
"""Compress and archive old log files to Cloudflare R2."""

import gzip
import io
import logging
import os
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
) -> bool:
    """Compress, upload to R2, delete local file. Returns True on success."""
    try:
        compressed = compress_bytes(filepath.read_bytes())
        key = f"{category}/{filepath.name}.gz"
        s3_client.put_object(Bucket=bucket, Key=key, Body=compressed)
        filepath.unlink()
        msg = f"UPLOADED {filepath} -> {key} ({len(compressed)} bytes)"
        _append_archive_log(archive_log, msg)
        _LOG.info(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        msg = f"FAILED {filepath}: {exc}"
        _append_archive_log(archive_log, msg)
        _LOG.warning(msg)
        return False


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
        _LOG.warning("%s not set — skipping R2 archiving.", access_key_env)
        return {"skipped": True, "reason": "no_access_key"}
    if not secret_key:
        _LOG.warning("%s not set — skipping R2 archiving.", secret_key_env)
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

    uploaded = 0
    failed = 0
    for directory, category in scan_dirs:
        for filepath in find_old_files(directory, age_seconds):
            if upload_file(s3, bucket, category, filepath, archive_log):
                uploaded += 1
            else:
                failed += 1

    _LOG.info("Archive run complete: %d uploaded, %d failed.", uploaded, failed)
    return {"skipped": False, "uploaded": uploaded, "failed": failed}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = archive_logs()
    if result.get("skipped"):
        _LOG.info("Skipped: %s", result.get("reason"))


if __name__ == "__main__":
    main()
