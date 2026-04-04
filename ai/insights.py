import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import lance
import pyarrow as pa

from ai import LANCE_PATH
from ai.metrics import MetricsRecorder


class InsightsEngine:
    def __init__(self, path: str | None = None):
        self.path = path or f"{LANCE_PATH}/insights"
        self.metrics = MetricsRecorder()
        self._ensure_schema()

    def _ensure_schema(self):
        Path(self.path).mkdir(parents=True, exist_ok=True)
        schema = pa.schema(
            [
                pa.field("timestamp", pa.string()),
                pa.field("insight_type", pa.string()),
                pa.field("description", pa.string()),
                pa.field("confidence", pa.float32()),
                pa.field("metrics_snapshot", pa.string()),
                pa.field("recommendations", pa.string()),
            ]
        )
        try:
            lance.dataset(self.path)
        except Exception:
            lance.write_dataset([], self.path, schema=schema)

    def generate_weekly_insights(self) -> dict[str, Any]:
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        metrics = self.metrics.query_timeseries(
            "cache_hit", since=week_ago
        ) + self.metrics.query_timeseries("budget_usage", since=week_ago)

        insights = []
        recommendations = []

        cache_hits = sum(1 for m in metrics if m.get("event") == "cache_hit")
        cache_misses = sum(1 for m in metrics if m.get("event") == "cache_miss")
        total = cache_hits + cache_misses
        hit_rate = cache_hits / total if total > 0 else 0

        if hit_rate < 0.7:
            insights.append(
                {
                    "type": "cache_performance",
                    "description": f"Cache hit rate {hit_rate:.1%} below 70% threshold",
                    "confidence": 0.85,
                    "recommendation": "Expand semantic cache TTL or improve embedding similarity",
                }
            )
            recommendations.append("Increase cache_ttl_minutes in config")
            recommendations.append("Review embedding model for semantic drift")

        budget_spends = [m for m in metrics if m.get("event") == "budget_spend"]
        if budget_spends:
            total_spend = sum(m.get("tokens", 0) for m in budget_spends)
            avg_daily = total_spend / 7
            if avg_daily > 50000:
                recommendations.append(
                    f"High daily spend: ~{avg_daily:.0f} tokens/day - review provider优先级"
                )

        if len(recommendations) == 0:
            insights.append(
                {
                    "type": "system_healthy",
                    "description": "All systems operating within normal parameters",
                    "confidence": 0.95,
                    "recommendation": "Continue current configuration",
                }
            )
            recommendations.append("No changes recommended")

        result = {
            "generated_at": datetime.now().isoformat(),
            "period": "7d",
            "insights": insights,
            "recommendations": recommendations,
            "metrics_summary": {
                "cache_hit_rate": hit_rate,
                "total_requests": total,
                "avg_daily_tokens": avg_daily if budget_spends else 0,
            },
        }

        self._store_insight(result)
        return result

    def _store_insight(self, data: dict[str, Any]):
        table = lance.dataset(self.path).to_table()
        batch = pa.record_batch(
            [[datetime.now().isoformat()], [json.dumps(data)]], schema=table.schema
        )
        lance.write_dataset(batch, self.path, mode="append")

    def get_latest_insights(self, limit: int = 4) -> list[dict[str, Any]]:
        ds = lance.dataset(self.path)
        table = ds.to_table()
        if table.num_rows == 0:
            return []
        return [{"data": json.loads(row["data"])} for row in table.sort_by("timestamp").tail(limit)]
