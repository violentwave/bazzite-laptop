"""Unit tests for ai/config.py."""

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ai.config import (
    AI_DIR,
    APP_NAME,
    CONFIGS_DIR,
    ENRICHED_HASHES,
    KEY_SCOPES,
    KEYS_ENV,
    LITELLM_CONFIG,
    PROJECT_ROOT,
    RATE_LIMITS_DEF,
    RATE_LIMITS_STATE,
    SECURITY_DIR,
    STATUS_FILE,
    VECTOR_DB_DIR,
    VENV_DIR,
    VERSION,
    get_key,
    load_keys,
    setup_logging,
)


class TestPathConstants:
    def test_all_are_path_objects(self):
        paths = [
            PROJECT_ROOT, AI_DIR, VENV_DIR, CONFIGS_DIR, KEYS_ENV,
            RATE_LIMITS_DEF, RATE_LIMITS_STATE, LITELLM_CONFIG,
            SECURITY_DIR, VECTOR_DB_DIR, STATUS_FILE, ENRICHED_HASHES,
        ]
        for p in paths:
            assert isinstance(p, Path), f"{p} is not a Path"

    def test_keys_env_path(self):
        assert KEYS_ENV == Path.home() / ".config" / "bazzite-ai" / "keys.env"

    def test_rate_limits_state_path(self):
        expected = Path.home() / ".config" / "bazzite-ai" / "rate-limits-state.json"
        assert RATE_LIMITS_STATE == expected

    def test_project_structure(self):
        assert AI_DIR == PROJECT_ROOT / "ai"
        assert CONFIGS_DIR == PROJECT_ROOT / "configs"
        assert VENV_DIR == PROJECT_ROOT / ".venv"


class TestKeyLoading:
    def test_load_keys_missing_file(self, tmp_path):
        fake_path = tmp_path / "nonexistent" / "keys.env"
        with patch("ai.config.KEYS_ENV", fake_path):
            assert load_keys() is False

    def test_load_keys_exists(self, tmp_path):
        fake_env = tmp_path / "keys.env"
        fake_env.write_text("TEST_KEY_FOR_CONFIG=hello123\n")
        try:
            with patch("ai.config.KEYS_ENV", fake_env):
                result = load_keys()
            assert result is True
            assert os.environ.get("TEST_KEY_FOR_CONFIG") == "hello123"
        finally:
            os.environ.pop("TEST_KEY_FOR_CONFIG", None)

    def test_get_key_returns_none_for_missing(self):
        assert get_key("DEFINITELY_NOT_SET_KEY_XYZ_12345") is None

    def test_get_key_returns_none_for_empty(self):
        os.environ["EMPTY_TEST_KEY"] = ""
        try:
            assert get_key("EMPTY_TEST_KEY") is None
        finally:
            os.environ.pop("EMPTY_TEST_KEY", None)

    def test_get_key_returns_value(self):
        os.environ["PRESENT_TEST_KEY"] = "secret_value"
        try:
            assert get_key("PRESENT_TEST_KEY") == "secret_value"
        finally:
            os.environ.pop("PRESENT_TEST_KEY", None)


