# Test Coverage Gap Analysis

Generated: 2026-04-06 (refreshed from repo truth)
Test suite: 2071 tests collected

---

## Summary

This analysis was refreshed to reflect the current state of the codebase.
All 16 modules previously marked as "missing tests" now have test coverage.

---

## Modules Now Actually Covered (2026-04-06)

The following modules were claimed missing in older analysis but now have test coverage:

| Module | Test Files | Verification |
|--------|------------|--------------|
| `ai.code_quality.analyzer` | test_code_quality_analyzer.py | ✓ 11 tests |
| `ai.code_quality.formatter` | test_code_quality_formatter.py | ✓ |
| `ai.code_quality.models` | test_code_quality_models.py | ✓ |
| `ai.code_quality.runner` | test_code_quality_runner.py | ✓ |
| `ai.gaming.models` | test_gaming_models.py | ✓ |
| `ai.log_intel.anomalies` | test_log_intel_anomalies.py | ✓ |
| `ai.log_intel.ingest` | test_log_intel_ingest.py | ✓ |
| `ai.log_intel.queries` | test_log_intel.py | ✓ |
| `ai.mcp_bridge.server` | test_mcp_bridge_server.py | ✓ 15 tests |
| `ai.mcp_bridge.tools` | test_mcp_bridge_tools.py | ✓ |
| `ai.threat_intel.formatters` | test_threat_formatters.py | ✓ |
| `ai.threat_intel.lookup` | test_ioc_lookup.py, test_threat_intel.py | ✓ |
| `ai.threat_intel.models` | test_threat_intel.py | ✓ |
| `ai.threat_intel.playbooks` | test_playbooks.py, test_playbooks_comprehensive.py | ✓ |
| `ai.threat_intel.summary` | test_threat_summary.py | ✓ |
| `ai.utils.freshness` | test_phase14_freshness.py | ✓ |

---

## Test Coverage by Module

Based on pytest collection and import analysis:

| Module | Test Files | Status |
|--------|------------|--------|
| `ai.agents` | test_agents.py | ✓ |
| `ai.budget` | test_budget.py | ✓ |
| `ai.cache` | test_cache.py, test_semantic_cache.py | ✓ |
| `ai.code_intel` | test_code_intel.py | ✓ |
| `ai.code_quality` | 10 test files | ✓ Full |
| `ai.config` | test_config.py | ✓ |
| `ai.gaming` | 7 test files | ✓ |
| `ai.health` | test_health.py, test_health_v2.py | ✓ |
| `ai.insights` | test_insights.py (11 tests) | ✓ |
| `ai.learning` | test_learning.py, test_testing_intelligence.py | ✓ |
| `ai.log_intel` | test_log_intel.py, test_log_intel_anomalies.py, test_log_intel_ingest.py | ✓ |
| `ai.memory` | test_memory.py | ✓ |
| `ai.metrics` | test_metrics.py, test_performance.py | ✓ |
| `ai.mcp_bridge` | test_mcp_bridge_*.py (multiple) | ✓ |
| `ai.provider_intel` | test_provider_intel.py | ✓ |
| `ai.rag` | 13 test files | ✓ Full |
| `ai.rate_limiter` | test_rate_limiter.py | ✓ |
| `ai.router` | test_router*.py (5 files) | ✓ |
| `ai.security` | test_security*.py | ✓ |
| `ai.system` | test_system*.py, test_perf_profiler.py, test_mcp_generator.py, etc. | ✓ |
| `ai.testing` | test_testing_intelligence.py | ✓ |
| `ai.threat_intel` | 11 test files | ✓ Full |

---

## Partially Covered Modules

These modules have some tests but may have gaps in coverage:

| Module | Current Coverage | Gap |
|--------|-----------------|-----|
| `ai.workflows` | test_workflows.py | Limited - runner only |
| `ai.tools` | test_tool_filter.py, test_tools.py | Builder/executor not fully tested |
| `ai.hooks` | test_hooks.py | Limited coverage |

---

## Still Missing Meaningful Tests

Priority 1 (high-impact, user-facing):

| Module | Rationale |
|--------|-----------|
| `ai/tray.py` | UI code, but state machine tested in test_tray_state_machine.py |
| `ai/tools/builder.py` | Dynamic tool creation - security-critical, limited tests |
| `ai/router.py` | Core routing logic - extensive test suite exists |

Priority 2 (lower impact):

| Module | Rationale |
|--------|-----------|
| `ai/workflows/definitions.py` | Workflow storage - limited test coverage |
| `ai/workflows/triggers.py` | Event triggers - limited test coverage |

---

## Test Statistics

- **Total tests collected**: 2071
- **Test files**: 100+
- **Modules with coverage**: 23 (full or partial)
- **Stale claims removed**: 16 modules previously marked "missing"

---

## Verification Commands

```bash
# Count tests
python -m pytest tests/ --collect-only -q

# Run specific module tests
python -m pytest tests/test_mcp_bridge*.py -v
python -m pytest tests/test_threat_intel.py -v

# Check coverage
ruff check ai/ tests/
```
