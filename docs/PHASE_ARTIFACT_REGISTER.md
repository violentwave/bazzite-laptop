# Phase Artifact Register — Bazzite AI Layer

> Per-phase inventory of repo artifacts and Notion references.
> Updated 2026-04-17.
> Canonical source: Notion `Bazzite Phases` database + `git log` + repo artifacts.
> Use this file as the artifact ledger. Use `docs/PHASE_INDEX.md` for the full chronological phase index.

## Artifact Naming Conventions

| Phase Artifact Type | Naming Pattern | Example |
|---------------------|----------------|---------|
| Planning Document | `P{NN}_PLAN.md` | `P68_PLAN.md` |
| Completion Report | `P{NN}_COMPLETION_REPORT.md` | `P61_COMPLETION_REPORT.md` |
| Training Summary | `P{NN}_TRAINING_SUMMARY.md` | `P61_TRAINING_SUMMARY.md` |
| Remediation Summary | `P{NN}_REMEDIATION_SUMMARY.md` | `P60_REMEDIATION_SUMMARY.md` |
| Evidence Bundle | `docs/evidence/p{NN}/` | `docs/evidence/p118/` |
| Code Module | `ai/{module}/` | `ai/orchestration/` |
| Test Suite | `tests/test_{module}.py` | `tests/test_pattern_store.py` |
| Systemd Timer | `systemd/{timer}.timer` | `ai-workflow-health.timer` |
| Config File | `configs/{name}.yaml` | `configs/mcp-bridge-allowlist.yaml` |

## Current Artifact State

| Category | Current State |
|----------|---------------|
| Current completed Security Autopilot + Workbench phases | `P119`, `P120`, `P121`, `P122`, `P123`, `P124`, `P125`, `P126`, `P127` |
| Current active phase | None |
| Next gated phase | `P128 — Identity Step-Up` |
| Primary phase truth | Notion `Bazzite Phases` row properties |
| Lightweight session truth | `HANDOFF.md` |
| Standing agent rules | `docs/AGENT.md` |
| Phase chronology | `docs/PHASE_INDEX.md` |
| Security Autopilot + Agent Workbench roadmap | `docs/P119_P139_SECURITY_AUTOPILOT_AGENT_WORKBENCH_ROADMAP.md` |

## Historical Coverage Model

The repo has complete historical coverage across the earlier tranches, but older phases are increasingly normalized in `docs/PHASE_INDEX.md` rather than re-listed here line-by-line.

### Historical tranche summary

| Tranche | Coverage | Primary Artifact Families |
|--------|----------|---------------------------|
| P00-P18 | Foundation, router, MCP bridge, threat intel, RAG, timers, logging, docs | `ai/config.py`, `ai/router.py`, `ai/mcp_bridge/`, `ai/threat_intel/`, `ai/rag/`, `systemd/`, `docs/` |
| P19-P28 | Validation, timer sentinel, pattern store, budget/cache/metrics/memory/provider intel/alerts/insights | `ai/security/`, `ai/agents/`, `ai/rag/`, `ai/budget.py`, `ai/cache_semantic.py`, `ai/metrics.py`, `ai/memory.py`, `ai/provider_intel.py`, `ai/alerts/`, `ai/insights.py` |
| P29-P39 | Code intelligence, workflows, collaboration, testing intelligence, dynamic tools, dep audit | `ai/code_intel/`, `ai/workflows/`, `ai/collab/`, `ai/testing/`, `ai/tools/`, `ai/system/dep_audit.py` |
| P40-P58 | Observability, integration tests, Newelle sync, Slack/Notion integrations, orchestration, phase control, stabilization | `ai/intel_scraper.py`, `tests/test_integration_*.py`, `docs/newelle-*`, `ai/slack/`, `ai/notion/`, `ai/orchestration/`, `ai/phase_control/` |
| P59-P76 | Frontend capability pack, documentation normalization, code intelligence fusion, preflight, ingestion automation | `docs/frontend-capability-pack/`, `docs/patterns/frontend/`, `docs/PHASE_*.md`, `ai/code_intel/`, `ai/phase_control/` |
| P77-P100 | Midnight Glass UI architecture, shell/settings/providers/chat/security/projects UI, runtime recovery, evidence rebaseline, Figma reconciliation, connectivity recovery | `docs/PHASE77_*`, `docs/PHASE78_*`, `ui/src/components/*`, `ui/src/hooks/*`, `ai/settings_service.py`, `ai/shell_service.py`, `ai/project_workflow_service.py`, `docs/evidence/p99/`, `docs/evidence/p100/` |
| P101-P118 | MCP governance/discovery/marketplace/analytics/federation, browser evidence, routing persistence, chat profiles, runtime acceptance | `ai/mcp_bridge/governance/`, `ai/mcp_bridge/discovery.py`, `ai/mcp_bridge/marketplace/`, `ai/mcp_bridge/analytics_advanced/`, `ai/mcp_bridge/federation/`, `docs/evidence/p106/`, `docs/evidence/p113/`, `docs/evidence/p114/`, `docs/evidence/p115/`, `docs/evidence/p116/`, `docs/evidence/p117/`, `docs/evidence/p118/` |

