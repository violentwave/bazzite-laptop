"""LiteLLM wrapper for provider-agnostic LLM routing (V2).

Routes queries through litellm.Router with health-weighted provider selection,
auto-demotion, g4f fallback, and stream recovery. No proxy daemon -- Router
runs in-process.

V2 changes from V1:
- Health-weighted provider selection (replaces simple-shuffle)
- litellm.Router num_retries=0 -- our code handles retries
- g4f fallback injection (runtime, not YAML)
- Stream recovery with 2KB buffer commit threshold
- route_query(), route_query_stream(), reset_router() backward compat preserved

Usage:
    from ai.router import route_query
    result = route_query("fast", "Summarize this alert...")
"""

import json
import logging
import time
from collections.abc import AsyncGenerator

import yaml

from ai.config import APP_NAME, LITELLM_CONFIG, load_keys
from ai.health import HealthTracker
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

VALID_TASK_TYPES = ("fast", "reason", "batch", "code", "embed")

# Fallback chains: if no models for the requested task_type, try these
_FALLBACK_CHAINS: dict[str, list[str]] = {
    "fast": ["reason"],
    "batch": ["reason"],
    "code": ["reason"],
    "embed": [],
    "reason": [],
}

# Stream recovery: buffer up to this many bytes before committing to a provider
_STREAM_COMMIT_THRESHOLD = 2048  # 2KB

_config: dict | None = None
_router = None
_rate_limiter: RateLimiter | None = None
_health_tracker: HealthTracker = HealthTracker()

# g4f fallback configuration
_G4F_MODEL_ENTRY = {
    "model_name": "__g4f__",
    "litellm_params": {
        "model": "openai/auto",
        "api_key": "dummy",
        "api_base": None,  # set at runtime from G4F_PORT
    },
}


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
        raise RuntimeError("LiteLLM config has no model_list -- cannot initialize Router")

    router_settings = config.get("router_settings", {})
    _router = litellm.Router(
        model_list=model_list,
        routing_strategy=router_settings.get("routing_strategy", "simple-shuffle"),
        num_retries=0,  # V2: our code handles retries, not litellm
        timeout=router_settings.get("timeout", 30),
        allowed_fails=router_settings.get("allowed_fails", 1),
    )
    return _router


def _get_models_for_task(config: dict, task_type: str) -> list[dict]:
    """Get model entries from config for a given task_type."""
    return [m for m in config.get("model_list", []) if m.get("model_name") == task_type]


def _get_provider_order(config: dict, task_type: str) -> list[str]:
    """Get health-sorted provider names for a task type, including fallbacks."""
    limiter = _get_rate_limiter()
    models = _get_models_for_task(config, task_type)

    # Include fallback chain models
    for fb in _FALLBACK_CHAINS.get(task_type, []):
        models.extend(_get_models_for_task(config, fb))

    # Extract unique provider names, filter by rate limits
    providers = []
    seen: set[str] = set()
    for m in models:
        params = m.get("litellm_params", {})
        provider = _extract_provider(params.get("model", ""))
        if provider and provider not in seen and limiter.can_call(provider):
            seen.add(provider)
            providers.append(provider)

    # Sort by health score (descending), excluding disabled
    healthy = _health_tracker.get_sorted(providers)
    return [h.name for h in healthy]


def _g4f_available() -> bool:
    """Check if g4f manager is importable and can potentially run."""
    try:
        from ai.g4f_manager import get_manager  # noqa: PLC0415, F401

        return True
    except ImportError:
        return False


