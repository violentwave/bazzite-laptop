"""Context model for workspace, actor, and project isolation.

This module provides the canonical context model for P129:
- Workspace: top-level isolation boundary
- Actor: operator identity (from P128)
- Project: workbench project (from P123-P124)
- Session: workbench/shell session
- Artifact scope: path restrictions
- Audit correlation: for tracing events

No cloud auth - local-only context tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def generate_context_id(prefix: str = "ctx") -> str:
    """Generate a unique context ID."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"session-{uuid.uuid4().hex[:12]}"


@dataclass
class WorkspaceContext:
    """Workspace is the top-level isolation boundary."""

    workspace_id: str
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, name: str, metadata: dict[str, Any] | None = None) -> WorkspaceContext:
        """Create a new workspace."""
        return cls(
            workspace_id=generate_context_id("ws"),
            name=name,
            metadata=metadata or {},
        )


@dataclass
class ActorContext:
    """Actor represents the operator identity (from P128)."""

    actor_id: str
    workspace_id: str
    identity_id: str | None = None
    step_up_level: str = "none"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls, workspace_id: str, identity_id: str | None = None, step_up_level: str = "none"
    ) -> ActorContext:
        """Create a new actor context."""
        return cls(
            actor_id=generate_context_id("actor"),
            workspace_id=workspace_id,
            identity_id=identity_id,
            step_up_level=step_up_level,
        )


@dataclass
class ProjectContext:
    """Project is a workbench project (from P123-P124)."""

    project_id: str
    workspace_id: str
    name: str
    root_path: str
    actor_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workspace_id: str,
        actor_id: str,
        name: str,
        root_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectContext:
        """Create a new project context."""
        return cls(
            project_id=generate_context_id("proj"),
            workspace_id=workspace_id,
            actor_id=actor_id,
            name=name,
            root_path=root_path,
            metadata=metadata or {},
        )


@dataclass
class SessionContext:
    """Session is a workbench or shell session."""

    session_id: str
    workspace_id: str
    actor_id: str
    project_id: str | None
    session_type: str
    cwd: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workspace_id: str,
        actor_id: str,
        project_id: str | None,
        session_type: str,
        cwd: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionContext:
        """Create a new session context."""
        return cls(
            session_id=generate_session_id(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_type=session_type,
            cwd=cwd,
            metadata=metadata or {},
        )


@dataclass
class AuditContext:
    """Audit context for correlating events across the system."""

    correlation_id: str
    workspace_id: str
    actor_id: str
    project_id: str | None = None
    session_id: str | None = None
    operation: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workspace_id: str,
        actor_id: str,
        operation: str,
        project_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditContext:
        """Create a new audit context."""
        return cls(
            correlation_id=f"audit-{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            operation=operation,
            metadata=metadata or {},
        )


@dataclass
class ArtifactScope:
    """Artifact scope defines path restrictions for file operations."""

    root_path: str
    allowed_extensions: list[str] = field(default_factory=list)
    max_size_mb: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextValidator:
    """Validates context boundaries and prevents cross-project leakage."""

    @staticmethod
    def validate_path_in_scope(path: str, scope: ArtifactScope) -> bool:
        """Validate that a path is within the artifact scope."""
        import os

        try:
            abs_path = os.path.abspath(path)
            abs_root = os.path.abspath(scope.root_path)
            return abs_path.startswith(abs_root + os.sep) or abs_path == abs_root
        except Exception:
            return False

    @staticmethod
    def validate_workspace_match(ctx1: WorkspaceContext, ctx2: WorkspaceContext) -> bool:
        """Validate two contexts are in the same workspace."""
        return ctx1.workspace_id == ctx2.workspace_id

    @staticmethod
    def can_access_project(
        session_workspace_id: str, session_project_id: str, target_project_id: str
    ) -> bool:
        """Check if a session can access a target project."""
        return session_project_id == target_project_id


def create_workspace(name: str, metadata: dict[str, Any] | None = None) -> WorkspaceContext:
    """Create a new workspace context."""
    return WorkspaceContext.create(name, metadata)


def create_project(
    workspace_id: str,
    actor_id: str,
    name: str,
    root_path: str,
    metadata: dict[str, Any] | None = None,
) -> ProjectContext:
    """Create a new project context."""
    return ProjectContext.create(workspace_id, actor_id, name, root_path, metadata)


def create_session(
    workspace_id: str,
    actor_id: str,
    project_id: str | None,
    session_type: str,
    cwd: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SessionContext:
    """Create a new session context."""
    return SessionContext.create(workspace_id, actor_id, project_id, session_type, cwd, metadata)


def create_audit_context(
    workspace_id: str,
    actor_id: str,
    operation: str,
    project_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditContext:
    """Create a new audit context."""
    return AuditContext.create(workspace_id, actor_id, operation, project_id, session_id, metadata)
