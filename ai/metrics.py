"""Metrics recorder — buffered LanceDB time-series for the AI layer.

Provides two systems in one module:

1. ``MetricsRecorder`` — LanceDB-backed persistent time-series (P24 spec).
   Use ``get_recorder()`` and ``record_metric(metric_type, name, value, ...)``.

2. ``track_performance`` / ``get_metrics`` / ``reset_metrics`` — lightweight
   in-memory counters (backward-compat with P40 tests and embedder.py).
   ``record_metric(name, value)`` (2-arg form) also writes here.
"""
from __future__ import annotations

import functools
import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger(__name__)

# ── LanceDB constants ────────────────────────────────────────────────────────

VALID_METRIC_TYPES = {"cache", "budget", "provider", "tool", "timer"}
TABLE_NAME = "metrics"
FLUSH_COUNT = 100
FLUSH_INTERVAL_S = 60

_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("ts", pa.string()),
    pa.field("metric_type", pa.string()),
    pa.field("name", pa.string()),
    pa.field("tags", pa.string()),
    pa.field("value", pa.float32()),
    pa.field("window_s", pa.int32()),
])

# ── In-memory store (backward-compat) ───────────────────────────────────────

_metrics: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"calls": 0, "total_ms": 0.0, "errors": 0, "last_ms": 0.0}
)
_metrics_lock = threading.Lock()


# ── LanceDB MetricsRecorder ──────────────────────────────────────────────────

class MetricsRecorder:
    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or str(VECTOR_DB_DIR)
        self._db = lancedb.connect(path)
        self._table = self._ensure_table()
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()

    def _ensure_table(self):
        try:
            return self._db.open_table(TABLE_NAME)
        except Exception:
            return self._db.create_table(TABLE_NAME, schema=_SCHEMA)

    def record(
        self,
        metric_type: str,
        name: str,
        value: float,
        tags: dict | str | None = None,
        window_s: int = 60,
    ) -> None:
        if metric_type not in VALID_METRIC_TYPES:
            raise ValueError(
                f"Invalid metric_type {metric_type!r}. Must be one of {VALID_METRIC_TYPES}"
            )
        if isinstance(tags, dict):
            tags_str = json.dumps(tags)
        elif tags is None:
            tags_str = "{}"
        else:
            tags_str = str(tags)
        row = {
            "id": str(uuid.uuid4()),
            "ts": datetime.now(UTC).isoformat(),
            "metric_type": metric_type,
            "name": name,
            "tags": tags_str,
            "value": float(value),
            "window_s": int(window_s),
        }
        with self._lock:
            self._buffer.append(row)
        self._maybe_flush()

    def _maybe_flush(self) -> None:
        with self._lock:
            count = len(self._buffer)
            elapsed = time.monotonic() - self._last_flush
        if count >= FLUSH_COUNT or elapsed >= FLUSH_INTERVAL_S:
            self._flush()

    def _flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            rows = self._buffer[:]
            self._buffer.clear()
            self._last_flush = time.monotonic()
        try:
            self._table.add(rows)
        except Exception:
            logger.exception("MetricsRecorder flush failed")

    def flush(self) -> None:
        self._flush()

    def query_summary(
        self,
        hours: int = 24,
        metric_type: str | None = None,
    ) -> dict[str, Any]:
        try:
            self._flush()
            cutoff = datetime.fromtimestamp(
                time.time() - hours * 3600, tz=UTC
            ).isoformat()
            df = self._table.to_pandas()
            df = df[df["ts"] >= cutoff]
            if metric_type:
                df = df[df["metric_type"] == metric_type]
            if df.empty:
                return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}
            vals = df["value"].astype(float)
            return {
                "count": int(len(vals)),
                "mean": float(vals.mean()),
                "min": float(vals.min()),
                "max": float(vals.max()),
                "p95": float(vals.quantile(0.95)),
            }
        except Exception:
            logger.exception("query_summary failed")
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}

    def get_raw(
        self,
        hours: int = 24,
        metric_type: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        try:
            self._flush()
            cutoff = datetime.fromtimestamp(
                time.time() - hours * 3600, tz=UTC
            ).isoformat()
            df = self._table.to_pandas()
            df = df[df["ts"] >= cutoff]
            if metric_type:
                df = df[df["metric_type"] == metric_type]
            df = df.tail(limit)
            return df.to_dict(orient="records")
        except Exception:
            logger.exception("get_raw failed")
            return []


_recorder: MetricsRecorder | None = None
_recorder_lock = threading.Lock()


def get_recorder() -> MetricsRecorder:
    global _recorder
    if _recorder is None:
        with _recorder_lock:
            if _recorder is None:
                _recorder = MetricsRecorder()
    return _recorder


# ── Backward-compat in-memory helpers ───────────────────────────────────────


def track_performance[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that records call count, latency, and errors.

    Writes to the in-memory ``_metrics`` dict (readable via ``get_metrics``)
    and best-effort to LanceDB via ``record_metric``.
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
            record_metric("tool", func.__qualname__, 0.0, tags={"error": "1"})
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            with _metrics_lock:
                entry = _metrics[func.__qualname__]
                entry["calls"] += 1
                entry["total_ms"] += elapsed_ms
                entry["last_ms"] = elapsed_ms
            record_metric("tool", func.__qualname__, elapsed_ms)

    return wrapper


def get_metrics(name: str | None = None) -> dict[str, dict[str, Any]] | dict[str, Any]:
    """Return a snapshot of in-memory metrics recorded via ``track_performance``.

    Args:
        name: If provided, return metrics for a single function (includes
              ``avg_ms``). Otherwise return the full metrics dict.
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
    """Clear in-memory metrics.

    Args:
        name: If provided, clear only that key. Otherwise clear everything.
    """
    with _metrics_lock:
        if name is not None:
            _metrics.pop(name, None)
        else:
            _metrics.clear()


# ── record_metric (dual-mode) ────────────────────────────────────────────────


def record_metric(  # type: ignore[misc]
    metric_type_or_name: str,
    name_or_value: str | float,
    value: float | None = None,
    tags: dict | str | None = None,
    window_s: int = 60,
) -> None:
    """Record a metric.

    Two call signatures are supported:

    **New (LanceDB)**: ``record_metric(metric_type, name, value, tags, window_s)``
        ``metric_type`` must be in ``VALID_METRIC_TYPES``.

    **Legacy (in-memory)**: ``record_metric(name, numeric_value)``
        Writes to the in-memory ``_metrics`` dict readable via ``get_metrics``.
    """
    if value is None:
        # Legacy 2-arg form: record_metric(name, numeric_value)
        val = float(name_or_value)
        with _metrics_lock:
            _metrics[metric_type_or_name]["calls"] += 1
            _metrics[metric_type_or_name]["total_ms"] += val
    else:
        # New 3+-arg form: record_metric(metric_type, name, value, ...)
        try:
            get_recorder().record(
                metric_type_or_name,
                str(name_or_value),
                value,
                tags=tags,
                window_s=window_s,
            )
        except Exception:
            logger.debug("record_metric suppressed error", exc_info=True)
