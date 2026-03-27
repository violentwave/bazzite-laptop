"""Tests for scripts/newelle-exec.sh and scripts/newelle-sudo.sh."""

import os
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
EXEC_SCRIPT = SCRIPTS_DIR / "newelle-exec.sh"
SUDO_SCRIPT = SCRIPTS_DIR / "newelle-sudo.sh"


class TestNewelleExec:
    def test_script_exists(self):
        assert EXEC_SCRIPT.exists(), "newelle-exec.sh not found"

    def test_script_is_executable(self):
        assert os.access(EXEC_SCRIPT, os.X_OK), "newelle-exec.sh is not executable"

    def test_shellcheck_clean(self):
        result = subprocess.run(
            ["shellcheck", str(EXEC_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"shellcheck errors:\n{result.stdout}"


class TestNewelleSudo:
    def test_script_exists(self):
        assert SUDO_SCRIPT.exists(), "newelle-sudo.sh not found"

    def test_script_is_executable(self):
        assert os.access(SUDO_SCRIPT, os.X_OK), "newelle-sudo.sh is not executable"

    def test_shellcheck_clean(self):
        result = subprocess.run(
            ["shellcheck", str(SUDO_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"shellcheck errors:\n{result.stdout}"

    def test_rejects_unlisted_command(self):
        result = subprocess.run(
            [str(SUDO_SCRIPT), "rm", "-rf", "/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not in allowlist" in result.stderr

    def test_rejects_empty_args(self):
        result = subprocess.run(
            [str(SUDO_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Usage:" in result.stderr

    def test_rejects_partial_allowlist_match(self):
        # Only "systemctl start system-health.service" is allowed —
        # "systemctl start" alone must be rejected.
        result = subprocess.run(
            [str(SUDO_SCRIPT), "systemctl", "start"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not in allowlist" in result.stderr

    def test_rejects_disallowed_service(self):
        result = subprocess.run(
            [str(SUDO_SCRIPT), "systemctl", "start", "sshd.service"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not in allowlist" in result.stderr
