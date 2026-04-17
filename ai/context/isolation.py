"""Context isolation enforcement for P129.

This module provides server-side enforcement of workspace/project/actor isolation:
- Decorators to validate context boundaries
- Path restrictions for shell sessions
- Cross-project leakage prevention
- Audit context attachment

UI state is NOT trusted as isolation boundary - all enforcement is server-side.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from ai.context.models import (
    AuditContext,
    create_audit_context,
)


class IsolationError(Exception):
    """Raised when context isolation is violated."""

    pass


@dataclass
class IsolationResult:
    """Result of an isolation check."""

    allowed: bool
    error_code: str | None = None
    error: str | None = None
    context: dict[str, Any] | None = None


def require_workspace_context(workspace_id: str) -> Callable:
    """Decorator to require workspace context for an operation.

    Usage:
        @require_workspace_context(workspace_id)
        def sensitive_operation(...)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not workspace_id or workspace_id.strip() == "":
                raise IsolationError("workspace_id is required for this operation")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_artifact_path(path: str, allowed_root: str) -> IsolationResult:
    """Validate that a path is within the allowed root.

    Rejects:
    - Path traversal (..)
    - Symlink escape
    - Paths outside allowed_root
    """
    try:
        abs_path = os.path.abspath(path)
        abs_root = os.path.abspath(allowed_root)

        if ".." in path:
            return IsolationResult(
                allowed=False,
                error_code="path_traversal",
                error="Path traversal detected",
            )

        if os.path.islink(path):
            real_path = os.path.abspath(os.path.realpath(path))
            if not real_path.startswith(abs_root + os.sep):
                return IsolationResult(
                    allowed=False,
                    error_code="symlink_escape",
                    error="Symlink escape attempt detected",
                )

        if not (abs_path.startswith(abs_root + os.sep) or abs_path == abs_root):
            return IsolationResult(
                allowed=False,
                error_code="path_out_of_scope",
                error=f"Path {path} is not within allowed scope {allowed_root}",
            )

        return IsolationResult(allowed=True, context={"resolved_path": abs_path})
    except Exception as e:
        return IsolationResult(
            allowed=False,
            error_code="path_validation_error",
            error=str(e),
        )


def check_cross_project_access(
    session_project_id: str | None, target_project_id: str
) -> IsolationResult:
    """Check if session can access target project (prevent cross-project leakage)."""
    if session_project_id is None:
        return IsolationResult(
            allowed=False,
            error_code="no_project_context",
            error="Session has no project context",
        )

    if session_project_id != target_project_id:
        return IsolationResult(
            allowed=False,
            error_code="cross_project_access_denied",
            error=f"Cannot access project {target_project_id} from session {session_project_id}",
        )

    return IsolationResult(allowed=True)


def enforce_session_workspace(
    session_workspace_id: str, required_workspace_id: str
) -> IsolationResult:
    """Enforce that session is within required workspace."""
    if session_workspace_id != required_workspace_id:
        return IsolationResult(
            allowed=False,
            error_code="workspace_mismatch",
            error=f"Session workspace {session_workspace_id} != required {required_workspace_id}",
        )

    return IsolationResult(allowed=True)


def attach_audit_context(
    workspace_id: str,
    actor_id: str,
    operation: str,
    project_id: str | None = None,
    session_id: str | None = None,
) -> AuditContext:
    """Create audit context for an operation."""
    return create_audit_context(
        workspace_id=workspace_id,
        actor_id=actor_id,
        operation=operation,
        project_id=project_id,
        session_id=session_id,
    )


def sanitize_for_logging(context: dict[str, Any]) -> dict[str, Any]:
    """Sanitize context for logging - remove sensitive paths and secrets."""
    sanitized = context.copy()

    sensitive_keys = ["secret", "pin", "token", "key", "password", "credential"]
    paths_to_sanitize = ["root_path", "cwd", "artifact_path", "file_path"]

    for key in list(sanitized.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            sanitized[key] = "***REDACTED***"

    for path_key in paths_to_sanitize:
        if path_key in sanitized and sanitized[path_key]:
            sanitized[path_key] = "[PATH_REDACTED]"

    return sanitized


class ContextIsolationManager:
    """Manages context isolation across the system."""

    def __init__(self):
        self._current_context: dict[str, Any] = {}

    def set_context(
        self,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Set current execution context."""
        if workspace_id:
            self._current_context["workspace_id"] = workspace_id
        if actor_id:
            self._current_context["actor_id"] = actor_id
        if project_id:
            self._current_context["project_id"] = project_id
        if session_id:
            self._current_context["session_id"] = session_id

    def get_current_workspace(self) -> str | None:
        """Get current workspace ID."""
        return self._current_context.get("workspace_id")

    def get_current_actor(self) -> str | None:
        """Get current actor ID."""
        return self._current_context.get("actor_id")

    def get_current_project(self) -> str | None:
        """Get current project ID."""
        return self._current_context.get("project_id")

    def clear_context(self) -> None:
        """Clear current context."""
        self._current_context.clear()


_context_manager = ContextIsolationManager()


def get_context_manager() -> ContextIsolationManager:
    """Get the global context manager."""
    return _context_manager
