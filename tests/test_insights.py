"""Tests for ai.insights.InsightsEngine.

lance is not installed in this environment.  Inject a module-level mock
into sys.modules BEFORE importing ai.insights so the top-level
``import lance`` succeeds without a real native extension.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pyarrow as pa

# ── Module-level mock for lance ──────────────────────────────────────────────
# Must be done before any import that touches ai.insights.
_mock_lance = sys.modules.setdefault("lance", MagicMock())

# ai/__init__.py is empty — inject LANCE_PATH so ai.insights can import it.
import ai as _ai_pkg  # noqa: E402

if not hasattr(_ai_pkg, "LANCE_PATH"):
    _ai_pkg.LANCE_PATH = "/tmp/test-lance"

import ai.insights as ins_mod  # noqa: E402

# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_mock_ds():
    """Return a mock lance dataset whose to_table() yields an empty PA table."""
    mock_ds = MagicMock()
    mock_ds.to_table.return_value = pa.table(
        {
            "timestamp": pa.array([], type=pa.string()),
            "data": pa.array([], type=pa.string()),
        }
    )
    return mock_ds


def _make_cache_metric(event: str) -> dict:
    return {"event": event, "ts": "2026-01-01T00:00:00"}


# ── Test classes ──────────────────────────────────────────────────────────────

class TestInsightsInit:
    def test_init_accepts_custom_path(self, tmp_path):
        custom = str(tmp_path / "custom_insights")
        mock_ds = _empty_mock_ds()

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=custom)

        assert engine.path == custom


class TestGenerateWeeklyInsights:
    def test_returns_expected_keys(self, tmp_path):
        mock_ds = _empty_mock_ds()

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            result = engine.generate_weekly_insights()

        assert set(result.keys()) >= {
            "generated_at",
            "period",
            "insights",
            "recommendations",
            "metrics_summary",
        }

    def test_period_is_7d(self, tmp_path):
        mock_ds = _empty_mock_ds()

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            result = engine.generate_weekly_insights()

        assert result["period"] == "7d"

    def test_healthy_system_insight(self, tmp_path):
        # 8 hits + 2 misses → 80% hit rate → above 70% threshold → system_healthy
        raw_cache = [_make_cache_metric("cache_hit")] * 8 + [
            _make_cache_metric("cache_miss")
        ] * 2
        mock_ds = _empty_mock_ds()

        def fake_get_raw(self_m, hours=24, metric_type=None, limit=1000):
            if metric_type == "cache_hit":
                return raw_cache
            return []

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", fake_get_raw),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            result = engine.generate_weekly_insights()

        types = [i["type"] for i in result["insights"]]
        assert "system_healthy" in types

    def test_low_cache_hit_rate_insight(self, tmp_path):
        # 3 hits + 7 misses → 30% hit rate → below 70% threshold
        raw_cache = [_make_cache_metric("cache_hit")] * 3 + [
            _make_cache_metric("cache_miss")
        ] * 7
        mock_ds = _empty_mock_ds()

        def fake_get_raw(self_m, hours=24, metric_type=None, limit=1000):
            if metric_type == "cache_hit":
                return raw_cache
            return []

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", fake_get_raw),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            result = engine.generate_weekly_insights()

        types = [i["type"] for i in result["insights"]]
        assert "cache_performance" in types


class TestGetLatestInsights:
    def test_empty_table_returns_empty_list(self, tmp_path):
        mock_ds = _empty_mock_ds()

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            result = engine.get_latest_insights()

        assert result == []

    def test_stored_insight_returned(self, tmp_path):
        payload = json.dumps({"period": "7d", "insights": []})

        # get_latest_insights calls lance.dataset(self.path) then .to_table()
        # .to_table().num_rows > 0 → .sort_by("timestamp").tail(limit)
        # The tail() result is iterated and each row["data"] is json-decoded.
        table_mock = MagicMock()
        table_mock.num_rows = 1
        table_mock.sort_by.return_value.tail.return_value = [
            {"timestamp": "2026-01-01T00:00:00", "data": payload}
        ]

        populated_ds = MagicMock()
        populated_ds.to_table.return_value = table_mock

        # During __init__ lance.dataset raises so write_dataset creates the schema.
        # During get_latest_insights we want lance.dataset to return populated_ds.
        # Use side_effect: first call (init) raises, second call (get_latest) returns.
        _mock_lance.dataset.side_effect = [Exception("not found"), populated_ds]

        with (
            patch.object(_mock_lance, "write_dataset"),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            result = engine.get_latest_insights()

        # Restore side_effect so other tests aren't affected
        _mock_lance.dataset.side_effect = None

        assert len(result) == 1
        assert "data" in result[0]


class TestStoreInsight:
    def test_store_calls_write_dataset(self, tmp_path):
        mock_ds = _empty_mock_ds()
        mock_write = MagicMock()

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset", mock_write),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            mock_write.reset_mock()
            engine._store_insight({"test": "data"})

        mock_write.assert_called_once()
        _, kwargs = mock_write.call_args
        assert kwargs.get("mode") == "append"

    def test_stored_data_is_json(self, tmp_path):
        mock_ds = _empty_mock_ds()
        captured_tables: list = []

        def capture_write(table, path, **kwargs):
            captured_tables.append(table)

        with (
            patch.object(_mock_lance, "dataset", return_value=mock_ds),
            patch.object(_mock_lance, "write_dataset", side_effect=capture_write),
            patch.object(ins_mod.MetricsRecorder, "__init__", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "get_raw", return_value=[]),
            patch.object(ins_mod.MetricsRecorder, "flush", return_value=None),
            patch.object(ins_mod.MetricsRecorder, "_ensure_table", return_value=None),
        ):
            engine = ins_mod.InsightsEngine(path=str(tmp_path / "ins"))
            captured_tables.clear()
            engine._store_insight({"key": "value", "num": 42})

        assert len(captured_tables) == 1
        written_table = captured_tables[0]
        data_col = written_table.column("data")
        raw_str = data_col[0].as_py()
        parsed = json.loads(raw_str)
        assert parsed["key"] == "value"
        assert parsed["num"] == 42
