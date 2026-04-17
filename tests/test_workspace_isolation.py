"""Tests for workspace/actor context isolation (P129).

These tests verify:
- Context creation (workspace, actor, project, session, audit)
- Path validation and traversal rejection
- Symlink escape rejection
- Cross-project access rejection
- Audit context generation
- Context manager behavior
"""



from ai.context import (
    check_cross_project_access,
    create_audit_context,
    create_project,
    create_session,
    create_workspace,
    enforce_session_workspace,
    get_context_manager,
    get_project_safe_paths,
    is_safe_path,
    resolve_path,
    sanitize_for_logging,
    validate_artifact_operation,
    validate_artifact_path,
)


class TestContextCreation:
    """Tests for context creation."""

    def test_create_workspace(self):
        """Can create workspace context."""
        ws = create_workspace("test-workspace", {"description": "Test"})
        assert ws.workspace_id.startswith("ws-")
        assert ws.name == "test-workspace"
        assert ws.metadata["description"] == "Test"

    def test_create_project(self):
        """Can create project context."""
        ws = create_workspace("test-workspace")
        proj = create_project(ws.workspace_id, "actor-123", "MyProject", "/home/user/project")
        assert proj.project_id.startswith("proj-")
        assert proj.workspace_id == ws.workspace_id
        assert proj.actor_id == "actor-123"
        assert proj.name == "MyProject"
        assert proj.root_path == "/home/user/project"

    def test_create_session(self):
        """Can create session context."""
        ws = create_workspace("test-workspace")
        session = create_session(
            ws.workspace_id, "actor-123", "proj-456", "workbench", cwd="/home/user"
        )
        assert session.session_id.startswith("session-")
        assert session.workspace_id == ws.workspace_id
        assert session.actor_id == "actor-123"
        assert session.project_id == "proj-456"
        assert session.session_type == "workbench"

    def test_create_audit_context(self):
        """Can create audit context."""
        ws = create_workspace("test-workspace")
        audit = create_audit_context(
            ws.workspace_id,
            "actor-123",
            "file.read",
            project_id="proj-456",
            session_id="session-789",
        )
        assert audit.correlation_id.startswith("audit-")
        assert audit.workspace_id == ws.workspace_id
        assert audit.actor_id == "actor-123"
        assert audit.operation == "file.read"
        assert audit.project_id == "proj-456"
        assert audit.session_id == "session-789"


class TestPathValidation:
    """Tests for path validation and restriction."""

    def test_path_traversal_rejected(self, tmp_path):
        """Path traversal (..) is rejected."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()

        result = validate_artifact_path(str(allowed / ".." / "etc" / "passwd"), str(allowed))
        assert result.allowed is False
        assert result.error_code == "path_traversal"

    def test_path_outside_scope_rejected(self, tmp_path):
        """Path outside allowed root is rejected."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()

        result = validate_artifact_path("/etc/passwd", str(allowed))
        assert result.allowed is False
        assert result.error_code == "path_out_of_scope"

    def test_path_within_scope_allowed(self, tmp_path):
        """Path within allowed root is accepted."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        file_path = allowed / "file.txt"
        file_path.write_text("test")

        result = validate_artifact_path(str(file_path), str(allowed))
        assert result.allowed is True

    def test_is_safe_path_traversal(self, tmp_path):
        """is_safe_path rejects traversal."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        assert is_safe_path(str(allowed / ".." / "secret"), str(allowed)) is False

    def test_is_safe_path_valid(self, tmp_path):
        """is_safe_path accepts valid paths."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        assert is_safe_path(str(allowed / "file.txt"), str(allowed)) is True

    def test_resolve_path_returns_none_for_invalid(self, tmp_path):
        """resolve_path returns None for invalid paths."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        assert resolve_path(str(allowed / ".." / "secret"), str(allowed)) is None


