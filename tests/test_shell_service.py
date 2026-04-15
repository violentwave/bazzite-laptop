"""Tests for shell_service module — P94 runtime recovery."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai.shell_service import (
    ShellService,
    _atomic_write,
    _is_command_allowed,
)


@pytest.fixture
def tmp_shell_dir(tmp_path):
    data_dir = tmp_path / "shell"
    data_dir.mkdir()
    sessions_file = data_dir / "sessions.json"
    audit_file = data_dir / "audit.jsonl"
    with patch.object(
        ShellService,
        "__init__",
        lambda self: _init_service(self, data_dir, sessions_file, audit_file),
    ):
        service = ShellService()
        yield service, data_dir, sessions_file, audit_file


def _init_service(self, data_dir, sessions_file, audit_file):
    import ai.shell_service as mod

    mod.SESSIONS_FILE = sessions_file
    mod.AUDIT_LOG_FILE = audit_file
    self._sessions = {}
    self._save_sessions()


class TestAtomicWrite:
    def test_writes_file_successfully(self, tmp_path):
        target = tmp_path / "test.json"
        _atomic_write(target, '{"ok": true}')
        assert target.exists()
        assert json.loads(target.read_text()) == {"ok": True}

    def test_replaces_existing_file(self, tmp_path):
        target = tmp_path / "test.json"
        target.write_text("old")
        _atomic_write(target, "new")
        assert target.read_text() == "new"


class TestCommandAllowlisting:
    def test_allows_simple_commands(self):
        ok, reason = _is_command_allowed("ls -la")
        assert ok is True
        assert reason == ""

    def test_allows_piped_commands(self):
        ok, _ = _is_command_allowed("echo hello | grep h")
        assert ok is True

    def test_blocks_empty_command(self):
        ok, reason = _is_command_allowed("")
        assert ok is False
        assert "Empty" in reason

    def test_blocks_sudo(self):
        ok, reason = _is_command_allowed("sudo apt install")
        assert ok is False
        assert "Privilege" in reason

    def test_blocks_su(self):
        ok, reason = _is_command_allowed("su - root")
        assert ok is False

    def test_blocks_dangerous_patterns(self):
        ok, reason = _is_command_allowed("rm -rf /")
        assert ok is False
        assert "Blocked" in reason

    def test_blocks_oversized_command(self):
        ok, reason = _is_command_allowed("a" * 5000)
        assert ok is False
        assert "maximum length" in reason


class TestShellServiceCreateSession:
    def test_creates_session_successfully(self, tmp_shell_dir):
        service, data_dir, sessions_file, _ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 12345
            mock_popen.return_value.__enter__ = lambda s: s
            mock_popen.return_value.__exit__ = lambda s, *a: None
            session = service.create_session(name="Test Session")

        assert session.id is not None
        assert session.name == "Test Session"
        assert session.status == "active"
        assert session.pid == 12345
        assert session.cwd == str(Path.home())

    def test_persists_sessions(self, tmp_shell_dir):
        service, data_dir, sessions_file, _ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 11111
            service.create_session()
        assert sessions_file.exists()
        data = json.loads(sessions_file.read_text())
        assert len(data["sessions"]) == 1


class TestShellServiceExecuteCommand:
    def test_returns_session_not_found(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        result = service.execute_command("nonexistent", "ls")
        assert result["success"] is False
        assert result["error"] == "session_not_found"

    def test_returns_command_blocked(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 22222
            service.create_session()

        session_id = list(service._sessions.keys())[0]
        result = service.execute_command(session_id, "sudo rm -rf /")
        assert result["success"] is False
        assert result["error"] == "command_blocked"

    def test_executes_command_successfully(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 33333
            service.create_session()

        session_id = list(service._sessions.keys())[0]

        mock_result = type(
            "CMD",
            (),
            {
                "returncode": 0,
                "stdout": "hello world\n",
                "stderr": "",
            },
        )()

        with patch("ai.shell_service.subprocess.run", return_value=mock_result):
            result = service.execute_command(session_id, "echo hello world")

        assert result["success"] is True
        assert result["stdout"] == "hello world\n"

    def test_handles_command_timeout(self, tmp_shell_dir):
        import subprocess

        service, *_ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 44444
            service.create_session()

        session_id = list(service._sessions.keys())[0]

        with patch(
            "ai.shell_service.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)
        ):
            result = service.execute_command(session_id, "sleep 999")

        assert result["success"] is False
        assert result["error"] == "command_timeout"

    def test_handles_command_not_found(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 55555
            service.create_session()

        session_id = list(service._sessions.keys())[0]

        with patch(
            "ai.shell_service.subprocess.run", side_effect=FileNotFoundError("No such file")
        ):
            result = service.execute_command(session_id, "nonexistent_cmd")

        assert result["success"] is False
        assert result["error"] == "command_not_found"


class TestShellServiceTerminateSession:
    def test_terminates_active_session(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 66666
            service.create_session()

        session_id = list(service._sessions.keys())[0]
        with patch("ai.shell_service.os.kill"):
            result = service.terminate_session(session_id)

        assert result["success"] is True
        assert service._sessions[session_id].status == "disconnected"

    def test_returns_error_for_missing_session(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        result = service.terminate_session("nonexistent")
        assert result["success"] is False
        assert result["error"] == "session_not_found"


class TestShellServiceGetSessionContext:
    def test_returns_context_for_session(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 77777
            service.create_session()

        session_id = list(service._sessions.keys())[0]
        context = service.get_session_context(session_id)

        assert context is not None
        assert context["session_id"] == session_id
        assert "user" in context
        assert "hostname" in context
        assert "cwd" in context

    def test_returns_error_for_missing_session(self, tmp_shell_dir):
        service, *_ = tmp_shell_dir
        result = service.get_session_context("nonexistent")
        assert result.get("error") == "session_not_found"


class TestShellServiceAuditLog:
    def test_logs_session_creation(self, tmp_shell_dir):
        service, _, _, audit_file = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 88888
            service.create_session()

        assert audit_file.exists()
        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) >= 1
        entry = json.loads(lines[0])
        assert entry["action"] == "session_created"

    def test_retrieves_audit_log(self, tmp_shell_dir):
        service, _, _, _ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 99999
            service.create_session()

        entries = service.get_audit_log()
        assert isinstance(entries, list)

    def test_filters_by_session_id(self, tmp_shell_dir):
        service, _, _, _ = tmp_shell_dir
        with patch("ai.shell_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 100001
            s1 = service.create_session(name="s1")
            service.create_session(name="s2")

        entries = service.get_audit_log(session_id=s1.id)
        assert all(e["session_id"] == s1.id for e in entries)
