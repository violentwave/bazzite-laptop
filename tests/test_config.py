"""Unit tests for ai/config.py."""

import logging
import os
from pathlib import Path
from unittest.mock import patch

from ai.config import (
    AI_DIR,
    APP_NAME,
    CONFIGS_DIR,
    ENRICHED_HASHES,
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
        with patch("ai.config.KEYS_ENV", fake_env):
            result = load_keys()
        assert result is True
        assert os.environ.get("TEST_KEY_FOR_CONFIG") == "hello123"
        # Cleanup
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
