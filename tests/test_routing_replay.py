"""Tests for P131 routing replay and explanation lab."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.routing_replay import (
    ReplayFixture,
    load_replay_fixture,
    load_replay_fixtures,
    replay_all_fixtures,
    replay_fixture,
)

FIXTURE_DIR = Path("docs/routing_replay/fixtures")


def _fixture_by_id(fixtures: list[ReplayFixture], fixture_id: str) -> ReplayFixture:
    for fixture in fixtures:
        if fixture.fixture_id == fixture_id:
            return fixture
    raise AssertionError(f"fixture not found: {fixture_id}")


def test_fixture_loading_inventory() -> None:
    fixtures = load_replay_fixtures(FIXTURE_DIR)
    ids = sorted(f.fixture_id for f in fixtures)
    assert ids == [
        "budget-constrained-session",
        "coding-agent-session",
        "degraded-provider-failover",
        "security-analysis-reasoning",
        "stale-metrics-health-variation",
    ]


def test_explanation_payload_shape() -> None:
    fixture = load_replay_fixture(FIXTURE_DIR / "security_analysis_reasoning.json")
    explanation = replay_fixture(fixture)

    required_keys = {
        "requested_task_type",
        "available_candidates",
        "provider_health_inputs",
        "budget_constraints",
        "failover_conditions",
        "selected_route",
        "rejected_routes",
        "reason_summary",
    }
    assert required_keys.issubset(set(explanation.keys()))
    assert explanation["selected_route"] is not None


def test_stale_metrics_cap_is_visible() -> None:
    fixture = load_replay_fixture(FIXTURE_DIR / "stale_metrics_health_variation.json")
    explanation = replay_fixture(fixture)

    gemini_entry = next(c for c in explanation["available_candidates"] if c["provider"] == "gemini")
    assert gemini_entry["health"]["effective_score"] <= 0.8


def test_failover_marks_rejection() -> None:
    fixture = load_replay_fixture(FIXTURE_DIR / "degraded_provider_failover.json")
    explanation = replay_fixture(fixture)

    rejected = {r["provider"]: r["reason"] for r in explanation["rejected_routes"]}
    assert "groq" in rejected
    assert "forced_failover" in rejected["groq"]
    assert explanation["selected_route"]["provider"] != "groq"


def test_budget_constraint_blocks_route() -> None:
    fixture = load_replay_fixture(FIXTURE_DIR / "budget_constrained_session.json")
    explanation = replay_fixture(fixture)

    assert explanation["budget_constraints"]["applied"] is True
    assert explanation["budget_constraints"]["allowed"] is False
    assert explanation["selected_route"] is None


def test_task_type_differences_between_security_and_coding() -> None:
    fixtures = load_replay_fixtures(FIXTURE_DIR)
    security = replay_fixture(_fixture_by_id(fixtures, "security-analysis-reasoning"))
    coding = replay_fixture(_fixture_by_id(fixtures, "coding-agent-session"))

    assert security["requested_task_type"] == "reason"
    assert coding["requested_task_type"] == "code"
    assert security["task_chain"] != coding["task_chain"]


def test_sensitive_fixture_is_rejected(tmp_path: Path) -> None:
    payload = {
        "fixture_id": "bad-secret",
        "title": "bad",
        "task_type": "fast",
        "source": "unit",
        "prompt": "api_key=sk-THISSHOULDNOTPASS1234567890",
        "candidates": [
            {
                "provider": "groq",
                "model": "groq/llama",
                "task_types": ["fast"],
            }
        ],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="sensitive content"):
        load_replay_fixture(path)


def test_replay_does_not_mutate_router_defaults() -> None:
    from ai import router

    before_chain = dict(router._FALLBACK_CHAINS)
    before_router = router._router

    fixture = load_replay_fixture(FIXTURE_DIR / "coding_agent_session.json")
    _ = replay_fixture(fixture)

    assert dict(router._FALLBACK_CHAINS) == before_chain
    assert router._router is before_router


def test_replay_is_deterministic() -> None:
    fixture = load_replay_fixture(FIXTURE_DIR / "security_analysis_reasoning.json")
    first = replay_fixture(fixture)
    second = replay_fixture(fixture)
    assert first == second


def test_replay_all_report_shape() -> None:
    report = replay_all_fixtures(FIXTURE_DIR)
    assert report["fixture_count"] == 5
    assert len(report["fixtures"]) == 5
