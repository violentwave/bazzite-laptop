"""Routing evaluation and replay lab for P131.

Evaluation-only module for replaying sanitized routing fixtures without changing
production router defaults. The replay model compares candidate providers across
health, latency, estimated cost, task type eligibility, failover conditions,
and scoped budget constraints from P130.
"""

from __future__ import annotations

import json
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai.budget_scoped import BudgetManager, BudgetScope
from ai.config import LITELLM_CONFIG
from ai.health import HealthTracker

_DEFAULT_FIXTURES_DIR = Path("docs/routing_replay/fixtures")

_TASK_TYPE_CHAIN: dict[str, list[str]] = {
    "fast": ["fast", "reason"],
    "reason": ["reason"],
    "batch": ["batch", "reason"],
    "code": ["code", "reason"],
    "embed": ["embed"],
}

_SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
]

_PATH_PATTERN = re.compile(r"/(?:home|var/home|root)/[^\s\"']+")


@dataclass(frozen=True)
class ReplayCandidate:
    """Candidate route for replay evaluation."""

    provider: str
    model: str
    task_types: list[str]
    estimated_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True)
class ReplayBudget:
    """Scoped budget input consumed through P130 budget manager APIs."""

    scope_type: BudgetScope
    scope_id: str
    token_limit: int
    estimated_tokens: int
    spent_tokens: int = 0
    cost_limit_usd: float = 0.0
    spent_cost_usd: float = 0.0
    warning_threshold_pct: float = 80.0
    stop_threshold_pct: float = 100.0


@dataclass(frozen=True)
class ReplayFixture:
    """Sanitized routing replay scenario."""

    fixture_id: str
    title: str
    task_type: str
    source: str
    prompt: str
    candidates: list[ReplayCandidate]
    health_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    failover_providers: list[str] = field(default_factory=list)
    budget: ReplayBudget | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _extract_provider(model_name: str) -> str:
    if "/" in model_name:
        return model_name.split("/", 1)[0]
    return model_name


def _redact_text(value: str) -> str:
    sanitized = value
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    sanitized = _PATH_PATTERN.sub("[REDACTED_PATH]", sanitized)
    return sanitized


def _contains_sensitive_text(value: str) -> bool:
    return value != _redact_text(value)


def _candidate_score(candidate: ReplayCandidate, health_score: float) -> float:
    latency_component = 1.0 / (1.0 + max(candidate.estimated_latency_ms, 0.0) / 1000.0)
    cost_component = 1.0 / (1.0 + max(candidate.estimated_cost_usd, 0.0) * 1000.0)
    return round(health_score * latency_component * cost_component, 6)


def _task_type_chain(task_type: str) -> list[str]:
    return _TASK_TYPE_CHAIN.get(task_type, [task_type])


def _load_raw_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, sort_keys=True)
    if _contains_sensitive_text(serialized):
        raise ValueError(f"fixture contains sensitive content: {path}")
    return payload


def _parse_budget(raw: dict[str, Any] | None) -> ReplayBudget | None:
    if not raw:
        return None
    return ReplayBudget(
        scope_type=BudgetScope(raw.get("scope_type", "session")),
        scope_id=str(raw.get("scope_id", "replay")),
        token_limit=int(raw.get("token_limit", 0)),
        estimated_tokens=int(raw.get("estimated_tokens", 0)),
        spent_tokens=int(raw.get("spent_tokens", 0)),
        cost_limit_usd=float(raw.get("cost_limit_usd", 0.0)),
        spent_cost_usd=float(raw.get("spent_cost_usd", 0.0)),
        warning_threshold_pct=float(raw.get("warning_threshold_pct", 80.0)),
        stop_threshold_pct=float(raw.get("stop_threshold_pct", 100.0)),
    )


def load_replay_fixture(path: Path) -> ReplayFixture:
    """Load and validate one routing replay fixture from JSON."""
    raw = _load_raw_fixture(path)
    candidates = [
        ReplayCandidate(
            provider=str(item["provider"]),
            model=str(item["model"]),
            task_types=[str(task) for task in item.get("task_types", [])],
            estimated_latency_ms=float(item.get("estimated_latency_ms", 0.0)),
            estimated_cost_usd=float(item.get("estimated_cost_usd", 0.0)),
        )
        for item in raw.get("candidates", [])
    ]
    fixture = ReplayFixture(
        fixture_id=str(raw["fixture_id"]),
        title=str(raw.get("title", raw["fixture_id"])),
        task_type=str(raw["task_type"]),
        source=_redact_text(str(raw.get("source", ""))),
        prompt=_redact_text(str(raw.get("prompt", ""))),
        candidates=candidates,
        health_overrides=raw.get("health_overrides", {}),
        failover_providers=[str(p) for p in raw.get("failover_providers", [])],
        budget=_parse_budget(raw.get("budget")),
        metadata=raw.get("metadata", {}),
    )
    if not fixture.candidates:
        raise ValueError(f"fixture has no candidates: {path}")
    return fixture


def load_replay_fixtures(fixtures_dir: Path | None = None) -> list[ReplayFixture]:
    """Load all JSON fixtures from the replay fixture directory."""
    fixture_dir = fixtures_dir or _DEFAULT_FIXTURES_DIR
    paths = sorted(fixture_dir.glob("*.json"))
    return [load_replay_fixture(path) for path in paths]