> For exact older-phase entries, commit SHAs, and notes, see `docs/PHASE_INDEX.md` and the corresponding `docs/P{NN}_*.md` artifacts.

## Detailed Artifact Inventory — Recent and Active Phases

### P101 — MCP Tool Governance + Analytics Platform
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `73d6e54`
- **Repo Artifacts**:
  - `docs/P101_PLAN.md`
  - `ai/mcp_bridge/governance/`
  - governance analytics and lifecycle tooling
- **Tests**:
  - governance test coverage for lifecycle and analytics flows
- **Notion**: P101 row exists and is normalized to Done

### P102 — Dynamic Tool Discovery
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `1e081ca`
- **Repo Artifacts**:
  - `docs/P102_PLAN.md`
  - `ai/mcp_bridge/discovery.py`
  - `ai/mcp_bridge/dynamic_registry.py`
  - `ai/mcp_bridge/tool_discovery_handlers.py`
  - `tests/test_p102_dynamic_tool_discovery.py`
- **Notion**: P102 row exists and is Done

### P103 — MCP Tool Marketplace + Tool Pack Import/Export
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `8c9b2e5`
- **Repo Artifacts**:
  - `docs/P103_PLAN.md`
  - `ai/mcp_bridge/marketplace/`
  - `ai/mcp_bridge/tool_marketplace_handlers.py`
  - `tests/test_p103_tool_marketplace.py`
- **Notion**: P103 row exists and is Done

### P104 — Advanced Tool Analytics + Optimization
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `63cad68`
- **Repo Artifacts**:
  - `docs/P104_PLAN.md`
  - `ai/mcp_bridge/analytics_advanced/`
  - advanced anomaly/cost/forecast tooling
  - `tests/test_p104_advanced_tool_analytics.py`
- **Notion**: P104 row exists and is Done

### P105 — External MCP Federation Governance
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `c2866b6`
- **Repo Artifacts**:
  - `docs/P105_PLAN.md`
  - `ai/mcp_bridge/federation/`
  - federation governance models, trust, policy, discovery
  - `tests/test_p105_mcp_federation.py`
- **Notion**: P105 row exists and is Done

### P106 — Full Browser Runtime Evidence Rebaseline
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `0975fcb`
- **Repo Artifacts**:
  - `docs/P106_PLAN.md`
  - `docs/evidence/p106/`
- **Key Evidence**:
  - panel evidence JSON
  - visible text sampling
  - runtime validation outputs
- **Notion**: P106 row exists and is Done

### P107 — UI Feature Wiring Completion
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `bfd174c`
- **Repo Artifacts**:
  - `docs/P107_PLAN.md`
- **Key Output**:
  - UI wiring audit and runtime reality confirmation
- **Notion**: P107 row exists and is Done

### P108 — Persistent Shell Gateway Upgrade
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `9975b42`
- **Repo Artifacts**:
  - `docs/P108_PLAN.md`
  - `ai/shell_service.py`
  - `tests/test_shell_service.py`
- **Key Output**:
  - persistent session manager
  - audit logging
  - command safety checks
- **Notion**: P108 row exists and is Done

