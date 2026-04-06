"""Tests for ai/metrics.py — MetricsRecorder and helpers."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from ai.metrics import VALID_METRIC_TYPES, MetricsRecorder, get_recorder, record_metric


@pytest.fixture()
def recorder(tmp_path):
    return MetricsRecorder(db_path=str(tmp_path / "test_metrics_db"))


def test_valid_metric_types_set():
    assert VALID_METRIC_TYPES == {"cache", "budget", "provider", "tool", "timer"}


def test_record_metric_basic(recorder):
    recorder.record("cache", "hit", 1.0)
    recorder.flush()
    raw = recorder.get_raw(hours=1)
    assert len(raw) == 1
    assert raw[0]["name"] == "hit"
    assert raw[0]["metric_type"] == "cache"


def test_record_invalid_type_raises(recorder):
    with pytest.raises(ValueError, match="Invalid metric_type"):
        recorder.record("unknown_type", "test", 1.0)


def test_record_metric_tags_dict(recorder):
    recorder.record("provider", "latency", 0.42, tags={"provider": "gemini"})
    recorder.flush()
    raw = recorder.get_raw(hours=1)
    assert len(raw) == 1
    tags = json.loads(raw[0]["tags"])
    assert tags["provider"] == "gemini"


def test_record_metric_tags_none(recorder):
    recorder.record("tool", "call", 1.0, tags=None)
    recorder.flush()
    raw = recorder.get_raw(hours=1)
    assert json.loads(raw[0]["tags"]) == {}


def test_buffer_flush_on_count(tmp_path):
    rec = MetricsRecorder(db_path=str(tmp_path / "flush_count_db"))
    for i in range(100):
        rec.record("tool", f"call_{i}", float(i))
    # Auto-flush should have triggered at 100
    raw = rec.get_raw(hours=1)
    assert len(raw) == 100


def test_query_summary_empty(recorder):
    result = recorder.query_summary(hours=1)
    assert result["count"] == 0
    assert result["mean"] == 0.0


def test_query_summary_with_data(recorder):
    for i in range(1, 6):
        recorder.record("budget", "spend", float(i))
    recorder.flush()
    summary = recorder.query_summary(hours=1)
    assert summary["count"] == 5
    assert summary["min"] == pytest.approx(1.0, abs=0.01)
    assert summary["max"] == pytest.approx(5.0, abs=0.01)
    assert summary["mean"] == pytest.approx(3.0, abs=0.01)


def test_query_summary_type_filter(recorder):
    recorder.record("cache", "hit", 1.0)
    recorder.record("provider", "latency", 0.5)
    recorder.flush()
    cache_summary = recorder.query_summary(hours=1, metric_type="cache")
    provider_summary = recorder.query_summary(hours=1, metric_type="provider")
    assert cache_summary["count"] == 1
    assert provider_summary["count"] == 1


def test_get_raw_returns_correct_keys(recorder):
    recorder.record("timer", "run", 1.0)
    recorder.flush()
    raw = recorder.get_raw(hours=1)
    assert len(raw) == 1
    for key in ("id", "ts", "metric_type", "name", "tags", "value", "window_s"):
        assert key in raw[0]


def test_get_raw_limit(recorder):
    for i in range(10):
        recorder.record("tool", "call", float(i))
    recorder.flush()
    raw = recorder.get_raw(hours=1, limit=5)
    assert len(raw) == 5


def test_thread_safety(tmp_path):
    rec = MetricsRecorder(db_path=str(tmp_path / "thread_db"))

    def worker():
        for _ in range(10):
            rec.record("tool", "concurrent", 1.0)

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(worker) for _ in range(5)]
        for f in futures:
            f.result()
    rec.flush()
    raw = rec.get_raw(hours=1)
    assert len(raw) == 50


def test_singleton_same_instance():
    a = get_recorder()
    b = get_recorder()
    assert a is b


def test_record_metric_convenience(tmp_path, monkeypatch):
    rec = MetricsRecorder(db_path=str(tmp_path / "conv_db"))
    import ai.metrics as m

    monkeypatch.setattr(m, "_recorder", rec)
    record_metric("cache", "test", 1.0, tags={"x": "y"})
    rec.flush()
    raw = rec.get_raw(hours=1)
    assert len(raw) == 1
