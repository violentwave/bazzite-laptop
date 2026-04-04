"""Unit tests for ai/provider_intel.py ProviderIntel."""

import pytest

from ai.provider_intel import (
    PROVIDER_COSTS,
    PROVIDER_TASKS,
    ProviderIntel,
    get_intel,
)


class TestProviderIntel:
    def test_score_provider_returns_dict(self):
        intel = ProviderIntel()
        result = intel.score_provider("gemini", "fast")
        assert "provider" in result
        assert "score" in result
        assert "latency_p95" in result
        assert "error_rate" in result
        assert "health" in result

    def test_score_provider_unknown_task(self):
        intel = ProviderIntel()
        result = intel.score_provider("gemini", "unknown_task")
        assert result["score"] == 0.0

    def test_rank_providers_returns_list(self):
        intel = ProviderIntel()
        result = intel.rank_providers("fast")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_choose_best_excludes(self):
        intel = ProviderIntel()
        result = intel.choose_best("fast", exclude=["gemini"])
        assert result is None or result != "gemini"

    def test_get_status_format(self):
        intel = ProviderIntel()
        result = intel.get_status()
        assert "providers" in result
        assert isinstance(result["providers"], dict)


class TestProviderCosts:
    def test_all_costs_defined(self):
        assert "gemini" in PROVIDER_COSTS
        assert "groq" in PROVIDER_COSTS
        assert "openrouter" in PROVIDER_COSTS


class TestProviderTasks:
    def test_all_tasks_defined(self):
        assert "fast" in PROVIDER_TASKS
        assert "reason" in PROVIDER_TASKS
        assert "code" in PROVIDER_TASKS


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        i1 = get_intel()
        i2 = get_intel()
        assert i1 is i2