### P109 — Production-Grade Settings & Secrets UX
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `b0dc074`
- **Repo Artifacts**:
  - `docs/P109_PLAN.md`
  - settings/secrets validation and UX analysis artifacts
- **Key Output**:
  - PIN-gated settings/secrets UX confirmed production-grade
- **Notion**: P109 row exists and is Done

### P110 — Tool Control Center UI
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `60c5daf`
- **Repo Artifacts**:
  - `docs/P110_PLAN.md`
  - `ui/src/components/tool-control/`
  - `ui/src/app/page.tsx`
  - `ui/src/components/shell/IconRail.tsx`
- **Notion**: P110 row exists and is Done

### P111 — Final Production Acceptance Gate
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: pending repo-ledger normalization
- **Repo Artifacts**:
  - `docs/P111_PLAN.md`
  - `docs/P111_FINAL_ACCEPTANCE_REPORT.md`
  - repo-wide acceptance updates in `HANDOFF.md`, `CHANGELOG.md`, `USER-GUIDE.md`, `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`
- **Notion**: P111 row exists and is Done-ready / Done depending on latest row sync

### P112 — UI Dev Runtime / Turbopack Launch Crash Remediation
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: pending repo-ledger normalization
- **Repo Artifacts**:
  - `scripts/start-console-ui.sh`
  - `ui/next.config.ts`
  - `ui/src/components/security/SecurityOverview.tsx`
- **Notion**: P112 row exists and is Done

### P113 — Runtime UI Repair + Provider Onboarding
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `2ffc3dc`
- **Repo Artifacts**:
  - `ui/src/components/providers/ModelsList.tsx`
  - `ui/src/components/providers/AddProviderPanel.tsx`
  - `docs/evidence/p113_runtime_ui_repair.md`
- **Notion**: P113 row exists and is Done
- **External Artifacts**:
  - Figma / FigJam runtime repair references linked in Notion comments

### P114 — MCP Contract Convergence + Runtime Manifest CI
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `7ad75c6`
- **Repo Artifacts**:
  - `ai/mcp_bridge/parity_check.py`
  - `docs/evidence/p114/mcp_contract.json`
  - `docs/evidence/p114/parity_report.json`
- **Notion**: P114 row exists and is Done
- **Key Output**:
  - MCP contract v1.0.0
  - 169-tool parity validation

### P115 — Provider Registry + Routing Persistence v2
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `99a7fcb`
- **Repo Artifacts**:
  - `ai/provider_registry.py`
  - `tests/test_provider_registry.py`
  - `docs/evidence/p115/`
- **Notion**: P115 row exists and is Done

### P116 — Chat Workspace Routing Profiles
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `0e67e4f`
- **Repo Artifacts**:
  - `ui/src/components/chat/ChatProfileSelector.tsx`
  - `ui/src/components/chat/ChatRouteInfo.tsx`
  - `ui/src/hooks/useChatRouting.ts`
  - `docs/evidence/p116/`
- **Notion**: P116 row exists and is Done

### P117 — Security + Shell Operations Hardening v2
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `4537314`
- **Repo Artifacts**:
  - `ui/src/components/security/SecurityContainer.tsx`
  - `ui/src/components/shell-gateway/ShellContainer.tsx`
  - `docs/evidence/p117/`
- **Notion**: P117 row exists and is Done

### P118 — Final System Acceptance Gate
- **Status**: Done
- **Finished**: 2026-04-15
- **Commit SHA**: `fe619bf`
- **Repo Artifacts**:
  - `docs/evidence/p118/acceptance.md`
- **Notion**: P118 row exists and is Done
- **Key Output**:
  - full system acceptance validated across UI, backend, MCP, routing, failure-awareness, and docs

### P119 — Security Autopilot Core
- **Status**: Done
- **Finished**: 2026-04-16
- **Commit SHA**: `d502c21`
- **Repo Artifacts**:
  - `ai/security_autopilot/__init__.py`
  - `ai/security_autopilot/models.py`
  - `ai/security_autopilot/sensors.py`
  - `ai/security_autopilot/classifier.py`
  - `ai/security_autopilot/planner.py`
  - `ai/security_autopilot/audit.py`
  - `tests/test_security_autopilot.py`
  - `docs/P119_PLAN.md`
  - supporting ledger updates in `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`, `CHANGELOG.md`, `HANDOFF.md`
