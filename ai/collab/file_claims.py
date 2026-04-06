"""File claim system for agent collaboration."""

import json
import logging
from pathlib import Path

import filelock

logger = logging.getLogger("ai.collab")

_CLAIMS_FILE = Path.home() / ".config" / "bazzite-ai" / ".file-claims.json"
_CLAIM_TIMEOUT_HOURS = 2


def _ensure_claims_dir() -> None:
    """Ensure config directory exists."""
    _CLAIMS_FILE.parent.mkdir(parents=True, exist_ok=True)


def claim_file(agent: str, filepath: str) -> bool:
    """Claim a file for exclusive editing. Returns True if claimed, False if already claimed."""
    _ensure_claims_dir()
    lock = filelock.FileLock(str(_CLAIMS_FILE) + ".lock")

    with lock:
        if _CLAIMS_FILE.exists():
            claims = json.loads(_CLAIMS_FILE.read_text())
        else:
            claims = {}

        # Check for expired claims first (before checking ownership)
        import time

        now = time.time()
        expired = []
        for path, info in claims.items():
            if now - info.get("claimed_at", 0) > _CLAIM_TIMEOUT_HOURS * 3600:
                expired.append(path)

        for path in expired:
            del claims[path]

        # Check if already claimed by another agent
        if filepath in claims:
            existing_agent = claims[filepath].get("agent")
            if existing_agent != agent:
                return False

        # Claim the file
        claims[filepath] = {
            "agent": agent,
            "claimed_at": now,
        }
        _CLAIMS_FILE.write_text(json.dumps(claims))
        return True


def release_file(agent: str, filepath: str) -> bool:
    """Release a claimed file. Returns True if released, False if not owned by agent."""
    _ensure_claims_dir()
    lock = filelock.FileLock(str(_CLAIMS_FILE) + ".lock")

    with lock:
        if not _CLAIMS_FILE.exists():
            return True

        claims = json.loads(_CLAIMS_FILE.read_text())

        if filepath not in claims:
            return True

        if claims[filepath].get("agent") != agent:
            return False

        del claims[filepath]
        _CLAIMS_FILE.write_text(json.dumps(claims))
        return True


def get_claims() -> dict:
    """Get all current claims. Returns {filepath: agent}."""
    _ensure_claims_dir()

    if not _CLAIMS_FILE.exists():
        return {}

    try:
        claims = json.loads(_CLAIMS_FILE.read_text())

        # Filter expired
        import time

        now = time.time()
        valid_claims = {}
        for path, info in claims.items():
            if now - info.get("claimed_at", 0) <= _CLAIM_TIMEOUT_HOURS * 3600:
                valid_claims[path] = info.get("agent")

        return valid_claims
    except Exception as e:
        logger.warning(f"Failed to read claims: {e}")
        return {}
