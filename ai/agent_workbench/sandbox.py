"""Sandbox capability profiles for Agent Workbench sessions."""

from __future__ import annotations

from ai.agent_workbench.models import SandboxProfile

_PROFILES: dict[str, SandboxProfile] = {
    "conservative": SandboxProfile(
        profile_id="conservative",
        name="Conservative",
        allowed_tools=["workbench.*", "project.*", "code.*", "knowledge.*", "memory.search"],
        read_roots=["{project_root}"],
        write_roots=["{project_root}"],
        shell_access=False,
        network_access=False,
        approval_mode="manual",
        notes="Default profile. No raw shell execution. Limited to project context tools.",
    ),
    "analysis": SandboxProfile(
        profile_id="analysis",
        name="Analysis",
        allowed_tools=["workbench.*", "project.*", "code.*", "knowledge.*", "memory.search"],
        read_roots=["{project_root}"],
        write_roots=[],
        shell_access=False,
        network_access=False,
        approval_mode="manual",
        notes="Read-heavy profile for diagnostics and planning.",
    ),
}


def get_profile(profile_id: str = "conservative") -> SandboxProfile:
    return _PROFILES.get(profile_id, _PROFILES["conservative"])


def list_profiles() -> list[dict]:
    return [profile.to_dict() for profile in _PROFILES.values()]