- **Notion**: P119 row exists and is Done
- **Key Output**:
  - plan-only Security Autopilot core
  - normalized findings/incidents/plans
  - redacted evidence handling
  - append-only hash-chained audit records
- **External Artifacts**:
  - FigJam reference: `P119-P122 Security Autopilot Control Flow`

### P120 — Security Policy Engine
- **Status**: Done
- **Finished**: 2026-04-16
- **Commit SHA**: `9471662`
- **Repo Artifacts**:
  - `ai/security_autopilot/policy.py`
  - `ai/security_autopilot/__init__.py`
  - `configs/security-autopilot-policy.yaml`
  - `tests/test_security_autopilot_policy.py`
  - `docs/P120_PLAN.md`
  - supporting ledger updates in `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`, `CHANGELOG.md`, `HANDOFF.md`
- **Notion**: P120 row exists and is Done
- **Key Output**:
  - policy modes (`monitor_only`, `recommend_only`, `safe_auto`, `approval_required`, `lockdown`)
  - allow / approval / block decisions
  - malformed-input rejection
  - redaction-aware policy output

### P121 — Security Autopilot UI
- **Status**: Done
- **Finished**: 2026-04-16
- **Commit SHA**: `c120c9f`
- **Repo Artifacts**:
  - `docs/P121_PLAN.md`
  - `docs/evidence/p121/validation.md`
  - `ai/security_autopilot/ui_service.py`
  - `ui/src/components/security/AutopilotPanels.tsx`
  - `ui/src/hooks/useSecurityAutopilot.ts`
  - `ui/src/types/security-autopilot.ts`
  - `tests/test_security_autopilot_tools.py`
- **Notion**: P121 row exists and is Done

### P122 — Safe Remediation Runner
- **Status**: Done
- **Finished**: 2026-04-16
- **Commit SHA**: pending
- **Repo Artifacts**:
  - `ai/security_autopilot/executor.py`
  - `ai/security_autopilot/__init__.py`
  - `tests/test_security_autopilot_executor.py`
  - `docs/P122_PLAN.md`
  - `docs/evidence/p122/`
  - supporting ledger updates in `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`, `CHANGELOG.md`, `HANDOFF.md`
- **Notion**: P122 row in progress during implementation; done on closeout
- **Key Output**:
  - fixed allowlisted action execution only
  - strict policy + approval gating before execution
  - deterministic rejection for unknown/unsafe/malformed requests
  - audit + evidence emission for every attempted action

### P123 — Agent Workbench Core
- **Status**: Done
- **Finished**: 2026-04-17
- **Commit SHA**: `14b0f78`
- **Repo Artifacts**:
  - `ai/agent_workbench/`
  - `ai/mcp_bridge/tools.py`
  - `ai/mcp_bridge/server.py`
  - `configs/mcp-bridge-allowlist.yaml`
  - `tests/test_agent_workbench.py`
  - `docs/P123_PLAN.md`
  - `docs/evidence/p123/validation.md`
- **Notion**: P123 row in progress during implementation; done on closeout
- **Key Output**:
  - bounded project registry with allowed-root path policy
  - controlled session lifecycle with backend allowlist and cwd boundary checks
  - read-only git status summaries and safe registered test command execution
  - 11 `workbench.*` MCP tools with allowlist contracts and drift-doc alignment

### P124 — Codex/OpenCode UI Integration
- **Status**: Done
- **Finished**: 2026-04-17
- **Commit SHA**: 28bf021
- **Repo Artifacts**:
  - `ui/src/components/workbench/`
  - `ui/src/hooks/useAgentWorkbench.ts`
  - `ui/src/types/agent-workbench.ts`
  - `ui/src/app/page.tsx`
  - `ui/src/components/shell/IconRail.tsx`
  - `ui/src/components/shell/CommandPalette.tsx`
  - `tests/test_agent_workbench_tools.py`
  - `docs/P124_PLAN.md`
  - `docs/evidence/p124/`
- **Key Output**:
  - unified Agent Workbench panel integrated into console navigation and routing
  - real project picker, bounded agent/profile controls, and session lifecycle actions
  - read-only git diff metadata, safe registered test execution, and handoff/artifact capture
  - explicit degraded-state rendering with no fake green states or secret exposure

