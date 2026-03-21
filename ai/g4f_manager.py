"""Singleton manager for the g4f subprocess.

g4f is GPL v3 -- NEVER import g4f in this module. Only interact via
subprocess + HTTP. This keeps our code license-clean.

g4f subprocess gets a scrubbed environment: all API keys are removed
before spawning to prevent credential leakage.
"""

import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger("ai.g4f_manager")

_MAX_RESTARTS = 3
_RESTART_WINDOW_S = 900
_COOLDOWN_S = 1800
_STARTUP_TIMEOUT_S = 10
_PORT_POLL_INTERVAL_S = 0.5


class G4FManager:
    """Singleton manager for the g4f subprocess."""

    _SCRUB_KEYS = {
        "GROQ_API_KEY", "ZAI_API_KEY", "GEMINI_API_KEY",
        "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "CEREBRAS_API_KEY",
        "CLOUDFLARE_API_KEY", "VT_API_KEY", "OTX_API_KEY", "ABUSEIPDB_KEY",
    }

    def __init__(self, port: int | None = None, idle_timeout: int = 300) -> None:
        self._port = port or int(os.environ.get("G4F_PORT", "1337"))
        self._idle_timeout = idle_timeout
        self._process: subprocess.Popen | None = None
        self._last_request: float = 0.0
        self._restart_count: int = 0
        self._restart_window_start: float = 0.0
        self._cooldown_until: float = 0.0
        xdg = os.environ.get("XDG_RUNTIME_DIR")
        if not xdg:
            raise RuntimeError("XDG_RUNTIME_DIR not set -- cannot create PID file safely")
        self._pid_file = Path(xdg) / "g4f.pid"

    def _clean_env(self) -> dict[str, str]:
        """Return os.environ minus all API keys."""
        return {k: v for k, v in os.environ.items() if k not in self._SCRUB_KEYS}

    def _probe_port(self) -> bool:
        """Check if g4f port is accepting connections."""
        deadline = time.time() + _STARTUP_TIMEOUT_S
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self._port), timeout=1):
                    return True
            except (ConnectionRefusedError, OSError):
                time.sleep(_PORT_POLL_INTERVAL_S)
        return False

    def _health_probe(self) -> bool:
        """Send a minimal test request to verify g4f is responding."""
        try:
            import httpx
            resp = httpx.get(f"http://127.0.0.1:{self._port}/v1/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _build_command(self) -> list[str]:
        """Build the g4f launch command with sandboxing."""
        # g4f CLI expects --bind as host:port format
        base_cmd = [sys.executable, "-m", "g4f", "api",
                     "--bind", f"127.0.0.1:{self._port}"]
        if shutil.which("systemd-run"):
            return [
                "systemd-run", "--user", "--scope",
                "-p", "ProtectHome=yes",
                "-p", "NoNewPrivileges=yes",
                "-p", "PrivateTmp=yes",
                "-p", "MemoryMax=512M",
                "-p", "ReadOnlyPaths=/",
                *base_cmd,
            ]
        if shutil.which("bwrap"):
            return [
                "bwrap", "--ro-bind", "/", "/",
                "--tmpfs", str(Path.home()),
                "--dev", "/dev", "--proc", "/proc",
                "--unshare-all", "--share-net",
                *base_cmd,
            ]
        logger.warning("Neither systemd-run nor bwrap found, running g4f WITHOUT sandboxing")
        return base_cmd

    def ensure_running(self) -> bool:
        """Start g4f if not running. Returns True if healthy."""
        if self._process is not None and self._process.poll() is None:
            if self._health_probe():
                return True
            self._process.terminate()
            self._process = None

        now = time.time()
        if now < self._cooldown_until:
            logger.warning("g4f circuit breaker open -- cooldown until %.0f", self._cooldown_until)
            return False

        if now - self._restart_window_start > _RESTART_WINDOW_S:
            self._restart_count = 0
            self._restart_window_start = now

        if self._restart_count >= _MAX_RESTARTS:
            self._cooldown_until = now + _COOLDOWN_S
            logger.error("g4f circuit breaker open -- too many restart failures")
            return False

        cmd = self._build_command()
        try:
            self._process = subprocess.Popen(
                cmd, env=self._clean_env(),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError) as e:
            logger.error("Failed to start g4f: %s", e)
            self._restart_count += 1
            return False

        if not self._probe_port():
            logger.error("g4f did not bind port %d within %ds", self._port, _STARTUP_TIMEOUT_S)
            self._restart_count += 1
            return False

        if not self._health_probe():
            logger.error("g4f health probe failed after startup")
            self._restart_count += 1
            return False

        try:
            self._pid_file.write_text(str(self._process.pid))
        except OSError as e:
            logger.warning("Failed to write PID file: %s", e)

        logger.info("g4f started on port %d (PID %d)", self._port, self._process.pid)
        return True

    def stop(self) -> None:
        """Kill g4f subprocess and remove PID file."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError:
            pass

    def idle_check(self) -> None:
        """Kill g4f if no requests for idle_timeout seconds."""
        if self._process is None or self._process.poll() is not None:
            return
        if time.time() - self._last_request > self._idle_timeout:
            logger.info("g4f idle timeout -- stopping")
            self.stop()

    def record_request(self) -> None:
        """Update last_request timestamp."""
        self._last_request = time.time()

    @property
    def is_running(self) -> bool:
        """True if the g4f process is alive."""
        return self._process is not None and self._process.poll() is None


_manager: G4FManager | None = None


def get_manager() -> G4FManager:
    """Get or create the module-level G4FManager singleton."""
    global _manager
    if _manager is None:
        _manager = G4FManager()
    return _manager
