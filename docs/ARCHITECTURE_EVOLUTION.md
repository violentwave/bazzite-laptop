# Architecture Evolution — Bazzite AI Layer

> How the architecture evolved through phases P0-P70.
> Generated 2026-04-12. Shows layer-by-layer capability growth.

## Evolution Overview

The Bazzite AI Layer evolved through 8 distinct architectural layers, each building on the previous while adding new capability dimensions.

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 8: Ops & Evaluation (P68-P69)                          │
│ GitNexus evaluation + Ops runbooks                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 7: Frontend Capability (P59-P67)                       │
│ Capability pack + Pattern intel + QA + Design + Runtime      │
├─────────────────────────────────────────────────────────────┤
│ Layer 6: Control Plane (P44-P58)                            │
│ Input validation + Cache + Budget + Metrics + Orchestration │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: Integration (P34-P43)                              │
│ Parity + Stabilization + Alerts + Task patterns + DepAudit │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Governance (P22-P33)                               │
│ Budget + Cache + Metrics + Memory + Code intel + Collab     │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Security (P19-P21)                                 │
│ Input validation + Timer sentinel + Pattern store           │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Intelligence (P10-P18)                             │
│ Intel scraper + Timers + PingMiddleware + BM25 + Logging    │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Foundation (P0-P9)                                 │
│ Config + Router + Health + MCP Bridge + Threat intel + RAG │
└─────────────────────────────────────────────────────────────┘
```

## Layer-by-Layer Evolution

### Layer 1: Foundation (P0-P9)

**Timeline**: Feb 3-28, 2026

**Core capabilities:**
- P0: Project bootstrapping, config paths, router foundation
- P1: Systemd service architecture
- P2: LiteLLM V2 router with health-weighted provider selection
- P3: FastMCP bridge on :8766
- P4: Threat intel integration (VT, OTX, AbuseIPDB)
- P5: LanceDB RAG foundation
- P6: MCP tool registration via YAML allowlist
- P7: Provider health metrics
- P8: Code quality tooling (ruff, bandit)
- P9: Gaming peripheral support (MangoHud profiles)

**Architecture impact:**
Established the dual-service architecture (MCP Bridge :8766, LLM Proxy :8767), threat intel foundation, and RAG-based intelligence layer.

### Layer 2: Intelligence (P10-P18)

**Timeline**: Mar 2-20, 2026

**Core capabilities:**
- P10: Intel scraper (CVE, releases, Fedora updates)
- P11: Timer expansion (systemd timers for scheduled tasks)
- P12: PingMiddleware 25s keepalive for MCP connection stability
- P13: BM25 full-text search in LanceDB
- P14: Cost tracking and Sentry error reporting
- P15: Workflow engine with ReAct loop
- P16: Structured JSON logging throughout
- P17: Test infrastructure (133 test files)
- P18: Documentation pass (24 docs)

**Architecture impact:**
Added scheduled intelligence gathering, connection stability, observability foundation, and test/ doc infrastructure.

### Layer 3: Security (P19-P21)

**Timeline**: Apr 3, 2026 (compressed)

**Core capabilities:**
- P19: Input validation layer (51 tests)
- P20: Timer sentinel + headless security briefing
- P21: Pattern store with frontend metadata schema

**Architecture impact:**
Hardened input handling, added autonomous security briefing capability, and established pattern intelligence foundation.

### Layer 4: Governance (P22-P33)

**Timeline**: Apr 5-9, 2026

**Core capabilities:**
- P22-P23: Token budget + Semantic cache (stabilization batch)
- P24: Metrics recording with time-series buffering
- P25: Conversation memory with semantic retrieval
- P26: Provider intelligence for dynamic routing
- P27: Security alert evaluation system
- P28: Weekly AI-generated insights
- P29: Structural code intelligence (AST + grimp)
- P30: Workflow engine expansion
- P31: Agent collaboration (task queue, shared context)
- P32: Testing intelligence (stability tracker, testmon)
- P33: Dynamic tool creation with safety validation

**Architecture impact:**
Established governance layer with budget enforcement, semantic caching, observability, multi-agent collaboration, and code intelligence.

### Layer 5: Integration (P34-P43)

**Timeline**: Mar 27 - Apr 6, 2026

**Core capabilities:**
- P34-P36: Integration parity and agent stabilization
- P37: Alert rules module (dispatcher, history)
- P38: Task patterns for learning from successful completions
- P39: Dependency vulnerability auditing (pip-audit)
- P40: Intel scraper expansion (18K+ lines)
- P41: Unified ingest pipeline
- P42-P43: Stabilization phases (lint, legacy assistant prompt sync)

**Architecture impact:**
Filled integration gaps, added dependency security scanning, unified log ingestion, and stabilized agent behavior.

### Layer 6: Control Plane (P44-P58)

**Timeline**: Apr 5-10, 2026

**Core capabilities:**
- P44: Input validation v2 (safety rules, validation layer)
- P45-P49: Cache/Budget/Pattern/Memory/Insights v2 (referenced in P44)
- P50: Integration tests for P44-P49
- P51: Legacy assistant skills sync (system prompt, 9 skill bundles)
- P52: Slack + Notion integrations with scoped secret loading
- P53: Orchestration bus with agent registry
- P54: Workflow hardening with step-level observability
- P55: Phase control (Notion + Slack autonomous control plane)
- P56-P58: Stabilization + cross-system burn down + whitespace fixes

**Architecture impact:**
Added autonomous control plane, multiagent orchestration, Notion/Slack phase coordination, and comprehensive observability.

### Layer 7: Frontend Capability (P59-P67)

**Timeline**: Apr 10-12, 2026

**Core capabilities:**
- P59: Branch convergence (git reconciliation)
- P60: Intelligence reliability audit (runtime fixes)
- P61: Frontend capability pack (14 docs, 5 archetypes)
- P62: Frontend pattern intelligence (22 patterns)
- P63: QA layer (browser evidence workflow)
- P64: Design/media enhancement (SVG, hero, CTA, motion)
- P65: Runtime harness + browser evidence loop
- P66: Website brief intake + content/SEO schema
- P67: Deployment target pack + launch handoff

**Architecture impact:**
Created comprehensive frontend generation capability with patterns, QA, runtime evidence, and deployment guidance for external React/Tailwind projects.

### Layer 8: Ops & Evaluation (P68-P69)

**Timeline**: Apr 12, 2026

**Core capabilities:**
- P68: GitNexus evaluation (recommendation: defer, enhance existing capabilities)
- P69: Ops runbook pack (DNS, TLS, reverse proxy, launch, troubleshooting, monitoring)

**Architecture impact:**
Evaluated potential code-graph augmentation, delivered operational runbooks for deployment handoff.

## Key Architectural Decisions

### P12: PingMiddleware Keepalive
Keep MCP connections stable with 25s keepalive. Prevents connection drops during long-running operations.

### P44: Input Validation Layer v2
Centralized safety rules in `configs/safety-rules.json`. InputValidator applies rules before dispatch to any MCP tool.

### P53: Orchestration Bus
Agent orchestration with Bus, Registry, and BaseAgent adapters for 5 agent types. Enables multi-agent collaboration.

### P55: Phase Control
Autonomous phase management with Notion database as source of truth. Slack notifications for phase transitions.

### P61: Frontend Capability Pack
External-only capability for React/Tailwind website generation. NOT a frontend app in this repo.

### P68: GitNexus Decision
Deferred GitNexus integration due to licensing (PolyForm Noncommercial), duplication of existing capabilities, and maintenance burden. Enhanced existing Bazzite code intelligence instead.

## Architecture Metrics

| Metric | P0-P9 | P10-P18 | P19-P21 | P22-P33 | P34-P43 | P44-P58 | P59-P67 | P68-P69 |
|--------|-------|---------|---------|---------|---------|---------|---------|---------|
| MCP Tools | 10 → 20 | 20 → 35 | 35 → 40 | 40 → 60 | 60 → 65 | 65 → 80 | 80 → 90 | 90 → 96 |
| LanceDB Tables | 1 → 3 | 3 → 7 | 7 → 8 | 8 → 15 | 15 → 18 | 18 → 25 | 25 → 28 | 28 |
| Systemd Timers | 0 → 5 | 5 → 12 | 12 → 13 | 13 → 18 | 18 → 20 | 20 → 24 | 24 | 24 |
| Test Count | 25 → 100 | 100 → 500 | 500 → 600 | 600 → 1200 | 1200 → 1600 | 1600 → 2058 | 2058 → 2236 | 2236 |
| Docs (docs/) | 3 → 8 | 8 → 15 | 15 → 18 | 18 → 25 | 25 → 30 | 30 → 35 | 35 → 72 | 72 → 78 |

## Current Architecture State (Post-P69)

```
┌─────────────────────────────────────────────────────────────┐
│ Unified Control Console (primary local operator surface)     │
│ ↓ http://127.0.0.1:8767/v1 (OpenAI-compatible fast/reason)   │
│ ↓ http://127.0.0.1:8766/mcp (FastMCP streamable-http, 96 tools)│
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ MCP Bridge :8766                                            │
│ 96 tools: system.*, security.*, knowledge.*, memory.*,      │
│ gaming.*, logs.*, code.*, collab.*, workflow.*, agents.*,  │
│ intel.*, slack.*, notion.*                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM Proxy :8767                                             │
│ 6 cloud providers + Ollama embed fallback                   │
│ Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Intelligence Layer                                          │
│ LanceDB (ext-SSD): 28 tables                                │
│ RAG: documents, code_index, log_entries, code_patterns,     │
│ task_patterns, semantic_cache, metrics, conversation_memory  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Orchestration Layer                                         │
│ OrchestrationBus, AgentRegistry, 5 agent types              │
│ Collab: task queue, shared context, knowledge base           │
│ Workflows: ReAct loop, event triggers, LanceDB logging       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase Control + Observability                               │
│ Notion: Bazzite Phases database (autonomous control plane)  │
│ Slack: Notifications for phase transitions                  │
│ Sentry: Error tracking with 5% trace sampling               │
│ Metrics: Time-series with buffered writes                   │
└─────────────────────────────────────────────────────────────┘
```

## Future Architecture Considerations

1. **P70: Documentation Overhaul** — This phase normalizes phase documentation and establishes future artifact placement rules.

2. **Potential P71+**: Based on P68 GitNexus evaluation, future phases could enhance existing Bazzite code intelligence with structural analysis (call graphs, dependency graphs) rather than adding GitNexus.

3. **Frontend Evolution**: The frontend capability pack (P61-P67) is designed for external projects. No frontend app is planned for this repo.

4. **Control Plane Extensions**: Phase control (P55) provides autonomous project management. Future extensions could include automatic phase transition based on test results and coverage metrics.