def _budget_constraint(budget: ReplayBudget | None) -> dict[str, Any]:
    if budget is None:
        return {
            "applied": False,
            "allowed": True,
            "reason": "no_budget",
            "state": "active",
            "remaining_tokens": None,
        }

    with tempfile.TemporaryDirectory(prefix="routing-replay-budget-") as tmp_dir:
        manager = BudgetManager(db_path=Path(tmp_dir) / "budgets.json")
        created = manager.create_budget(
            scope_type=budget.scope_type,
            scope_id=budget.scope_id,
            name=f"replay_{budget.scope_id}",
            token_limit=budget.token_limit,
            cost_limit_usd=budget.cost_limit_usd,
            warning_threshold_pct=budget.warning_threshold_pct,
            stop_threshold_pct=budget.stop_threshold_pct,
        )
        created.spent_tokens = budget.spent_tokens
        created.spent_cost_usd = budget.spent_cost_usd
        check = manager.check_can_spend(
            created.budget_id,
            budget.estimated_tokens,
            0.0,
        )
        check["applied"] = True
        return check


def replay_fixture(fixture: ReplayFixture) -> dict[str, Any]:
    """Replay one fixture and return a deterministic explanation payload."""
    task_chain = _task_type_chain(fixture.task_type)
    tracker = HealthTracker()
    now = time.time()

    for provider, state in sorted(fixture.health_overrides.items()):
        health = tracker.get(provider)
        health.success_count = int(state.get("success_count", 0))
        health.failure_count = int(state.get("failure_count", 0))
        health.consecutive_failures = int(state.get("consecutive_failures", 0))
        health.total_latency_ms = float(state.get("total_latency_ms", 0.0))
        health.auth_broken = bool(state.get("auth_broken", False))
        health.last_probe_time = now - float(state.get("stale_seconds", 0.0))
        if bool(state.get("disabled", False)):
            health.disabled_until = now + 3600

    budget_check = _budget_constraint(fixture.budget)
    evaluations: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []

    for candidate in sorted(fixture.candidates, key=lambda c: (c.provider, c.model)):
        reasons: list[str] = []
        if not any(task in task_chain for task in candidate.task_types):
            reasons.append("task_type_ineligible")

        health = tracker.get(candidate.provider)
        health_state = {
            "provider": candidate.provider,
            "score": round(health.score, 6),
            "effective_score": round(health.effective_score, 6),
            "auth_broken": health.auth_broken,
            "disabled": health.is_disabled,
            "stale_seconds": round((now - health.last_probe_time), 3)
            if health.last_probe_time is not None
            else None,
        }
        if health.auth_broken or health.is_disabled:
            reasons.append("provider_unhealthy")

        if candidate.provider in fixture.failover_providers:
            reasons.append("forced_failover")

        if budget_check.get("allowed") is False:
            reasons.append(str(budget_check.get("reason", "budget_blocked")))

        score = _candidate_score(candidate, health.effective_score)
        evaluation = {
            "provider": candidate.provider,
            "model": candidate.model,
            "task_types": list(candidate.task_types),
            "latency_ms": round(candidate.estimated_latency_ms, 3),
            "estimated_cost_usd": round(candidate.estimated_cost_usd, 6),
            "health": health_state,
            "score": score,
            "accepted": len(reasons) == 0,
            "reasons": reasons,
        }
        evaluations.append(evaluation)
        if reasons:
            rejected.append({"provider": candidate.provider, "reason": ",".join(reasons)})

    accepted = [entry for entry in evaluations if entry["accepted"]]
    accepted.sort(key=lambda item: (-item["score"], item["provider"], item["model"]))
    selected = accepted[0] if accepted else None

    if selected is None and budget_check.get("allowed") is False:
        summary = (
            f"Route blocked by budget constraints ({budget_check.get('reason', 'budget_blocked')})."
        )
    elif selected is None:
        summary = "No viable candidate remained after health and failover filtering."
    else:
        summary = (
            "Selected provider with highest replay score after task-type, health, "
            "budget, and failover filtering."
        )

    payload = {
        "fixture_id": fixture.fixture_id,
        "title": fixture.title,
        "requested_task_type": fixture.task_type,
        "task_chain": task_chain,
        "source": fixture.source,
        "prompt": fixture.prompt,
        "available_candidates": evaluations,
        "provider_health_inputs": [entry["health"] for entry in evaluations],
        "budget_constraints": budget_check,
        "failover_conditions": sorted(fixture.failover_providers),
        "selected_route": (
            {
                "provider": selected["provider"],
                "model": selected["model"],
                "score": selected["score"],
            }
            if selected
            else None
        ),
        "rejected_routes": rejected,
        "reason_summary": summary,
    }
    return payload


def replay_all_fixtures(fixtures_dir: Path | None = None) -> dict[str, Any]:
    """Replay all fixtures and return a deterministic evaluation report."""
    fixtures = load_replay_fixtures(fixtures_dir)
    explanations = [replay_fixture(fixture) for fixture in fixtures]
    return {
        "fixture_count": len(explanations),
        "fixtures": explanations,
        "router_config_path": str(LITELLM_CONFIG),
    }
