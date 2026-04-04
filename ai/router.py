"""LiteLLM wrapper for provider-agnostic LLM routing (V2).

Routes queries through litellm.Router with health-weighted provider selection,
auto-demotion, and stream recovery. No proxy daemon -- Router runs in-process.

V2 changes from V1:
- Health-weighted provider selection (replaces simple-shuffle)
- litellm.Router num_retries=0 -- our code handles retries
- Stream recovery with 2KB buffer commit threshold
- route_query(), route_query_stream(), reset_router() backward compat preserved
- Config mtime tracking to avoid unnecessary file reads
- httpx.Client with connection pooling passed to litellm.Router

Usage:
    from ai.router import route_query
    result = route_query("fast", "Summarize this alert...")
"""

import os

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=0.05,
    integrations=[AsyncioIntegration()],
    environment=os.environ.get("SENTRY_ENV", "production"),
    send_default_pii=False,
    ignore_errors=[KeyboardInterrupt, SystemExit],
)

import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import litellm
import yaml

from ai.budget import BudgetExhaustedError, classify_task, get_budget
from ai.cache import JsonFileCache
from ai.cache_semantic import SemanticCache
from ai.config import APP_NAME, LITELLM_CONFIG, load_keys
from ai.health import AllProvidersExhausted, HealthTracker
from ai.metrics import record_metric, track_performance
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

_config_mtime: float | None = None
_httpx_client: httpx.Client | None = None

