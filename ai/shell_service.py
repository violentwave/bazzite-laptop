"""Interactive Shell Gateway service for managing terminal sessions.

This service provides a local shell session management for the Unified Control Console.
It manages terminal sessions, tracks context, and maintains session audit trails.

P94: Runtime recovery — fixes shell=True security violation, adds precise error
states, atomic file writes, and proper session lifecycle management.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SHELL_DATA_DIR = Path.home() / ".config" / "bazzite-ai" / "shell"
SHELL_DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = SHELL_DATA_DIR / "sessions.json"
AUDIT_LOG_FILE = SHELL_DATA_DIR / "audit.jsonl"

MAX_COMMAND_LENGTH = 4096
MAX_SESSIONS = 10
COMMAND_TIMEOUT = 30

BLOCKED_COMMANDS: frozenset[str] = frozenset(
    {
        "rm -rf /",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",
        "chmod -R 777 /",
        "wget | sh",
        "curl | sh",
    }
)


class ShellSessionCreationError(Exception):
    pass


class ShellSessionNotFoundError(Exception):
    pass


class ShellCommandError(Exception):
    pass


@dataclass
class ShellSession:
    id: str
    name: str
    created_at: str
    updated_at: str
    status: str
    cwd: str
    pid: int | None = None
    command_history: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "cwd": self.cwd,
            "pid": self.pid,
            "command_history": self.command_history[-50:],
            "metadata": self.metadata,
        }


@dataclass
class SessionContext:
    session_id: str
    user: str
    hostname: str
    cwd: str
    shell: str
    start_time: str
    idle_time: int


def _atomic_write(path: Path, content: str) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(tmp_fd, content.encode())
        os.close(tmp_fd)
        os.replace(tmp_path, str(path))
    except OSError:
        try:
            os.close(tmp_fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _is_command_allowed(command: str) -> tuple[bool, str]:
    stripped = command.strip()
    if not stripped:
        return False, "Empty command"
    if len(stripped) > MAX_COMMAND_LENGTH:
        return False, f"Command exceeds maximum length ({MAX_COMMAND_LENGTH} characters)"
    lower = stripped.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in lower:
            return False, f"Blocked command pattern: {blocked}"
    if lower.startswith("sudo ") or lower.startswith("su "):
        return False, "Privilege escalation commands are not allowed"
    return True, ""


class ShellService:
    def __init__(self) -> None:
        self._sessions: dict[str, ShellSession] = {}
        self._load_sessions()

    def _load_sessions(self) -> None:
        try:
            if SESSIONS_FILE.exists():
                data = json.loads(SESSIONS_FILE.read_text())
                for session_data in data.get("sessions", []):
                    session = ShellSession(
                        id=session_data["id"],
                        name=session_data.get("name", f"Session {session_data['id'][:8]}"),
                        created_at=session_data["created_at"],
                        updated_at=session_data["updated_at"],
                        status="disconnected",
                        cwd=session_data.get("cwd", str(Path.home())),
                        pid=None,
                        command_history=session_data.get("command_history", []),
                        metadata=session_data.get("metadata", {}),
                    )
                    self._sessions[session.id] = session
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Failed to load sessions: %s", e)

    def _save_sessions(self) -> None:
        try:
            data = {
                "sessions": [s.to_dict() for s in self._sessions.values()],
                "saved_at": datetime.now().isoformat(),
            }
            _atomic_write(SESSIONS_FILE, json.dumps(data, indent=2))
        except OSError as e:
            logger.error("Failed to save sessions: %s", e)

    def _log_audit(self, action: str, session_id: str, details: dict | None = None) -> None:
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "session_id": session_id,
                "details": details or {},
            }
            line = json.dumps(entry) + "\n"
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(line)
        except OSError as e:
            logger.error("Failed to write audit log: %s", e)

    def _check_session_liveness(self, session: ShellSession) -> str:
        if session.pid and session.status == "active":
            try:
                os.kill(session.pid, 0)
                return "active"
            except (OSError, ProcessLookupError):
                return "disconnected"
        return session.status

    def create_session(
        self, name: str | None = None, cwd: str | None = None, env: dict | None = None
    ) -> ShellSession:
        if len(self._sessions) >= MAX_SESSIONS:
            raise ShellSessionCreationError(f"Maximum number of sessions reached ({MAX_SESSIONS})")

        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        session_cwd = cwd or str(Path.home())

        if not Path(session_cwd).is_dir():
            session_cwd = str(Path.home())

        session_env = os.environ.copy()
        if env:
            session_env.update(env)
        session_env["Bazzite_SESSION_ID"] = session_id

        try:
            process = subprocess.Popen(  # noqa: S607
                ["/usr/bin/env", "bash", "-l"],
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

        except OSError as e:
            logger.error("Failed to create session: %s", e)
            session = ShellSession(
                id=session_id,
                name=name or f"Session {session_id}",
                created_at=now,
                updated_at=now,
                status="error",
                cwd=session_cwd,
                metadata={"error": f"Failed to start shell process: {e}"},
            )
            self._sessions[session_id] = session
            self._save_sessions()
            self._log_audit("session_create_failed", session_id, {"error": str(e)})
            return session

    def get_session(self, session_id: str) -> ShellSession | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        live_status = self._check_session_liveness(session)
        if live_status != session.status:
            session.status = live_status
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()
        return session

    def list_sessions(self) -> list[ShellSession]:
        for session in self._sessions.values():
            live_status = self._check_session_liveness(session)
            if live_status != session.status:
                session.status = live_status
        self._save_sessions()
        return list(self._sessions.values())

    def execute_command(self, session_id: str, command: str) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {
                "success": False,
                "error": "session_not_found",
                "error_detail": f"No session with ID '{session_id}'",
                "operator_action": "List sessions and use a valid session ID",
            }

        if session.status == "error":
            return {
                "success": False,
                "error": "session_error",
                "error_detail": (
                    f"Session '{session_id}' is in error state: "
                    f"{session.metadata.get('error', 'unknown')}"
                ),
                "operator_action": "Terminate this session and create a new one",
            }

        if session.status == "disconnected":
            return {
                "success": False,
                "error": "session_disconnected",
                "error_detail": f"Session '{session_id}' process is no longer running",
                "operator_action": "Create a new session to continue",
            }

        if session.status != "active":
            return {
                "success": False,
                "error": f"session_{session.status}",
                "error_detail": f"Session is in '{session.status}' state",
                "operator_action": "Check session status and create a new session if needed",
            }

        allowed, reason = _is_command_allowed(command)
        if not allowed:
            self._log_audit(
                "command_blocked", session_id, {"command": command[:200], "reason": reason}
            )
            return {
                "success": False,
                "error": "command_blocked",
                "error_detail": reason,
                "operator_action": (
                    "Use allowed commands only; no privilege escalation or destructive patterns"
                ),
            }

        try:
            cmd_parts = shlex.split(command)
            result = subprocess.run(  # noqa: S603
                cmd_parts,
                shell=False,
                cwd=session.cwd,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                env={**os.environ, "Bazzite_SESSION_ID": session_id},
            )

            session.command_history.append(command)
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()

            self._log_audit(
                "command_executed",
                session_id,
                {"command": command[:200], "exit_code": result.returncode},
            )

            response: dict[str, Any] = {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
            }
            if result.stdout:
                response["stdout"] = result.stdout[:4096]
            if result.stderr:
                response["stderr"] = result.stderr[:4096]
            if result.returncode != 0 and not result.stderr:
                response["error"] = f"Command exited with code {result.returncode}"
            return response

        except subprocess.TimeoutExpired:
            self._log_audit("command_timeout", session_id, {"command": command[:200]})
            return {
                "success": False,
                "error": "command_timeout",
                "error_detail": f"Command timed out after {COMMAND_TIMEOUT}s",
                "operator_action": "Try a shorter-running command or increase timeout",
            }
        except FileNotFoundError as e:
            return {
                "success": False,
                "error": "command_not_found",
                "error_detail": f"Command not found: {e}",
                "operator_action": "Check command name and PATH",
            }
        except Exception as e:
            return {
                "success": False,
                "error": "execution_failed",
                "error_detail": str(e),
                "operator_action": "Check the command syntax and try again",
            }

    def terminate_session(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {
                "success": False,
                "error": "session_not_found",
                "error_detail": f"No session with ID '{session_id}'",
            }

        if session.pid and session.status == "active":
            try:
                os.kill(session.pid, 15)
            except (OSError, ProcessLookupError):
                pass

        session.status = "disconnected"
        session.updated_at = datetime.now().isoformat()
        session.pid = None
        self._save_sessions()
        self._log_audit("session_terminated", session_id)
        return {"success": True, "session_id": session_id}

    def get_session_context(self, session_id: str) -> dict | None:
        session = self._sessions.get(session_id)
        if not session:
            return {
                "error": "session_not_found",
                "error_detail": f"No session with ID '{session_id}'",
            }

        live_status = self._check_session_liveness(session)
        if live_status != session.status:
            session.status = live_status
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()

        try:
            updated = datetime.fromisoformat(session.updated_at)
            idle_seconds = int((datetime.now() - updated).total_seconds())
        except (ValueError, TypeError):
            idle_seconds = 0

        return {
            "session_id": session.id,
            "user": os.environ.get("USER", "unknown"),
            "hostname": os.uname().nodename,
            "cwd": session.cwd,
            "shell": session.metadata.get("shell", "bash"),
            "start_time": session.created_at,
            "idle_time": idle_seconds,
            "status": session.status,
            "command_count": len(session.command_history),
        }

    def get_audit_log(self, session_id: str | None = None, limit: int = 100) -> list[dict]:
        entries: list[dict] = []
        try:
            if AUDIT_LOG_FILE.exists():
                with open(AUDIT_LOG_FILE) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if session_id is None or entry.get("session_id") == session_id:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except OSError as e:
            logger.error("Failed to read audit log: %s", e)

        return entries[-limit:]


_shell_service: ShellService | None = None


def get_shell_service() -> ShellService:
    global _shell_service
    if _shell_service is None:
        _shell_service = ShellService()
    return _shell_service


def create_session(name: str | None = None, cwd: str | None = None) -> dict:
    service = get_shell_service()
    try:
        session = service.create_session(name=name, cwd=cwd)
        return session.to_dict()
    except ShellSessionCreationError as e:
        return {
            "success": False,
            "error": "session_limit_reached",
            "error_detail": str(e),
            "operator_action": "Terminate an existing session before creating a new one",
        }


def list_sessions() -> list[dict]:
    service = get_shell_service()
    return [s.to_dict() for s in service.list_sessions()]


def get_session(session_id: str) -> dict:
    service = get_shell_service()
    session = service.get_session(session_id)
    if session:
        return session.to_dict()
    return {
        "success": False,
        "error": "session_not_found",
        "error_detail": f"No session with ID '{session_id}'",
        "operator_action": "List sessions and use a valid session ID",
    }


def execute_command(session_id: str, command: str) -> dict:
    service = get_shell_service()
    return service.execute_command(session_id, command)


def terminate_session(session_id: str) -> dict:
    service = get_shell_service()
    return service.terminate_session(session_id)


def get_session_context(session_id: str) -> dict:
    service = get_shell_service()
    result = service.get_session_context(session_id)
    if result is None:
        return {
            "error": "session_not_found",
            "error_detail": f"No session with ID '{session_id}'",
        }
    return result


def get_audit_log(session_id: str | None = None, limit: int = 100) -> list[dict]:
    service = get_shell_service()
    return service.get_audit_log(session_id=session_id, limit=limit)
