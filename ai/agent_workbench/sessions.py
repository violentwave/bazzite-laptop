"""Session lifecycle management for Agent Workbench."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from ai.agent_workbench.models import SessionRecord
from ai.agent_workbench.paths import SESSIONS_PATH, atomic_write, now_iso
from ai.agent_workbench.registry import ProjectRegistry

VALID_BACKENDS = {"codex", "opencode", "claude-code", "gemini-cli"}
VALID_STATUSES = {"active", "stopped", "expired"}


class SessionManager:
    def __init__(
        self,
        *,
        registry: ProjectRegistry,
        sessions_path: Path | None = None,
    ) -> None:
        self._registry = registry
        self._sessions_path = sessions_path or SESSIONS_PATH
        self._sessions = self._load()

    def _load(self) -> dict[str, SessionRecord]:
        if not self._sessions_path.exists():
            return {}
        try:
            payload = json.loads(self._sessions_path.read_text(encoding="utf-8"))
            rows = payload.get("sessions", []) if isinstance(payload, dict) else []
            sessions: dict[str, SessionRecord] = {}
            for row in rows:
                record = SessionRecord(**row)
                if record.status not in VALID_STATUSES:
                    record.status = "stopped"
                sessions[record.session_id] = record
            return sessions
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            return {}

    def _save(self) -> None:
        self._sessions_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessions": [session.to_dict() for session in self._sessions.values()],
            "updated_at": now_iso(),
        }
        atomic_write(self._sessions_path, json.dumps(payload, indent=2, sort_keys=True))

    def create_session(
        self,
        *,
        project_id: str,
        backend: str,
        cwd: str | None = None,
        sandbox_profile: str = "conservative",
        lease_minutes: int | None = None,
    ) -> SessionRecord:
        project = self._registry.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")
        if backend not in VALID_BACKENDS:
            raise ValueError("Unsupported backend")

        root = Path(project.root_path)
        session_cwd = Path(cwd).expanduser().resolve(strict=False) if cwd else root
        if not session_cwd.exists() or not session_cwd.is_dir():
            raise ValueError("Session cwd is invalid")
        try:
            session_cwd.relative_to(root)
        except ValueError as exc:
            raise ValueError("Session cwd must stay within project root") from exc

        created = now_iso()
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        expires_at = None
        if lease_minutes and lease_minutes > 0:
            from datetime import UTC, datetime, timedelta

            expires = datetime.now(UTC) + timedelta(minutes=lease_minutes)
            expires_at = expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")

        record = SessionRecord(
            session_id=session_id,
            project_id=project_id,
            backend=backend,
            cwd=str(session_cwd),
            status="active",
            sandbox_profile=sandbox_profile,
            created_at=created,
            updated_at=created,
            expires_at=expires_at,
        )
        self._sessions[session_id] = record
        self._save()
        return record

    def list_sessions(
        self, *, project_id: str | None = None, status: str | None = None
    ) -> list[SessionRecord]:
        rows = list(self._sessions.values())
        if project_id:
            rows = [row for row in rows if row.project_id == project_id]
        if status:
            rows = [row for row in rows if row.status == status]
        return sorted(rows, key=lambda item: item.updated_at, reverse=True)

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def stop_session(self, session_id: str) -> SessionRecord:
        record = self._sessions.get(session_id)
        if record is None:
            raise ValueError("Session not found")
        record.status = "stopped"
        record.updated_at = now_iso()
        self._save()
        return record