### P125 — Browser Runtime Acceptance
- **Status**: Done
- **Finished**: 2026-04-17
- **Commit SHA**: 28bf021
- **Repo Artifacts**:
  - `docs/P125_PLAN.md`
  - `docs/evidence/p125/validation.md`
- **Key Output**:
  - Validated Security Autopilot UI (P121) runtime acceptance
  - Validated Agent Workbench UI (P124) runtime acceptance
  - MCP bridge and LLM proxy health verified
  - UI typecheck, build, lint, and tests pass
  - Browser evidence at http://localhost:3000 shows unified console with Security and Workbench panels
  - P126 scope NOT implemented

### P126 — Full Autopilot Acceptance Gate
- **Status**: Done
- **Finished**: 2026-04-17
- **Commit SHA**: 7d3b17b
- **Repo Artifacts**:
  - `docs/evidence/p126/validation.md`
- **Key Output**:
  - Validated P119–P125 as integrated system
  - Policy modes verified (recommend_only/approval/safe_auto)
  - Approval gates proven (executor.py approval.approved flag)
  - Remediation safety proven (bounded actions, no arbitrary shell)
  - Workbench safety proven (project registry, session isolation, git read-only)
  - No unrestricted AI execution verified
  - No secrets exposed verified
  - MCP bridge: 193 tools, status ok
  - LLM proxy: status ok
  - UI typecheck/build: pass
  - Ruff/targeted pytest: pass
  - **Result**: PASS — Approval gates and safety proofs confirmed

### P119 — Security Autopilot Core
- **Status**: Done
- **Finished**: 2026-04-16

| Type | Path | Description |
|------|------|-------------|
| Plan | `docs/P119_PLAN.md` | Phase scope, safety boundaries, and validation commands |
| Backend Package | `ai/security_autopilot/__init__.py` | Public exports for P119 autopilot primitives |
| Backend Module | `ai/security_autopilot/models.py` | Typed models for findings, incidents, plans, decisions, audit, evidence |
| Backend Module | `ai/security_autopilot/sensors.py` | Safe adapters for approved Bazzite security/system/log/agent signals |
| Backend Module | `ai/security_autopilot/classifier.py` | Finding normalization and incident grouping heuristics |
| Backend Module | `ai/security_autopilot/planner.py` | Plan-only remediation generation with no destructive actions |
| Backend Module | `ai/security_autopilot/audit.py` | Redacted evidence bundles + append-only hash-chained audit ledger |
| Tests | `tests/test_security_autopilot.py` | Coverage for model safety, sensors, classification, grouping, planning, audit |

### P120 — Security Policy Engine
- **Status**: Done
- **Finished**: 2026-04-16

| Type | Path | Description |
|------|------|-------------|
| Plan | `docs/P120_PLAN.md` | P120 objective, policy semantics, safety constraints, validation, DoD |
| Backend Module | `ai/security_autopilot/policy.py` | Policy modes/categories/decisions, request/result models, evaluator, redaction, and config loader |
| Config | `configs/security-autopilot-policy.yaml` | Default safe policy rules for mode-based allow/approval/block behavior |
| Package Export | `ai/security_autopilot/__init__.py` | Public policy engine exports |
| Tests | `tests/test_security_autopilot_policy.py` | Coverage for safe defaults, lockdown, malformed input, redaction, and P119 action evaluation |

### P121 — Security Autopilot UI
- **Status**: Done
- **Finished**: 2026-04-16