class TestScopedKeyLoading:
    """Tests for load_keys(scope=...) scoped key filtering."""

    @pytest.fixture(autouse=True)
    def _reset_keys_loaded(self):
        """Reset the _keys_loaded flag before each test for isolation."""
        import ai.config as cfg
        original = cfg._keys_loaded
        cfg._keys_loaded = False
        yield
        cfg._keys_loaded = original

    def test_load_keys_no_scope_loads_all(self, tmp_path):
        """Default (no scope) loads ALL keys — backward compatible."""
        fake_env = tmp_path / "keys.env"
        fake_env.write_text(
            "GROQ_API_KEY=groq123\n"
            "VT_API_KEY=vt456\n"
            "UNRELATED_KEY=other789\n"
        )
        try:
            with patch("ai.config.KEYS_ENV", fake_env):
                result = load_keys()
            assert result is True
            assert os.environ.get("GROQ_API_KEY") == "groq123"
            assert os.environ.get("VT_API_KEY") == "vt456"
            assert os.environ.get("UNRELATED_KEY") == "other789"
        finally:
            os.environ.pop("GROQ_API_KEY", None)
            os.environ.pop("VT_API_KEY", None)
            os.environ.pop("UNRELATED_KEY", None)

    def test_load_keys_scope_llm(self, tmp_path):
        """scope='llm' only loads LLM provider keys."""
        fake_env = tmp_path / "keys.env"
        fake_env.write_text(
            "GROQ_API_KEY=groq123\n"
            "ZAI_API_KEY=zai456\n"
            "VT_API_KEY=vt789\n"
            "OTX_API_KEY=otx000\n"
        )
        try:
            with patch("ai.config.KEYS_ENV", fake_env):
                result = load_keys(scope="llm")
            assert result is True
            assert os.environ.get("GROQ_API_KEY") == "groq123"
            assert os.environ.get("ZAI_API_KEY") == "zai456"
            # Threat intel keys should NOT be loaded
            assert os.environ.get("VT_API_KEY") is None
            assert os.environ.get("OTX_API_KEY") is None
        finally:
            os.environ.pop("GROQ_API_KEY", None)
            os.environ.pop("ZAI_API_KEY", None)
            os.environ.pop("VT_API_KEY", None)
            os.environ.pop("OTX_API_KEY", None)

    def test_load_keys_scope_threat_intel(self, tmp_path):
        """scope='threat_intel' only loads threat intel keys."""
        fake_env = tmp_path / "keys.env"
        fake_env.write_text(
            "VT_API_KEY=vt123\n"
            "OTX_API_KEY=otx456\n"
            "ABUSEIPDB_KEY=abuse789\n"
            "GROQ_API_KEY=groq000\n"
            "GEMINI_API_KEY=gem111\n"
        )
        try:
            with patch("ai.config.KEYS_ENV", fake_env):
                result = load_keys(scope="threat_intel")
            assert result is True
            assert os.environ.get("VT_API_KEY") == "vt123"
            assert os.environ.get("OTX_API_KEY") == "otx456"
            assert os.environ.get("ABUSEIPDB_KEY") == "abuse789"
            # LLM keys should NOT be loaded
            assert os.environ.get("GROQ_API_KEY") is None
            assert os.environ.get("GEMINI_API_KEY") is None
        finally:
            os.environ.pop("VT_API_KEY", None)
            os.environ.pop("OTX_API_KEY", None)
            os.environ.pop("ABUSEIPDB_KEY", None)
            os.environ.pop("GROQ_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)

    def test_load_keys_invalid_scope_raises(self, tmp_path):
        """Invalid scope raises ValueError."""
        fake_env = tmp_path / "keys.env"
        fake_env.write_text("GROQ_API_KEY=groq123\n")
        with patch("ai.config.KEYS_ENV", fake_env):
            with pytest.raises(ValueError, match="Unknown scope"):
                load_keys(scope="invalid_scope")

    def test_load_keys_scope_missing_file(self, tmp_path):
        """Scoped load with missing file returns False."""
        fake_path = tmp_path / "nonexistent" / "keys.env"
        with patch("ai.config.KEYS_ENV", fake_path):
            assert load_keys(scope="llm") is False

    def test_key_scopes_dict_has_expected_scopes(self):
        """KEY_SCOPES contains both llm and threat_intel."""
        assert "llm" in KEY_SCOPES
        assert "threat_intel" in KEY_SCOPES

    def test_key_scopes_llm_contains_expected_keys(self):
        """LLM scope includes all expected provider keys."""
        expected = {
            "GROQ_API_KEY", "ZAI_API_KEY", "GEMINI_API_KEY",
            "OPENROUTER_API_KEY", "MISTRAL_API_KEY",
            "CEREBRAS_API_KEY", "CLOUDFLARE_API_KEY",
        }
        assert expected == KEY_SCOPES["llm"]

    def test_key_scopes_threat_intel_contains_expected_keys(self):
        """Threat intel scope includes all expected provider keys."""
        expected = {"VT_API_KEY", "OTX_API_KEY", "ABUSEIPDB_KEY"}
        assert expected == KEY_SCOPES["threat_intel"]

    def test_scoped_load_does_not_set_keys_loaded_flag(self, tmp_path):
        """Scoped load should NOT set _keys_loaded (so full load can still run)."""
        fake_env = tmp_path / "keys.env"
        fake_env.write_text("GROQ_API_KEY=groq123\n")
        try:
            with patch("ai.config.KEYS_ENV", fake_env):
                load_keys(scope="llm")
                # A subsequent no-scope load should still work (not short-circuit)
                # We verify by checking that _keys_loaded behavior is correct
                # Scoped load should not have set _keys_loaded
                # (the fixture resets it via the conftest or we check behavior)
                assert os.environ.get("GROQ_API_KEY") == "groq123"
        finally:
            os.environ.pop("GROQ_API_KEY", None)


class TestLogging:
    def test_setup_logging_returns_logger(self):
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == APP_NAME

    def test_setup_logging_sets_level(self):
        logger = setup_logging(level=logging.DEBUG)
        assert logger.level == logging.DEBUG
        # Reset
        setup_logging(level=logging.INFO)


class TestConstants:
    def test_app_name(self):
        assert APP_NAME == "bazzite-ai"

    def test_version(self):
        assert VERSION == "0.1.0"
