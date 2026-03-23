"""Unit tests for scripts/archive-logs-r2.py."""

import gzip  # noqa: I001
import importlib.util
import os
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

# Stub boto3 before loading the module — it may not be installed in the venv.
if "boto3" not in sys.modules:
    _boto3_stub = types.ModuleType("boto3")
    _boto3_stub.client = MagicMock(return_value=MagicMock())
    sys.modules["boto3"] = _boto3_stub

# Load module with hyphenated filename via importlib
_SCRIPT = Path(__file__).parent.parent / "scripts" / "archive-logs-r2.py"
_spec = importlib.util.spec_from_file_location("archive_logs_r2", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

find_old_files = _mod.find_old_files
compress_bytes = _mod.compress_bytes
load_config = _mod.load_config
load_keys_env = _mod.load_keys_env
upload_file = _mod.upload_file
archive_logs = _mod.archive_logs

# New-format YAML helpers
_VALID_R2_YAML = """\
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


# ---------------------------------------------------------------------------
# find_old_files
# ---------------------------------------------------------------------------


class TestFindOldFiles:
    def test_missing_directory_returns_empty(self, tmp_path):
        assert find_old_files(tmp_path / "nonexistent", 3600) == []

    def test_empty_directory_returns_empty(self, tmp_path):
        assert find_old_files(tmp_path, 3600) == []

    def test_old_file_is_returned(self, tmp_path):
        f = tmp_path / "old.log"
        f.write_text("data")
        old_mtime = time.time() - 8 * 24 * 3600
        os.utime(f, (old_mtime, old_mtime))
        assert f in find_old_files(tmp_path, 7 * 24 * 3600)

    def test_recent_file_is_excluded(self, tmp_path):
        f = tmp_path / "new.log"
        f.write_text("data")
        assert f not in find_old_files(tmp_path, 7 * 24 * 3600)

    def test_symlinks_are_excluded(self, tmp_path):
        target = tmp_path / "real.log"
        target.write_text("data")
        old_mtime = time.time() - 8 * 24 * 3600
        os.utime(target, (old_mtime, old_mtime))
        link = tmp_path / "link.log"
        link.symlink_to(target)

        result = find_old_files(tmp_path, 7 * 24 * 3600)
        assert target in result
        assert link not in result

    def test_directories_are_excluded(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        old_mtime = time.time() - 8 * 24 * 3600
        os.utime(subdir, (old_mtime, old_mtime))
        assert subdir not in find_old_files(tmp_path, 7 * 24 * 3600)


# ---------------------------------------------------------------------------
# compress_bytes
# ---------------------------------------------------------------------------


class TestCompressBytes:
    def test_output_is_valid_gzip(self):
        data = b"hello world log entry"
        assert gzip.decompress(compress_bytes(data)) == data

    def test_compressed_smaller_for_repetitive_data(self):
        data = b"AAAA" * 1000
        assert len(compress_bytes(data)) < len(data)

    def test_empty_bytes_compresses_without_error(self):
        assert gzip.decompress(compress_bytes(b"")) == b""


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert load_config(tmp_path / "nonexistent.yaml") == {}

    def test_new_format_config_parsed(self, tmp_path):
        cfg = tmp_path / "r2.yaml"
        cfg.write_text(_VALID_R2_YAML)
        result = load_config(cfg)
        assert result["r2"]["endpoint"] == "https://abc123.r2.cloudflarestorage.com"
        assert result["r2"]["bucket"] == "bazzite-logs"
        assert result["archive"]["local_retention_days"] == 7
        assert result["keys"]["access_key_env"] == "R2_ACCESS_KEY_ID"

    def test_empty_file_returns_empty_dict(self, tmp_path):
        cfg = tmp_path / "r2.yaml"
        cfg.write_text("")
        assert load_config(cfg) == {}


# ---------------------------------------------------------------------------
# archive_logs — skip conditions
# ---------------------------------------------------------------------------


class TestArchiveLogsSkips:
    def test_missing_config_skips_no_endpoint(self, tmp_path):
        result = archive_logs(
            config_file=tmp_path / "nonexistent.yaml",
            keys_file=tmp_path / "keys.env",
        )
        assert result["skipped"] is True
        assert result["reason"] == "no_endpoint"

    def test_empty_endpoint_skips(self, tmp_path):
        cfg = tmp_path / "r2.yaml"
        cfg.write_text("r2:\n  endpoint: ''\n  bucket: b\nkeys:\n  access_key_env: X\n")
        result = archive_logs(config_file=cfg, keys_file=tmp_path / "keys.env")
        assert result["skipped"] is True
        assert result["reason"] == "no_endpoint"

    def test_missing_access_key_skips(self, tmp_path):
        cfg = tmp_path / "r2.yaml"
        cfg.write_text(_VALID_R2_YAML)
        keys = tmp_path / "keys.env"
        keys.write_text("OTHER_KEY=value\n")
        env = {k: v for k, v in os.environ.items() if k != "R2_ACCESS_KEY_ID"}
        with patch.dict(os.environ, env, clear=True):
            result = archive_logs(config_file=cfg, keys_file=keys)
        assert result["skipped"] is True
        assert result["reason"] == "no_access_key"

    def test_missing_secret_key_skips(self, tmp_path):
        cfg = tmp_path / "r2.yaml"
        cfg.write_text(_VALID_R2_YAML)
        keys = tmp_path / "keys.env"
        keys.write_text("R2_ACCESS_KEY_ID=mykey\n")  # no secret
        _skip = {"R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"}
        env = {k: v for k, v in os.environ.items() if k not in _skip}
        with patch.dict(os.environ, env, clear=True):
            result = archive_logs(config_file=cfg, keys_file=keys)
        assert result["skipped"] is True
        assert result["reason"] == "no_secret_key"


# ---------------------------------------------------------------------------
# upload_file — boto3 mock
# ---------------------------------------------------------------------------


class TestUploadFile:
    def test_put_object_called_with_gz_key(self, tmp_path):
        f = tmp_path / "health-2026-03-01.log"
        f.write_text("log data here")
        archive_log = tmp_path / "archive-log.txt"
        mock_s3 = MagicMock()

        result = upload_file(mock_s3, "bazzite-logs", "system-health", f, archive_log)

        assert result is True
        mock_s3.put_object.assert_called_once()
        kwargs = mock_s3.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "bazzite-logs"
        assert kwargs["Key"] == "system-health/health-2026-03-01.log.gz"
        assert gzip.decompress(kwargs["Body"]) == b"log data here"

    def test_local_file_deleted_after_upload(self, tmp_path):
        f = tmp_path / "old.log"
        f.write_text("data")
        upload_file(MagicMock(), "bucket", "category", f, tmp_path / "log.txt")
        assert not f.exists()

    def test_upload_failure_returns_false_keeps_file(self, tmp_path):
        f = tmp_path / "old.log"
        f.write_text("data")
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = RuntimeError("network error")

        result = upload_file(mock_s3, "bucket", "category", f, tmp_path / "log.txt")

        assert result is False
        assert f.exists()

    def test_archive_log_entry_written(self, tmp_path):
        f = tmp_path / "report.log"
        f.write_text("report data")
        archive_log = tmp_path / "archive-log.txt"

        upload_file(MagicMock(), "bucket", "audit-reports", f, archive_log)

        log_text = archive_log.read_text()
        assert "UPLOADED" in log_text
        assert "report.log.gz" in log_text


# ---------------------------------------------------------------------------
# archive_logs — full run with mocked boto3 client
# ---------------------------------------------------------------------------


class TestArchiveLogsFullRun:
    def _write_cfg(self, tmp_path):
        cfg = tmp_path / "r2.yaml"
        cfg.write_text(_VALID_R2_YAML)
        keys = tmp_path / "keys.env"
        keys.write_text("R2_ACCESS_KEY_ID=mykey\nR2_SECRET_ACCESS_KEY=mysecret\n")
        return cfg, keys

    def test_uploads_old_files_returns_count(self, tmp_path):
        cfg, keys = self._write_cfg(tmp_path)
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        old_file = log_dir / "old.log"
        old_file.write_text("old data")
        os.utime(old_file, (time.time() - 8 * 24 * 3600,) * 2)

        mock_s3 = MagicMock()
        _skip = {"R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"}
        env = {k: v for k, v in os.environ.items() if k not in _skip}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(_mod.boto3, "client", return_value=mock_s3):
                result = archive_logs(
                    config_file=cfg,
                    keys_file=keys,
                    archive_log=tmp_path / "archive-log.txt",
                    scan_dirs=[(log_dir, "system-health")],
                )

        assert result == {"skipped": False, "uploaded": 1, "failed": 0}
        mock_s3.put_object.assert_called_once()

    def test_skips_recent_files(self, tmp_path):
        cfg, keys = self._write_cfg(tmp_path)
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "recent.log").write_text("recent data")

        mock_s3 = MagicMock()
        _skip = {"R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"}
        env = {k: v for k, v in os.environ.items() if k not in _skip}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(_mod.boto3, "client", return_value=mock_s3):
                result = archive_logs(
                    config_file=cfg,
                    keys_file=keys,
                    archive_log=tmp_path / "archive-log.txt",
                    scan_dirs=[(log_dir, "system-health")],
                )

        assert result["uploaded"] == 0
        mock_s3.put_object.assert_not_called()

    def test_client_uses_config_endpoint_and_region(self, tmp_path):
        cfg, keys = self._write_cfg(tmp_path)

        _skip = {"R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"}
        env = {k: v for k, v in os.environ.items() if k not in _skip}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(_mod.boto3, "client", return_value=MagicMock()) as mock_client:
                archive_logs(
                    config_file=cfg,
                    keys_file=keys,
                    archive_log=tmp_path / "archive-log.txt",
                    scan_dirs=[],
                )

        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args.kwargs
        assert call_kwargs["endpoint_url"] == "https://abc123.r2.cloudflarestorage.com"
        assert call_kwargs["region_name"] == "auto"
        assert call_kwargs["aws_access_key_id"] == "mykey"
        assert call_kwargs["aws_secret_access_key"] == "mysecret"
