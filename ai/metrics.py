"""Metrics recording and aggregation for the Bazzite AI layer.

Provides MetricsRecorder for time-series observability of cache hit rates,
provider latency, budget usage, tool errors, and timer health. Writes to
LanceDB 'metrics' table with buffered writes and thread-safe flushing.
"""

import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger("bazzite-ai.metrics")

VALID_METRIC_TYPES = frozenset({"cache", "budget", "provider", "tool", "timer"})

METRICS_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("ts", pa.string()),
        pa.field("metric_type", pa.string()),
        pa.field("name", pa.string()),
        pa.field("tags", pa.string()),
        pa.field("value", pa.float32()),
        pa.field("window_s", pa.int32()),
    ]
)

BUFFER_SIZE = 100
FLUSH_INTERVAL_S = 60


class MetricsRecorder:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or VECTOR_DB_DIR
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = datetime.now(UTC)
        self._db = None
        self._table = None
        self._ensure_table()

    def _ensure_table(self) -> None:
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        if self._table is None:
            try:
                self._table = self._db.open_table("metrics")
            except Exception:
                self._table = self._db.create_table("metrics", schema=METRICS_SCHEMA)

    def record(
        self,
        metric_type: str,
        name: str,
        value: float,
        tags: dict[str, Any] | None = None,
        window_s: int = 60,
    ) -> None:
        if metric_type not in VALID_METRIC_TYPES:
            raise ValueError(
                f"Invalid metric_type '{metric_type}'. Must be one of {VALID_METRIC_TYPES}"
            )

        record = {
            "id": str(uuid.uuid4()),
            "ts": datetime.now(UTC).isoformat(),
            "metric_type": metric_type,
            "name": name,
            "tags": json.dumps(tags or {}),
            "value": float(value),
            "window_s": int(window_s),
        }
        self._buffer.append(record)
        self._maybe_flush()

    def _maybe_flush(self) -> None:
        now = datetime.now(UTC)
        should_flush = (
            len(self._buffer) >= BUFFER_SIZE
            or (now - self._last_flush).total_seconds() >= FLUSH_INTERVAL_S
        )
        if should_flush:
            self._flush()

    def _flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            data_to_flush = self._buffer.copy()
            self._buffer.clear()
            self._last_flush = datetime.now(UTC)

        try:
            self._ensure_table()
            self._table.add(data_to_flush)
            logger.debug(f"Flushed {len(data_to_flush)} metric records")
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")

    def flush(self) -> None:
        with self._lock:
            if self._buffer:
                self._flush()

    def query_summary(self, hours: int = 24, metric_type: str | None = None) -> dict[str, Any]:
        self.flush()
        self._ensure_table()

        cutoff = datetime.now(UTC)
        from datetime import timedelta

        cutoff = (cutoff - timedelta(hours=hours)).isoformat()

        df = self._table.to_pandas()
        if df.empty:
            return {
                "count": 0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p95": 0.0,
            }

        df = df[df["ts"] >= cutoff]
        if metric_type:
            df = df[df["metric_type"] == metric_type]

        if df.empty:
            return {
                "count": 0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p95": 0.0,
            }

        sorted_vals = sorted(df["value"].tolist())
        p95_idx = int(len(sorted_vals) * 0.95)
        p95 = sorted_vals[p95_idx] if sorted_vals else 0.0

        return {
            "count": len(df),
            "mean": float(df["value"].mean()),
            "min": float(df["value"].min()),
            "max": float(df["value"].max()),
            "p95": float(p95),
        }

    def get_raw(
        self, hours: int = 24, metric_type: str | None = None, limit: int = 1000
    ) -> list[dict[str, Any]]:
        self.flush()
        self._ensure_table()

        cutoff = datetime.now(UTC)
        from datetime import timedelta

        cutoff = (cutoff - timedelta(hours=hours)).isoformat()

        df = self._table.to_pandas()
        if df.empty:
            return []

        df = df[df["ts"] >= cutoff]
        if metric_type:
            df = df[df["metric_type"] == metric_type]

        df = df.tail(limit)
        return df.to_dict("records")


_recorder: MetricsRecorder | None = None
_recorder_lock = threading.Lock()


def get_recorder() -> MetricsRecorder:
    global _recorder
    if _recorder is None:
        with _recorder_lock:
            if _recorder is None:
                _recorder = MetricsRecorder()
    return _recorder


def record_metric(
    metric_type: str,
    name: str,
    value: float,
    tags: dict[str, Any] | None = None,
    window_s: int = 60,
) -> None:
    try:
        get_recorder().record(metric_type, name, value, tags, window_s)
    except Exception:  # noqa: S110
        pass  # Metrics should never break the main flow
