"""Persistent project registry for Agent Workbench."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai.agent_workbench.models import ProjectRecord
from ai.agent_workbench.paths import (
    REGISTRY_PATH,
    atomic_write,
    normalize_project_path,
    now_iso,
    parse_allowed_roots,
)


class ProjectRegistry:
    def __init__(
        self,
        *,
        registry_path: Path | None = None,
        allowed_roots: list[str] | None = None,
        allow_non_project_dirs: bool = False,
    ) -> None:
        self._registry_path = registry_path or REGISTRY_PATH
        self._allowed_roots = parse_allowed_roots(allowed_roots)
        self._allow_non_project_dirs = allow_non_project_dirs
        self._projects = self._load()

    def _load(self) -> dict[str, ProjectRecord]:
        if not self._registry_path.exists():
            return {}
        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
            rows = payload.get("projects", []) if isinstance(payload, dict) else []
            return {item["project_id"]: ProjectRecord(**item) for item in rows}
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            return {}

    def _save(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "projects": [proj.to_dict() for proj in self._projects.values()],
            "updated_at": now_iso(),
        }
        atomic_write(self._registry_path, json.dumps(payload, indent=2, sort_keys=True))

    @property
    def allowed_roots(self) -> list[str]:
        return [str(path) for path in self._allowed_roots]

    def list_projects(self) -> list[ProjectRecord]:
        return sorted(self._projects.values(), key=lambda item: item.updated_at, reverse=True)

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self._projects.get(project_id)

    def find_by_root(self, root_path: str) -> ProjectRecord | None:
        for project in self._projects.values():
            if project.root_path == root_path:
                return project
        return None

    def register_project(
        self,
        *,
        path: str,
        name: str | None = None,
        tags: list[str] | None = None,
        description: str = "",
        allow_non_project_dirs: bool | None = None,
    ) -> ProjectRecord:
        allow_non_project = (
            self._allow_non_project_dirs
            if allow_non_project_dirs is None
            else allow_non_project_dirs
        )
        root = normalize_project_path(
            path,
            allowed_roots=self._allowed_roots,
            allow_non_project_dirs=allow_non_project,
        )
        existing = self.find_by_root(str(root))
        now = now_iso()

        if existing:
            existing.name = name or existing.name
            existing.description = description or existing.description
            existing.tags = sorted(set(tags or existing.tags))
            existing.updated_at = now
            self._save()
            return existing

        digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
        project_id = f"proj_{digest}"
        record = ProjectRecord(
            project_id=project_id,
            name=name or root.name,
            root_path=str(root),
            created_at=now,
            updated_at=now,
            tags=sorted(set(tags or [])),
            description=description,
        )
        self._projects[project_id] = record
        self._save()
        return record

    def open_project(self, project_id: str) -> ProjectRecord:
        project = self.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")

        now = now_iso()
        project.last_opened_at = now
        project.updated_at = now
        self._save()
        return project

    def project_status(self, project_id: str) -> dict:
        project = self.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")

        root = Path(project.root_path)
        return {
            "project": project.to_dict(),
            "exists": root.exists(),
            "is_dir": root.is_dir(),
            "allowed_roots": self.allowed_roots,
        }
