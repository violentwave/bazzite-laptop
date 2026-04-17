"""Read-only git metadata extraction for Agent Workbench."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai.agent_workbench.models import GitFileChange, GitStatusSummary

_TIMEOUT_SECONDS = 15
_MAX_CHANGED_FILES = 100
_GIT_BIN = "/usr/bin/git"


def _run_git(repo: Path, args: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(  # noqa: S603
            [_GIT_BIN, "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
        output = completed.stdout.strip()
        return completed.returncode, output
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def _parse_porcelain(porcelain: str) -> tuple[int, int, int, list[GitFileChange]]:
    staged = 0
    unstaged = 0
    untracked = 0
    files: list[GitFileChange] = []

    for line in porcelain.splitlines():
        if line.startswith("##"):
            continue
        if len(line) < 4:
            continue
        x = line[0]
        y = line[1]
        path = line[3:].strip()
        if x != " " and x != "?":
            staged += 1
        if y != " ":
            unstaged += 1
        if x == "?" and y == "?":
            untracked += 1
        if len(files) < _MAX_CHANGED_FILES:
            files.append(GitFileChange(path=path, status=f"{x}{y}".strip()))

    return staged, unstaged, untracked, files


def _parse_ahead_behind(branch_line: str) -> tuple[int, int]:
    ahead = 0
    behind = 0
    if "ahead" in branch_line:
        try:
            ahead = int(branch_line.split("ahead ")[1].split("]")[0])
        except (IndexError, ValueError):
            ahead = 0
    if "behind" in branch_line:
        try:
            behind = int(branch_line.split("behind ")[1].split("]")[0])
        except (IndexError, ValueError):
            behind = 0
    return ahead, behind


def get_git_status_summary(project_root: str) -> GitStatusSummary:
    repo = Path(project_root)
    inside_code, inside_text = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    if inside_code != 0 or inside_text != "true":
        return GitStatusSummary(
            is_git_repo=False,
            branch="",
            is_dirty=False,
            ahead=0,
            behind=0,
            recent_commit="",
            staged_count=0,
            unstaged_count=0,
            untracked_count=0,
            changed_files=[],
            staged_diff_stat="",
            unstaged_diff_stat="",
        )

    _, branch = _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    _, recent_commit = _run_git(repo, ["log", "-1", "--pretty=%h %s"])
    _, porcelain = _run_git(repo, ["status", "--porcelain=1", "--branch"])
    _, staged_diff_stat = _run_git(repo, ["diff", "--cached", "--shortstat"])
    _, unstaged_diff_stat = _run_git(repo, ["diff", "--shortstat"])

    branch_line = porcelain.splitlines()[0] if porcelain else ""
    ahead, behind = _parse_ahead_behind(branch_line)
    staged, unstaged, untracked, files = _parse_porcelain(porcelain)

    return GitStatusSummary(
        is_git_repo=True,
        branch=branch,
        is_dirty=bool(staged or unstaged or untracked),
        ahead=ahead,
        behind=behind,
        recent_commit=recent_commit,
        staged_count=staged,
        unstaged_count=unstaged,
        untracked_count=untracked,
        changed_files=files,
        staged_diff_stat=staged_diff_stat,
        unstaged_diff_stat=unstaged_diff_stat,
    )
