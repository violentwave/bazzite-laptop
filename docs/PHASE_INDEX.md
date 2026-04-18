# Phase Index — Bazzite AI Layer

> Master index of repo-tracked phases through P146.
> Updated 2026-04-18.
> Source of truth: Notion `Bazzite Phases` database + `git log`; Notion row properties are authoritative when repo docs lag.
> Note: references to legacy assistant/tray surfaces are historical phase records, not active runtime guidance.

## Quick Stats

| Metric | Value |
|--------|-------|
| Total Phases Tracked | P0-P146 tracked in repo index |
| Completed | P0-P146 complete in current repo-ledger terms |
| Active | P146 (Workspace personalization and preset persistence closeout) |
| Next Gated | P147 — (see P143 implementation map) |
| Historical Truth Conflict | P80 remains a repo-vs-Notion reconciliation note for later cleanup |
| Repo Docs | docs/*.md, docs/patterns/frontend/*.md, docs/frontend-capability-pack/*.md |
| Notion DB | `398c13ed-47f6-4f7e-9e54-eb339b462c90` |

## Phase Delivery Timeline

| Period | Phases | Delivery Pattern |
|--------|--------|------------------|
| 2026-02-03 to 2026-02-28 | P0-P9 | Foundation: initial setup, MCP bridge, threat intel |
| 2026-03-02 to 2026-03-20 | P10-P18 | Intelligence: RAG, timer expansion, structured logging |
| 2026-03-27 to 2026-04-03 | P19-P21 | Security: input validation, timer sentinel, pattern store |
| 2026-04-03 to 2026-04-08 | P22-P28 | Governance: stabilization phases (token budget, cache, metrics, memory, provider intel, alerts, insights) |
| 2026-04-07 to 2026-04-10 | P29-P33 | Scale: code intel, workflow engine, collab, testing intelligence, dynamic tools |
| 2026-04-08 to 2026-04-10 | P34-P39 | Integration: parity work, agent stabilization, dep audit |
| 2026-04-10 to 2026-04-11 | P40-P50 | Observability: intel scraper, integration tests, legacy assistant skills |
| 2026-04-09 to 2026-04-12 | P51-P58 | Control plane: Slack, Notion, phase control, cross-system burn down |
| 2026-04-10 to 2026-04-12 | P59-P69 | Frontend capability pack: P59 (branch convergence), P60 (intelligence reliability), P61 (frontend pack), P62 (pattern intel), P63 (QA layer), P64 (design/media), P65 (runtime harness), P66 (brief intake), P67 (deployment pack), P68 (GitNexus evaluation), P69 (ops runbooks) |
| 2026-04-13 to 2026-04-15 | P70-P118 | Documentation normalization, Midnight Glass UI, runtime repair, MCP governance, provider/routing persistence, release candidate acceptance |
| 2026-04-16 | P119-P122 | Security Autopilot foundation: core, policy, UI surfaces, and safe remediation runner |
| 2026-04-17 | P126-P130 | Full Autopilot Acceptance Gate + MCP Policy-as-Code + Local Identity + Workspace Isolation + Cost Quotas |
| Next | P133+ | Provenance graph, governance integration |

## Phase Index

| Phase | Name | Status | Commit SHA | Finished | Key Repo Artifacts | Key Notion Ref | Notes |
|-------|------|--------|------------|----------|-------------------|----------------|-------|
| P00 | Initial Foundation | Done | Initial | 2026-02-03 | ai/config.py, ai/router.py, ai/health.py | Notion row | Project bootstrapping |
| P01 | Systemd Service Setup | Done | Early systemd | 2026-02-05 | systemd/*.service | Notion row | Inferred historical boundary |
| P02 | LiteLLM Router V2 | Done | d5ff4cc3 | 2026-02-08 | ai/router.py (873 lines) | Notion row | Provider chain foundation |
| P03 | MCP Bridge Alpha | Done | Early MCP | 2026-02-12 | ai/mcp_bridge/ | Notion row | Inferred historical boundary |
| P04 | Threat Intel Core | Done | Early security | 2026-02-15 | ai/threat_intel/ | Notion row | Inferred historical boundary |
| P05 | RAG Foundation | Done | RAG init | 2026-02-18 | ai/rag/store.py | Notion row | LanceDB integration |
| P06 | Tool Registration | Done | Tool reg | 2026-02-20 | configs/mcp-bridge-allowlist.yaml | Notion row | Inferred historical boundary |
| P07 | Health Metrics | Done | Health metrics | 2026-02-22 | ai/health.py | Notion row | Inferred historical boundary |
| P08 | Code Quality Setup | Done | Code quality | 2026-02-25 | .ruff.toml, pyproject.toml | Notion row | Inferred historical boundary |
| P09 | Gaming MangoHud | Done | Gaming modes | 2026-02-28 | ai/gaming/ | Notion row | Inferred historical boundary |
| P10 | Intel Scraper Core | Done | Intel scraper | 2026-03-02 | ai/intel_scraper.py | Notion row | CVE/release/ Fedora watchers |
| P11 | Timer Expansion | Done | Timer expansion | 2026-03-05 | ai/cache.py (211 lines) | Notion row | Multiple systemd timers |
| P12 | PingMiddleware Keepalive | Done | 73fe5f6 | 2026-03-08 | ai/mcp_bridge/server.py | Notion row | 25s keepalive |
| P13 | BM25 Full-Text Search | Done | Provider search | 2026-03-10 | ai/rag/store.py | Notion row | LanceDB FTS |
| P14 | Cost Tracking + Sentry | Done | Multiple | 2026-03-12 | ai/router.py, ai/llm_proxy.py | Notion row | Cost + error tracking |
| P15 | Workflow Engine | Done | Workflow engine | 2026-03-14 | ai/workflows/ | Notion row | ReAct loop foundation |
| P16 | Structured Logging | Done | 2e5cb5fe | 2026-03-16 | JSON logging | Notion row | Structured output |
| P17 | Test Infrastructure | Done | Testing expansion | 2026-03-18 | tests/ (133 files) | Notion row | 2221 test functions |
| P18 | Documentation Pass | Done | Documentation | 2026-03-20 | docs/ (24 files) | Notion row | AGENT.md, USER-GUIDE.md |
| P19 | Input Validation Layer | Done | c97aba0 | 2026-04-03 | ai/security/input_validator.py | Notion row | 51 tests |
| P20 | Timer Sentinel + Headless | Done | 903ab26 | 2026-04-03 | scripts/security-briefing.py | Notion row | Headless security |
| P21 | Pattern Store | Done | 7eb5906 | 2026-04-03 | ai/rag/pattern_store.py | Notion row | 11 tests, code patterns |
| P22 | Token Budget (P24 batch) | Done | 9f5c3b6e | 2026-04-05 | ai/budget.py | Notion row | Stabilization phase |
| P23 | Semantic Cache (P24 batch) | Done | dc293c5e | 2026-04-06 | ai/cache_semantic.py | Notion row | Stabilization phase |
| P24 | Metrics Recording | Done | 98c5c2d2 | 2026-04-07 | ai/metrics.py | Notion row | 14 tests |
| P25 | Conversation Memory | Done | 98c5c2d2 | 2026-04-07 | ai/memory.py (250 lines) | Notion row | conversation_memory table |
| P26 | Provider Intel | Done | 98c5c2d2 | 2026-04-07 | ai/provider_intel.py | Notion row | P24-P28 batch |
| P27 | Security Alerts | Done | 98c5c2d2 | 2026-04-07 | ai/alerts/rules.py | Notion row | 15 tests |
| P28 | Weekly Insights | Done | 98c5c2d2 | 2026-04-08 | ai/insights.py | Notion row | 9 tests |
| P29 | Structural Code Intel | Done | e2ad3753 | 2026-04-09 | ai/code_intel/ | Notion row | AST parser + grimp |
| P30 | Workflow Engine Expansion | Done | 9b7af54 | 2026-04-09 | ai/workflows/ | Notion row | ReAct loop |
| P31 | Agent Collaboration | Done | 82de124 | 2026-04-09 | ai/collab/ | Notion row | Task queue |
| P32 | Testing Intelligence | Done | 0ea5077 | 2026-04-09 | ai/testing/ | Notion row | Stability tracker |
| P33 | Dynamic Tools | Done | 42cacb0 | 2026-04-09 | ai/tools/builder.py | Notion row | system.create_tool |
| P34 | Integration Parity | Done | b45fc5ba | 2026-04-10 | Various fixes | Notion row | P34-P36 batch |
| P35 | Agent Stabilization | Done | 790bd62 | 2026-04-10 | Agent fixes | Notion row | P34-P36 batch |
| P36 | Documentation Reconcile | Done | 773f87f | 2026-04-10 | AGENT.md counts | Notion row | P34-P36 batch |
| P37 | Alert Rules | Done | 39cef00 | 2026-03-27 | ai/alerts/ | Notion row | rules.py, dispatcher.py |
| P38 | Task Patterns | Done | 39cef00 | 2026-03-29 | ai/learning/handoff_parser.py | Notion row | 9 tests |
| P39 | DepAudit | Done | 39cef00 | 2026-04-01 | ai/system/depaudit.py | Notion row | 11 tests |
| P40 | Intel Scraper Expansion | Done | debc0a3 | 2026-04-02 | ai/intel_scraper.py (18K+ lines) | Notion row | 6 MCP tools |
| P41 | Unified Ingest Pipeline | Done | Combined | 2026-04-03 | ai/system/ingest_pipeline.py | Notion row | Unified ingest |
| P42 | Stabilization | Done | cf9e7db | 2026-04-05 | Test fixes | docs/P42_PLAN.md | Process phase |
| P43 | Lint + Newelle Sync | Done | e022b3c | 2026-04-06 | Newelle sync | docs/P43_PLAN.md | Process phase |
| P44 | Input Validation v2 | Done | aae5965 | 2026-04-06 | ai/security/input_validator.py | docs/P44_PLAN.md | P44-P54 roadmap |
| P45 | Semantic Cache v2 | Done | See P44 | 2026-04-07 | ai/cache_semantic.py (310 lines) | Notion row | Referenced in P44 |
| P46 | Token Budget v2 | Done | See P44 | 2026-04-07 | ai/budget.py | Notion row | Delivered in P23 |
| P47 | Code Patterns | Done | See P44 | 2026-04-07 | ai/rag/pattern_store.py | Notion row | Referenced in P44 |
| P48 | Conversation Memory v2 | Done | See P44 | 2026-04-07 | ai/memory.py | Notion row | Referenced in P44 |
| P49 | Weekly Insights v2 | Done | See P44 | 2026-04-07 | ai/insights.py | Notion row | Referenced in P44 |
| P50 | Integration Tests | Done | 909f5dc | 2026-04-08 | tests/test_integration_*.py | docs/P50_PLAN.md | P44-P49 integration |
| P51 | Newelle Skills Sync | Done | 904b1d4 | 2026-04-08 | docs/newelle-*.md | docs/P51_PLAN.md | System prompt sync |
| P52 | Slack + Notion Integrations | Done | 9871497 | 2026-04-09 | ai/slack/, ai/notion/ | Notion row | 302 + 312 lines |
| P53 | Orchestration Expansion | Done | e023411 | 2026-04-10 | ai/orchestration/ | docs/P53_PLAN.md | Bus, registry, 5 agents |
| P54 | Workflow Hardening | Done | d33d8ee | 2026-04-10 | ai/workflows/ | Notion row | Observer, steps |
| P55 | Phase Control | Done | 1008d84 | 2026-04-10 | ai/phase_control/ | docs/P55_PLAN.md | 15 files, 1460 lines |
| P56 | Stabilization | Done | 1008d84 | 2026-04-10 | Process fixes | Notion row | Process phase |
| P57 | Cross-System Burn Down | Done | bd76dca1 | 2026-04-10 | Multiple fixes | docs/P57_PLAN.md | Final burn down |
| P58 | Whitespace + Syntax | Done | 07b5a63 | 2026-04-10 | docs/zo-tools/ | Notion row | Process phase |
| P59 | Branch Convergence | Done | 28955d01 | 2026-04-10 | HANDOFF.md reconcile | Notion row | Git converge |
| P60 | Intelligence Reliability | Done | a0b5da9 | 2026-04-11 | ai/router.py, ai/mcp_bridge/ | docs/P60_REMEDIATION_SUMMARY.md | Runtime fixes |
| P61 | Frontend Capability Pack | Done | a97213c | 2026-04-10 | docs/frontend-capability-pack/ | docs/P61_TRAINING_SUMMARY.md | 14 docs created |
| P62 | Pattern Intelligence | Done | b07290c | 2026-04-12 | ai/rag/pattern_store.py | Notion row | 22 frontend patterns |
| P63 | Build Validation + QA | Done | 170f30c | 2026-04-12 | docs/patterns/frontend/qa-*.md | docs/P63_PLAN.md | QA layer |
| P64 | Design/Media Enhancement | Done | e33b671 | 2026-04-12 | docs/patterns/frontend/svg-*.md | docs/P64_PLAN.md | Media layer |
| P65 | Runtime Harness | Done | 84a013f | 2026-04-11 | docs/frontend-capability-pack/runtime-harness.md | HANDOFF.md | Browser evidence |
| P66 | Brief Intake + Content Schema | Done | 4bdda9e | 2026-04-11 | docs/frontend-capability-pack/website-brief-schema.md | HANDOFF.md | Intake forms |
| P67 | Deployment Pack + Handoff | Done | 908d987 | 2026-04-11 | docs/frontend-capability-pack/deployment-target-pack.md | HANDOFF.md | Launch docs |
| P68 | GitNexus Evaluation | Done | 3efff8c | 2026-04-12 | docs/P68_PLAN.md | HANDOFF.md | Evaluation |
| P69 | Ops Runbook Pack | Done | 007d7b2 | 2026-04-12 | docs/frontend-capability-pack/ops-*.md | HANDOFF.md | 6 runbooks |
| P70 | Phase Doc Overhaul | Done | 8b34ddb | 2026-04-12 | docs/PHASE_*.md | This page | Documentation |
| P71 | Structural Analysis Enhancement | Done | — | 2026-04-12 | ai/code_intel/, scripts/index-code.py, tests/test_code_intel.py, docs/P71_*.md | Notion row | AST + store + MCP fixes |
| P72 | Dependency Graph + Impact Alignment | Done | — | 2026-04-13 | ai/code_intel/parser.py, ai/code_intel/store.py, ai/mcp_bridge/{tools.py,server.py}, tests/test_code_intel.py, docs/P72_*.md | Notion row | Real dependency graph queries, cycles, and impact integration |
| P73 | Impact Analysis | Done | — | 2026-04-13 | ai/code_intel/store.py, ai/mcp_bridge/{tools.py,server.py}, scripts/index-code.py, tests/{test_dependency.py,test_impact.py}, docs/P73_*.md | Notion row | Blast radius, weighted impact scoring, and co-change analysis |
| P74 | Code Intelligence Fusion Layer | Done | — | 2026-04-13 | ai/code_intel/store.py, ai/rag/code_query.py, ai/mcp_bridge/{tools.py,server.py}, configs/mcp-bridge-allowlist.yaml, tests/test_code_fusion.py, docs/P74_*.md | Notion row | Unified semantic+structural+artifact retrieval path |
| P75 | Project Intelligence Preflight + Execution Gating | Done | — | 2026-04-13 | ai/phase_control/{preflight.py,runner.py,policy.py,result_models.py}, tests/test_phase_control_preflight.py, docs/P75_*.md | Notion row | Required preflight context + gate before phase execution |
| P76 | Ingestion Reliability + Continuous Learning Automation | Done | 38b8ea7 | 2026-04-13 | ai/phase_control/{closeout.py,closeout_targets.py}, tests/test_phase_control_closeout.py, docs/P76_*.md | Notion row | Automated closeout ingestion with retry, dead-letter, coverage tracking |
| P77 | UI Architecture + Contracts Baseline | Done | 0af6fb3 | 2026-04-13 | docs/PHASE77_UI_ARCHITECTURE.md | Notion row | Bazzite Unified Control Console architecture |
| P78 | Midnight Glass Design System + Figma Mapping | Done | 0af6fb3 | 2026-04-13 | docs/PHASE78_MIDNIGHT_GLASS_DESIGN_SYSTEM.md | Notion row | Midnight Glass visual system, tokens, components |
| P79 | Frontend Shell Bootstrap | Done | dadd5fa | 2026-04-13 | docs/P79_UI_SHELL_BOOTSTRAP.md, ui/src/components/shell/* | Notion row | Shell frame, icon rail, command palette |
| P80 | Auth, 2FA, Recovery, Gmail Notifications | Deferred | — | — | Placeholder only | Notion row | Deferred per roadmap reconciliation |
| P81 | PIN-Gated Settings + Secrets Service | Done | 06c8f21 | 2026-04-13 | ai/settings_service.py, ui/src/components/settings/*, docs/HANDOFF | Notion row | PIN auth, masked secrets, audit logging |
| P82 | Provider + Model Discovery / Routing Console | Done | 4461ec8 | 2026-04-13 | ai/provider_service.py, ui/src/components/providers/* | Notion row | Provider health, model catalog, routing console |
| P83 | Chat + MCP Workspace Integration | Done | 79af39a | 2026-04-13 | docs/P83_CHAT_WORKSPACE.md, ui/src/components/chat/* | Notion row | Streaming chat + inline MCP tool results |
| P84 | Security Ops Center | Done | 812225c | 2026-04-13 | docs/P84_SECURITY_OPS_CENTER.md, ui/src/components/security/* | Notion row | Security overview, alerts, findings, provider health |
| P85 | Interactive Shell Gateway | Done | 75be187 | 2026-04-13 | docs/P85_INTERACTIVE_SHELL_GATEWAY.md, ai/shell_service.py, ui/src/components/shell-gateway/* | Notion row | Local shell sessions with audit strip |
| P86 | Project + Workflow + Phase Panels | Done | ff56276 | 2026-04-13 | docs/P86_PROJECT_WORKFLOW_PHASE_PANELS.md, ai/project_workflow_service.py, ui/src/components/project-workflow/* | Notion row | Project context, workflow history, phase timeline |
| P87 | Newelle/PySide Migration + Compatibility Cutover | Done | 877efdd | 2026-04-13 | docs/P87_MIGRATION_CUTOVER.md, docs/USER-GUIDE.md, docs/AGENT.md, docs/newelle-system-prompt.md | Notion row | Console-first UX cutover with fallback/rollback model |
| P88 | UI Hardening, Validation, Docs, Launch Handoff | Done | — | 2026-04-14 | docs/P88_UI_HARDENING_LAUNCH_HANDOFF.md, docs/USER-GUIDE.md, docs/newelle-system-prompt.md | Notion row | Final UI tranche hardening, launch readiness, and deferred-risk reconciliation |
| P89 | Security Improvement + Remediation Closure | Done | — | 2026-04-14 | scripts/install-user-timers.sh, systemd/user/*.service, systemd/user/*.timer, ai/code_intel/store.py, docs/P76_SYSTEMD_SCOPE_REMEDIATION.md | Notion row | User-scoped timer/service remediation and security-run stability closure |
| P90 | Console Runtime Recovery + Contract Reconciliation | Done | — | 2026-04-14 | docs/P90_CONSOLE_RUNTIME_RECOVERY_CONTRACT_RECONCILIATION.md, ui/src/lib/mcp-client.ts, ui/src/hooks/use*.ts, ui/next.config.ts, ai/project_workflow_service.py, tests/test_project_workflow_service.py, scripts/start-console-ui.sh | Notion row | MCP streamable-http contract reconciliation, panel runtime recovery, and UI startup workflow |
| P91 | Settings, Secrets, and PIN End-to-End Hardening | Done | — | 2026-04-14 | docs/P91_SETTINGS_SECRETS_PIN_HARDENING.md, ai/mcp_bridge/tools.py, ui/src/components/settings/SettingsContainer.tsx | Notion row | Precise error codes for settings operations, improved PIN/secrets flow error handling |
| P92 | Providers + Security Surfaces Live Integration | Done | — | 2026-04-14 | docs/P92_PLAN.md, ai/mcp_bridge/tools.py, ui/src/hooks/useProviders.ts, ui/src/hooks/useSecurity.ts, ui/src/components/providers/ProvidersContainer.tsx, ui/src/components/security/SecurityContainer.tsx | Notion row | Live backend truth rendering with explicit degraded/manual states for provider and security surfaces |
| P93 | Project, Workflow, and Phase Truth Integration | Done | — | 2026-04-14 | docs/P93_PLAN.md, ai/project_workflow_service.py, ui/src/components/project-workflow/*, ui/src/hooks/useProjectWorkflow.ts, ui/src/types/project-workflow.ts, tests/test_project_workflow_service.py | Notion row | HANDOFF truth integration with Notion parity, deferred phase handling, degraded sync states |
| P94 | Shell Gateway End-to-End Runtime Recovery | Done | — | 2026-04-14 | docs/P94_PLAN.md, ai/shell_service.py, ai/mcp_bridge/tools.py, ui/src/components/shell-gateway/*, ui/src/hooks/useShellSessions.ts, tests/test_shell_service.py | Notion row | Removed shell=True, precise error states, command allowlisting, session limit, atomic writes, disconnected/error UI |
| P95 | Full Console Acceptance + Launch Gate | Done | — | 2026-04-14 | docs/P95_PLAN.md, ui/src/hooks/useChat.ts, ui/src/hooks/useProviders.ts, ui/src/hooks/useSecurity.ts, ui/src/hooks/useProjectWorkflow.ts, ui/src/hooks/useShellSessions.ts, ui/src/components/security/SecurityActionsPanel.tsx, ui/src/components/providers/ProvidersContainer.tsx, ui/src/components/shell-gateway/ShellContainer.tsx, ui/src/components/project-workflow/CurrentPhaseHeader.tsx, ui/src/types/shell.ts, ai/settings_service.py | Notion row | Console acceptance pass across 6 panels, stale closure fix, chat abort fix, null safety, launch gate with debt classification |
| P96 | Figma MCP + Design Artifact Reconciliation | Done | — | 2026-04-14 | docs/P96_PLAN.md, ai/figma_service.py, tests/test_figma_service.py, ai/mcp_bridge/tools.py, configs/mcp-bridge-allowlist.yaml, ai/config.py | Notion row | Figma REST API integration with 6 MCP tools, Midnight Glass artifact reconciliation, read-only API limitations documented |
| P97 | Live UI Reality Reconciliation + Figma Parity | Done | — | 2026-04-14 | docs/P97_PLAN.md, docs/P97_RECONCILIATION.md, ui/src/components/settings/SettingsContainer.tsx, ui/src/components/settings/SecretsList.tsx, ui/src/components/security/SecurityActionsPanel.tsx, ui/src/components/security/SecurityContainer.tsx, ui/src/hooks/useChat.ts, ui/src/hooks/useProjectWorkflow.ts, ui/src/hooks/useShellSessions.ts, ai/mcp_bridge/tools.py, ai/project_workflow_service.py, tests/test_mcp_tools_validation.py, tests/test_project_workflow_service.py | Notion row missing (API row-create permission denial) | Reality-based reconciliation pass correcting claimed-vs-actual mismatches from P89-P95, restoring live project context truth, and wiring P96-parity flows |
| P98 | Console UX Debt Burn-Down + Figma Parity | Done | — | 2026-04-14 | docs/P98_PLAN.md, docs/P98_DEBT_BURNDOWN.md, ui/src/components/shell/CommandPalette.tsx, ui/src/components/shell/NotificationsPanel.tsx, ui/src/components/shell/TopBar.tsx, ui/src/components/shell/Layout.tsx, ui/src/components/security/AlertFeed.tsx | Notion row `342f793e-df7b-8194-b4ad-f799da9ea776` | Removed misleading non-functional affordances and placeholder runtime surfaces while preserving explicit degraded states |
| P99 | Live Console Evidence Rebaseline + Trust Restore | Done | — | 2026-04-14 | docs/P99_PLAN.md, docs/P99_EVIDENCE_BASELINE.md, docs/evidence/p99/panel-evidence.json, docs/evidence/p99/panel-visible-text.json, docs/evidence/p99/screenshots/* | Notion row | Browser-verified localhost evidence baseline established |
| P100 | Browser-to-Local Service Connectivity Recovery | Done | — | 2026-04-14 | docs/P100_PLAN.md, docs/P100_CONNECTIVITY_DIAGNOSIS.md, ai/mcp_bridge/__main__.py, ai/llm_proxy.py | Notion row | Fixed browser CORS block: added localhost-only CORS middleware |
| P101 | MCP Tool Governance + Analytics Platform | Done | 73d6e54 | 2026-04-15 | docs/P101_PLAN.md, ai/mcp_bridge/governance/* | Notion row | Governance framework, lifecycle management, 12 new MCP tools |
| P102 | Dynamic Tool Discovery | Done | 1e081ca | 2026-04-15 | docs/P102_PLAN.md, ai/mcp_bridge/discovery.py, ai/mcp_bridge/dynamic_registry.py | Notion row | AST-based tool discovery, dynamic registry, hot-reload |
| P103 | MCP Tool Marketplace + Tool Pack Import/Export | Done | 8c9b2e5 | 2026-04-15 | docs/P103_PLAN.md, ai/mcp_bridge/marketplace/* | Notion row | Tool pack validation, import/export, staging, installation |
| P104 | Advanced Tool Analytics + Optimization | Done | 63cad68 | 2026-04-15 | docs/P104_PLAN.md, ai/mcp_bridge/analytics_advanced/* | Notion row | Anomaly detection, cost analysis, latency reporting, forecasting |
| P105 | External MCP Federation Governance | Done | c2866b6 | 2026-04-15 | docs/P105_PLAN.md, ai/mcp_bridge/federation/* | Notion row | External MCP server discovery, trust scoring, policy enforcement |
| P106 | Full Browser Runtime Evidence Rebaseline | Done | 0975fcb | 2026-04-15 | docs/P106_PLAN.md, docs/evidence/p106/* | Notion row | Browser runtime evidence for all panels, 169 tools verified |
| P107 | UI Feature Wiring Completion | Done | bfd174c | 2026-04-15 | docs/P107_PLAN.md | Notion row | Analyzed UI wiring - all browser dialogs replaced |
| P108 | Persistent Shell Gateway Upgrade | Done | 9975b42 | 2026-04-15 | docs/P108_PLAN.md, ai/shell_service.py | Notion row | Persistent sessions with CWD, audit logging, 23 tests pass |
| P109 | Production-Grade Settings & Secrets UX | Done | b0dc074 | 2026-04-15 | docs/P109_PLAN.md | Notion row | Analysis confirms production-grade UX already implemented |
| P110 | Tool Control Center UI | Done | 60c5daf | 2026-04-15 | docs/P110_PLAN.md, ui/src/components/tool-control/* | Notion row | Unified UI for governance, discovery, marketplace, optimization, federation |
| P111 | Final Production Acceptance Gate | Done | pending | 2026-04-15 | docs/P111_PLAN.md, docs/P111_FINAL_ACCEPTANCE_REPORT.md | Notion row | Comprehensive system acceptance validation |
| P112 | UI Dev Runtime / Turbopack Launch Crash Remediation | Done | pending | 2026-04-15 | scripts/start-console-ui.sh, ui/next.config.ts, ui/src/components/security/SecurityOverview.tsx | Notion row | Fixed Next.js Turbopack dev server crash due to tailwind root pollution |
| P113 | Runtime UI Repair + Provider Onboarding | Done | 2ffc3dc | 2026-04-15 | ui/src/components/providers/ModelsList.tsx, ui/src/components/providers/AddProviderPanel.tsx, docs/evidence/p113_runtime_ui_repair.md | Notion row | Runtime UI repair, provider onboarding UX, routing disclaimer, empty-state cleanup |
| P114 | MCP Contract Convergence + Runtime Manifest CI | Done | 7ad75c6 | 2026-04-15 | ai/mcp_bridge/parity_check.py, docs/evidence/p114/* | Notion row | MCP contract convergence, parity report, runtime manifest CI checks |
| P115 | Provider Registry + Routing Persistence v2 | Done | 99a7fcb | 2026-04-15 | ai/provider_registry.py, tests/test_provider_registry.py, docs/evidence/p115/* | Notion row | Provider registry CRUD, deterministic routing generation, 6 new MCP tools |
| P116 | Chat Workspace Routing Profiles | Done | 0e67e4f | 2026-04-15 | ui/src/components/chat/ChatProfileSelector.tsx, ui/src/components/chat/ChatRouteInfo.tsx, ui/src/hooks/useChatRouting.ts, docs/evidence/p116/* | Notion row | Profile selector, route visibility, localStorage persistence |
| P117 | Security + Shell Operations Hardening v2 | Done | 4537314 | 2026-04-15 | ui/src/components/security/SecurityContainer.tsx, ui/src/components/shell-gateway/ShellContainer.tsx, docs/evidence/p117/* | Notion row | Hardened degraded states, audit visibility, blocked/unavailable messages |
| P118 | Final System Acceptance Gate | Done | fe619bf | 2026-04-15 | docs/evidence/p118/acceptance.md | Notion row | Full system acceptance validated: UI/backend/MCP/routing/failure-awareness/docs aligned, ready for production |
| P119 | Security Autopilot Core | Done | d502c21 | 2026-04-16 | ai/security_autopilot/{models.py,sensors.py,classifier.py,planner.py,audit.py,__init__.py}, tests/test_security_autopilot.py, docs/P119_PLAN.md | Notion row | Plan-only Security Autopilot core with findings/incidents/plans, redacted evidence, and append-only hash-chained audit logging |
| P120 | Security Policy Engine | Done | 9471662 | 2026-04-16 | ai/security_autopilot/policy.py, configs/security-autopilot-policy.yaml, tests/test_security_autopilot_policy.py, docs/P120_PLAN.md | Notion row | Policy modes, allow/approval/block decisions, safe defaults, malformed-input rejection, redaction-aware output |
| P121 | Security Autopilot UI | Done | c120c9f | 2026-04-16 | ai/security_autopilot/ui_service.py, ui/src/components/security/AutopilotPanels.tsx, ui/src/hooks/useSecurityAutopilot.ts, tests/test_security_autopilot_tools.py, docs/P121_PLAN.md, docs/evidence/p121/* | Notion row | Added seven read-only autopilot surfaces with policy/evidence/audit visibility and degraded-state handling |
| P122 | Safe Remediation Runner | Done | pending | 2026-04-16 | ai/security_autopilot/executor.py, tests/test_security_autopilot_executor.py, docs/P122_PLAN.md, docs/evidence/p122/* | Notion row | Added fixed allowlisted remediation execution with P120 policy gating, approval enforcement, deterministic rejection paths, and audit/evidence records for every attempt |
| P123 | Agent Workbench Core | Done | 14b0f78 | 2026-04-17 | ai/agent_workbench/*, ai/mcp_bridge/{tools.py,server.py}, configs/mcp-bridge-allowlist.yaml, tests/test_agent_workbench.py, docs/P123_PLAN.md, docs/evidence/p123/* | Notion row | Added bounded project/session workbench primitives and 11 `workbench.*` MCP tools with allowlist, safety checks, and validation evidence |
| P124 | Codex/OpenCode UI Integration | Done | pending | 2026-04-17 | ui/src/components/workbench/*, ui/src/hooks/useAgentWorkbench.ts, ui/src/types/agent-workbench.ts, ui/src/app/page.tsx, ui/src/components/shell/{IconRail.tsx,CommandPalette.tsx}, tests/test_agent_workbench_tools.py, docs/P124_PLAN.md, docs/evidence/p124/* | Notion row | Added integrated Agent Workbench panel with real project/session/git/test/handoff flows and truthful degraded-state rendering |
| P126 | Full Autopilot Acceptance Gate | Done | 7d3b17b | 2026-04-17 | docs/evidence/p126/validation.md | Notion row | Validated P119-P125 as integrated system with policy/approval gates, safety proofs, MCP/LLM health, UI build, no unrestricted AI/shell/secrets |
| P127 | MCP Policy-as-Code and Approval Gates | Done | aea4d5c | 2026-04-17 | ai/mcp_bridge/policy/*, tests/test_mcp_policy.py, docs/evidence/p127/validation.md | Notion row | Implemented canonical MCP tool policy metadata, default-deny evaluation, approval gate enforcement, bypass resistance, auditability, policy parity with P120/P122 |
| P128 | Local Identity and Step-Up Security | Done | f524b84 | 2026-04-17 | ai/identity/*, tests/test_identity_stepup.py, docs/evidence/p128/validation.md | Notion row | Implemented local identity layer with step-up security, test isolation fixed (23 pass), backend enforcement, P127 policy integration |
| P129 | Workspace and Actor Context Isolation | Done | 861a277 | 2026-04-17 | ai/context/*, tests/test_workspace_isolation.py, docs/evidence/p129/validation.md | Notion row | Implemented workspace/actor/project context isolation, server-side path restrictions, cross-project leakage prevention, audit correlation, 24 tests pass |
| P130 | Cost Quotas and Budget Automation | Done | be08087 | 2026-04-17 | ai/budget_scoped.py, ai/budget_routing.py, tests/test_budget_scoped.py, docs/evidence/p130/validation.md | Notion row | Implemented scoped budget model with token/cost limits, warning/stop thresholds, routing constraints, audit events, 17 tests pass |
| P131 | Routing Evaluation and Replay Lab | Done | 661d3a8 | 2026-04-17 | ai/routing_replay.py, docs/routing_replay/*, tests/test_routing_replay.py, docs/evidence/p131/validation.md | Notion row | Added deterministic replay fixtures and explanation payloads comparing routing across health/cost/latency/task type/failover and P130 budget constraints |
| P132 | Human-in-the-loop Orchestration Runbooks | Done | f266c4b | 2026-04-17 | docs/runbooks/*, docs/runbooks/workflows/*, ai/workflows/runbooks.py, tests/test_runbooks.py, tests/test_workflow_runbooks.py, docs/evidence/p132/validation.md | Notion row | Added explicit high-risk operator runbooks, machine-readable workflow metadata, and truthful manual-step/approval-state surfacing via workflow handlers |
| P133 | Memory, Artifact, and Provenance Graph | Done | f4a578b | 2026-04-17 | ai/provenance.py, ai/security_autopilot/executor.py, ai/agent_workbench/handoff.py, ai/mcp_bridge/tools.py, configs/mcp-bridge-allowlist.yaml, tests/test_provenance_graph.py, docs/P133_PLAN.md, docs/evidence/p133/validation.md | Notion row | Added scoped provenance graph linking incidents, evidence, actions, sessions, diffs, tests, artifacts, memory, and phase records with attribution and redaction |
| P134 | Self-healing Control Plane | Done | 81daf2c | 2026-04-17 | ai/self_healing.py, tests/test_self_healing.py, docs/P134_PLAN.md, docs/evidence/p134/validation.md | Notion row | Added detection checks for service health/timers/providers/LLM, fixed allowlisted repair actions, policy gating, approval-gated restart, cooldown/no-loop prevention, and degradation state visibility |
| P135 | Integration Governance for Notion, Slack, and GitHub Actions | Done | eedd8db | 2026-04-17 | ai/integration_governance.py, ai/notion/handlers.py, ai/slack/handlers.py, tests/test_integration_governance.py, docs/P135_PLAN.md, docs/evidence/p135/validation.md | Notion row | Added integration action registry with risk metadata, default-deny for unknown actions, scope/attribution requirements, redaction for sensitive content, and audit linkage for Notion/Slack/GitHub operations |
| P136 | Retention, Privacy, and Export Controls | Done | fc2e8bd | 2026-04-17 | ai/retention_privacy.py, tests/test_retention_privacy.py, docs/P136_PLAN.md, docs/evidence/p136/validation.md | Notion row | Added retention policies for 7 data classes, redaction for secrets/PII/paths, export bundle generation with metadata and integrity verification |
| P137 | Deployment Profiles and Environment Packaging | Done | 5f2431c | 2026-04-17 | ai/deployment_profiles.py, tests/test_deployment_profiles.py, docs/deploy/profiles.md, docs/P137_PLAN.md, docs/evidence/p137/validation.md | Notion row | Added three deployment profiles (local-only, security-autopilot, agent-workbench) with fail-closed validation, key presence checks without secrets, service/health endpoint validation, startup/shutdown documentation |
| P138 | Browser/Service Canary Release Automation | Done | [TBD] | 2026-04-18 | ai/canary.py, scripts/canary.sh, tests/test_canary.py, docs/P138_PLAN.md, docs/evidence/p138/validation.md | Notion row | Added canary runner with 6 stages (preflight, service health, MCP tools, UI build, policy gates, evidence bundle), non-destructive validation, fail-closed behavior |
| P139 | Pre-P140 contract and readiness alignment | Done | 99cf063 | 2026-04-18 | HANDOFF.md, docs/AGENT.md, Notion P140 contract references | Notion row | Prepared final P140 execution contract, guardrails, and acceptance checklist path |
| P140 | Chat Workspace and Home Screen Operator Integration | Done | f3c1795 | 2026-04-18 | ui/src/components/{chat,home,shell}/*, ui/src/hooks/{useChat,useProviders}.ts, ui/src/lib/{workspace-session-binding,thread-store,operator-runtime,home-dashboard,console-simplify}.*, docs/evidence/p140/validation.md | Notion row `346f793e-df7b-815c-9eb4-f727888095b4` | Integrated Home + Chat operator flows, truthful runtime/tool surfaces, thread organization/merge/archive UX, and closeout reconciliation |
| P141 | Workspace Evidence Refresh and Post-closeout Polish | Done | 58a2934 | 2026-04-18 | docs/evidence/p141/screenshots/*, docs/evidence/p141/validation.md, Chat/Home wording polish files | Notion row `346f793e-df7b-81df-88dd-e7d1953e7672` | Final Home/Chat evidence refresh completed with post-closeout UX polish and reconciled ledger truth |
| P142 | Console Asset Loading and Runtime Stability Fix | In Progress | pending | pending | ui/scripts/dev-stable.mjs, scripts/start-console-ui.sh, ui/next.config.ts, ui/src/lib/mcp-client.ts, ui/src/hooks/useChat.ts, ui/src/lib/thread-store.js, docs/evidence/p142/validation.md, docs/evidence/p142/screenshots/* | Notion row `346f793e-df7b-8031-a3ab-cb048203415d` | White-shell regression mitigated and happy-path evidence refreshed; awaiting final Notion row reconciliation before Done |
| P143 | Adaptive Minimalist UI Redesign Spec | Done | pending | 2026-04-18 | docs/P143_UI_REDESIGN_SPEC.md, docs/P143_WIDGET_CATALOG.md, docs/P143_UI_IMPLEMENTATION_MAP.md | Notion row | Spec-only phase; source of truth for P144-P146 implementation |
| P144 | Home Dashboard Redesign Implementation | Done | pending | 2026-04-18 | ui/src/components/home/HomeContainer.tsx, ui/src/components/home/widgets/*, docs/evidence/p144/* | Notion row | Rebuilt Home to widget-based preset-driven layout with live project/thread/runtime/security data and add/remove widget flow |
| P145 | Chat Workspace and Thread Rail Redesign | Done | d08478b | 2026-04-18 | ui/src/components/chat/{ChatContainer,ThreadSidebar,ChatMessage,ChatInput}.tsx, ui/src/lib/console-simplify.js, docs/evidence/p145/* | Notion row `346f793e-df7b-81d7-bae2-c9972d936c87` | Implemented calmer chat workspace, compact truthful runtime strip, progressive diagnostics, professional thread rail grouping, and polished archive/restore/merge/bulk flows |
| P146 | Workspace Personalization and Preset Persistence | Done | b758dea | 2026-04-18 | ui/src/lib/workspace-personalization.ts, ui/src/hooks/useWorkspacePersonalization.ts, ui/src/components/{home/HomeContainer,chat/ChatContainer}.tsx, docs/evidence/p146/* | Notion row `346f793e-df7b-8172-9192-d21af39c0da8` | Added durable local-first preset/widget/layout personalization, chat visibility rules by preset, and explicit Standard fallback notice for unavailable/cleared persistence |

## Notion Database Reference

Database ID: `398c13ed-47f6-4f7e-9e54-eb339b462c90`

Key properties:
- `Phase Number`: Integer identifier
- `Name`: Phase title
- `Status`: Planned / Ready / In Progress / Blocked / Needs Review / Done / Cancelled
- `Commit SHA`: Git commit (short form)
- `Finished At`: Completion date
- `Validation Summary`: Prose completion summary
- `Dependencies`: Prerequisite phases
- `Execution Mode`: bounded / manual-approval / other phase execution constraints
- `Approval Required` / `Approval State`: gate metadata for high-risk phases

## Cross-References

- [PHASE_ARTIFACT_REGISTER.md](./PHASE_ARTIFACT_REGISTER.md) — Per-phase artifact inventory
- [PHASE_DEPENDENCY_GRAPH.mmd](./PHASE_DEPENDENCY_GRAPH.mmd) — Mermaid dependency visualization
- [PHASE_DELIVERY_TIMELINE.md](./PHASE_DELIVERY_TIMELINE.md) — Timeline view
- [ARCHITECTURE_EVOLUTION.md](./ARCHITECTURE_EVOLUTION.md) — Architecture evolution narrative
- [PHASE_DOCUMENTATION_POLICY.md](./PHASE_DOCUMENTATION_POLICY.md) — Future artifact placement rules
- [P119_P139_SECURITY_AUTOPILOT_AGENT_WORKBENCH_ROADMAP.md](./P119_P139_SECURITY_AUTOPILOT_AGENT_WORKBENCH_ROADMAP.md) — Security Autopilot + Agent Workbench roadmap
