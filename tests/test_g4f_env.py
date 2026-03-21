"""Verify g4f environment scrubbing -- no API keys leak to subprocess."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _set_xdg_runtime(tmp_path):
    with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(tmp_path)}):
        yield


class TestEnvironmentScrubbing:
    def test_all_scrub_keys_defined(self):
        from ai.g4f_manager import G4FManager
        expected = {
            "GROQ_API_KEY", "ZAI_API_KEY", "GEMINI_API_KEY",
            "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "CEREBRAS_API_KEY",
            "CLOUDFLARE_API_KEY", "VT_API_KEY", "OTX_API_KEY", "ABUSEIPDB_KEY",
        }
        assert G4FManager._SCRUB_KEYS == expected

    def test_clean_env_removes_every_key(self):
        from ai.g4f_manager import G4FManager
        fake_env = {k: f"secret-{k}" for k in G4FManager._SCRUB_KEYS}
        fake_env["PATH"] = "/usr/bin"
        fake_env["XDG_RUNTIME_DIR"] = "/run/user/1000"
        with patch.dict(os.environ, fake_env, clear=True):
            m = G4FManager()
            clean = m._clean_env()
        for key in G4FManager._SCRUB_KEYS:
            assert key not in clean, f"{key} leaked into g4f environment!"
        assert "PATH" in clean

    def test_clean_env_preserves_safe_vars(self):
        from ai.g4f_manager import G4FManager
        safe_vars = {"PATH": "/usr/bin", "HOME": "/home/lch", "LANG": "en_US.UTF-8"}
        with patch.dict(os.environ, {**safe_vars, "XDG_RUNTIME_DIR": "/run/user/1000"}, clear=True):
            m = G4FManager()
            clean = m._clean_env()
        for k, v in safe_vars.items():
            assert clean[k] == v
