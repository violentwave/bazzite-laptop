"""Tests for ai/insights.py — InsightsEngine."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

import ai.insights as _ins_mod

# Pre-load modules so patch("ai.metrics.get_recorder") / patch("ai.memory.get_memory")
# can resolve them via sys.modules before any test runs.
import ai.memory  # noqa: F401
import ai.metrics  # noqa: F401
from ai.insights import InsightsEngine, get_engine, run_insights_generation

_MOCK_STATS = {"count": 10, "mean": 0.5, "min": 0.1, "max": 1.0, "p95": 0.9}


@pytest.fixture()
def engine(tmp_path):
    return InsightsEngine(db_path=str(tmp_path / "test_insights_db"))


# ── generate_weekly ──────────────────────────────────────────────────────────


def test_generate_weekly_returns_dict(engine):
    with patch("ai.metrics.get_recorder") as mock_rec, \
         patch("ai.memory.get_memory") as mock_mem:
        mock_rec.return_value.query_summary.return_value = _MOCK_STATS
        mock_mem.return_value.get_recent.return_value = []
        result = engine.generate_weekly()
    assert result["kind"] == "weekly"
    assert "generated_at" in result


def test_generate_on_demand_returns_dict(engine):
    with patch("ai.metrics.get_recorder") as mock_rec, \
         patch("ai.memory.get_memory") as mock_mem:
        mock_rec.return_value.query_summary.return_value = _MOCK_STATS
        mock_mem.return_value.get_recent.return_value = []
        result = engine.generate_on_demand()
    assert result["kind"] == "on_demand"


# ── get_cached_insights ──────────────────────────────────────────────────────


def test_get_cached_insights_empty(engine):
    results = engine.get_cached_insights()
    assert results == []


def test_get_cached_insights_after_generate(engine):
    with patch("ai.metrics.get_recorder") as mock_rec, \
         patch("ai.memory.get_memory") as mock_mem:
        mock_rec.return_value.query_summary.return_value = _MOCK_STATS
        mock_mem.return_value.get_recent.return_value = []
        engine.generate_weekly()
    cached = engine.get_cached_insights()
    assert len(cached) >= 1
    assert cached[0]["kind"] == "weekly"


def test_get_cached_insights_kind_filter(engine):
    with patch("ai.metrics.get_recorder") as mock_rec, \
         patch("ai.memory.get_memory") as mock_mem:
        mock_rec.return_value.query_summary.return_value = _MOCK_STATS
        mock_mem.return_value.get_recent.return_value = []
        engine.generate_weekly()
        engine.generate_on_demand()
    weekly = engine.get_cached_insights(kind="weekly")
    on_demand = engine.get_cached_insights(kind="on_demand")
    assert all(i["kind"] == "weekly" for i in weekly)
    assert all(i["kind"] == "on_demand" for i in on_demand)


# ── format_for_newelle ───────────────────────────────────────────────────────


def test_format_for_newelle_no_data(engine):
    result = engine.format_for_newelle()
    assert "No insights" in result


def test_format_for_newelle_with_data(engine):
    with patch("ai.metrics.get_recorder") as mock_rec, \
         patch("ai.memory.get_memory") as mock_mem:
        mock_rec.return_value.query_summary.return_value = {
            "count": 42, "mean": 0.25, "min": 0.1, "max": 1.0, "p95": 0.8
        }
        mock_mem.return_value.get_recent.return_value = [
            {"summary": "User prefers dark mode"}
        ]
        engine.generate_weekly()
    result = engine.format_for_newelle()
    assert "AI Layer Insights" in result
    assert "42" in result


# ── TTL expiry ───────────────────────────────────────────────────────────────


def test_ttl_expiry_prunes_old(tmp_path):
    eng = InsightsEngine(db_path=str(tmp_path / "ttl_db"))
    expired_ts = (datetime.now(UTC) - timedelta(hours=200)).isoformat()
    eng._table.add([{
        "id": "test-expired",
        "ts": expired_ts,
        "kind": "weekly",
        "summary": json.dumps({"kind": "weekly", "generated_at": expired_ts}),
        "expires_at": expired_ts,
    }])
    cached = eng.get_cached_insights()
    assert not any(i.get("generated_at") == expired_ts for i in cached)


# ── singletons & helpers ─────────────────────────────────────────────────────


def test_singleton_same_instance(engine, monkeypatch):
    # Pre-seed singleton with fixture engine so get_engine() skips DB creation
    monkeypatch.setattr(_ins_mod, "_engine", engine)
    a = get_engine()
    b = get_engine()
    assert a is b
    assert a is engine


def test_run_insights_generation():
    with patch("ai.insights.get_engine") as mock_engine:
        mock_engine.return_value.generate_weekly.return_value = {"kind": "weekly"}
        result = run_insights_generation()
    assert result["kind"] == "weekly"