| Type | Path | Description |
|------|------|-------------|
| Plan | `docs/P121_PLAN.md` | Phase scope, safety boundaries, and validation commands for Security Autopilot UI |
| Evidence | `docs/evidence/p121/validation.md` | Validation matrix and command outcomes |
| Backend Module | `ai/security_autopilot/ui_service.py` | Read-only aggregation for autopilot overview/findings/incidents/evidence/audit/policy/queue |
| MCP Bridge | `ai/mcp_bridge/tools.py` | Added `security.autopilot_*` tool handlers with explicit degraded responses |
| Config | `configs/mcp-bridge-allowlist.yaml` | Registered seven `security.autopilot_*` read-only tools |
| UI Hook | `ui/src/hooks/useSecurityAutopilot.ts` | Aggregates autopilot tool calls with partial/degraded state handling |
| UI Types | `ui/src/types/security-autopilot.ts` | Typed contracts for autopilot surfaces |
| UI Components | `ui/src/components/security/AutopilotPanels.tsx` | Seven autopilot surface panels |
| UI Integration | `ui/src/components/security/SecurityContainer.tsx` | Security panel tab model switched to autopilot-focused surfaces |
| Tests | `tests/test_security_autopilot_tools.py` | Coverage for overview aggregation, plan-only queue, and redaction behavior |

### P122 — Safe Remediation Runner
- **Status**: Done
- **Finished**: 2026-04-16

| Type | Path | Description |
|------|------|-------------|
| Plan | `docs/P122_PLAN.md` | P122 objective, allowlisted action catalog, policy/approval gates, safety rules, and validation |
| Evidence | `docs/evidence/p122/README.md` | Evidence index and redaction behavior notes |
| Evidence | `docs/evidence/p122/safe-execution.json` | Sample successful non-destructive execution record |
| Evidence | `docs/evidence/p122/approval-required-rejection.json` | Sample deterministic rejection when approval is missing |
| Evidence | `docs/evidence/p122/blocked-rejection.json` | Sample policy-blocked rejection record |
| Evidence | `docs/evidence/p122/sample-audit.jsonl` | Sample append-only audit events from executor runs |
| Backend Module | `ai/security_autopilot/executor.py` | Fixed allowlisted remediation runner with safety checks, policy gating, and audit/evidence emission |
| Package Export | `ai/security_autopilot/__init__.py` | Exports for executor request/result and approval metadata |
| Tests | `tests/test_security_autopilot_executor.py` | Coverage for execution, rejection paths, safety checks, approval enforcement, and rollback metadata |

### P123 — Agent Workbench Core
- **Status**: Done
- **Finished**: 2026-04-17

| Type | Path | Description |
|------|------|-------------|
| Plan | `docs/P123_PLAN.md` | P123 scope, constraints, validation commands, and done criteria |
| Evidence | `docs/evidence/p123/validation.md` | Validation command outputs and pass/fail summary |
| Backend Package | `ai/agent_workbench/` | Project registry, sessions, sandbox profiles, git summary, testing hooks, and handoff helper |
| MCP Bridge | `ai/mcp_bridge/tools.py` | Added 11 `workbench.*` handlers with stable JSON envelopes |
| MCP Server | `ai/mcp_bridge/server.py` | Added workbench annotations and argument pass-through registration |
| Config | `configs/mcp-bridge-allowlist.yaml` | Added allowlist entries and argument schemas for all `workbench.*` tools |
| Tests | `tests/test_agent_workbench.py` | Coverage for path safety, persistence, session rules, command restrictions, and MCP envelopes |

### P124 — Codex/OpenCode UI Integration
- **Status**: Done
- **Finished**: 2026-04-17

| Type | Path | Description |
|------|------|-------------|
| Plan | `docs/P124_PLAN.md` | P124 objective, UI scope, boundaries, and validation outcomes |
| Evidence | `docs/evidence/p124/validation.md` | Validation command outcomes, service checks, and browser runtime notes |
| Evidence | `docs/evidence/p124/screenshots/` | Browser screenshots for project/session/git/test/handoff and degraded MCP state |
| UI Components | `ui/src/components/workbench/` | Workbench panel container and project/agent/session/git/test/handoff surfaces |
| UI Hook | `ui/src/hooks/useAgentWorkbench.ts` | MCP-backed project/session/git/test/handoff orchestration with truthful errors |
| UI Types | `ui/src/types/agent-workbench.ts` | Workbench contracts for project/session/git/test/handoff payloads |
| UI Integration | `ui/src/app/page.tsx` | Panel routing and status integration for Agent Workbench |
| Shell Navigation | `ui/src/components/shell/IconRail.tsx` | Added Workbench navigation entry to unified icon rail |
| Command Palette | `ui/src/components/shell/CommandPalette.tsx` | Added Workbench navigation command |
| Tests | `tests/test_agent_workbench_tools.py` | MCP contract coverage for P124 UI-dependent workbench envelopes |

