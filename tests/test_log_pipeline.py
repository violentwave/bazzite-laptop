"""Tests for the log lifecycle pipeline: prune, archive state, and unit dependency wiring."""

from __future__ import annotations

import configparser
import importlib.util
import json
import os
import sys
import time
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest

# ── Module loading ─────────────────────────────────────────────────────────────

# Stub boto3 before loading archive module — may not be on system PATH
if "boto3" not in sys.modules:
    _boto3_stub = types.ModuleType("boto3")
    _boto3_stub.client = MagicMock(return_value=MagicMock())
    sys.modules["boto3"] = _boto3_stub

_ARCHIVE_SCRIPT = Path(__file__).parent.parent / "scripts" / "archive-logs-r2.py"
_archive_spec = importlib.util.spec_from_file_location("archive_logs_r2_pipeline", _ARCHIVE_SCRIPT)
_archive_mod = importlib.util.module_from_spec(_archive_spec)
_archive_spec.loader.exec_module(_archive_mod)

upload_file = _archive_mod.upload_file
archive_logs = _archive_mod.archive_logs
load_archive_state = _archive_mod.load_archive_state
save_archive_state = _archive_mod.save_archive_state

_PRUNE_SCRIPT = Path(__file__).parent.parent / "scripts" / "lancedb-prune.py"
_prune_spec = importlib.util.spec_from_file_location("lancedb_prune_pipeline", _PRUNE_SCRIPT)
_prune_mod = importlib.util.module_from_spec(_prune_spec)
_prune_spec.loader.exec_module(_prune_mod)

prune_table = _prune_mod.prune_table
clean_tmp_dirs = _prune_mod.clean_tmp_dirs

PROJECT_ROOT = Path(__file__).parent.parent
SYSTEMD_DIR = PROJECT_ROOT / "systemd"

# ── Shared config YAML ─────────────────────────────────────────────────────────

_R2_YAML = """\
r2:
  endpoint: "https://abc123.r2.cloudflarestorage.com"
  bucket: "bazzite-logs"
  region: "auto"
  storage_class: "STANDARD"
archive:
  local_log_dirs: []
  report_dirs: []
  local_retention_days: 7
  remote_retention_days: 365
keys:
  access_key_env: "R2_ACCESS_KEY_ID"
  secret_key_env: "R2_SECRET_ACCESS_KEY"
"""


def _write_cfg(tmp_path: Path) -> tuple[Path, Path]:
    cfg = tmp_path / "r2.yaml"
    cfg.write_text(_R2_YAML)
    keys = tmp_path / "keys.env"
    keys.write_text("R2_ACCESS_KEY_ID=mykey\nR2_SECRET_ACCESS_KEY=mysecret\n")
    return cfg, keys


def _iso_days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _make_ts_table(db, name: str, rows: list[dict]):
    """Create a minimal LanceDB table with id + timestamp columns."""
    schema = pa.schema([pa.field("id", pa.utf8()), pa.field("timestamp", pa.utf8())])
    table = db.create_table(name, schema=schema)
    if rows:
        table.add(rows)
    return table


def _run_archive(
    tmp_path: Path,
    log_dir: Path,
    *,
    ingest_state: dict,
    health_log_dir: Path | None = None,
) -> tuple[dict, MagicMock]:
    """Helper: run archive_logs with mocked R2 + patched state files."""
    cfg, keys = _write_cfg(tmp_path)
    archive_state_file = tmp_path / ".archive-state.json"
    ingest_state_file = tmp_path / ".ingest-state.json"
    ingest_state_file.write_text(json.dumps(ingest_state))
    mock_s3 = MagicMock()
    target_health_dir = health_log_dir or log_dir

    _skip = {"R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"}
    env = {k: v for k, v in os.environ.items() if k not in _skip}
    with (
        patch.object(_archive_mod, "ARCHIVE_STATE_FILE", archive_state_file),
        patch.object(_archive_mod, "INGEST_STATE_FILE", ingest_state_file),
        patch.object(_archive_mod, "_HEALTH_LOG_DIR", target_health_dir),
        patch.object(_archive_mod.boto3, "client", return_value=mock_s3),
        patch.dict(os.environ, env, clear=True),
    ):
        result = archive_logs(
            config_file=cfg,
            keys_file=keys,
            archive_log=tmp_path / "archive-log.txt",
            scan_dirs=[(log_dir, "health")],
        )
    return result, mock_s3


# ══════════════════════════════════════════════════════════════════════════════
# A. LanceDB prune tests
# ══════════════════════════════════════════════════════════════════════════════


