"""Context module for P129 — Workspace and Actor Context Isolation.

This module provides:
- Context models (workspace, actor, project, session, audit)
- Isolation enforcement (path validation, cross-project checks)
- Path utilities for artifact scope

No cloud auth - local-only context tracking.
"""

from ai.context.isolation import (
    ContextIsolationManager,
    IsolationError,
    IsolationResult,
    attach_audit_context,
    check_cross_project_access,
    enforce_session_workspace,
    get_context_manager,
    sanitize_for_logging,
    validate_artifact_path,
)
from ai.context.models import (
    AuditContext,
    ProjectContext,
    SessionContext,
    WorkspaceContext,
    create_audit_context,
    create_project,
    create_session,
    create_workspace,
)
from ai.context.paths import (
    get_project_safe_paths,
    is_safe_path,
    resolve_path,
    sanitize_path_for_display,
    validate_artifact_operation,
)

__all__ = [
    "WorkspaceContext",
    "ActorContext",
    "ProjectContext",
    "SessionContext",
    "AuditContext",
    "ArtifactScope",
    "ContextValidator",
    "create_workspace",
    "create_project",
    "create_session",
    "create_audit_context",
    "IsolationError",
    "IsolationResult",
    "attach_audit_context",
    "check_cross_project_access",
    "enforce_session_workspace",
    "validate_artifact_path",
    "sanitize_for_logging",
    "get_context_manager",
    "ContextIsolationManager",
    "is_safe_path",
    "resolve_path",
    "sanitize_path_for_display",
    "validate_artifact_operation",
    "get_project_safe_paths",
]