### P126 — Full Autopilot Acceptance Gate
- **Status**: Done
- **Finished**: 2026-04-17

| Type | Path | Description |
|------|------|-------------|
| Evidence | `docs/evidence/p126/validation.md` | Full acceptance validation across P119-P125 with policy/approval gates, safety proofs, service checks |

### P127 — MCP Policy-as-Code and Approval Gates
- **Status**: Done
- **Finished**: 2026-04-17

| Type | Path | Description |
|------|------|-------------|
| Package | `ai/mcp_bridge/policy/` | MCP policy-as-code module |
| Models | `ai/mcp_bridge/policy/models.py` | ToolPolicyMetadata, RiskTier, PolicyDecision, ApprovalMetadata |
| Engine | `ai/mcp_bridge/policy/engine.py` | MCPToolPolicyEngine with default-deny evaluation |
| Approval | `ai/mcp_bridge/policy/approval.py` | ApprovalGate for high-risk tool enforcement |
| Tests | `tests/test_mcp_policy.py` | 26 policy tests |
| Evidence | `docs/evidence/p127/validation.md` | P127 validation with policy model, approval gates, bypass resistance, auditability |

## Cross-Phase Documentation

### Hub Docs (docs/ root)
| Doc | Purpose | Current Role |
|-----|---------|--------------|
| `AGENT.md` | Agent reference (rules, architecture, source-of-truth order) | Standing execution rules |
| `CHANGELOG.md` | Version history | Tracks recent closeouts |
| `USER-GUIDE.md` | End-user guide | Operator guidance |
| `PHASE_INDEX.md` | Master phase chronology | Full ledger and phase timeline |
| `PHASE_ARTIFACT_REGISTER.md` | Artifact inventory | This file |
| `PHASE_DEPENDENCY_GRAPH.mmd` | Dependency visualization | Graph reference |
| `PHASE_DELIVERY_TIMELINE.md` | Delivery timeline | Historical timing reference |
| `ARCHITECTURE_EVOLUTION.md` | Architecture evolution | Narrative reference |
| `PHASE_DOCUMENTATION_POLICY.md` | Artifact placement rules | Documentation policy |
| `P119_P139_SECURITY_AUTOPILOT_AGENT_WORKBENCH_ROADMAP.md` | Current roadmap | Security Autopilot + Agent Workbench direction |

### Design / External Artifact References
| Artifact | Purpose |
|----------|---------|
| `P119-P122 Security Autopilot Control Flow` | Design/runtime map for Security Autopilot foundation |
| `P123-P126 Agent Workbench Acceptance Flow` | Design/runtime map for Agent Workbench + acceptance phases (verified in P126) |

## Known Gaps / Notes

1. Older historical phases intentionally remain summarized here and detailed in `docs/PHASE_INDEX.md`.
2. Some earlier phases used batch commits, inferred historical boundaries, or alternative artifact types instead of dedicated `P{NN}_PLAN.md` documents.
3. P80 remains a repo-vs-Notion truth reconciliation note for future cleanup.
4. P125-P139 remain planned in Notion and tracked in the roadmap doc; they are not listed here as completed artifacts yet.

## Cross-References

- [PHASE_INDEX.md](./PHASE_INDEX.md) — Full phase chronology and current active phase pointer
- [PHASE_DEPENDENCY_GRAPH.mmd](./PHASE_DEPENDENCY_GRAPH.mmd) — Mermaid dependency visualization
- [PHASE_DELIVERY_TIMELINE.md](./PHASE_DELIVERY_TIMELINE.md) — Timeline view
- [ARCHITECTURE_EVOLUTION.md](./ARCHITECTURE_EVOLUTION.md) — Architecture evolution narrative
- [PHASE_DOCUMENTATION_POLICY.md](./PHASE_DOCUMENTATION_POLICY.md) — Future artifact placement rules
- [P119_P139_SECURITY_AUTOPILOT_AGENT_WORKBENCH_ROADMAP.md](./P119_P139_SECURITY_AUTOPILOT_AGENT_WORKBENCH_ROADMAP.md) — Current roadmap
