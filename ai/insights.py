"""Insights engine — summarises AI layer activity without LLM calls."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger(__name__)

TABLE_NAME = "insights_cache"
DEFAULT_TTL_HOURS = 168  # 7 days

_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("ts", pa.string()),
    pa.field("kind", pa.string()),        # "weekly" | "on_demand"
    pa.field("summary", pa.string()),     # JSON-encoded dict
    pa.field("expires_at", pa.string()), # ISO8601 UTC
])


class InsightsEngine:
    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or str(VECTOR_DB_DIR)
        self._db = lancedb.connect(path)
        self._table = self._ensure_table()

    def _ensure_table(self):
        try:
            return self._db.open_table(TABLE_NAME)
        except Exception:
            return self._db.create_table(TABLE_NAME, schema=_SCHEMA)

    def _build_summary(self, kind: str) -> dict[str, Any]:
        summary: dict[str, Any] = {"kind": kind, "generated_at": datetime.now(UTC).isoformat()}

        # Metrics snapshot
        try:
            from ai.metrics import get_recorder
            rec = get_recorder()
            summary["cache_stats"] = rec.query_summary(hours=168, metric_type="cache")
            summary["provider_stats"] = rec.query_summary(hours=168, metric_type="provider")
            summary["budget_stats"] = rec.query_summary(hours=168, metric_type="budget")
        except Exception:
            logger.debug("insights: metrics unavailable", exc_info=True)

        # Recent memories
        try:
            from ai.memory import get_memory
            recent = get_memory().get_recent(n=5)
            summary["recent_memories"] = [m.get("summary", "") for m in recent]
        except Exception:
            logger.debug("insights: memory unavailable", exc_info=True)

        return summary

    def _store(self, kind: str, summary: dict[str, Any]) -> str:
        row_id = str(uuid.uuid4())
        expires_at = datetime.fromtimestamp(
            time.time() + DEFAULT_TTL_HOURS * 3600, tz=UTC
        ).isoformat()
        self._table.add([{
            "id": row_id,
            "ts": datetime.now(UTC).isoformat(),
            "kind": kind,
            "summary": json.dumps(summary),
            "expires_at": expires_at,
        }])
        return row_id

    def _prune_expired(self) -> None:
        try:
            now = datetime.now(UTC).isoformat()
            self._table.delete(f"expires_at < '{now}'")
        except Exception:
            logger.debug("insights: prune failed", exc_info=True)

    def generate_weekly(self) -> dict[str, Any]:
        self._prune_expired()
        summary = self._build_summary("weekly")
        self._store("weekly", summary)
        return summary

    def generate_on_demand(self) -> dict[str, Any]:
        summary = self._build_summary("on_demand")
        self._store("on_demand", summary)
        return summary

    def get_cached_insights(self, kind: str | None = None) -> list[dict[str, Any]]:
        try:
            self._prune_expired()
            df = self._table.to_pandas()
            now = datetime.now(UTC).isoformat()
            df = df[df["expires_at"] >= now]
            if kind:
                df = df[df["kind"] == kind]
            df = df.sort_values("ts", ascending=False)
            results = []
            for _, row in df.iterrows():
                try:
                    results.append(json.loads(row["summary"]))
                except Exception:  # noqa: BLE001
                    logger.debug("insights: failed to parse row", exc_info=True)
            return results
        except Exception:
            logger.exception("get_cached_insights failed")
            return []

    def format_for_newelle(self) -> str:
        cached = self.get_cached_insights()
        if not cached:
            return "No insights available yet. Run generate_weekly() to populate."
        latest = cached[0]
        lines = [f"# AI Layer Insights ({latest.get('generated_at', 'unknown')})"]
        if "cache_stats" in latest:
            cs = latest["cache_stats"]
            lines.append(f"Cache: {cs.get('count', 0)} lookups, mean={cs.get('mean', 0):.2f}")
        if "provider_stats" in latest:
            ps = latest["provider_stats"]
            lines.append(
                f"Provider latency p95: {ps.get('p95', 0):.3f}s over {ps.get('count', 0)} calls"
            )
        if "budget_stats" in latest:
            bs = latest["budget_stats"]
            total = bs.get("mean", 0) * bs.get("count", 1)
            lines.append(f"Budget: {bs.get('count', 0)} spend events, total={total:.0f} tokens")
        if "recent_memories" in latest:
            lines.append("Recent memories:")
            for m in latest["recent_memories"][:3]:
                lines.append(f"  - {m}")
        return "\n".join(lines)


_engine: InsightsEngine | None = None


def get_engine() -> InsightsEngine:
    global _engine
    if _engine is None:
        _engine = InsightsEngine()
    return _engine


def run_insights_generation() -> dict[str, Any]:
    return get_engine().generate_weekly()