# Per-task-type cache TTLs (seconds). External SSD reduces internal SSD wear.
# TTL=0 means never cache (embed type).
_TASK_TTL: dict[str, int] = {
    "fast": 300,  # 5 min — health checks, quick lookups
    "code": 3600,  # 1 hour — code generation
    "reason": 1800,  # 30 min — analysis
    "batch": 86400,  # 24 hours — bulk operations
    "embed": 0,  # never cache embeddings
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

_llm_cache = JsonFileCache(_CACHE_DIR, default_ttl=300)
litellm.cache = None

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
_STREAM_COMMIT_THRESHOLD = 8192  # 8KB — gives room for provider failover

# Per-task-type timeouts (seconds). reason/batch get more time for deep analysis.
_DEFAULT_TIMEOUTS: dict[str, int] = {
    "fast": 30,
    "code": 30,
    "reason": 60,
    "batch": 60,
    "embed": 30,
}

_config: dict | None = None
_router = None
_rate_limiter: RateLimiter | None = None
_health_tracker: HealthTracker = HealthTracker()

# Semantic cache singleton for embedding-based cache hits
_semantic_cache: SemanticCache | None = None


def _get_semantic_cache() -> SemanticCache:
    """Get or create the semantic cache singleton."""
    global _semantic_cache
    if _semantic_cache is None:
        try:
            _semantic_cache = SemanticCache()
        except Exception:  # noqa: S110
            pass
    return _semantic_cache


def _budget_reset_str() -> str:
    """Return human-readable budget reset time string."""
    try:
        budget = get_budget()
        reset_h = budget.config.get("reset_hour_utc", 0)
        return f"{reset_h:02d}:00 UTC"
    except Exception:  # noqa: S110
        return "midnight UTC"


# Thread-safe usage counters (not embed — no token usage there)
_usage_counters: dict[str, dict[str, int]] = {
    tt: {"prompt_tokens": 0, "completion_tokens": 0, "requests": 0}
    for tt in ("fast", "reason", "batch", "code")
}


# Cost/token tracking (resets on service restart)
_cost_stats: dict = {
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    "call_count": 0,
    "by_provider": {},
    "by_task_type": {},
    "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
}


def _track_cost(response: object, task_type: str, provider: str) -> None:
    """Track token usage and cost from a completion response.

    Never raises — cost tracking failures must not affect the request path.
    """
    try:
        usage = getattr(response, "usage", None)
        if not usage:
            return
        cost = litellm.completion_cost(completion_response=response) or 0.0
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0

        _cost_stats["total_tokens"] += prompt_tokens + completion_tokens
        _cost_stats["total_cost_usd"] += cost
        _cost_stats["by_provider"][provider] = _cost_stats["by_provider"].get(provider, 0.0) + cost
        _cost_stats["by_task_type"][task_type] = (
            _cost_stats["by_task_type"].get(task_type, 0.0) + cost
        )
        _cost_stats["call_count"] += 1
        _maybe_archive_stats()
    except Exception:  # noqa: BLE001, S110
        pass  # Never let cost tracking break the request path


def _maybe_archive_stats() -> None:
    """Archive and reset cost stats when call_count exceeds 100,000."""
    if _cost_stats["call_count"] <= 100_000:
        return
    archive_path = (
        Path.home()
        / "security"
        / f"cost-archive-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    )
    try:
        with open(archive_path, "w") as f:
            json.dump(_cost_stats, f, indent=2)
        logger.info("Archived cost stats to %s", archive_path)
        reset_cost_stats()
    except OSError:
        logger.warning("Failed to archive cost stats", exc_info=True)


def get_cost_stats() -> dict:
    """Return a copy of cost tracking counters since service start."""
    return {
        "total_tokens": _cost_stats["total_tokens"],
        "total_cost_usd": _cost_stats["total_cost_usd"],
        "call_count": _cost_stats["call_count"],
        "by_provider": dict(_cost_stats["by_provider"]),
        "by_task_type": dict(_cost_stats["by_task_type"]),
        "started_at": _cost_stats["started_at"],
    }


def reset_cost_stats() -> None:
    """Zero all cost counters. Used for test isolation."""
    _cost_stats["total_tokens"] = 0
    _cost_stats["total_cost_usd"] = 0.0
    _cost_stats["call_count"] = 0
    _cost_stats["by_provider"].clear()
    _cost_stats["by_task_type"].clear()
    _cost_stats["started_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
    """Load the LiteLLM routing config from YAML with mtime-based caching."""
    global _config, _config_mtime  # noqa: PLW0603
    try:
        current_mtime = os.path.getmtime(LITELLM_CONFIG)
    except OSError:
        return _config or {}

    if _config_mtime != current_mtime:
        logger.info(
            "LiteLLM config file changed (mtime %.0f -> %.0f), reloading",
            _config_mtime,
            current_mtime,
        )
        _config_mtime = current_mtime
        try:
            with open(LITELLM_CONFIG) as f:
                _config = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.warning("Could not load LiteLLM config: %s", e)
            _config = {}
    return _config or {}


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
    """Lazily build and cache the litellm.Router from YAML config with connection pooling."""
    global _router, _httpx_client  # noqa: PLW0603
    if _router is not None:
        return _router

    import litellm  # noqa: PLC0415

    load_keys()
    config = _load_config()
    model_list = config.get("model_list")
    if not model_list:
        raise RuntimeError("LiteLLM config has no model_list -- cannot initialize Router")

    if _httpx_client is None:
        _httpx_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

    router_settings = config.get("router_settings", {})
    _router = litellm.Router(
        model_list=model_list,
        routing_strategy=router_settings.get("routing_strategy", "simple-shuffle"),
        num_retries=0,
        timeout=router_settings.get("timeout", 30),
        allowed_fails=router_settings.get("allowed_fails", 1),
        http_client=_httpx_client,
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
        record_metric(
            "provider",
            "provider_latency",
            latency_ms / 1000.0,
            tags={"provider": actual_provider, "task_type": task_type},
        )
        return response
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        status_code = getattr(e, "status_code", None)
        _health_tracker.record_failure(provider_name, "call failed", status_code=status_code)
        record_metric(
            "provider",
            "provider_error",
            1.0,
            tags={"provider": provider_name, "task_type": task_type, "error": str(e)[:100]},
        )
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
    raise AllProvidersExhausted(
        task_type,
        f"all providers rate-limited{wait_msg}",
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
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        _health_tracker.record_failure(provider_name, "stream failed", status_code=status_code)
        raise


@track_performance
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
            raise AllProvidersExhausted(task_type, str(e)) from e

    # Semantic cache + budget checks (skip for embed)
    query_text = prompt  # used for semantic cache key
    cacheable = task_type in ("fast", "reason", "code", "batch")
    task_class = classify_task(task_type, source="")

    # Check semantic cache first
    if cacheable:
        try:
            sc = _get_semantic_cache()
            if sc is not None:
                cached_response = sc.get(query_text, task_type=task_type)
                if cached_response is not None:
                    logger.debug("Semantic cache hit for task_type=%s", task_type)
                    return cached_response.get("content", str(cached_response))
        except Exception:  # noqa: S110
            pass  # cache failure must not break LLM path

    # Check token budget
    try:
        budget = get_budget()
        estimated_tokens = len(query_text.split()) * 2
        if not budget.can_spend(task_class, estimated_tokens):
            tier_priority = budget.config["tiers"].get(task_class, {}).get("priority", 3)
            if tier_priority >= 2:
                raise BudgetExhaustedError(
                    f"Daily token budget exhausted for '{task_class}'. "
                    f"Try again after {_budget_reset_str()}"
                )
            logger.warning("Budget exceeded for %s, proceeding (priority tier)", task_class)
    except BudgetExhaustedError:
        raise
    except Exception:  # noqa: S110
        pass  # budget check failure should not break LLM path

    # Health-weighted provider ordering
    providers = _get_provider_order(config, task_type)

    # Provider intelligence optimization
    try:
        from ai.provider_intel import get_intel

        excluded = []
        intel = get_intel()
        best = intel.choose_best(task_type, exclude=excluded)
        if best and best in providers:
            providers = [best] + [p for p in providers if p != best]
    except Exception:  # noqa: S110
        pass  # intel failure should not break routing

    if not providers:
        raise AllProvidersExhausted(task_type, "no available providers")

    # Manual cache lookup
    cache_key = f"{task_type}:{hashlib.sha256(prompt.encode()).hexdigest()}"
    cached = _llm_cache.get(cache_key)
    if cached is not None:
        return cached["content"]

    # Memory retrieval for context enrichment
    try:
        from ai.memory import get_memory

        memories = get_memory().retrieve_memories(query=prompt, top_k=3)
        if memories:
            memory_context = "\n".join(f"- {m['summary']}" for m in memories)
            prompt = f"Previous relevant context:\n{memory_context}\n\nCurrent query: {prompt}"
    except Exception:  # noqa: S110
        pass  # memory retrieval should not break LLM path

    last_error = None
    for provider in providers:
        try:
            response = _try_provider(provider, task_type, prompt, **kwargs)
            _increment_usage(task_type, response)
            _track_cost(response, task_type=task_type, provider=provider)
            content = response.choices[0].message.content
            ttl = _TASK_TTL.get(task_type, 300)
            if ttl > 0:
                _llm_cache.set(cache_key, {"content": content}, ttl=ttl)

            # Record spend and cache response (best-effort)
            try:
                budget = get_budget()
                _usage = getattr(response, "usage", None)
                actual_tokens = getattr(_usage, "total_tokens", None) or estimated_tokens
                cost = float(getattr(_usage, "cost", None) or 0.0)
                budget.record_spend(task_class, actual_tokens, cost)

                if cacheable:
                    sc = _get_semantic_cache()
                    if sc is not None:
                        sc.put(
                            query_text,
                            {"content": content},
                            task_type=task_type,
                        )
            except Exception:  # noqa: S110
                pass  # recording failure must not break response

            return content
        except Exception as e:
            last_error = e
            logger.warning("Provider '%s' failed: %s", provider, e)
            continue

    raise AllProvidersExhausted(
        task_type,
        f"all providers exhausted. Last error: {last_error}",
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

    # Extract query text for semantic cache from last user message
    query_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            query_text = msg.get("content", "")
            break

    cacheable = task_type in ("fast", "reason", "code", "batch")
    task_class = classify_task(task_type, source="")

    # Check semantic cache first
    if cacheable and query_text:
        try:
            sc = _get_semantic_cache()
            if sc is not None:
                cached_response = sc.get(query_text, task_type=task_type)
                if cached_response is not None:
                    logger.debug("Semantic cache hit for task_type=%s", task_type)
                    return cached_response.get("content", str(cached_response))
        except Exception:  # noqa: S110
            pass  # cache failure must not break LLM path

    # Check token budget
    try:
        budget = get_budget()
        estimated_tokens = len(query_text.split()) * 2 if query_text else 100
        if not budget.can_spend(task_class, estimated_tokens):
            tier_priority = budget.config["tiers"].get(task_class, {}).get("priority", 3)
            if tier_priority >= 2:
                raise BudgetExhaustedError(
                    f"Daily token budget exhausted for '{task_class}'. "
                    f"Try again after {_budget_reset_str()}"
                )
            logger.warning("Budget exceeded for %s, proceeding (priority tier)", task_class)
    except BudgetExhaustedError:
        raise
    except Exception:  # noqa: S110
        pass  # budget check failure should not break LLM path

    providers = _get_provider_order(config, task_type)

    if not providers:
        raise AllProvidersExhausted(task_type, "no available providers")

    # Manual cache lookup
    _msg_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    cache_key = f"{task_type}:chat:{_msg_hash}"
    cached = _llm_cache.get(cache_key)
    if cached is not None:
        return cached["content"]

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
            _track_cost(response, task_type=task_type, provider=actual_provider)
            content = response.choices[0].message.content
            ttl = _TASK_TTL.get(task_type, 300)
            if ttl > 0:
                _llm_cache.set(cache_key, {"content": content}, ttl=ttl)

            # Record spend and cache response (best-effort)
            try:
                budget = get_budget()
                _usage = getattr(response, "usage", None)
                actual_tokens = getattr(_usage, "total_tokens", None) or estimated_tokens
                cost = float(getattr(_usage, "cost", None) or 0.0)
                budget.record_spend(task_class, actual_tokens, cost)

                if cacheable and query_text:
                    sc = _get_semantic_cache()
                    if sc is not None:
                        sc.put(
                            query_text,
                            {"content": content},
                            task_type=task_type,
                        )
            except Exception:  # noqa: S110
                pass  # recording failure must not break response

            return content
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            _health_tracker.record_failure(provider, "call failed", status_code=status_code)
            last_error = e
            logger.warning("Provider '%s' failed (chat): %s", provider, e)
            continue

    raise AllProvidersExhausted(
        task_type,
        f"all providers exhausted. Last error: {last_error}",
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
        raise ValueError(f"task_type must be one of {valid_stream_types}, got '{task_type}'")

    config = _load_config()
    _check_rate_limits(config, task_type)

    providers = _get_provider_order(config, task_type)

    if not providers:
        raise AllProvidersExhausted(task_type, "no available providers")

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
                provider,
                e,
            )
            continue

    raise AllProvidersExhausted(
        task_type,
        f"all providers exhausted. Last error: {last_error}",
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
    _llm_cache.clear()
    reset_cost_stats()


def reset_health_scores() -> None:
    """Reset all provider health scores to 1.0. Called on service startup."""
    _health_tracker.reset_all_scores()
