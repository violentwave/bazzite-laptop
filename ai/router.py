"""LiteLLM wrapper for provider-agnostic LLM routing (V2).

Routes queries through litellm.Router with health-weighted provider selection,
auto-demotion, and stream recovery. No proxy daemon -- Router runs in-process.

V2 changes from V1:
- Health-weighted provider selection (replaces simple-shuffle)
- litellm.Router num_retries=0 -- our code handles retries
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
from pathlib import Path

import litellm
import yaml
from litellm.caching.caching import Cache

from ai.config import APP_NAME, LITELLM_CONFIG, load_keys
from ai.health import HealthTracker
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# Per-task-type cache TTLs (seconds). External SSD reduces internal SSD wear.
_CACHE_TTL: dict[str, int] = {
    "fast": 300,       # 5 min — health checks, quick lookups
    "code": 3600,      # 1 hour — code generation
    "reason": 1800,    # 30 min — analysis
    "batch": 86400,    # 24 hours — bulk operations
}

# Prefer external SSD; fall back to ~/security/llm-cache; then tmpdir.
_EXT_SSD_CACHE = Path("/var/mnt/ext-ssd/bazzite-ai/llm-cache")
_INTERNAL_CACHE = Path.home() / "security" / "llm-cache"
_CACHE_DIR = _EXT_SSD_CACHE if _EXT_SSD_CACHE.parent.exists() else _INTERNAL_CACHE
try:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Fall back to TMPDIR in restricted environments (e.g. test sandboxes)
    import tempfile  # noqa: PLC0415
    _CACHE_DIR = Path(tempfile.gettempdir()) / "bazzite-llm-cache"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
def _init_litellm_cache(cache_dir: Path) -> "Cache | None":
    """Initialize LiteLLM disk cache, returning None on failure."""
    try:
        return Cache(
            type="disk",
            disk_cache_dir=str(cache_dir),
            default_in_memory_ttl=300,
        )
    except Exception as exc:
        logger.debug("LLM disk cache unavailable at %s: %s", cache_dir, exc)
        return None


# Try preferred location first; if read-only (e.g. created by systemd as root),
# fall back to the project temp dir, then disable caching as a last resort.
litellm.cache = _init_litellm_cache(_CACHE_DIR)
if litellm.cache is None:
    import tempfile as _tempfile  # noqa: PLC0415

    _FALLBACK_CACHE_DIR = Path(_tempfile.gettempdir()) / "bazzite-llm-cache"
    try:
        _FALLBACK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    litellm.cache = _init_litellm_cache(_FALLBACK_CACHE_DIR)
    if litellm.cache is not None:
        _CACHE_DIR = _FALLBACK_CACHE_DIR
    else:
        logger.warning("LLM disk cache unavailable — running without cache")

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

# Per-task-type timeouts (seconds). reason/batch get more time for deep analysis.
_DEFAULT_TIMEOUTS: dict[str, int] = {
    "fast": 30, "code": 30, "reason": 60, "batch": 60, "embed": 30,
}

_config: dict | None = None
_router = None
_rate_limiter: RateLimiter | None = None
_health_tracker: HealthTracker = HealthTracker()

# Thread-safe usage counters (not embed — no token usage there)
_usage_counters: dict[str, dict[str, int]] = {
    tt: {"prompt_tokens": 0, "completion_tokens": 0, "requests": 0}
    for tt in ("fast", "reason", "batch", "code")
}


def _increment_usage(task_type: str, response: object) -> None:
    """Increment per-task-type token counters from a successful response."""
    if task_type not in _usage_counters:
        return
    counters = _usage_counters[task_type]
    counters["requests"] += 1
    usage = getattr(response, "usage", None)
    if usage is not None:
        counters["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
        counters["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0


def get_usage_stats() -> dict[str, dict[str, int]]:
    """Return a copy of token usage counters per task type."""
    return {tt: dict(counters) for tt, counters in _usage_counters.items()}


def reset_usage_stats() -> None:
    """Zero all usage counters. Used for test isolation."""
    for counters in _usage_counters.values():
        counters["prompt_tokens"] = 0
        counters["completion_tokens"] = 0
        counters["requests"] = 0


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


def _get_timeout(task_type: str) -> int:
    """Return the configured timeout for a task type, falling back to defaults."""
    config = _load_config()
    router_settings = config.get("router_settings", {})
    timeouts = router_settings.get("timeouts", {})
    return timeouts.get(task_type, _DEFAULT_TIMEOUTS.get(task_type, 30))


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
        if not provider or provider in seen:
            continue
        seen.add(provider)
        if limiter.can_call(provider):
            providers.append(provider)
        else:
            wait = limiter.wait_time(provider)
            logger.debug("Skipping %s (rate-limited, available in %.1fs)", provider, wait)

    # Sort by health score (descending), excluding disabled
    healthy = _health_tracker.get_sorted(providers)
    return [h.name for h in healthy]


def _try_provider(provider_name: str, task_type: str, prompt: str, **kwargs) -> object:
    """Try a single provider for a completion. Returns the response or raises."""
    router = _get_router()

    kwargs.setdefault("timeout", _get_timeout(task_type))
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

    wait_times: list[float] = []
    for model_entry in models:
        params = model_entry.get("litellm_params", {})
        provider = _extract_provider(params.get("model", ""))
        if not provider:
            continue
        if limiter.can_call(provider):
            return
        wait_times.append(limiter.wait_time(provider))

    try:
        min_wait = min(wait_times) if wait_times else 0.0
        wait_msg = f" (shortest wait: {min_wait:.1f}s)" if min_wait > 0 else ""
    except TypeError:
        wait_msg = ""
    raise RuntimeError(
        f"All providers rate-limited for task_type '{task_type}'{wait_msg}"
    )


async def _stream_provider(
    provider_name: str,
    task_type: str,
    messages: list[dict],
    **kwargs,
) -> AsyncGenerator[str, None]:
    """Stream from a single provider. Yields chunks."""
    router = _get_router()
    limiter = _get_rate_limiter()

    kwargs.setdefault("timeout", _get_timeout(task_type))
    start = time.time()
    try:
        response = await router.acompletion(
            model=task_type,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
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

    if not providers:
        raise RuntimeError(f"No available providers for task_type '{task_type}'")

    # Inject per-task-type TTL for disk cache unless caller overrides
    kwargs.setdefault("cache", {
        "namespace": task_type,
        "ttl": _CACHE_TTL.get(task_type, 300),
    })

    last_error = None
    for provider in providers:
        try:
            response = _try_provider(provider, task_type, prompt, **kwargs)
            _increment_usage(task_type, response)
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            logger.warning("Provider '%s' failed: %s", provider, e)
            continue

    raise RuntimeError(
        f"LLM call failed for task_type '{task_type}': "
        f"all providers exhausted. Last error: {last_error}"
    ) from last_error


async def route_chat(task_type: str, messages: list[dict], **kwargs: object) -> str:
    """Route a multi-turn conversation to the best available provider.

    Unlike route_query(), this accepts the full messages array (including
    system prompt, assistant turns, and conversation history) so multi-turn
    context is preserved. Used by the non-streaming path of llm_proxy.py.

    Args:
        task_type: One of "fast", "reason", "batch", "code"
        messages: Full litellm-format messages list
        **kwargs: Additional LiteLLM parameters

    Returns:
        The LLM response text.

    Raises:
        ValueError: If task_type is not recognized or is "embed".
        RuntimeError: If all providers are exhausted or rate-limited.
    """
    valid_chat_types = {"fast", "reason", "batch", "code"}
    if task_type not in valid_chat_types:
        raise ValueError(f"task_type must be one of {valid_chat_types}, got '{task_type}'")

    config = _load_config()
    _check_rate_limits(config, task_type)
    providers = _get_provider_order(config, task_type)

    if not providers:
        raise RuntimeError(f"No available providers for task_type '{task_type}'")

    # Inject per-task-type TTL for disk cache unless caller overrides
    kwargs.setdefault("cache", {
        "namespace": task_type,
        "ttl": _CACHE_TTL.get(task_type, 300),
    })

    router = _get_router()
    last_error = None
    for provider in providers:
        kwargs.setdefault("timeout", _get_timeout(task_type))
        start = time.time()
        try:
            response = await router.acompletion(
                model=task_type,
                messages=messages,
                **kwargs,
            )
            latency_ms = (time.time() - start) * 1000
            actual_provider = _extract_provider(getattr(response, "model", "") or provider)
            _health_tracker.record_success(actual_provider, latency_ms)
            _get_rate_limiter().record_call(actual_provider)
            _increment_usage(task_type, response)
            return response.choices[0].message.content
        except Exception as e:
            _health_tracker.record_failure(provider, "call failed")
            last_error = e
            logger.warning("Provider '%s' failed (chat): %s", provider, e)
            continue

    raise RuntimeError(
        f"LLM call failed for task_type '{task_type}': "
        f"all providers exhausted. Last error: {last_error}"
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


def get_health_snapshot() -> dict[str, dict]:
    """Return health snapshot for all known providers."""
    return {
        name: {"score": round(h.score, 4), "auth_broken": h.auth_broken}
        for name, h in _health_tracker._providers.items()
    }


def reset_router() -> None:
    """Reset cached Router and config. Used for test isolation."""
    global _router, _config, _rate_limiter, _health_tracker  # noqa: PLW0603
    _router = None
    _config = None
    _rate_limiter = None
    _health_tracker = HealthTracker()
