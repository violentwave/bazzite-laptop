"""Core models for Agent Workbench state and contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class ProjectRecord:
    project_id: str
    name: str
    root_path: str
    created_at: str
    updated_at: str
    last_opened_at: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    project_id: str
    backend: str
    cwd: str
    status: str
    sandbox_profile: str
    created_at: str
    updated_at: str
    expires_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SandboxProfile:
    profile_id: str
    name: str
    allowed_tools: list[str]
    read_roots: list[str]
    write_roots: list[str]
    shell_access: bool
    network_access: bool
    approval_mode: str
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class GitFileChange:
    path: str
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class GitStatusSummary:
    is_git_repo: bool
    branch: str
    is_dirty: bool
    ahead: int
    behind: int
    recent_commit: str
    staged_count: int
    unstaged_count: int
    untracked_count: int
    changed_files: list[GitFileChange]
    staged_diff_stat: str
    unstaged_diff_stat: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["changed_files"] = [item.to_dict() for item in self.changed_files]
        return data


@dataclass(slots=True)
class TestCommand:
    name: str
    command: list[str]
    description: str
    timeout_seconds: int = 120
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class HandoffNote:
    timestamp: str
    phase: str
    summary: str
    artifacts: list[str] = field(default_factory=list)
    session_id: str | None = None

    def to_markdown(self) -> str:
        head = f"### {self.timestamp} — {self.phase}"
        body = [head, f"- {self.summary}"]
        if self.session_id:
            body.append(f"- Session: `{self.session_id}`")
        if self.artifacts:
            body.append(f"- Artifacts: {', '.join(f'`{item}`' for item in self.artifacts)}")
        return "\n".join(body) + "\n"
