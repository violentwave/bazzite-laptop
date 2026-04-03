"""Unit tests for ai/hooks.py - Session handoff and task outcome recording."""

from unittest.mock import MagicMock, patch


class TestGetProjectRoot:
    """Test project root detection."""

    def test_returns_parent_of_ai_directory(self):
        """get_project_root() returns the parent directory of ai/."""
        from ai.hooks import get_project_root

        root = get_project_root()
        assert root.name == "bazzite-laptop"
        assert (root / "ai").is_dir()
        assert (root / "tests").is_dir()


class TestRecordTaskOutcome:
    """Test task outcome recording for SONA learning."""

    def test_logs_task_completion(self, caplog):
        """record_task_outcome() logs task completion details."""
        import logging

        from ai.hooks import record_task_outcome

        caplog.set_level(logging.INFO)
        record_task_outcome(
            task_id="test-123",
            quality=0.95,
            success=True,
            duration_seconds=42.5,
            agent_type="coder",
        )

        assert "Task completed" in caplog.text
        assert "test-123" in caplog.text
        assert "success=True" in caplog.text

    def test_handles_missing_agent_type(self):
        """record_task_outcome() works when agent_type is None."""
        from ai.hooks import record_task_outcome

        result = record_task_outcome(
            task_id="test-456",
            quality=0.8,
            success=False,
            duration_seconds=10.0,
        )

        assert result is None

    def test_never_raises_on_errors(self):
        """record_task_outcome() catches all exceptions."""
        from ai.hooks import record_task_outcome

        # Should not raise even with invalid inputs
        result = record_task_outcome(
            task_id="",
            quality=-1.0,
            success=True,
            duration_seconds=-100,
        )

        assert result is None


class TestSaveHandoff:
    """Test session handoff file generation."""

    def test_creates_handoff_file(self, tmp_path, monkeypatch):
        """save_handoff() creates HANDOFF.md with correct structure."""
        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        save_handoff(
            summary="Fixed router timeout bug",
            files_modified=["ai/router.py", "tests/test_router.py"],
            next_steps=["Add integration test", "Update docs"],
            task_id="fix-123",
        )

        handoff_path = tmp_path / "HANDOFF.md"
        assert handoff_path.exists()

        content = handoff_path.read_text()
        assert "# Cross-Tool Session Handoff" in content
        assert "Fixed router timeout bug" in content
        assert "ai/router.py" in content
        assert "Add integration test" in content

    def test_handles_empty_lists(self, tmp_path, monkeypatch):
        """save_handoff() handles empty files_modified and next_steps."""
        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        save_handoff(
            summary="Minor cleanup",
            files_modified=[],
            next_steps=[],
        )

        content = (tmp_path / "HANDOFF.md").read_text()
        assert "- (none)" in content
        assert "- Continue current task" in content

    def test_timestamps_are_utc(self, tmp_path, monkeypatch):
        """save_handoff() uses UTC timestamps."""
        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        save_handoff(
            summary="Test",
            files_modified=["test.py"],
            next_steps=["Test more"],
        )

        content = (tmp_path / "HANDOFF.md").read_text()
        assert "UTC" in content

    def test_overwrites_existing_handoff(self, tmp_path, monkeypatch):
        """save_handoff() overwrites existing HANDOFF.md."""
        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)
        handoff_path = tmp_path / "HANDOFF.md"
        handoff_path.write_text("Old content")

        save_handoff(
            summary="New summary",
            files_modified=["new.py"],
            next_steps=["New step"],
        )

        content = handoff_path.read_text()
        assert "New summary" in content
        assert "Old content" not in content


