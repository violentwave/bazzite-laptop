"""Tests for P123 Agent Workbench core."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai.agent_workbench.git import get_git_status_summary
from ai.agent_workbench.handoff import append_handoff_note
from ai.agent_workbench.paths import normalize_project_path, parse_allowed_roots
from ai.agent_workbench.registry import ProjectRegistry
from ai.agent_workbench.sandbox import get_profile
from ai.agent_workbench.sessions import SessionManager
from ai.agent_workbench.testing import TestRunnerHooks as WorkbenchTestRunnerHooks


def _make_project(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(path), "init"], check=False, capture_output=True, text=True)
    (path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    return path


def test_allowed_project_root_registration_succeeds(tmp_path: Path):
    root = tmp_path / "workspace"
    project = _make_project(root / "demo")
    registry = ProjectRegistry(registry_path=tmp_path / "registry.json", allowed_roots=[str(root)])

    item = registry.register_project(path=str(project), name="Demo")

    assert item.name == "Demo"
    assert item.root_path == str(project.resolve())
    assert item.project_id.startswith("proj_")


def test_disallowed_project_root_registration_fails(tmp_path: Path):
    allowed = tmp_path / "allowed"
    blocked = tmp_path / "blocked"
    _make_project(blocked / "demo")
    registry = ProjectRegistry(
        registry_path=tmp_path / "registry.json", allowed_roots=[str(allowed)]
    )

    with pytest.raises(ValueError, match="outside allowed roots"):
        registry.register_project(path=str(blocked / "demo"))


def test_path_traversal_is_rejected(tmp_path: Path):
    root = tmp_path / "workspace"
    _make_project(root / "demo")
    allowed = [root.resolve()]

    with pytest.raises(ValueError, match="must be absolute"):
        normalize_project_path(
            "../workspace/demo",
            allowed_roots=allowed,
            allow_non_project_dirs=False,
        )


def test_symlink_escape_is_rejected(tmp_path: Path):
    allowed_root = tmp_path / "allowed"
    outside_root = tmp_path / "outside"
    allowed_root.mkdir(parents=True)
    escaped = _make_project(outside_root / "actual")

    link = allowed_root / "linked-project"
    link.symlink_to(escaped, target_is_directory=True)

    with pytest.raises(ValueError, match="outside allowed roots"):
        normalize_project_path(
            str(link),
            allowed_roots=[allowed_root.resolve()],
            allow_non_project_dirs=False,
        )


def test_registry_persistence_and_reload(tmp_path: Path):
    root = tmp_path / "workspace"
    project = _make_project(root / "demo")
    registry_path = tmp_path / "registry.json"

    registry = ProjectRegistry(registry_path=registry_path, allowed_roots=[str(root)])
    created = registry.register_project(path=str(project))

    loaded = ProjectRegistry(registry_path=registry_path, allowed_roots=[str(root)])
    fetched = loaded.get_project(created.project_id)
    assert fetched is not None
    assert fetched.root_path == created.root_path


def test_session_lifecycle_create_list_get_stop(tmp_path: Path):
    root = tmp_path / "workspace"
    project = _make_project(root / "demo")
    registry = ProjectRegistry(registry_path=tmp_path / "registry.json", allowed_roots=[str(root)])
    record = registry.register_project(path=str(project))

    manager = SessionManager(registry=registry, sessions_path=tmp_path / "sessions.json")
    created = manager.create_session(project_id=record.project_id, backend="opencode")
    listed = manager.list_sessions(project_id=record.project_id)
    fetched = manager.get_session(created.session_id)
    stopped = manager.stop_session(created.session_id)

    assert len(listed) == 1
    assert fetched is not None
    assert fetched.session_id == created.session_id
    assert stopped.status == "stopped"


def test_session_create_rejects_unknown_project(tmp_path: Path):
    registry = ProjectRegistry(
        registry_path=tmp_path / "registry.json", allowed_roots=[str(tmp_path)]
    )
    manager = SessionManager(registry=registry, sessions_path=tmp_path / "sessions.json")

    with pytest.raises(ValueError, match="Project not found"):
        manager.create_session(project_id="proj_deadbeef000", backend="opencode")


def test_sandbox_default_is_conservative():
    profile = get_profile()
    assert profile.profile_id == "conservative"
    assert profile.shell_access is False
    assert profile.network_access is False
    assert profile.approval_mode == "manual"


def test_git_status_returns_bounded_metadata(tmp_path: Path):
    project = _make_project(tmp_path / "repo")
    summary = get_git_status_summary(str(project))

    assert summary.is_git_repo is True
    assert isinstance(summary.changed_files, list)
    assert len(summary.changed_files) <= 100


def test_test_runner_accepts_registered_and_rejects_arbitrary(tmp_path: Path):
    hooks = WorkbenchTestRunnerHooks(commands_path=tmp_path / "test-commands.json")
    project = _make_project(tmp_path / "demo")
    project_id = "proj_abc123abc123"
    commands = hooks.ensure_defaults(project_id, str(project))

    assert len(commands) >= 1

    with pytest.raises(ValueError, match="Unknown test command"):
        hooks.execute_command(project_id, "not-registered", str(project))


def test_handoff_helper_appends_safely(tmp_path: Path):
    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text("# Handoff\n", encoding="utf-8")

    result = append_handoff_note(
        summary="Workbench session completed",
        artifacts=["docs/evidence/p123/validation.md"],
        phase="P123",
        session_id="sess_deadbeefcafe",
        handoff_path=handoff,
    )

    content = handoff.read_text(encoding="utf-8")
    assert result["success"] is True
    assert "Workbench session completed" in content
    assert "docs/evidence/p123/validation.md" in content


@pytest.mark.asyncio
async def test_mcp_handlers_return_stable_envelopes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from ai.mcp_bridge.tools import execute_tool

    allowed = tmp_path / "workspace"
    project = _make_project(allowed / "demo")
    registry = ProjectRegistry(
        registry_path=tmp_path / "registry.json", allowed_roots=[str(allowed)]
    )
    sessions = SessionManager(registry=registry, sessions_path=tmp_path / "sessions.json")
    hooks = WorkbenchTestRunnerHooks(commands_path=tmp_path / "tests.json")

    monkeypatch.setenv("BAZZITE_WORKBENCH_ALLOWED_ROOTS", str(allowed))
    import ai.agent_workbench as wb

    monkeypatch.setattr(wb, "get_registry", lambda: registry)
    monkeypatch.setattr(wb, "get_session_manager", lambda: sessions)
    monkeypatch.setattr(wb, "get_test_hooks", lambda: hooks)

    import ai.mcp_bridge.tools as bridge_tools

    monkeypatch.setattr(
        bridge_tools,
        "_VALIDATOR",
        type(
            "_ValidatorStub",
            (),
            {
                "validate_tool_args": staticmethod(lambda *_args, **_kwargs: (True, [])),
                "redact_secrets": staticmethod(lambda text: text),
            },
        )(),
    )

    registered_raw = await execute_tool(
        "workbench.project_register",
        {
            "path": str(project),
            "name": "demo",
            "description": "local demo",
            "tags": "python,workbench",
        },
    )
    registered = json.loads(registered_raw)
    assert registered["success"] is True

    project_id = registered["project"]["project_id"]
    opened = json.loads(await execute_tool("workbench.project_open", {"project_id": project_id}))
    assert opened["success"] is True

    created = json.loads(
        await execute_tool(
            "workbench.session_create",
            {"project_id": project_id, "backend": "opencode"},
        )
    )
    assert created["success"] is True

    listed = json.loads(await execute_tool("workbench.session_list", {"project_id": project_id}))
    assert listed["success"] is True
    assert listed["count"] == 1

    git_summary = json.loads(await execute_tool("workbench.git_status", {"project_id": project_id}))
    assert git_summary["success"] is True
    assert "git" in git_summary

    commands = json.loads(await execute_tool("workbench.test_commands", {"project_id": project_id}))
    assert commands["success"] is True
    assert "commands" in commands


def test_parse_allowed_roots_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()

    monkeypatch.setenv("BAZZITE_WORKBENCH_ALLOWED_ROOTS", f"{root_a}:{root_b}")
    roots = parse_allowed_roots()

    assert root_a.resolve() in roots
    assert root_b.resolve() in roots
