"""Keys tab data layer — pure Python, no Qt.

Provides load_key_status() and key grouping constants consumed by the
Keys tab in tray/dashboard_window.py.
"""
from __future__ import annotations

import json
from pathlib import Path

# File written atomically by ai/key_manager.py on every list_keys() call.
KEY_STATUS_FILE = Path.home() / "security" / "key-status.json"

# Key groupings — mirrors ai/key_manager.py but without importing private names.
LLM_GROUP: list[str] = [
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "XAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "HF_TOKEN",
    "GITHUB_TOKEN",
    "NVIDIA_API_KEY",
    "CLOUDFLARE_API_TOKEN",
]

THREAT_GROUP: list[str] = [
    "VT_API_KEY",
    "OTX_API_KEY",
    "ABUSEIPDB_KEY",
    "GREYNOISE_KEY",
    "HYBRID_ANALYSIS_KEY",
    "NVD_API_KEY",
]


def load_key_status(path: Path | None = None) -> dict | None:
    """Load key-status.json.  Returns None if file missing or invalid JSON."""
    target = path or KEY_STATUS_FILE
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
