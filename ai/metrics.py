"""Lightweight performance metrics for the Bazzite AI layer.

Provides a thread-safe metrics store and a ``@track_performance`` decorator
for recording call counts, latencies, and error rates on key functions.

Usage:
    from ai.metrics import track_performance, get_metrics, reset_metrics

    @track_performance
    def my_expensive_function():
        ...

    stats = get_metrics("my_expensive_function")
    # {"calls": 42, "total_ms": 1234.5, "errors": 1, "avg_ms": 29.4}

    reset_metrics()  # clear all recorded data
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("ai.metrics")

T = TypeVar("T")

_metrics: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"calls": 0, "total_ms": 0.0, "errors": 0, "last_ms": 0.0}
)
_metrics_lock = threading.Lock()


def track_performance[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that records call count, latency, and errors.

    Metrics are stored in the module-level ``_metrics`` dict under the
    function's qualified name.  Safe to use on any synchronous function.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            with _metrics_lock:
                _metrics[func.__qualname__]["errors"] += 1
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            with _metrics_lock:
                entry = _metrics[func.__qualname__]
                entry["calls"] += 1
                entry["total_ms"] += elapsed_ms
                entry["last_ms"] = elapsed_ms

    return wrapper


def get_metrics(name: str | None = None) -> dict[str, dict[str, Any]] | dict[str, Any]:
    """Return a snapshot of recorded metrics.

    Args:
        name: If provided, return metrics for a single function.
              Otherwise return the full metrics dict.

    Returns:
        Dict of metric entries.  Each entry contains::

            {"calls": int, "total_ms": float, "errors": int, "last_ms": float}

        When a name is given, ``avg_ms`` is also included.
    """
    with _metrics_lock:
        if name is not None:
            entry = dict(_metrics.get(name, {}))
            if entry and entry["calls"] > 0:
                entry["avg_ms"] = entry["total_ms"] / entry["calls"]
            return entry
        result = {}
        for key, entry in _metrics.items():
            snap = dict(entry)
            if snap["calls"] > 0:
                snap["avg_ms"] = snap["total_ms"] / snap["calls"]
            result[key] = snap
        return result


def reset_metrics(name: str | None = None) -> None:
    """Clear recorded metrics.

    Args:
        name: If provided, clear only that function's metrics.
              Otherwise clear everything.
    """
    with _metrics_lock:
        if name is not None:
            _metrics.pop(name, None)
        else:
            _metrics.clear()


def record_metric(name: str, value: float) -> None:
    """Record an arbitrary metric value under the given name.

    This is a lightweight append-only counter for metrics that don't fit
    the decorator pattern (e.g. token counts, cache hit rates).

    Args:
        name: Metric key (e.g. "tokens.total", "cache.hits").
        value: Numeric value to add.
    """
    with _metrics_lock:
        _metrics[name]["calls"] += 1
        _metrics[name]["total_ms"] += value
