"""API key presence checker for the Bazzite AI layer.

Reads ~/.config/bazzite-ai/keys.env and reports which expected keys are set or
missing.  NEVER returns actual key values — only "set" or "missing" status.

On every call to list_keys() the current presence snapshot is written atomically
to ~/security/key-status.json so the MCP bridge can expose it without ever
importing this module or reading keys.env directly.

Usage:
    python -m ai.key_manager          # same as 'list'
    python -m ai.key_manager list     # per-key presence as JSON
    python -m ai.key_manager status   # categorised summary as JSON (exit 1 if missing)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from ai.config import APP_NAME, KEYS_ENV, SECURITY_DIR
from ai.utils.freshness import stamp_generated_at

logger = logging.getLogger(APP_NAME)

# ── Expected keys ─────────────────────────────────────────────────────────────

_LLM_KEYS: list[str] = [
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "ZAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "HF_TOKEN",
    "GITHUB_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "DEEPSEEK_API_TOKEN",
]

_THREAT_KEYS: list[str] = [
    "VT_API_KEY",
    "ABUSEIPDB_KEY",
    "OTX_API_KEY",
    "NVD_API_KEY",
    "GREYNOISE_KEY",
    "HYBRID_ANALYSIS_KEY",
]

_STORAGE_KEYS: list[str] = [
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
]

_MONITORING_KEYS: list[str] = ["SENTRY_DSN"]

_CODE_QUALITY_KEYS: list[str] = ["SEMGREP_APP_TOKEN"]

_ALL_EXPECTED_KEYS: list[str] = (
    _LLM_KEYS + _THREAT_KEYS + _STORAGE_KEYS + _MONITORING_KEYS + _CODE_QUALITY_KEYS
)

_KEY_STATUS_FILE = SECURITY_DIR / "key-status.json"


# ── Internal helpers ──────────────────────────────────────────────────────────


def _parse_keys_env(path: Path) -> dict[str, str]:
    """Read *path* line-by-line and return {KEY: "set"|"missing"} for expected keys.

    Lines that are empty, comments, or lack a "=" separator are skipped.
    Unknown keys are ignored.  Values are never stored — only presence is recorded.
    """
    present: set[str] = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key in _ALL_EXPECTED_KEYS and value.strip():
                    present.add(key)
    return {k: "set" if k in present else "missing" for k in _ALL_EXPECTED_KEYS}


def _compute_summary(key_presence: dict[str, str]) -> dict:
    """Derive categorised flags from a key-presence dict."""
    missing = [k for k, v in key_presence.items() if v == "missing"]
    return {
        "all_llm_keys_present": all(key_presence.get(k) == "set" for k in _LLM_KEYS),
        "all_threat_keys_present": all(key_presence.get(k) == "set" for k in _THREAT_KEYS),
        "all_storage_keys_present": all(key_presence.get(k) == "set" for k in _STORAGE_KEYS),
        "missing_keys": missing,
        "categories": {
            "llm_providers": {k: key_presence.get(k, "missing") for k in _LLM_KEYS},
            "threat_intel": {k: key_presence.get(k, "missing") for k in _THREAT_KEYS},
            "storage": {k: key_presence.get(k, "missing") for k in _STORAGE_KEYS},
            "monitoring": {k: key_presence.get(k, "missing") for k in _MONITORING_KEYS},
            "code_quality": {k: key_presence.get(k, "missing") for k in _CODE_QUALITY_KEYS},
        },
    }


# ── Public API ────────────────────────────────────────────────────────────────


def list_keys(keys_env: Path | None = None) -> dict[str, str]:
    """Return {KEY_NAME: "set" | "missing"} for every expected key.

    Reads ~/.config/bazzite-ai/keys.env (or *keys_env* override).
    NEVER returns actual key values.

    As a side effect, writes a fresh snapshot to ~/security/key-status.json.

    Args:
        keys_env: Override path to keys.env (used in tests).
    """
    presence = _parse_keys_env(keys_env or KEYS_ENV)
    write_status_file(presence)
    return presence


def get_key_status(keys_env: Path | None = None) -> dict:
    """Return a categorised summary of API key presence.

    Calls list_keys() internally (which refreshes key-status.json).

    Returns:
        dict with keys:
            all_llm_keys_present (bool)
            all_threat_keys_present (bool)
            all_storage_keys_present (bool)
            missing_keys (list[str])
            categories (dict): per-section key presence for tray display
    """
    presence = list_keys(keys_env)
    return _compute_summary(presence)


def write_status_file(key_presence: dict[str, str] | None = None) -> None:
    """Write combined key-presence + summary to ~/security/key-status.json.

    Uses an atomic tmp-file + rename so readers never see a partial write.

    Args:
        key_presence: Pre-computed dict from list_keys().  If None, reads
            keys.env fresh (used when calling this function directly).
    """
    if key_presence is None:
        key_presence = _parse_keys_env(KEYS_ENV)

    payload = {
        "keys": key_presence,
        "summary": _compute_summary(key_presence),
    }
    stamp_generated_at(payload)
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(SECURITY_DIR),
        prefix=".key-status-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.rename(tmp_path, str(_KEY_STATUS_FILE))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.debug("Key status written to %s", _KEY_STATUS_FILE)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point.  Use: python -m ai.key_manager [list|status]"""
    import argparse  # noqa: PLC0415
    import sys  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description="Check API key presence in keys.env (values are never shown)",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="list",
        choices=["list", "status"],
        help="'list' shows per-key presence; 'status' shows a categorised summary",
    )
    args = parser.parse_args()

    if args.command == "status":
        data = get_key_status()
        print(json.dumps(data, indent=2))
        if data["missing_keys"]:
            sys.exit(1)
    else:
        print(json.dumps(list_keys(), indent=2))


if __name__ == "__main__":
    main()