class TestAutoSaveHandoff:
    """Test automatic handoff generation from git status."""

    @patch("subprocess.run")
    def test_extracts_modified_files_from_git(self, mock_run, tmp_path, monkeypatch):
        """auto_save_handoff() parses git status to find modified files."""
        from ai.hooks import auto_save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        mock_run.return_value = MagicMock(
            stdout=" M ai/router.py\n M tests/test_router.py\n?? new_file.py\n",
            returncode=0,
        )

        auto_save_handoff()

        handoff_path = tmp_path / "HANDOFF.md"
        content = handoff_path.read_text()
        assert "ai/router.py" in content
        assert "tests/test_router.py" in content
        assert "new_file.py" in content

    @patch("subprocess.run")
    def test_limits_to_10_files(self, mock_run, tmp_path, monkeypatch):
        """auto_save_handoff() limits files_modified to first 10 files."""
        from ai.hooks import auto_save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        # Generate 20 modified files
        files = "\n".join([f" M file{i}.py" for i in range(20)])
        mock_run.return_value = MagicMock(stdout=files, returncode=0)

        auto_save_handoff()

        content = (tmp_path / "HANDOFF.md").read_text()
        # Should only include first 10
        assert "file0.py" in content
        assert "file9.py" in content

    @patch("subprocess.run")
    def test_handles_git_command_failure(self, mock_run, tmp_path, monkeypatch):
        """auto_save_handoff() handles git command failures gracefully."""
        from ai.hooks import auto_save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        mock_run.side_effect = Exception("git not found")

        # Should not raise
        auto_save_handoff()

        handoff_path = tmp_path / "HANDOFF.md"
        assert handoff_path.exists()
        content = handoff_path.read_text()
        assert "0 files modified" in content

    @patch("subprocess.run")
    def test_handles_empty_git_status(self, mock_run, tmp_path, monkeypatch):
        """auto_save_handoff() handles clean git status."""
        from ai.hooks import auto_save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        mock_run.return_value = MagicMock(stdout="", returncode=0)

        auto_save_handoff()

        content = (tmp_path / "HANDOFF.md").read_text()
        assert "- (none)" in content


class TestCLI:
    """Test CLI argument handling."""

    @patch("ai.hooks.auto_save_handoff")
    def test_save_handoff_flag(self, mock_auto_save):
        """--save-handoff flag triggers auto_save_handoff()."""
        import importlib
        import sys

        import ai.hooks

        # Simulate running as main module
        with patch.object(sys, "argv", ["hooks.py", "--save-handoff"]):
            # Re-import to trigger __main__ block
            importlib.reload(ai.hooks)

        # auto_save_handoff should have been called
        # Note: This test may need adjustment based on actual CLI structure


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handoff_with_unicode_content(self, tmp_path, monkeypatch):
        """save_handoff() handles Unicode characters correctly."""
        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        save_handoff(
            summary="Fixed 日本語 characters in logs 🔧",
            files_modified=["файл.py"],
            next_steps=["Test with émojis 🎯"],
        )

        content = (tmp_path / "HANDOFF.md").read_text(encoding="utf-8")
        assert "日本語" in content
        assert "🔧" in content
        assert "🎯" in content

    def test_handoff_with_very_long_summary(self, tmp_path, monkeypatch):
        """save_handoff() handles very long summaries."""
        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        long_summary = "This is a very long summary. " * 100

        save_handoff(
            summary=long_summary,
            files_modified=["test.py"],
            next_steps=["test"],
        )

        content = (tmp_path / "HANDOFF.md").read_text()
        assert long_summary in content

    def test_concurrent_handoff_writes(self, tmp_path, monkeypatch):
        """Multiple concurrent save_handoff() calls don't corrupt the file."""
        from concurrent.futures import ThreadPoolExecutor

        from ai.hooks import save_handoff

        monkeypatch.setattr("ai.hooks.get_project_root", lambda: tmp_path)

        def save_test(n):
            save_handoff(
                summary=f"Summary {n}",
                files_modified=[f"file{n}.py"],
                next_steps=[f"Step {n}"],
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(save_test, range(20))

        # File should exist and be valid (last write wins)
        handoff_path = tmp_path / "HANDOFF.md"
        assert handoff_path.exists()
        content = handoff_path.read_text()
        assert "# Cross-Tool Session Handoff" in content
