"""Tests for ai/key_manager.py — key presence checker."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_env(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "keys.env"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. list_keys()
# ---------------------------------------------------------------------------

class TestListKeys:
    def test_returns_all_expected_keys(self, tmp_path):
        from ai.key_manager import _ALL_EXPECTED_KEYS, list_keys

        env = _write_env(tmp_path, "")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        assert set(result.keys()) == set(_ALL_EXPECTED_KEYS)

    def test_set_key_reported_as_set(self, tmp_path):
        from ai.key_manager import list_keys

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc123\nGROQ_API_KEY=xyz\n")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        assert result["GEMINI_API_KEY"] == "set"
        assert result["GROQ_API_KEY"] == "set"

    def test_empty_value_reported_as_missing(self, tmp_path):
        from ai.key_manager import list_keys

        env = _write_env(tmp_path, "GEMINI_API_KEY=\nGROQ_API_KEY=\n")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        assert result["GEMINI_API_KEY"] == "missing"
        assert result["GROQ_API_KEY"] == "missing"

    def test_absent_key_reported_as_missing(self, tmp_path):
        from ai.key_manager import list_keys

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc123\n")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        assert result["GROQ_API_KEY"] == "missing"
        assert result["VT_API_KEY"] == "missing"

    def test_missing_file_all_missing(self, tmp_path):
        from ai.key_manager import list_keys

        nonexistent = tmp_path / "no-such.env"
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=nonexistent)

        assert all(v == "missing" for v in result.values())

    def test_comments_and_blank_lines_ignored(self, tmp_path):
        from ai.key_manager import list_keys

        env = _write_env(tmp_path, "# comment\n\nGEMINI_API_KEY=abc\n")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        assert result["GEMINI_API_KEY"] == "set"

    def test_unknown_keys_not_included(self, tmp_path):
        from ai.key_manager import _ALL_EXPECTED_KEYS, list_keys

        env = _write_env(tmp_path, "UNKNOWN_KEY=abc\nGEMINI_API_KEY=val\n")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        assert "UNKNOWN_KEY" not in result
        assert set(result.keys()) == set(_ALL_EXPECTED_KEYS)

    def test_values_only_set_or_missing(self, tmp_path):
        """Output must contain only 'set' or 'missing' — never real key values."""
        from ai.key_manager import list_keys

        secret = "super-secret-abc123"
        env = _write_env(tmp_path, f"GEMINI_API_KEY={secret}\n")
        with patch("ai.key_manager.write_status_file"):
            result = list_keys(keys_env=env)

        for v in result.values():
            assert v in ("set", "missing"), f"Unexpected value: {v!r}"
        assert secret not in str(result)

    def test_write_status_file_called_as_side_effect(self, tmp_path):
        from ai.key_manager import list_keys

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc\n")
        with patch("ai.key_manager.write_status_file") as mock_write:
            list_keys(keys_env=env)

        mock_write.assert_called_once()
        # Presence dict passed as first positional arg
        presence_arg = mock_write.call_args[0][0]
        assert presence_arg["GEMINI_API_KEY"] == "set"


# ---------------------------------------------------------------------------
# 2. get_key_status()
# ---------------------------------------------------------------------------

class TestGetKeyStatus:
    def test_required_keys_in_result(self, tmp_path):
        from ai.key_manager import get_key_status

        env = _write_env(tmp_path, "")
        with patch("ai.key_manager.write_status_file"):
            result = get_key_status(keys_env=env)

        assert set(result.keys()) == {
            "all_llm_keys_present",
            "all_threat_keys_present",
            "all_storage_keys_present",
            "missing_keys",
            "categories",
        }

    def test_all_present_flags_true(self, tmp_path):
        from ai.key_manager import _ALL_EXPECTED_KEYS, get_key_status

        content = "\n".join(f"{k}=value" for k in _ALL_EXPECTED_KEYS)
        env = _write_env(tmp_path, content)
        with patch("ai.key_manager.write_status_file"):
            result = get_key_status(keys_env=env)

        assert result["all_llm_keys_present"] is True
        assert result["all_threat_keys_present"] is True
        assert result["all_storage_keys_present"] is True
        assert result["missing_keys"] == []

    def test_partial_llm_keys_flags_false(self, tmp_path):
        from ai.key_manager import get_key_status

        env = _write_env(tmp_path, "GEMINI_API_KEY=val\n")
        with patch("ai.key_manager.write_status_file"):
            result = get_key_status(keys_env=env)

        assert result["all_llm_keys_present"] is False

    def test_missing_keys_list_populated(self, tmp_path):
        from ai.key_manager import get_key_status

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc\n")
        with patch("ai.key_manager.write_status_file"):
            result = get_key_status(keys_env=env)

        assert "GROQ_API_KEY" in result["missing_keys"]
        assert "VT_API_KEY" in result["missing_keys"]
        assert "GEMINI_API_KEY" not in result["missing_keys"]

    def test_empty_env_all_flags_false(self, tmp_path):
        from ai.key_manager import get_key_status

        env = _write_env(tmp_path, "")
        with patch("ai.key_manager.write_status_file"):
            result = get_key_status(keys_env=env)

        assert result["all_llm_keys_present"] is False
        assert result["all_threat_keys_present"] is False
        assert result["all_storage_keys_present"] is False


# ---------------------------------------------------------------------------
# 3. write_status_file()
# ---------------------------------------------------------------------------

class TestWriteStatusFile:
    def test_writes_valid_json(self, tmp_path):
        from ai.key_manager import write_status_file

        presence = {"GEMINI_API_KEY": "set", "GROQ_API_KEY": "missing"}
        status_file = tmp_path / "key-status.json"

        with (
            patch("ai.key_manager.SECURITY_DIR", tmp_path),
            patch("ai.key_manager._KEY_STATUS_FILE", status_file),
        ):
            write_status_file(presence)

        assert status_file.exists()
        data = json.loads(status_file.read_text())
        assert "keys" in data
        assert "summary" in data
        assert data["keys"]["GEMINI_API_KEY"] == "set"
        assert data["keys"]["GROQ_API_KEY"] == "missing"

    def test_no_tmp_files_left(self, tmp_path):
        """Atomic write must clean up — no .tmp files after success."""
        from ai.key_manager import write_status_file

        status_file = tmp_path / "key-status.json"
        with (
            patch("ai.key_manager.SECURITY_DIR", tmp_path),
            patch("ai.key_manager._KEY_STATUS_FILE", status_file),
        ):
            write_status_file({"GEMINI_API_KEY": "set"})

        assert list(tmp_path.glob(".key-status-*.tmp")) == []

    def test_values_not_in_output_file(self, tmp_path):
        """Secret values must never appear in the written file."""
        from ai.key_manager import list_keys

        secret = "my-secret-key-9x8y7z"
        env = _write_env(tmp_path, f"GEMINI_API_KEY={secret}\n")
        status_file = tmp_path / "key-status.json"

        with (
            patch("ai.key_manager.SECURITY_DIR", tmp_path),
            patch("ai.key_manager._KEY_STATUS_FILE", status_file),
        ):
            list_keys(keys_env=env)

        content = status_file.read_text()
        assert secret not in content
        data = json.loads(content)
        for v in data["keys"].values():
            assert v in ("set", "missing")

    def test_summary_flags_in_file(self, tmp_path):
        from ai.key_manager import write_status_file

        status_file = tmp_path / "key-status.json"
        with (
            patch("ai.key_manager.SECURITY_DIR", tmp_path),
            patch("ai.key_manager._KEY_STATUS_FILE", status_file),
        ):
            write_status_file({"GEMINI_API_KEY": "set", "VT_API_KEY": "missing"})

        data = json.loads(status_file.read_text())
        summary = data["summary"]
        assert "all_llm_keys_present" in summary
        assert "all_threat_keys_present" in summary
        assert "all_storage_keys_present" in summary
        assert "missing_keys" in summary

    def test_no_arg_reads_keys_env_fresh(self, tmp_path):
        """write_status_file() with no args should read keys.env directly."""
        from ai.key_manager import write_status_file

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc\n")
        status_file = tmp_path / "key-status.json"

        with (
            patch("ai.key_manager.KEYS_ENV", env),
            patch("ai.key_manager.SECURITY_DIR", tmp_path),
            patch("ai.key_manager._KEY_STATUS_FILE", status_file),
        ):
            write_status_file()

        data = json.loads(status_file.read_text())
        assert data["keys"]["GEMINI_API_KEY"] == "set"


# ---------------------------------------------------------------------------
# 4. CLI (main())
# ---------------------------------------------------------------------------

class TestCLI:
    def test_list_prints_json(self, tmp_path, capsys):
        from ai.key_manager import main

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc\n")
        with (
            patch("sys.argv", ["key_manager", "list"]),
            patch("ai.key_manager.KEYS_ENV", env),
            patch("ai.key_manager.write_status_file"),
        ):
            main()

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["GEMINI_API_KEY"] == "set"
        assert "GROQ_API_KEY" in data

    def test_status_exits_1_when_keys_missing(self, tmp_path):
        from ai.key_manager import main

        env = _write_env(tmp_path, "")
        with (
            patch("sys.argv", ["key_manager", "status"]),
            patch("ai.key_manager.KEYS_ENV", env),
            patch("ai.key_manager.write_status_file"),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    def test_status_exits_0_when_all_keys_present(self, tmp_path):
        from ai.key_manager import _ALL_EXPECTED_KEYS, main

        content = "\n".join(f"{k}=value" for k in _ALL_EXPECTED_KEYS)
        env = _write_env(tmp_path, content)
        with (
            patch("sys.argv", ["key_manager", "status"]),
            patch("ai.key_manager.KEYS_ENV", env),
            patch("ai.key_manager.write_status_file"),
        ):
            main()  # must not raise SystemExit

    def test_list_output_has_no_secret_values(self, tmp_path, capsys):
        """CLI output must never leak actual key values."""
        from ai.key_manager import main

        secret = "top-secret-9z8y7x"
        env = _write_env(tmp_path, f"GEMINI_API_KEY={secret}\n")
        with (
            patch("sys.argv", ["key_manager", "list"]),
            patch("ai.key_manager.KEYS_ENV", env),
            patch("ai.key_manager.write_status_file"),
        ):
            main()

        out = capsys.readouterr().out
        assert secret not in out
        for v in json.loads(out).values():
            assert v in ("set", "missing")

    def test_default_command_is_list(self, tmp_path, capsys):
        from ai.key_manager import main

        env = _write_env(tmp_path, "GEMINI_API_KEY=abc\n")
        with (
            patch("sys.argv", ["key_manager"]),
            patch("ai.key_manager.KEYS_ENV", env),
            patch("ai.key_manager.write_status_file"),
        ):
            main()

        out = capsys.readouterr().out
        data = json.loads(out)
        # list output is a flat KEY->status dict (not a summary dict)
        assert "GEMINI_API_KEY" in data
        assert "all_llm_keys_present" not in data
