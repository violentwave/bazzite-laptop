# Phase P53 — Agent Orchestration Expansion

> **Status:** Planning  
> **Date:** 2026-04-09  
> **Baseline:** Post-P52 (82 MCP tools, 2317 tests, 26 LanceDB tables, 22 timers, 0 ruff errors)  
> **CC Prompt Numbering:** Continues from 100 (use 101+)
> **Historical context:** references to Newelle in this plan describe a now-retired legacy client.

---

## Objective

Elevate the bazzite-laptop AI layer from a collection of independent tool-calling agents into a **workflow-driven multi-agent coordination system** — where security, dev, and gaming agents can hand off tasks to each other, share context, and compose multi-step operations through a common orchestration bus.

---

## Current State Assessment

### What Exists (Post-P52)

| Component | Location | State |
|---|---|---|
| 5 agent modules | `ai/agents/` | Isolated — `security_audit`, `code_quality_agent`, `performance_tuning`, `knowledge_storage`, `timer_sentinel` |
| Workflow engine | `ai/workflows/` | Basic — `definitions.py`, `runner.py`, `triggers.py` — no cross-agent handoff |
| MCP bridge | `ai/mcp_bridge/` | 82 tools, scoped loading (P52) — no orchestration tool |
| Collab layer | `ai/collab/` | Exists from P29-P33 — task queue/context sharing in place |
| Root `agents/` YAML | `agents/*.yaml` | 5 YAML stubs (architect, coder, reviewer, security-architect, tester) — decision pending |

### Gap Analysis

- Agents operate in silos — no mechanism for Agent A to trigger Agent B with shared context
- `ai/workflows/runner.py` lacks a task-handoff protocol between named agents
- No `workflow.*` MCP tools exposed — users cannot trigger orchestrated workflows from legacy clients
- Root `agents/*.yaml` stubs are disconnected from `ai/agents/` Python implementations
- No observability on inter-agent message passing or handoff latency

---

## P53 Deliverables

### P53-A: Agent Orchestration Bus (`ai/orchestration/`)

New module providing:
- `AgentMessage` dataclass — typed task handoff envelope (source_agent, target_agent, task_type, payload, correlation_id, priority)
- `OrchestrationBus` — async pub/sub message broker (in-process, no external deps)
- `AgentRegistry` — maps agent names to callable handlers
- `HandoffProtocol` — defines accept/reject/delegate semantics

File layout:
```
ai/orchestration/
├── __init__.py
├── bus.py          # OrchestrationBus
├── message.py      # AgentMessage, TaskEnvelope
├── registry.py     # AgentRegistry
└── protocol.py     # HandoffProtocol, task type constants
```

Constraints:
- NEVER import `ai.router` in `ai/orchestration/`
- NEVER use `shell=True` in subprocess
- Pure async (`asyncio`) — no threading
- All message passing must be atomic (no partial writes to shared state)

### P53-B: Agent Adapters — Wire Existing Agents to Bus

Wrap each existing agent with a `BaseAgent` interface:

```python
class BaseAgent(ABC):
    name: str
    supported_task_types: list[str]
    async def handle(self, message: AgentMessage) -> AgentResult
    async def can_handle(self, task_type: str) -> bool
```

Adapters for:
- `SecurityAuditAgent` — task types: `scan_ioc`, `run_audit`, `check_cve_freshness`
- `CodeQualityAgent` — task types: `lint_check`, `ast_query`, `suggest_refactor`
- `PerformanceTuningAgent` — task types: `profile_tool`, `detect_regression`, `tune_cache`
- `KnowledgeStorageAgent` — task types: `store_insight`, `retrieve_context`, `summarize_session`
- `TimerSentinelAgent` — task types: `check_timers`, `alert_stale`, `reschedule`

Handoff scenarios to implement and test:
1. **Security → Knowledge**: CVE scan result → auto-store in RAG with correlation tags
2. **CodeQuality → Performance**: Lint clean → trigger performance profile on changed files
3. **TimerSentinel → Security**: Stale timer detected → trigger `run_audit` for that subsystem
4. **Performance → Knowledge**: Regression detected → store tuning insight

### P53-C: Workflow Upgrade — Multi-Agent Compositions

Extend `ai/workflows/` to support agent-composed workflows:

- `WorkflowStep` gains optional `agent` field — steps can dispatch to named agents
- `runner.py` updated to call `OrchestrationBus.dispatch()` for agent-targeted steps
- New workflow definitions:
  - `security_deep_scan` — TimerSentinel → SecurityAudit → KnowledgeStorage
  - `code_health_check` — CodeQuality → PerformanceTuning → KnowledgeStorage
  - `morning_briefing_enriched` — all 5 agents in parallel fan-out, KnowledgeStorage final collect

### P53-D: MCP Tools — `workflow.*` Namespace (6 new tools)

Expose orchestration to legacy assistant clients/users:

