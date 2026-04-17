"""Agent Workbench core package (P123)."""

from ai.agent_workbench.git import get_git_status_summary
from ai.agent_workbench.handoff import append_handoff_note
from ai.agent_workbench.models import (
    GitStatusSummary,
    ProjectRecord,
    SandboxProfile,
    SessionRecord,
    TestCommand,
)
from ai.agent_workbench.registry import ProjectRegistry
from ai.agent_workbench.sandbox import get_profile, list_profiles
from ai.agent_workbench.sessions import SessionManager
from ai.agent_workbench.testing import TestRunnerHooks

_registry: ProjectRegistry | None = None
_sessions: SessionManager | None = None
_tests: TestRunnerHooks | None = None


def get_registry() -> ProjectRegistry:
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry


def get_session_manager() -> SessionManager:
    global _sessions
    if _sessions is None:
        _sessions = SessionManager(registry=get_registry())
    return _sessions


def get_test_hooks() -> TestRunnerHooks:
    global _tests
    if _tests is None:
        _tests = TestRunnerHooks()
    return _tests


__all__ = [
    "GitStatusSummary",
    "ProjectRecord",
    "ProjectRegistry",
    "SandboxProfile",
    "SessionManager",
    "SessionRecord",
    "TestCommand",
    "TestRunnerHooks",
    "append_handoff_note",
    "get_git_status_summary",
    "get_profile",
    "get_registry",
    "get_session_manager",
    "get_test_hooks",
    "list_profiles",
]
