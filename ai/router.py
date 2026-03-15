"""LiteLLM wrapper for provider-agnostic LLM routing.

Phase 0 scaffold — logs what would be called and returns a placeholder.
Full implementation comes in Phase 2 when RAG queries need it.

Usage:
    from ai.router import route_query
    result = route_query("fast", "Summarize this alert...")
"""

import logging

import yaml

from ai.config import APP_NAME, LITELLM_CONFIG

logger = logging.getLogger(APP_NAME)

VALID_TASK_TYPES = ("fast", "reason", "batch", "embed")

_config: dict | None = None


def _load_config() -> dict:
    """Load the LiteLLM routing config from YAML."""
    global _config  # noqa: PLW0603
    if _config is not None:
        return _config
    try:
        with open(LITELLM_CONFIG) as f:
            _config = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.warning("Could not load LiteLLM config: %s", e)
        _config = {}
    return _config


def route_query(task_type: str, prompt: str, **kwargs: object) -> str:
    """Route a query to the best available LLM provider via LiteLLM.

    Args:
        task_type: One of "fast", "reason", "batch", "embed"
        prompt: The user/system prompt to send
        **kwargs: Additional LiteLLM parameters (temperature, max_tokens, etc.)

    Returns:
        The LLM response text.

    Raises:
        ValueError: If task_type is not recognized.
        RuntimeError: If all providers are exhausted or rate-limited.
    """
    if task_type not in VALID_TASK_TYPES:
        raise ValueError(f"task_type must be one of {VALID_TASK_TYPES}, got '{task_type}'")

    config = _load_config()
    model_count = sum(
        1 for m in config.get("model_list", []) if m.get("model_name") == task_type
    )

    logger.info(
        "[SCAFFOLD] route_query: task_type=%s, prompt_len=%d, models_available=%d",
        task_type,
        len(prompt),
        model_count,
    )

    return (
        f"[SCAFFOLD] Would route '{task_type}' query to LiteLLM. "
        f"Prompt length: {len(prompt)} chars."
    )