| Tool | Description |
|---|---|
| `workflow.list` | List all registered workflow definitions with status |
| `workflow.run` | Trigger a named workflow with optional params (readOnly: false) |
| `workflow.status` | Get current status / last run result of a workflow |
| `workflow.agents` | List all registered agents with supported task types |
| `workflow.handoff` | Manually dispatch a task to a named agent |
| `workflow.history` | Query LanceDB `workflow_runs` table for past runs |

Total after P53: **88 MCP tools** (+6)

### P53-E: LanceDB Table — `workflow_runs`

New table schema:
```python
class WorkflowRun(LanceModel):
    run_id: str          # UUID
    workflow_name: str
    triggered_by: str    # "timer", "user", "agent:<name>"
    started_at: datetime
    completed_at: datetime | None
    status: str          # pending | running | completed | failed
    steps: str           # JSON array of step results
    agent_messages: str  # JSON array of AgentMessage envelopes
    error: str | None
```

LanceDB tables after P53: **27** (+1)

### P53-F: Root `agents/` YAML Decision — Wire or Remove

The root `agents/` directory contains 5 YAML stubs (`architect.yaml`, `coder.yaml`, `reviewer.yaml`, `security-architect.yaml`, `tester.yaml`). These are Claude Flow artifacts disconnected from the Python agent implementations.

**Recommended decision: KEEP and wire them** as OpenCode agent profile configs, mapping each YAML to the corresponding `ai/agents/` adapter via `agents/` → `ai/agents/<name>_adapter.py` convention. If the team decides not to use Claude Flow, DELETE them in P53 pre-flight.

### P53-G: Tests

Test coverage targets:
- `tests/test_orchestration_bus.py` — 25+ unit tests (message dispatch, registry lookup, handoff protocol)
- `tests/test_agent_adapters.py` — 20+ tests (one per agent × 4 task types each)
- `tests/test_workflow_orchestrated.py` — 15+ integration tests (multi-step workflows, agent fan-out)
- `tests/test_mcp_workflow_tools.py` — 6 smoke tests (one per new MCP tool)

Target: **2317 + 66 = 2383 tests** (≥0 failures)

---

## CC Prompts (101–107)

### CC-101: Pre-flight + Scaffolding
```
/feature-dev
Objective: P53 pre-flight and scaffolding

Do:
1. Run: pytest --tb=short -q && ruff check ai/ — confirm 0 errors, all tests pass
2. Confirm git status is clean on master
3. Create ai/orchestration/ with __init__.py, bus.py, message.py, registry.py, protocol.py (stubs only)
4. Add ai/orchestration/ to mcp-bridge-allowlist.yaml (scoped import entry)
5. Run ruff check ai/orchestration/ — 0 errors
6. Commit: "feat(p53): scaffold ai/orchestration module"

Do NOT:
- Do NOT import ai.router in any orchestration file
- Do NOT implement any logic yet — stubs only

Done when: ruff clean, git committed, orchestration/ exists with 5 files
```

### CC-102: OrchestrationBus Core
```
/feature-dev
Objective: Implement OrchestrationBus, AgentMessage, AgentRegistry

Query Context7 for asyncio Queue patterns before writing.

Do:
1. Implement AgentMessage dataclass in message.py (source_agent, target_agent, task_type, payload: dict, correlation_id: str, priority: int = 0)
2. Implement AgentRegistry in registry.py — register/lookup/list handlers
3. Implement OrchestrationBus in bus.py — dispatch(message), subscribe(agent_name, handler), async queue
4. Write tests/test_orchestration_bus.py (25 tests: dispatch, registry, round-trip)
5. Run pytest tests/test_orchestration_bus.py -v && ruff check ai/orchestration/
6. Commit: "feat(p53): implement OrchestrationBus and AgentMessage"

Do NOT:
- Do NOT use shell=True
- Do NOT import ai.router
- Do NOT use threading — asyncio only

Done when: 25 bus tests pass, 0 ruff errors
```

### CC-103: BaseAgent + 5 Adapters
```
/feature-dev
Objective: BaseAgent interface + adapter wrappers for all 5 existing agents

Do:
1. Add protocol.py: BaseAgent ABC, AgentResult dataclass, HandoffProtocol, TASK_TYPE constants
2. Create ai/agents/security_audit_adapter.py wrapping SecurityAuditAgent
3. Create ai/agents/code_quality_adapter.py wrapping CodeQualityAgent
4. Create ai/agents/performance_tuning_adapter.py wrapping PerformanceTuningAgent
5. Create ai/agents/knowledge_storage_adapter.py wrapping KnowledgeStorageAgent
6. Create ai/agents/timer_sentinel_adapter.py wrapping TimerSentinelAgent
7. Register all 5 in AgentRegistry at startup (ai/orchestration/__init__.py)
8. Write tests/test_agent_adapters.py (20 tests, mock agent internals)
9. Run full pytest && ruff check
10. Commit: "feat(p53): BaseAgent adapters for all 5 agents"

Do NOT:
- Do NOT modify ai/router.py and ai/mcp_bridge/ in the same commit
- Do NOT inline business logic in adapters — delegate to wrapped agent

Done when: 20 adapter tests pass, all prior tests still pass
```

