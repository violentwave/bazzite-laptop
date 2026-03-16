"""LiteLLM wrapper for provider-agnostic LLM routing.

Routes queries through litellm.Router with fallback chains, rate limit
integration, and lazy initialization. No proxy daemon — Router runs in-process.

Usage:
    from ai.router import route_query
    result = route_query("fast", "Summarize this alert...")
"""

import json
import logging

import yaml

from ai.config import APP_NAME, LITELLM_CONFIG, load_keys
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

VALID_TASK_TYPES = ("fast", "reason", "batch", "code", "embed")

# Fallback chains: if no models for the requested task_type, try these
_FALLBACK_CHAINS: dict[str, list[str]] = {
    "fast": ["reason"],
    "batch": ["reason"],
    "code": ["reason"],
    "embed": ["reason"],
    "reason": [],
}

_config: dict | None = None
_router = None
_rate_limiter: RateLimiter | None = None


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


def _extract_provider(model_str: str) -> str:
    """Extract provider name from a litellm model string like 'groq/llama-3'."""
    return model_str.split("/")[0] if "/" in model_str else model_str


def _get_rate_limiter() -> RateLimiter:
    """Get or create the singleton RateLimiter."""
    global _rate_limiter  # noqa: PLW0603
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def _get_router():
    """Lazily build and cache the litellm.Router from YAML config."""
    global _router  # noqa: PLW0603
    if _router is not None:
        return _router

    import litellm  # noqa: PLC0415

    load_keys()
    config = _load_config()
    model_list = config.get("model_list")
    if not model_list:
        raise RuntimeError("LiteLLM config has no model_list — cannot initialize Router")

    router_settings = config.get("router_settings", {})
    _router = litellm.Router(
        model_list=model_list,
        routing_strategy=router_settings.get("routing_strategy", "simple-shuffle"),
        num_retries=router_settings.get("num_retries", 2),
        timeout=router_settings.get("timeout", 30),
        allowed_fails=router_settings.get("allowed_fails", 1),
    )
    return _router


def _get_models_for_task(config: dict, task_type: str) -> list[dict]:
    """Get model entries from config for a given task_type."""
    return [m for m in config.get("model_list", []) if m.get("model_name") == task_type]


def _check_rate_limits(config: dict, task_type: str) -> None:
    """Pre-flight rate limit check. Raises RuntimeError if all providers blocked."""
    limiter = _get_rate_limiter()
    models = _get_models_for_task(config, task_type)

    # Also check fallback chains
    fallbacks = _FALLBACK_CHAINS.get(task_type, [])
    for fb in fallbacks:
        models.extend(_get_models_for_task(config, fb))

    if not models:
        return  # No models defined — let Router handle the error

    for model_entry in models:
        params = model_entry.get("litellm_params", {})
        provider = _extract_provider(params.get("model", ""))
        if limiter.can_call(provider):
            return  # At least one provider is available

    raise RuntimeError(f"All providers rate-limited for task_type '{task_type}'")


def route_query(task_type: str, prompt: str, **kwargs: object) -> str:
    """Route a query to the best available LLM provider via LiteLLM.

    Args:
        task_type: One of "fast", "reason", "batch", "embed"
        prompt: The user/system prompt to send
        **kwargs: Additional LiteLLM parameters (temperature, max_tokens, etc.)

    Returns:
        The LLM response text (or JSON-serialized embedding vector for "embed").

    Raises:
        ValueError: If task_type is not recognized.
        RuntimeError: If all providers are exhausted or rate-limited.
    """
    if task_type not in VALID_TASK_TYPES:
        raise ValueError(f"task_type must be one of {VALID_TASK_TYPES}, got '{task_type}'")

    config = _load_config()
    _check_rate_limits(config, task_type)

    router = _get_router()
    limiter = _get_rate_limiter()

    try:
        if task_type == "embed":
            response = router.embedding(model="embed", input=[prompt], **kwargs)
            # Record call for the provider that was used
            _record_usage(response, config, task_type, limiter)
            data = response.get("data", [{}])
            vector = data[0].get("embedding", []) if data else []
            return json.dumps(vector)

        response = router.completion(
            model=task_type,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        _record_usage(response, config, task_type, limiter)
        return response.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"LLM call failed for task_type '{task_type}': {e}") from e


def _record_usage(response, config: dict, task_type: str, limiter: RateLimiter) -> None:
    """Record a successful API call against the rate limiter."""
    # Try to extract the model that was actually used from the response
    model_used = getattr(response, "model", "") or ""
    if model_used:
        provider = _extract_provider(model_used)
    else:
        # Fallback: record against the first configured provider for this task
        models = _get_models_for_task(config, task_type)
        if models:
            params = models[0].get("litellm_params", {})
            provider = _extract_provider(params.get("model", ""))
        else:
            return
    if provider:
        limiter.record_call(provider)


def reset_router() -> None:
    """Reset cached Router and config. Used for test isolation."""
    global _router, _config, _rate_limiter  # noqa: PLW0603
    _router = None
    _config = None
    _rate_limiter = None
