"""Central configuration for the Bazzite AI enhancement layer.

All path constants, API key loading, and logging setup live here.
Every other AI module imports from this module.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

APP_NAME = "bazzite-ai"
VERSION = "0.1.0"

# ── Path Constants ──

PROJECT_ROOT = Path.home() / "projects" / "bazzite-laptop"
AI_DIR = PROJECT_ROOT / "ai"
VENV_DIR = PROJECT_ROOT / ".venv"
CONFIGS_DIR = PROJECT_ROOT / "configs"
KEYS_ENV = Path.home() / ".config" / "bazzite-ai" / "keys.env"
RATE_LIMITS_DEF = CONFIGS_DIR / "ai-rate-limits.json"
RATE_LIMITS_STATE = Path.home() / ".config" / "bazzite-ai" / "rate-limits-state.json"
LITELLM_CONFIG = CONFIGS_DIR / "litellm-config.yaml"
SECURITY_DIR = Path.home() / "security"
VECTOR_DB_DIR = SECURITY_DIR / "vector-db"
STATUS_FILE = SECURITY_DIR / ".status"
ENRICHED_HASHES = SECURITY_DIR / "quarantine-hashes-enriched.jsonl"

# ── Key Loading ──

_keys_loaded = False


def load_keys() -> bool:
    """Load API keys from keys.env into environment. Returns True if file was found."""
    global _keys_loaded  # noqa: PLW0603
    if _keys_loaded:
        return True
    if KEYS_ENV.exists():
        load_dotenv(KEYS_ENV)
        _keys_loaded = True
        return True
    logging.getLogger(APP_NAME).warning("keys.env not found at %s", KEYS_ENV)
    return False


def get_key(name: str) -> str | None:
    """Get an API key by environment variable name. Returns None if not set or empty."""
    return os.environ.get(name) or None


# ── Logging ──


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure logging for the AI layer. Returns the root app logger."""
    logger = logging.getLogger(APP_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
