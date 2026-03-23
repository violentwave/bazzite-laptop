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

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
AI_DIR = Path(__file__).parent.resolve()
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
CVE_REPORTS_DIR = SECURITY_DIR / "cve-reports"

# Gaming optimization (Phase 4)
GAME_PROFILES = Path.home() / ".config" / "bazzite-ai" / "game-profiles.json"
MANGOHUD_CONFIG = Path.home() / ".config" / "MangoHud" / "MangoHud.conf"
MANGOHUD_LOG_DIR = Path.home() / ".local" / "share" / "MangoHud"
STEAM_LIBRARY_DEFAULT = Path("/var/mnt/ext-ssd")
LLM_CACHE_DIR = Path("/var/mnt/ext-ssd/bazzite-ai/llm-cache")

# ── Key Scopes ──

KEY_SCOPES: dict[str, set[str]] = {
    "llm": {
        "GROQ_API_KEY",
        "ZAI_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "MISTRAL_API_KEY",
        "CEREBRAS_API_KEY",
        "CLOUDFLARE_API_KEY",
    },
    "threat_intel": {
        "VT_API_KEY",
        "OTX_API_KEY",
        "ABUSEIPDB_KEY",
    },
}

# ── Key Loading ──

_keys_loaded = False


def load_keys(scope: str | None = None) -> bool:
    """Load API keys from keys.env into environment. Returns True if file was found.

    Args:
        scope: Optional scope to filter which keys are loaded.
            None (default): load ALL keys (backward compatible).
            "llm": only load LLM provider keys.
            "threat_intel": only load threat intel keys.

    Raises:
        ValueError: If scope is not None and not a recognized scope name.
    """
    global _keys_loaded  # noqa: PLW0603

    if scope is not None and scope not in KEY_SCOPES:
        raise ValueError(f"Unknown scope '{scope}'. Valid scopes: {sorted(KEY_SCOPES.keys())}")

    # Unscoped load uses the cached flag for backward compatibility
    if scope is None:
        if _keys_loaded:
            return True
        if KEYS_ENV.exists():
            load_dotenv(KEYS_ENV)
            _keys_loaded = True
            return True
        logging.getLogger(APP_NAME).warning("keys.env not found at %s", KEYS_ENV)
        return False

    # Scoped load: parse the file and only set allowed keys
    if not KEYS_ENV.exists():
        logging.getLogger(APP_NAME).warning("keys.env not found at %s", KEYS_ENV)
        return False

    allowed_keys = KEY_SCOPES[scope]
    # Read the env file and selectively load only scoped keys
    with open(KEYS_ENV, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key in allowed_keys:
                os.environ[key] = value
    return True


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
