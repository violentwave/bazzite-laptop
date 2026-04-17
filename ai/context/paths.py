"""Path utilities for context isolation.

Provides path validation, sanitization, and restriction helpers.
"""

from __future__ import annotations

import os
from typing import Any


def is_safe_path(path: str, allowed_root: str) -> bool:
    """Check if path is within allowed root.

    Rejects:
    - Path traversal (..)
    - Absolute paths outside allowed_root
    - Symlink escapes
    """
    try:
        abs_path = os.path.abspath(path)
        abs_root = os.path.abspath(allowed_root)

        if ".." in path:
            return False

        if os.path.islink(path):
            real_path = os.path.abspath(os.path.realpath(path))
            if not real_path.startswith(abs_root + os.sep):
                return False
            return True

        return abs_path.startswith(abs_root + os.sep) or abs_path == abs_root
    except Exception:
        return False


def resolve_path(path: str, allowed_root: str) -> str | None:
    """Resolve path and return absolute path if valid, else None."""
    if not is_safe_path(path, allowed_root):
        return None

    try:
        return os.path.abspath(path)
    except Exception:
        return None


def sanitize_path_for_display(path: str) -> str:
    """Sanitize path for display in UI/logs - hide real paths."""
    return "[PATH_REDACTED]"


def get_project_safe_paths(project_root: str) -> dict[str, str]:
    """Get safe path mappings for a project."""
    return {
        "root": project_root,
        "src": os.path.join(project_root, "src"),
        "tests": os.path.join(project_root, "tests"),
        "docs": os.path.join(project_root, "docs"),
    }


def validate_artifact_operation(
    operation: str, path: str, scope_root: str, allowed_extensions: list[str] | None = None
) -> dict[str, Any]:
    """Validate an artifact operation against scope.

    Args:
        operation: Operation type (read, write, delete)
        path: Target path
        scope_root: Allowed root directory
        allowed_extensions: Optional list of allowed file extensions

    Returns:
        dict with 'valid' bool and 'error' str if invalid
    """
    if not is_safe_path(path, scope_root):
        return {"valid": False, "error": f"Path {path} is outside scope {scope_root}"}

    if allowed_extensions:
        ext = os.path.splitext(path)[1]
        if ext not in allowed_extensions:
            return {"valid": False, "error": f"Extension {ext} not allowed"}

    if operation == "write":
        parent = os.path.dirname(path)
        if not os.access(parent, os.W_OK):
            return {"valid": False, "error": f"Directory {parent} is not writable"}

    return {"valid": True}