class TestPruneLanceDB:
    @pytest.fixture(autouse=True)
    def _restore_real_lancedb(self):
        """Prune tests require real lancedb to create and list tables."""
        import importlib
        from unittest.mock import MagicMock as _MM

        saved = sys.modules.get("lancedb")
        if isinstance(saved, _MM):
            sys.modules.pop("lancedb", None)
            real = importlib.import_module("lancedb")
            sys.modules["lancedb"] = real
            yield
            sys.modules["lancedb"] = saved
        else:
            yield

    def test_prune_deletes_old_rows(self, tmp_path):
        """Rows older than retention_days are deleted; recent rows survive."""
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(tmp_path / "test-db"))
        _make_ts_table(
            db,
            "health_records",
            [
                {"id": "r1", "timestamp": _iso_days_ago(1)},  # 1 day  — survives
                {"id": "r30", "timestamp": _iso_days_ago(30)},  # 30 days — survives
                {"id": "r60", "timestamp": _iso_days_ago(60)},  # 60 days — survives
                {"id": "r91", "timestamp": _iso_days_ago(91)},  # 91 days — deleted
                {"id": "r120", "timestamp": _iso_days_ago(120)},  # 120 days — deleted
            ],
        )

        with patch.object(_prune_mod, "_run_maintenance", return_value=None):
            stats = prune_table(db, "health_records", 90, dry_run=False)

        assert stats["rows_before"] == 5
        assert stats["rows_deleted"] == 2
        assert stats["rows_after"] == 3
        assert not stats["skipped"]

    def test_prune_skips_missing_tables(self, tmp_path):
        """Prune against an empty DB skips gracefully without crashing."""
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(tmp_path / "empty-db"))
        stats = prune_table(db, "health_records", 90, dry_run=False)

        assert stats["skipped"] is True
        assert stats["skip_reason"] == "table not found"

    def test_prune_dry_run_no_deletes(self, tmp_path):
        """Dry-run reports would-delete count but does not modify the table."""
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(tmp_path / "test-db"))
        _make_ts_table(
            db,
            "health_records",
            [
                {"id": "old1", "timestamp": _iso_days_ago(100)},
                {"id": "old2", "timestamp": _iso_days_ago(110)},
                {"id": "new1", "timestamp": _iso_days_ago(10)},
            ],
        )

        stats = prune_table(db, "health_records", 90, dry_run=True)

        # Physical row count must be unchanged.
        assert db.open_table("health_records").count_rows() == 3
        # Stats report what would have happened.
        assert stats["rows_deleted"] == 2
        assert stats["rows_after"] == 1

    def test_prune_cleans_tmp_dirs(self, tmp_path):
        """Leftover .tmp* dirs inside the DB path are removed; others are kept."""
        db_path = tmp_path / "test-db"
        db_path.mkdir()
        (db_path / ".tmp_abc123").mkdir()
        (db_path / ".tmp_xyz789").mkdir()
        (db_path / "normal-dir").mkdir()

        removed = clean_tmp_dirs(db_path, dry_run=False)

        assert removed == 2
        assert not (db_path / ".tmp_abc123").exists()
        assert not (db_path / ".tmp_xyz789").exists()
        assert (db_path / "normal-dir").exists()

    def test_prune_threat_intel_180_days(self, tmp_path):
        """threat_intel uses 180-day retention: 90-day row survives, 200-day row deleted."""
        import lancedb  # noqa: PLC0415

        db = lancedb.connect(str(tmp_path / "test-db"))
        _make_ts_table(
            db,
            "threat_intel",
            [
                {"id": "t90", "timestamp": _iso_days_ago(90)},  # 90 days — survives (< 180)
                {"id": "t200", "timestamp": _iso_days_ago(200)},  # 200 days — deleted (> 180)
            ],
        )

        with patch.object(_prune_mod, "_run_maintenance", return_value=None):
            stats = prune_table(db, "threat_intel", 180, dry_run=False)

        assert stats["rows_before"] == 2
        assert stats["rows_deleted"] == 1
        assert stats["rows_after"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# B. Archive state and ingest gate tests
# ══════════════════════════════════════════════════════════════════════════════


class TestArchiveState:
    def test_archive_state_records_upload(self, tmp_path):
        """After a successful upload, .archive-state.json contains the file entry."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = log_dir / "health-20260301.log"
        log_file.write_text("health log data")
        os.utime(log_file, (time.time() - 10 * 24 * 3600,) * 2)

        archive_state_file = tmp_path / ".archive-state.json"
        # Non-log dir → ingest-exempt; empty ingest state is fine.
        result, mock_s3 = _run_archive(tmp_path, log_dir, ingest_state={}, health_log_dir=None)

        assert result["uploaded"] == 1
        assert archive_state_file.exists()
        saved = json.loads(archive_state_file.read_text())
        entry = saved["archived_files"]["health-20260301.log"]
        assert entry["r2_key"] == "health/health-20260301.log.gz"
        assert entry["size_bytes"] > 0
        assert "archived_at" in entry

    def test_archive_skips_delete_without_ingest(self, tmp_path):
        """File is uploaded to R2 but NOT deleted if LanceDB hasn't ingested it yet."""
        log_dir = tmp_path / "health"
        log_dir.mkdir()
        log_file = log_dir / "health-20260301.log"
        log_file.write_text("health log data")
        os.utime(log_file, (time.time() - 10 * 24 * 3600,) * 2)

        # last_health_file is an earlier filename — our file (March) > Feb, so not ingested.
        ingest_state = {"last_health_file": "health-20260201.log"}

        result, mock_s3 = _run_archive(
            tmp_path,
            log_dir,
            ingest_state=ingest_state,
            health_log_dir=log_dir,  # patch _HEALTH_LOG_DIR to log_dir
        )

        assert result["uploaded"] == 1
        mock_s3.put_object.assert_called_once()
        # Local file must still exist.
        assert log_file.exists()

    def test_archive_deletes_after_both_verified(self, tmp_path):
        """File IS deleted locally when the ingest pipeline has processed it."""
        log_dir = tmp_path / "health"
        log_dir.mkdir()
        log_file = log_dir / "health-20260201.log"
        log_file.write_text("old health log data")
        os.utime(log_file, (time.time() - 15 * 24 * 3600,) * 2)

        # last_health_file == our file → file has been ingested.
        ingest_state = {"last_health_file": "health-20260201.log"}

        result, mock_s3 = _run_archive(
            tmp_path,
            log_dir,
            ingest_state=ingest_state,
            health_log_dir=log_dir,
        )

        assert result["uploaded"] == 1
        mock_s3.put_object.assert_called_once()
        # Local file must be gone.
        assert not log_file.exists()


# ══════════════════════════════════════════════════════════════════════════════
# C. Systemd unit dependency tests
# ══════════════════════════════════════════════════════════════════════════════


def _parse_unit(name: str) -> configparser.ConfigParser:
    """Parse a systemd unit file. strict=False allows duplicate keys."""
    cp = configparser.ConfigParser(strict=False)
    cp.read(str(SYSTEMD_DIR / name))
    return cp


def _all_values_for(name: str, section: str, key: str) -> str:
    """Return concatenation of all values for *key* in *section* from unit file.

    configparser with strict=False keeps only the last duplicate; we read the
    raw text to collect all After= lines and join them for reliable assertions.
    """
    path = SYSTEMD_DIR / name
    collected: list[str] = []
    in_section = False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped == f"[{section}]":
            in_section = True
        elif stripped.startswith("[") and stripped.endswith("]"):
            in_section = False
        elif in_section and stripped.startswith(f"{key}="):
            collected.append(stripped[len(f"{key}=") :].strip())
    return " ".join(collected)


class TestSystemdDependencies:
    def test_archive_depends_on_ingest(self):
        """log-archive.service must declare After and Requires on log-ingest.service."""
        after = _all_values_for("log-archive.service", "Unit", "After")
        requires = _all_values_for("log-archive.service", "Unit", "Requires")
        assert "log-ingest.service" in after
        assert "log-ingest.service" in requires

    def test_optimize_depends_on_archive(self):
        """lancedb-optimize.service must declare After and Requires on log-archive.service."""
        after = _all_values_for("lancedb-optimize.service", "Unit", "After")
        requires = _all_values_for("lancedb-optimize.service", "Unit", "Requires")
        assert "log-archive.service" in after
        assert "log-archive.service" in requires

    def test_ingest_has_no_pipeline_deps(self):
        """log-ingest.service must not depend on archive or optimize."""
        after = _all_values_for("log-ingest.service", "Unit", "After")
        requires = _all_values_for("log-ingest.service", "Unit", "Requires")
        combined = after + " " + requires
        assert "log-archive" not in combined
        assert "lancedb-optimize" not in combined

    def test_pipeline_timer_order(self):
        """Sunday pipeline fires in order: ingest (00:30) < archive (01:00) < optimize (02:00)."""

        def _hhmm(name: str) -> str:
            """Extract HH:MM from OnCalendar of a timer file."""
            cp = _parse_unit(name)
            cal = cp.get("Timer", "OnCalendar", fallback="")
            # Handles "Sun 00:30" and "Sun *-*-* 02:00:00" formats.
            for token in reversed(cal.split()):
                if ":" in token and token[0].isdigit():
                    return token[:5]
            return cal

        ingest_t = _hhmm("log-ingest.timer")
        archive_t = _hhmm("log-archive.timer")
        optimize_t = _hhmm("lancedb-optimize.timer")

        assert ingest_t < archive_t, (
            f"ingest timer ({ingest_t!r}) must fire before archive ({archive_t!r})"
        )
        assert archive_t < optimize_t, (
            f"archive timer ({archive_t!r}) must fire before optimize ({optimize_t!r})"
        )