def _try_provider(provider_name: str, task_type: str, prompt: str, **kwargs) -> object:
    """Try a single provider for a completion. Returns the response or raises."""
    if provider_name == "g4f":
        return _try_g4f(task_type, prompt, **kwargs)

    router = _get_router()

    start = time.time()
    try:
        response = router.completion(
            model=task_type,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        latency_ms = (time.time() - start) * 1000
        actual_provider = _extract_provider(getattr(response, "model", "") or provider_name)
        _health_tracker.record_success(actual_provider, latency_ms)
        limiter = _get_rate_limiter()
        limiter.record_call(actual_provider)
        return response
    except Exception:
        latency_ms = (time.time() - start) * 1000
        _health_tracker.record_failure(provider_name, "call failed")
        raise


def _try_g4f(task_type: str, prompt: str, **kwargs) -> object:
    """Try g4f fallback provider."""
    import os  # noqa: PLC0415

    from ai.g4f_manager import get_manager  # noqa: PLC0415

    mgr = get_manager()
    if not mgr.ensure_running():
        raise RuntimeError("g4f is not available")

    mgr.record_request()
    port = mgr._port

    import httpx  # noqa: PLC0415

    resp = httpx.post(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    # Return a simple object matching litellm response shape
    from types import SimpleNamespace  # noqa: PLC0415

    choice = SimpleNamespace(
        message=SimpleNamespace(content=data["choices"][0]["message"]["content"]),
        delta=SimpleNamespace(content=None),
    )
    result = SimpleNamespace(choices=[choice], model="g4f/auto")
    return result


def _try_embed(task_type: str, prompt: str, **kwargs) -> str:
    """Handle embedding requests through litellm.Router."""
    router = _get_router()
    limiter = _get_rate_limiter()

    response = router.embedding(model="embed", input=[prompt], **kwargs)
    model_used = getattr(response, "model", "") or ""
    if model_used:
        provider = _extract_provider(model_used)
        limiter.record_call(provider)

    data = response.get("data", [{}])
    vector = data[0].get("embedding", []) if data else []
    return json.dumps(vector)


def _check_rate_limits(config: dict, task_type: str) -> None:
    """Pre-flight rate limit check. Raises RuntimeError if all providers blocked."""
    limiter = _get_rate_limiter()
    models = _get_models_for_task(config, task_type)

    for fb in _FALLBACK_CHAINS.get(task_type, []):
        models.extend(_get_models_for_task(config, fb))

    if not models:
        return

    for model_entry in models:
        params = model_entry.get("litellm_params", {})
        provider = _extract_provider(params.get("model", ""))
        if limiter.can_call(provider):
            return

    # Check if g4f could save us (g4f has no rate limit in our config)
    if _g4f_available():
        return

    raise RuntimeError(f"All providers rate-limited for task_type '{task_type}'")


async def _stream_provider(
    provider_name: str,
    task_type: str,
    messages: list[dict],
    **kwargs,
) -> AsyncGenerator[str, None]:
    """Stream from a single provider. Yields chunks."""
    router = _get_router()
    limiter = _get_rate_limiter()

    start = time.time()
    try:
        response = router.completion(
            model=task_type,
            messages=messages,
            stream=True,
            **kwargs,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

        latency_ms = (time.time() - start) * 1000
        _health_tracker.record_success(provider_name, latency_ms)
        limiter.record_call(provider_name)
    except Exception:
        _health_tracker.record_failure(provider_name, "stream failed")
        raise


def route_query(task_type: str, prompt: str, **kwargs: object) -> str:
    """Route a query to the best available LLM provider via LiteLLM.

    Args:
        task_type: One of "fast", "reason", "batch", "code", "embed"
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

    if task_type == "embed":
        try:
            return _try_embed(task_type, prompt, **kwargs)
        except Exception as e:
            raise RuntimeError(f"LLM call failed for task_type '{task_type}': {e}") from e

    # Health-weighted provider ordering
    providers = _get_provider_order(config, task_type)

    # Append g4f as last fallback
    if _g4f_available():
        providers.append("g4f")

    if not providers:
        raise RuntimeError(f"No available providers for task_type '{task_type}'")

    last_error = None
    for provider in providers:
        try:
            response = _try_provider(provider, task_type, prompt, **kwargs)
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            logger.warning("Provider '%s' failed: %s", provider, e)
            continue

    raise RuntimeError(
        f"LLM call failed for task_type '{task_type}': all providers exhausted. Last error: {last_error}"
    ) from last_error


async def route_query_stream(
    task_type: str,
    messages: list[dict],
    **kwargs: object,
) -> AsyncGenerator[str, None]:
    """Stream LLM response chunks with health-weighted selection and recovery.

    Args:
        task_type: One of "fast", "reason", "batch", "code"
        messages: litellm-format messages [{"role": "user", "content": "..."}]
        **kwargs: Additional LiteLLM parameters

    Yields:
        Response text chunks as they arrive from the LLM.

    Raises:
        ValueError: If task_type is invalid or "embed".
        RuntimeError: If all providers exhausted or stream fails after commit.
    """
    valid_stream_types = {"fast", "reason", "batch", "code"}
    if task_type not in valid_stream_types:
        raise ValueError(
            f"task_type must be one of {valid_stream_types}, got '{task_type}'"
        )

    config = _load_config()
    _check_rate_limits(config, task_type)

    providers = _get_provider_order(config, task_type)
    if _g4f_available():
        providers.append("g4f")

    if not providers:
        raise RuntimeError(f"No available providers for task_type '{task_type}'")

    last_error = None
    for provider in providers:
        buffer: list[str] = []
        buffer_size = 0
        committed = False

        try:
            async for chunk in _stream_provider(provider, task_type, messages, **kwargs):
                if committed:
                    # Already committed -- yield live
                    yield chunk
                else:
                    buffer.append(chunk)
                    buffer_size += len(chunk)
                    if buffer_size >= _STREAM_COMMIT_THRESHOLD:
                        # Commit: flush buffer and switch to live streaming
                        committed = True
                        for buffered in buffer:
                            yield buffered
                        buffer.clear()

            # Stream completed successfully
            if not committed:
                # Never hit commit threshold -- yield buffered content
                for buffered in buffer:
                    yield buffered
            return

        except Exception as e:
            if committed:
                # Post-commit failure -- cannot recover, re-raise
                raise RuntimeError(
                    f"Streaming failed after commit for provider '{provider}': {e}"
                ) from e
            # Pre-commit failure -- discard buffer, try next provider
            last_error = e
            logger.warning(
                "Stream from '%s' failed pre-commit, retrying next provider: %s",
                provider, e,
            )
            continue

    raise RuntimeError(
        f"Streaming LLM call failed for task_type '{task_type}': all providers exhausted. "
        f"Last error: {last_error}"
    ) from last_error


def _record_usage(response, config: dict, task_type: str, limiter: RateLimiter) -> None:
    """Record a successful API call against the rate limiter (V1 compat)."""
    model_used = getattr(response, "model", "") or ""
    if model_used:
        provider = _extract_provider(model_used)
    else:
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
    global _router, _config, _rate_limiter, _health_tracker  # noqa: PLW0603
    _router = None
    _config = None
    _rate_limiter = None
    _health_tracker = HealthTracker()