### CC-104: Workflow Engine Upgrade
```
/feature-dev
Objective: Extend ai/workflows/ to support agent-dispatched steps

Do:
1. Update WorkflowStep in definitions.py to add optional `agent: str | None` field
2. Update runner.py: if step.agent is set, dispatch via OrchestrationBus.dispatch()
3. Add 3 new workflow definitions: security_deep_scan, code_health_check, morning_briefing_enriched
4. Write tests/test_workflow_orchestrated.py (15 integration tests)
5. Run full pytest && ruff check
6. Commit: "feat(p53): agent-dispatched workflow steps + 3 new workflow defs"

Done when: 15 workflow tests pass, existing workflow tests still pass
```

### CC-105: MCP Tools — workflow.* namespace
```
/feature-dev
Objective: Add 6 workflow.* MCP tools

Do NOT modify ai/router.py in this prompt. Only touch ai/mcp_bridge/.

Do:
1. Add workflow_runs LanceDB table schema (ai/rag/tables.py or equivalent)
2. Implement 6 tools in ai/mcp_bridge/handlers/workflow_tools.py:
   workflow.list, workflow.run, workflow.status, workflow.agents, workflow.handoff, workflow.history
3. Add all 6 to configs/mcp-bridge-allowlist.yaml with appropriate readOnly annotations
4. Wire into mcp_bridge dispatch (_execute_python_tool)
5. Write tests/test_mcp_workflow_tools.py (6 smoke tests)
6. Run full pytest && ruff check
7. Commit: "feat(p53): workflow.* MCP tools (6 new tools, 88 total)"

Done when: 6 workflow tools registered, smoke tests pass, tool count = 88
```

### CC-106: agents/ YAML Decision + Wiring
```
/feature-dev
Objective: Resolve root agents/ YAML status

Do:
1. Read each agents/*.yaml and determine if Claude Flow format
2. If keeping: update each YAML to reference the corresponding ai/agents/*_adapter.py path
3. Update scripts/check-repo-structure.py to validate agents/ as permanent
4. Update docs/REPO-STRUCTURE.md and docs/AGENT.md to document agents/ purpose
5. Commit: "chore(p53): wire agents/ YAMLs to Python adapters"

Alternatively if removing:
1. `git rm -r agents/` and update check-repo-structure.py
2. Commit: "chore(p53): remove legacy agents/ YAML stubs"

Done when: agents/ status resolved, structure validator passes
```

### CC-107: Docs + Full Verification
```
/feature-dev
Objective: P53 final docs reconciliation and verification

Do:
1. Update docs/AGENT.md: tool count 88, LanceDB tables 27, add orchestration/ section
2. Update docs/CHANGELOG.md: append P53 entry
3. Update docs/USER-GUIDE.md: add workflow.* tool usage examples
4. Update docs/newelle-system-prompt.md: add workflow.* tools to legacy assistant skill block
5. Update HANDOFF.md: post-P53 state
6. Run: pytest --tb=short -q (target: 2383 tests, 0 failures)
7. Run: ruff check ai/ (0 errors)
8. Run: python scripts/check-repo-structure.py
9. /code-review
10. Commit: "docs(p53): reconcile all docs to post-P53 state"

Done when: all tests pass, 0 ruff, docs current, git clean
```

---

## Pre-Phase Blockers

| Item | Action | Owner |
|---|---|---|
| PR #18 (cryptography 46.0.7) | **MERGE NOW** — CVE-2026-39892 security fix | GitHub web UI |
| rescue/p45-cleanup-and-docs PR | Confirm merged or reopen | GitHub web UI |
| Dependabot triage | Merge remaining safe PRs after #18 | GitHub web UI |
| agents/ YAML decision | Decide before CC-106 | You |

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| OrchestrationBus deadlock on circular handoff | Medium | Add max-depth guard (default 5) in HandoffProtocol |
| ai/mcp_bridge + ai/router.py touched in same prompt | High if not careful | CC-105 explicitly bans router.py changes |
| agent adapters break existing agent test isolation | Medium | Mock OrchestrationBus in all existing agent tests |
| workflow_runs table migration pain | Low | Additive-only schema, new table |

---

## Success Criteria

- [ ] `ai/orchestration/` module exists and is lint-clean
- [ ] All 5 existing agents have BaseAgent adapters registered in AgentRegistry
- [ ] 4 handoff scenarios implemented and tested
- [ ] 6 new `workflow.*` MCP tools registered (total: 88)
- [ ] `workflow_runs` LanceDB table created (total: 27)
- [ ] 3 new multi-agent workflow definitions run end-to-end
- [ ] ≥2383 tests, 0 failures
- [ ] 0 ruff errors
- [ ] AGENT.md, CHANGELOG.md, HANDOFF.md all reconciled
- [ ] Legacy assistant system prompt updated with workflow.* tools
