"""Unit tests for ai/g4f_manager.py — g4f subprocess lifecycle."""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

_XDG = os.environ.get("XDG_RUNTIME_DIR", "/tmp/test-xdg")


@pytest.fixture(autouse=True)
def _set_xdg_runtime(tmp_path):
    with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(tmp_path)}):
        yield


@pytest.fixture()
def manager():
    from ai.g4f_manager import G4FManager
    return G4FManager(port=19999, idle_timeout=5)


class TestInit:
    def test_default_port_from_env(self, tmp_path):
        from ai.g4f_manager import G4FManager
        with patch.dict(os.environ, {"G4F_PORT": "4242", "XDG_RUNTIME_DIR": str(tmp_path)}):
            m = G4FManager()
            assert m._port == 4242

    def test_default_port_fallback(self, tmp_path):
        from ai.g4f_manager import G4FManager
        env = os.environ.copy()
        env.pop("G4F_PORT", None)
        env["XDG_RUNTIME_DIR"] = str(tmp_path)
        with patch.dict(os.environ, env, clear=True):
            m = G4FManager()
            assert m._port == 1337

    def test_missing_xdg_raises(self):
        from ai.g4f_manager import G4FManager
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="XDG_RUNTIME_DIR"):
                G4FManager()

    def test_pid_file_path(self, manager, tmp_path):
        assert manager._pid_file == tmp_path / "g4f.pid"


class TestCleanEnv:
    def test_scrubs_all_api_keys(self, manager):
        scrub_keys = {
            "GROQ_API_KEY", "ZAI_API_KEY", "GEMINI_API_KEY",
            "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "CEREBRAS_API_KEY",
            "CLOUDFLARE_API_KEY", "VT_API_KEY", "OTX_API_KEY", "ABUSEIPDB_KEY",
        }
        fake_env = {k: "secret" for k in scrub_keys}
        fake_env["PATH"] = "/usr/bin"
        fake_env["HOME"] = "/home/test"
        with patch.dict(os.environ, fake_env):
            clean = manager._clean_env()
        for key in scrub_keys:
            assert key not in clean
        assert clean["PATH"] == "/usr/bin"
        assert clean["HOME"] == "/home/test"


class TestEnsureRunning:
    @patch("ai.g4f_manager.subprocess.Popen")
    @patch("ai.g4f_manager.G4FManager._probe_port", return_value=True)
    @patch("ai.g4f_manager.G4FManager._health_probe", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/systemd-run")
    def test_starts_subprocess(self, _which, _health, _probe, mock_popen, manager):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        assert manager.ensure_running() is True
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args
        env = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env")
        assert "GROQ_API_KEY" not in (env or {})

    @patch("ai.g4f_manager.subprocess.Popen")
    @patch("ai.g4f_manager.G4FManager._probe_port", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/systemd-run")
    def test_returns_false_on_port_timeout(self, _which, _probe, mock_popen, manager):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        assert manager.ensure_running() is False

    def test_circuit_breaker_after_three_failures(self, manager):
        manager._restart_count = 3
        manager._restart_window_start = time.time()
        assert manager.ensure_running() is False

    @patch("ai.g4f_manager.subprocess.Popen")
    @patch("ai.g4f_manager.G4FManager._probe_port", return_value=True)
    @patch("ai.g4f_manager.G4FManager._health_probe", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/systemd-run")
    def test_writes_pid_file(self, _which, _health, _probe, mock_popen, manager):
        mock_proc = MagicMock()
        mock_proc.pid = 54321
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        manager.ensure_running()
        assert manager._pid_file.exists()
        assert manager._pid_file.read_text().strip() == "54321"

    def test_reuses_existing_process(self, manager):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        manager._process = mock_proc
        with patch.object(manager, "_health_probe", return_value=True):
            assert manager.ensure_running() is True


class TestStop:
    def test_terminates_process(self, manager):
        mock_proc = MagicMock()
        manager._process = mock_proc
        manager._pid_file.parent.mkdir(parents=True, exist_ok=True)
        manager._pid_file.write_text("12345")
        manager.stop()
        mock_proc.terminate.assert_called_once()
        assert not manager._pid_file.exists()
        assert manager._process is None

    def test_stop_no_process_is_noop(self, manager):
        manager.stop()


class TestIdleCheck:
    def test_kills_after_idle_timeout(self, manager):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        manager._process = mock_proc
        manager._last_request = time.time() - 10
        manager.idle_check()
        mock_proc.terminate.assert_called_once()

    def test_keeps_alive_within_timeout(self, manager):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        manager._process = mock_proc
        manager._last_request = time.time()
        manager.idle_check()
        mock_proc.terminate.assert_not_called()


class TestRecordRequest:
    def test_updates_timestamp(self, manager):
        before = time.time()
        manager.record_request()
        assert manager._last_request >= before
