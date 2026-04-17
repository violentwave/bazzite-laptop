"""Safe test command registry and execution hooks for Agent Workbench."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ai.agent_workbench.models import TestCommand
from ai.agent_workbench.paths import TEST_COMMANDS_PATH, atomic_write, now_iso

SAFE_EXECUTABLES = {
    ".venv/bin/python",
    "python",
    "python3",
    "pytest",
    "ruff",
    "uv",
    "npm",
    "npx",
}
BLOCKED_TOKENS = {"sudo", "rm", "mkfs", "dd"}
OUTPUT_LIMIT = 4000


class TestRunnerHooks:
    def __init__(self, *, commands_path: Path | None = None) -> None:
        self._commands_path = commands_path or TEST_COMMANDS_PATH
        self._commands = self._load()

    def _load(self) -> dict[str, list[TestCommand]]:
        if not self._commands_path.exists():
            return {}
        try:
            payload = json.loads(self._commands_path.read_text(encoding="utf-8"))
            rows = payload.get("commands", {}) if isinstance(payload, dict) else {}
            parsed: dict[str, list[TestCommand]] = {}
            for project_id, items in rows.items():
                parsed[project_id] = [TestCommand(**item) for item in items]
            return parsed
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return {}

    def _save(self) -> None:
        self._commands_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "commands": {
                key: [item.to_dict() for item in value] for key, value in self._commands.items()
            },
            "updated_at": now_iso(),
        }
        atomic_write(self._commands_path, json.dumps(payload, indent=2, sort_keys=True))

    def ensure_defaults(self, project_id: str, project_root: str) -> list[TestCommand]:
        existing = self._commands.get(project_id)
        if existing:
            return existing
        root = Path(project_root)
        defaults: list[TestCommand] = []
        if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists():
            defaults.append(
                TestCommand(
                    name="pytest",
                    command=[".venv/bin/python", "-m", "pytest", "-q"],
                    description="Run pytest quietly",
                    timeout_seconds=300,
                )
            )
            defaults.append(
                TestCommand(
                    name="ruff",
                    command=["ruff", "check", "ai", "tests"],
                    description="Run Ruff lint checks",
                    timeout_seconds=180,
                )
            )
        self._commands[project_id] = defaults
        self._save()
        return defaults

    def list_commands(self, project_id: str) -> list[dict]:
        return [item.to_dict() for item in self._commands.get(project_id, [])]

    def _validate_command(self, command: TestCommand) -> None:
        if not command.command:
            raise ValueError("Registered command is empty")
        executable = command.command[0]
        if executable not in SAFE_EXECUTABLES:
            raise ValueError("Command executable is not allowlisted")
        joined = " ".join(command.command).lower()
        if any(token in joined for token in BLOCKED_TOKENS):
            raise ValueError("Command contains blocked token")

    def execute_command(self, project_id: str, command_name: str, project_root: str) -> dict:
        commands = self._commands.get(project_id, [])
        command = next(
            (item for item in commands if item.name == command_name and item.enabled), None
        )
        if command is None:
            raise ValueError("Unknown test command")

        self._validate_command(command)

        try:
            completed = subprocess.run(  # noqa: S603
                command.command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=command.timeout_seconds,
                check=False,
            )
            output = (completed.stdout + "\n" + completed.stderr).strip()
            if len(output) > OUTPUT_LIMIT:
                output = output[:OUTPUT_LIMIT] + "...[truncated]"
            return {
                "success": completed.returncode == 0,
                "command": command.to_dict(),
                "exit_code": completed.returncode,
                "output": output,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "command": command.to_dict(),
                "exit_code": -1,
                "output": "[timed out]",
            }
