"""MCP contract tests for Agent Workbench tool handlers (P124)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai.agent_workbench.registry import ProjectRegistry
from ai.agent_workbench.sessions import SessionManager
from ai.agent_workbench.testing import TestRunnerHooks as WorkbenchTestRunnerHooks


def _make_project(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(path), "init"], check=False, capture_output=True, text=True)
    (path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    return path


def _install_validator_stub(monkeypatch: pytest.MonkeyPatch) -> None:
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


@pytest.mark.asyncio
async def test_workbench_project_list_empty_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai.mcp_bridge.tools import execute_tool

    registry = ProjectRegistry(
        registry_path=tmp_path / "registry.json", allowed_roots=[str(tmp_path)]
    )

    import ai.agent_workbench as wb

    monkeypatch.setattr(wb, "get_registry", lambda: registry)
    _install_validator_stub(monkeypatch)

    result = json.loads(await execute_tool("workbench.project_list", {}))

    assert result["success"] is True
    assert result["count"] == 0
    assert result["projects"] == []


@pytest.mark.asyncio
async def test_workbench_session_get_not_found_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai.mcp_bridge.tools import execute_tool

    registry = ProjectRegistry(
        registry_path=tmp_path / "registry.json", allowed_roots=[str(tmp_path)]
    )
    sessions = SessionManager(registry=registry, sessions_path=tmp_path / "sessions.json")

    import ai.agent_workbench as wb

    monkeypatch.setattr(wb, "get_registry", lambda: registry)
    monkeypatch.setattr(wb, "get_session_manager", lambda: sessions)
    _install_validator_stub(monkeypatch)

    result = json.loads(
        await execute_tool("workbench.session_get", {"session_id": "sess_deadbeefcafe"})
    )

    assert result["success"] is False
    assert result["error_code"] == "session_not_found"


@pytest.mark.asyncio
async def test_workbench_test_commands_execute_requires_command_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai.mcp_bridge.tools import execute_tool

    allowed = tmp_path / "workspace"
    project = _make_project(allowed / "demo")
    registry = ProjectRegistry(
        registry_path=tmp_path / "registry.json", allowed_roots=[str(allowed)]
    )
    created = registry.register_project(path=str(project), name="Demo")
    hooks = WorkbenchTestRunnerHooks(commands_path=tmp_path / "test-commands.json")

    import ai.agent_workbench as wb

    monkeypatch.setattr(wb, "get_registry", lambda: registry)
    monkeypatch.setattr(wb, "get_test_hooks", lambda: hooks)
    _install_validator_stub(monkeypatch)

    result = json.loads(
        await execute_tool(
            "workbench.test_commands",
            {"project_id": created.project_id, "execute": True},
        )
    )

    assert result["success"] is False
    assert result["error_code"] == "command_name_required"


@pytest.mark.asyncio
async def test_workbench_handoff_note_passthrough_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai.mcp_bridge.tools import execute_tool

    captured: dict[str, object] = {}

    def _fake_append_handoff_note(
        *,
        summary: str,
        artifacts: list[str] | None = None,
        phase: str = "P123",
        session_id: str | None = None,
    ) -> dict:
        captured["summary"] = summary
        captured["artifacts"] = artifacts or []
        captured["phase"] = phase
        captured["session_id"] = session_id
        return {
            "success": True,
            "note": {
                "timestamp": "2026-04-17T00:00:00Z",
                "phase": phase,
                "summary": summary,
                "artifacts": artifacts or [],
                "session_id": session_id,
            },
        }

    import ai.agent_workbench as wb

    monkeypatch.setattr(wb, "append_handoff_note", _fake_append_handoff_note)
    _install_validator_stub(monkeypatch)

    result = json.loads(
        await execute_tool(
            "workbench.handoff_note",
            {
                "summary": "P124 UI pass",
                "artifacts": "docs/evidence/p124/validation.md,docs/P124_PLAN.md",
                "phase": "P124",
                "session_id": "sess_deadbeefcafe",
            },
        )
    )

    assert result["success"] is True
    assert result["note"]["phase"] == "P124"
    assert captured["summary"] == "P124 UI pass"
    assert captured["artifacts"] == ["docs/evidence/p124/validation.md", "docs/P124_PLAN.md"]
