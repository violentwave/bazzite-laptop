"""Interactive Shell Gateway service for managing terminal sessions.

This service provides a local shell session management for the Unified Control Console.
It manages terminal sessions, tracks context, and maintains session audit trails.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Shell data directory
SHELL_DATA_DIR = Path.home() / ".config" / "bazzite-ai" / "shell"
SHELL_DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = SHELL_DATA_DIR / "sessions.json"
AUDIT_LOG_FILE = SHELL_DATA_DIR / "audit.jsonl"


@dataclass
class ShellSession:
    """Terminal session data structure."""

    id: str
    name: str
    created_at: str
    updated_at: str
    status: str  # active, idle, disconnected, error
    cwd: str
    pid: int | None = None
    command_history: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "cwd": self.cwd,
            "pid": self.pid,
            "command_history": self.command_history[-50:],  # Last 50 commands
            "metadata": self.metadata,
        }


@dataclass
class SessionContext:
    """Session context for audit/display."""

    session_id: str
    user: str
    hostname: str
    cwd: str
    shell: str
    start_time: str
    idle_time: int  # seconds


class ShellService:
    """Service for managing interactive shell sessions."""

    def __init__(self) -> None:
        """Initialize the shell service."""
        self._sessions: dict[str, ShellSession] = {}
        self._load_sessions()

    def _load_sessions(self) -> None:
        """Load persisted sessions."""
        try:
            if SESSIONS_FILE.exists():
                data = json.loads(SESSIONS_FILE.read_text())
                for session_data in data.get("sessions", []):
                    session = ShellSession(
                        id=session_data["id"],
                        name=session_data.get("name", f"Session {session_data['id'][:8]}"),
                        created_at=session_data["created_at"],
                        updated_at=session_data["updated_at"],
                        status="disconnected",  # Reset to disconnected on load
                        cwd=session_data.get("cwd", str(Path.home())),
                        pid=None,
                        command_history=session_data.get("command_history", []),
                        metadata=session_data.get("metadata", {}),
                    )
                    self._sessions[session.id] = session
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load sessions: {e}")

    def _save_sessions(self) -> None:
        """Persist sessions to disk."""
        try:
            data = {
                "sessions": [s.to_dict() for s in self._sessions.values()],
                "saved_at": datetime.now().isoformat(),
            }
            SESSIONS_FILE.write_text(json.dumps(data, indent=2))
        except OSError as e:
            logger.error(f"Failed to save sessions: {e}")

    def _log_audit(self, action: str, session_id: str, details: dict | None = None) -> None:
        """Log audit entry."""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "session_id": session_id,
                "details": details or {},
            }
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            logger.error(f"Failed to write audit log: {e}")

    def create_session(
        self, name: str | None = None, cwd: str | None = None, env: dict | None = None
    ) -> ShellSession:
        """Create a new terminal session."""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # Get current working directory
        session_cwd = cwd or str(Path.home())

        try:
            # Start shell process
            session_env = os.environ.copy()
            if env:
                session_env.update(env)
            session_env["Bazzite_SESSION_ID"] = session_id

            # Use subprocess to start shell
            process = subprocess.Popen(
                ["bash", "-l"],  # noqa: S607
                cwd=session_cwd,
                env=session_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )

            session = ShellSession(
                id=session_id,
                name=name or f"Session {session_id}",
                created_at=now,
                updated_at=now,
                status="active",
                cwd=session_cwd,
                pid=process.pid,
                metadata={"shell": "bash", "pty": False},
            )

            self._sessions[session_id] = session
            self._save_sessions()
            self._log_audit(
                "session_created", session_id, {"name": session.name, "cwd": session_cwd}
            )

            return session

        except (OSError, ImportError) as e:
            logger.error(f"Failed to create session: {e}")
            session = ShellSession(
                id=session_id,
                name=name or f"Session {session_id}",
                created_at=now,
                updated_at=now,
                status="error",
                cwd=session_cwd,
                metadata={"error": str(e)},
            )
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> ShellSession | None:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session:
            # Check if process is still running
            if session.pid and session.status == "active":
                try:
                    os.kill(session.pid, 0)
                except (OSError, ProcessLookupError):
                    session.status = "disconnected"
                    self._save_sessions()
        return session

    def list_sessions(self) -> list[ShellSession]:
        """List all sessions."""
        # Update status for active sessions
        for session in self._sessions.values():
            if session.pid and session.status == "active":
                try:
                    os.kill(session.pid, 0)
                except (OSError, ProcessLookupError):
                    session.status = "disconnected"

        self._save_sessions()
        return list(self._sessions.values())

    def execute_command(self, session_id: str, command: str) -> dict:
        """Execute a command in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if session.status != "active":
            return {"success": False, "error": f"Session is {session.status}"}

        try:
            # Execute command via subprocess
            result = subprocess.run(  # noqa: S602
                command,
                shell=True,
                cwd=session.cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Update session
            session.command_history.append(command)
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()

            self._log_audit(
                "command_executed",
                session_id,
                {"command": command, "exit_code": result.returncode},
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.pid and session.status == "active":
            try:
                os.kill(session.pid, 15)  # SIGTERM
                session.status = "disconnected"
                session.updated_at = datetime.now().isoformat()
                self._save_sessions()
                self._log_audit("session_terminated", session_id)
                return True
            except (OSError, ProcessLookupError):
                session.status = "disconnected"
                self._save_sessions()
                return True

        session.status = "disconnected"
        self._save_sessions()
        return True

    def get_session_context(self, session_id: str) -> SessionContext | None:
        """Get session context for display."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Calculate idle time
        try:
            updated = datetime.fromisoformat(session.updated_at)
            idle_seconds = int((datetime.now() - updated).total_seconds())
        except (ValueError, TypeError):
            idle_seconds = 0

        return SessionContext(
            session_id=session.id,
            user=os.environ.get("USER", "unknown"),
            hostname=os.uname().nodename,
            cwd=session.cwd,
            shell=session.metadata.get("shell", "bash"),
            start_time=session.created_at,
            idle_time=idle_seconds,
        )

    def get_audit_log(self, session_id: str | None = None, limit: int = 100) -> list[dict]:
        """Get audit log entries."""
        entries = []
        try:
            if AUDIT_LOG_FILE.exists():
                with open(AUDIT_LOG_FILE) as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        if session_id is None or entry.get("session_id") == session_id:
                            entries.append(entry)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read audit log: {e}")

        return entries[-limit:]


# Singleton instance
_shell_service: ShellService | None = None


def get_shell_service() -> ShellService:
    """Get the singleton shell service instance."""
    global _shell_service
    if _shell_service is None:
        _shell_service = ShellService()
    return _shell_service


# MCP tool functions


def create_session(name: str | None = None, cwd: str | None = None) -> dict:
    """Create a new shell session (for MCP)."""
    service = get_shell_service()
    session = service.create_session(name=name, cwd=cwd)
    return session.to_dict()


def list_sessions() -> list[dict]:
    """List all sessions (for MCP)."""
    service = get_shell_service()
    return [s.to_dict() for s in service.list_sessions()]


def get_session(session_id: str) -> dict | None:
    """Get session details (for MCP)."""
    service = get_shell_service()
    session = service.get_session(session_id)
    return session.to_dict() if session else None


def execute_command(session_id: str, command: str) -> dict:
    """Execute command in session (for MCP)."""
    service = get_shell_service()
    return service.execute_command(session_id, command)


def terminate_session(session_id: str) -> dict:
    """Terminate a session (for MCP)."""
    service = get_shell_service()
    success = service.terminate_session(session_id)
    return {"success": success, "session_id": session_id}


def get_session_context(session_id: str) -> dict | None:
    """Get session context (for MCP)."""
    service = get_shell_service()
    context = service.get_session_context(session_id)
    if not context:
        return None
    return {
        "session_id": context.session_id,
        "user": context.user,
        "hostname": context.hostname,
        "cwd": context.cwd,
        "shell": context.shell,
        "start_time": context.start_time,
        "idle_time": context.idle_time,
    }


def get_audit_log(session_id: str | None = None, limit: int = 100) -> list[dict]:
    """Get audit log (for MCP)."""
    service = get_shell_service()
    return service.get_audit_log(session_id=session_id, limit=limit)
