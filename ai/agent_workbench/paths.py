"""Path policies and normalization for Agent Workbench."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ai.config import PROJECT_ROOT

DEFAULT_ALLOWED_ROOTS = [PROJECT_ROOT, Path.home() / "projects"]
WORKBENCH_DATA_DIR = Path.home() / ".config" / "bazzite-ai" / "agent-workbench"
WORKBENCH_DATA_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_PATH = WORKBENCH_DATA_DIR / "projects.json"
SESSIONS_PATH = WORKBENCH_DATA_DIR / "sessions.json"
TEST_COMMANDS_PATH = WORKBENCH_DATA_DIR / "test-commands.json"

PROJECT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "setup.py",
)


def now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, content: str) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(path))
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _contains_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def parse_allowed_roots(raw_roots: list[str] | None = None) -> list[Path]:
    """Return normalized, resolved allowlisted roots."""
    if raw_roots:
        candidates = [Path(item).expanduser() for item in raw_roots]
    else:
        env_roots = os.environ.get("BAZZITE_WORKBENCH_ALLOWED_ROOTS", "").strip()
        if env_roots:
            candidates = [Path(item).expanduser() for item in env_roots.split(":") if item]
        else:
            candidates = DEFAULT_ALLOWED_ROOTS

    normalized: list[Path] = []
    for candidate in candidates:
        try:
            normalized.append(candidate.resolve(strict=False))
        except OSError:
            continue
    return normalized


def is_project_directory(path: Path) -> bool:
    return any((path / marker).exists() for marker in PROJECT_MARKERS)


def normalize_project_path(
    input_path: str,
    *,
    allowed_roots: list[Path],
    allow_non_project_dirs: bool,
) -> Path:
    """Resolve and validate a project path against workbench safety rules."""
    if not input_path or not input_path.strip():
        raise ValueError("Project path is required")

    raw = Path(input_path.strip()).expanduser()
    if not raw.is_absolute():
        raise ValueError("Project path must be absolute")

    try:
        resolved = raw.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ValueError("Project path does not exist or is inaccessible") from exc

    if not resolved.is_dir():
        raise ValueError("Project path must reference a directory")

    if not any(_contains_path(resolved, root) for root in allowed_roots):
        raise ValueError("Project path is outside allowed roots")

    if not allow_non_project_dirs and not is_project_directory(resolved):
        raise ValueError("Directory does not look like a project")

    return resolved