class TestSymlinkHandling:
    """Tests for symlink escape prevention."""

    def test_symlink_escape_rejected(self, tmp_path):
        """Symlink pointing outside allowed root is rejected."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "secret.txt"
        outside_file.write_text("secret")

        link = allowed / "link"
        link.symlink_to(outside_file)

        result = validate_artifact_path(str(link), str(allowed))
        assert result.allowed is False
        assert result.error_code == "symlink_escape"


class TestCrossProjectAccess:
    """Tests for cross-project access prevention."""

    def test_same_project_allowed(self):
        """Same project access is allowed."""
        result = check_cross_project_access("proj-123", "proj-123")
        assert result.allowed is True

    def test_cross_project_denied(self):
        """Cross-project access is denied."""
        result = check_cross_project_access("proj-123", "proj-456")
        assert result.allowed is False
        assert result.error_code == "cross_project_access_denied"

    def test_no_project_context_denied(self):
        """Access without project context is denied."""
        result = check_cross_project_access(None, "proj-456")
        assert result.allowed is False
        assert result.error_code == "no_project_context"


class TestWorkspaceEnforcement:
    """Tests for workspace context enforcement."""

    def test_same_workspace_allowed(self):
        """Same workspace is allowed."""
        result = enforce_session_workspace("ws-123", "ws-123")
        assert result.allowed is True

    def test_different_workspace_denied(self):
        """Different workspace is denied."""
        result = enforce_session_workspace("ws-123", "ws-456")
        assert result.allowed is False
        assert result.error_code == "workspace_mismatch"


class TestContextManager:
    """Tests for context manager."""

    def test_set_and_get_context(self):
        """Can set and get context values."""
        manager = get_context_manager()
        manager.clear_context()

        manager.set_context(workspace_id="ws-123", actor_id="actor-456", project_id="proj-789")
        assert manager.get_current_workspace() == "ws-123"
        assert manager.get_current_actor() == "actor-456"
        assert manager.get_current_project() == "proj-789"

    def test_clear_context(self):
        """Can clear context."""
        manager = get_context_manager()
        manager.set_context(workspace_id="ws-123")
        manager.clear_context()
        assert manager.get_current_workspace() is None


class TestSanitization:
    """Tests for context sanitization."""

    def test_sanitize_secrets(self):
        """Secrets are redacted in logging."""
        context = {"secret_key": "super-secret", "pin": "1234", "token": "abc123"}
        sanitized = sanitize_for_logging(context)
        assert sanitized["secret_key"] == "***REDACTED***"
        assert sanitized["pin"] == "***REDACTED***"
        assert sanitized["token"] == "***REDACTED***"

    def test_sanitize_paths(self):
        """Paths are redacted in logging."""
        context = {"root_path": "/home/user/project", "cwd": "/home/user"}
        sanitized = sanitize_for_logging(context)
        assert sanitized["root_path"] == "[PATH_REDACTED]"
        assert sanitized["cwd"] == "[PATH_REDACTED]"


class TestArtifactOperationValidation:
    """Tests for artifact operation validation."""

    def test_valid_read_operation(self, tmp_path):
        """Valid read operation is allowed."""
        root = tmp_path / "project"
        root.mkdir()
        (root / "file.txt").write_text("content")

        result = validate_artifact_operation("read", str(root / "file.txt"), str(root))
        assert result["valid"] is True

    def test_invalid_extension(self, tmp_path):
        """Invalid extension is rejected."""
        root = tmp_path / "project"
        root.mkdir()
        (root / "file.exe").write_text("malware")

        result = validate_artifact_operation(
            "read", str(root / "file.exe"), str(root), allowed_extensions=[".txt", ".md"]
        )
        assert result["valid"] is False

    def test_traversal_in_artifact_operation(self, tmp_path):
        """Traversal in artifact operation is rejected."""
        root = tmp_path / "project"
        root.mkdir()

        result = validate_artifact_operation("read", str(root / ".." / "etc" / "passwd"), str(root))
        assert result["valid"] is False

    def test_get_project_safe_paths(self, tmp_path):
        """Can get safe path mappings."""
        root = tmp_path / "project"
        paths = get_project_safe_paths(str(root))
        assert paths["root"] == str(root)
        assert paths["src"] == str(root / "src")
        assert paths["tests"] == str(root / "tests")
        assert paths["docs"] == str(root / "docs")
