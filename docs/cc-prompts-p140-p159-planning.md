# Bazzite AI Layer — Phase Planning: P119–P139 Improvements + P140–P159 Roadmap
<!-- Generated: 2026-04-16 | Based on: AGENT.md (96 tools, 24 timers, 28 LanceDB tables, 2236+ tests) -->
<!-- Last completed phase: P118 (commit f5b9b40) | System state: PRODUCTION READY -->

---

## Part 1: P119–P139 — Review and Improvements

The existing planned phases are well-structured but contain gaps, stale
assumptions, and missing cross-references. Improvements are noted per phase.

---

### P119 — Observability, Metrics, and Tracing
**Risk:** High | **Backend:** opencode

**Issues found:**
- Prompt doesn't name existing targets: `ai/metrics.py` (MetricsRecorder),
  `ai/provider_intel.py`, `ai/system/pipeline_status.py`.
- Validation commands are missing `pytest -k "metrics or tracing"` for `ai/metrics.py`.
- AGENT.md already shows `metrics-compact.timer` as a P40 artifact — P119 must NOT
  duplicate the timer; it extends coverage.

**Recommended additions to Execution Prompt:**
- "Extend `ai/metrics.py` and `ai/provider_intel.py` — do not replace."
- "Add correlation IDs to MCP bridge dispatch in `ai/mcp_bridge/server.py`."
- "Trace storage goes into existing `metrics` LanceDB table, not a new one."
- "Do NOT create a new `metrics-compact.timer` — P40 timer already exists."

---

### P120 — Multi-user Access Control + RBAC Foundation
**Risk:** Critical | **Backend:** opencode

**Issues found:**
- "Single-user fallback" constraint is mentioned in Done Criteria but not in the
  Execution Prompt — it must be explicit (local-only system, no network exposure).
- AGENT.md binding constraint: services bind to 127.0.0.1 only. RBAC must not
  introduce any network-accessible auth endpoint.
- Missing: explicit instruction to use `ai/security/inputvalidator.py` for all
  RBAC decision inputs.

**Recommended additions:**
- "RBAC must never introduce a network-accessible auth endpoint."
- "All RBAC decision inputs pass through `ai/security/inputvalidator.py`."
- "Single-user local mode must remain the default with zero config required."

---

### P121 — Advanced Routing Intelligence
**Risk:** High | **Backend:** opencode

**Issues found:**
- Depends on P115 and P116 (both Planned). P115 is the real hard blocker;
  P116 adds profile support but isn't strictly required for routing itself.
  Dependency list should reflect this.
- AGENT.md already has `ai/provider_intel.py` with health-weighted routing.
  P121 must EXTEND this, not replace it.
- Missing reference to `configs/litellm-config.yaml` and `ai/rate_limiter.py`
  as constraints.

**Recommended fix:** Mark P115 as hard dependency; P116 as soft/optional.
Add: "Extend `ai/provider_intel.py` and `configs/litellm-config.yaml` — do
not create a parallel routing system."

---

### P122 — Agent Orchestration Layer
**Risk:** Critical | **Backend:** opencode

**Issues found:**
- AGENT.md already has `ai/orchestration/` (OrchestrationBus, AgentRegistry,
  BaseAgent from P53) and 5 agent modules in `ai/agents/`. P122 must build on
  these, not re-implement them.
- Execution Prompt warns "don't create a parallel agent framework" but doesn't
  specify which existing modules to extend.
- Done Criteria mentions "smoke workflow evidence" but doesn't reference the
  existing `workflow.run` / `workflow.history` MCP tools as the test harness.

**Recommended additions:**
- "Extend `ai/orchestration/` — OrchestrationBus, AgentRegistry, BaseAgent
  already exist from P53."
- "Use existing `workflow.run` and `workflow.history` MCP tools to verify
  multi-step orchestration."
- "Do NOT add a new LanceDB table — `workflow_runs` and `workflow_steps`
  already exist."

---

### P123 — Browser Runtime Contract and Acceptance Automation
**Risk:** High | **Backend:** opencode

**Issues found:**
- The browser acceptance harness must target the UCC (Next.js, `ui/`) not
  Newelle or a generic web UI.
- P118 already created `docs/evidence/p118/acceptance.md`. P123 should
  reference this as the baseline and add repeatable automation on top.
- Validation commands include `npx tsc --noEmit && npm run build` but don't
  specify the `ui/` subdirectory path.

**Recommended additions:**
- "Target the UCC (`ui/` directory) — not Newelle or standalone React apps."
- "Reference `docs/evidence/p118/acceptance.md` as the baseline evidence template."
- "Browser acceptance evidence goes to `docs/evidence/p123/`."

---

### P124 — Service Runtime Budgeting and Concurrency Guardrails
**Risk:** High | **Backend:** opencode

**Issues found:**
- AGENT.md identifies the LLM Proxy TasksMax fix (raised to 128) as a P118
  repair. P124 should verify this is still correct and establish the formal
  ceiling policy, not re-apply the fix.
- Missing: reference to the 24 systemd timers as part of the resource budget.
  Timer concurrency (timers firing simultaneously) is an unaddressed risk.
- The `system.perf_metrics` tool (P40) already measures real-time performance.
  P124 should integrate this as the monitoring surface.

**Recommended additions:**
- "Verify P118's TasksMax=128 fix is still current and document rationale."
- "Include systemd timer concurrency in the resource budget analysis."
- "Use `system.perf_metrics` MCP tool as the runtime monitoring surface."

---

### P125 — Provider Onboarding, Secret References, and Registry Hardening
**Risk:** High | **Backend:** opencode

**Issues found:**
- AGENT.md already has `ai/key_manager.py` and `configs/keys.env.enc`
  (sops-encrypted). P125 must reference these.
- The "no raw API keys in provider forms" constraint is critical — the UI must
  only accept credential references (env var names or key-manager aliases).
- Missing: explicit mention of the 6 existing cloud providers
  (Gemini, Groq, Mistral, OpenRouter, z.ai, Cerebras) as the test baseline.

**Recommended additions:**
- "Credential references must be env var names resolved via `ai/key_manager.py`."
- "Validate against all 6 existing providers as the acceptance baseline."
- "Do not modify `configs/keys.env.enc` or `~/.config/bazzite-ai/keys.env`."

---

### P126 — Unified Audit Timeline and Event Explorer
**Risk:** High | **Backend:** opencode

**Issues found:**
- The existing `logs.anomalies`, `logs.search`, and `logs.stats` MCP tools
  already provide partial audit capability. P126 should surface these in the
  UCC rather than duplicating the storage layer.
- The `scripts/lancedb-prune.py` (90d logs, 180d threats) sets the retention
  policy. P126 must respect these bounds.
- Missing: reference to `workflow_steps` LanceDB table (P54) as an existing
  structured event source.

**Recommended additions:**
- "Surface existing `logs.*` MCP tools in the UCC audit panel."
- "Respect retention bounds from `scripts/lancedb-prune.py` (90d logs)."
- "Include `workflow_steps` table as a structured event source."

---

### P127 — MCP Policy-as-Code and Approval Gates
**Risk:** Critical | **Backend:** opencode

**Issues found:**
- AGENT.md shows MCP tools already carry annotations: `readOnly`, `destructive`,
  `openWorld` hints (P12). P127 should extend these into enforceable policy.
- `configs/mcp-bridge-allowlist.yaml` is the canonical tool definition source.
  Policy-as-code must be expressed relative to this file.
- Missing: `ai/security/inputvalidator.py` as the policy enforcement point.

**Recommended additions:**
- "Extend existing tool annotations (readOnly/destructive/openWorld from P12)
  into policy rules — do not redefine the metadata schema."
- "Policy rules are co-located with `configs/mcp-bridge-allowlist.yaml`."
- "Enforcement happens in `ai/mcp_bridge/server.py` dispatch path via
  `ai/security/inputvalidator.py`."

---

### P128 — Local Identity, Trusted Devices, and Step-up Security
**Risk:** Critical | **Approval Required:** YES

**Issues found:**
- The "P80 truth conflict" is unresolved. A P80 reconciliation step is needed
  before P128 can be approved.
- This is the most dangerous phase in the backlog — it touches identity
  boundaries on a local-only system. Single-user local model must remain
  the zero-config default.
- Missing: explicit constraint that no network-accessible auth endpoint is
  introduced (mirrors P120 constraint).

**Recommended pre-conditions:**
1. Reconcile P80 repo-vs-Notion truth BEFORE approval is granted.
2. Confirm single-user local mode is zero-config default in Done Criteria.
3. Explicit constraint: "No network-accessible identity or auth endpoint."
4. Approval gate must include a human review of the P80 reconciliation doc.

---

### P129 — Workspace and Actor Context Isolation
**Risk:** High | **Backend:** opencode

**Issues found:**
- Depends on P128 (Approval Required). Hard sequencing gate.
- "Cross-context leakage tests" must cover the LanceDB vector tables (memory,
  code_nodes, conversation_memory) — semantic search could leak context
  across actors if embeddings are shared.
- Missing: reference to `ai/memory.py` (ConversationMemory) as a primary
  isolation target.

**Recommended additions:**
- "Test LanceDB semantic search isolation — embeddings must not return
  cross-actor results from `conversation_memory` table."
- "Extend `ai/memory.py` with actor/workspace scope parameter."

---

### P130 — Cost Quotas and Budget Automation
**Risk:** Medium | **Backend:** opencode

**Issues found:**
- AGENT.md already has `ai/budget.py` (TokenBudget with priority tiers) and
  `system.budget_status` MCP tool. P130 must extend these.
- Dependency list includes P22/P24/P26 (long-complete) — these are
  "built on" references, not active blockers.
- Missing: reference to `configs/ai-rate-limits.json`.

**Recommended fix:** Clarify P22/P24/P26 as "foundations" not blockers.
Add: "Extend `ai/budget.py` — do not create a parallel budget system."

---

### P131 — Routing Evaluation and Replay Lab
**Risk:** Medium | **Backend:** opencode

**Issues found:**
- Good phase design. Missing: explicit instruction to use `system.metrics_summary`
  and `system.provider_status` MCP tools as data sources for the replay lab.
- "Operators can replay route decisions" needs a concrete interface — UCC
  panel or CLI script. Specify which.

**Recommended addition:**
- "Replay lab is a UCC panel backed by `system.metrics_summary` and
  `system.provider_status` data."

---

### P132 — Human-in-the-loop Orchestration Runbooks
**Risk:** High | **Backend:** opencode

**Issues found:**
- `workflow.cancel` already exists from P54. Pause/resume needs to be a new
  capability.
- Missing: reference to the `phase-control.timer` (Every 15m) as the existing
  autonomous control plane that HITL runbooks must integrate with.

**Recommended addition:**
- "Extend `ai/orchestration/` and `ai/workflows/` — `workflow.cancel` already
  exists from P54; add pause/resume as the new capability."
- "HITL runbooks must be visible to the `phase-control.timer` tick."

---

### P133–P139: Cross-cutting Improvements

**P133 (Provenance Graph):** LanceDB tables `workflow_runs`, `workflow_steps`,
`change_history`, `code_nodes` already exist — the graph is a query/join
layer over these, not new storage. Execution Prompt should say this.

**P134 (Self-healing):** `service-canary.timer` (Every 15m) and
`security-briefing.timer` auto-restart logic already exist. P134 extends these
bounded behaviors.

**P135 (Integration Governance):** P52 added Slack/Notion with scoped secret
loading. The governance layer must reference `ai/slack/` and `ai/notion/`
modules as the integration surfaces.

**P136 (Retention/Privacy):** `scripts/lancedb-prune.py` already implements
90d/180d retention. P136 makes this configurable and adds export/redaction —
not a new pruning system.

**P137 (Deployment Profiles):** AGENT.md already describes the full service
topology. P137 packages this as named profiles (dev/prod/recovery) with
startup smoke tests.

**P138 (Canary Automation):** Must reference the existing `service-canary.timer`
as the scheduling backbone — the canary automation IS the timer's logic,
promoted to a full test suite.

**P139 (GA Acceptance Gate):** CRITICAL — P128 must be Done before P139 can
start. The phase description is otherwise correct and complete.

---

## Part 2: P140–P159 — Next 20 Phases

Focus shifts from infrastructure hardening to operational maturity,
developer experience, and long-term maintainability.

---

### P140 — Post-GA Stabilization Sprint
**Risk:** Medium | **Dependencies:** P139
**Objective:** Immediately after GA, run a structured stabilization sprint:
fix any issues surfaced by P139's acceptance gate, update all doc counts in
AGENT.md (tools, timers, tests, tables), reconcile PHASE_INDEX.md and
CHANGELOG.md with Notion truth, and establish the "post-GA baseline" commit.

**Done Criteria:** AGENT.md counts match repo reality; PHASE_INDEX.md is
current through P139; CHANGELOG.md has the GA entry; all P139 findings are
resolved; `ruff` and `pytest` pass clean.

**Note:** "This phase is non-negotiable after P139 — do not skip stabilization
in favor of new feature work."

---

### P141 — LanceDB Schema Audit and Table Consolidation
**Risk:** Medium | **Dependencies:** P139, P140

**Objective:** AGENT.md lists 28 LanceDB tables. Audit all tables for
duplication, unused columns, orphaned data, and schema drift. Consolidate
where safe. Document the canonical schema for each surviving table.

**Done Criteria:** Each of the 28 tables has a documented schema and ownership
annotation; redundant tables are merged or removed; `lancedb-prune.py` and
`lancedb-optimize.timer` cover all surviving tables.

**Validation Commands:**
```bash
ruff check ai/ tests/ scripts/
pytest tests/ -q --tb=short -k "lancedb or vector or schema"
python scripts/lancedb-prune.py --dry-run
```

---

### P142 — Test Suite Health Audit (2236+ → Zero Fragility)
**Risk:** Medium | **Dependencies:** P140

**Objective:** Use the existing test stability tracker (`ai/testing/`) from P32
to identify and fix or quarantine flaky tests. Establish a test execution time
budget (full suite < 90s). Mark slow tests with `@pytest.mark.slow`. Add a
fast-path `pytest -m "not slow"` alias.

**Done Criteria:** Zero flaky tests in last 5 runs; full suite passes in < 90s
(or slow tests are gated); `tests/COVERAGE.md` added with module-level summary.

---

### P143 — Threat Intel API Resilience Hardening
**Risk:** High | **Dependencies:** P140

**Objective:** Harden timeout, retry, circuit-breaker, and degraded-mode
behavior for all 16 threat intel APIs. Ensure `security.*` MCP tools return
useful partial results when APIs are down, not silent failures.

**Done Criteria:** Each threat intel API has a documented timeout + retry
policy; `security.threat_summary` returns partial data with clear source
indicators when some APIs fail; circuit-breaker state is observable via
`system.provider_status`.

---

### P144 — Knowledge Base Freshness and RAG Quality
**Risk:** Medium | **Dependencies:** P141, P143

**Objective:** Audit all RAG knowledge table entries for embedding freshness
dates. Identify chunks with poor retrieval scores and re-embed stale content.
Add a `knowledge.freshness_report` MCP tool.

**Done Criteria:** All knowledge table entries have freshness timestamps;
stale content (> 30 days) is flagged; `knowledge.rag_query` quality is manually
validated against 10 representative queries; new tool registered in allowlist.

---

### P145 — UCC Performance and UX Polish
**Risk:** Medium | **Dependencies:** P123, P126, P129

**Objective:** Profile the Next.js bundle size, measure Time to Interactive,
optimize data-fetching patterns, add loading states for all async panels,
and polish rough UX edges identified during P138 canary runs.

**Done Criteria:** UCC bundle size < 500 KB initial load; Time to Interactive
< 2s on localhost; all MCP-backed panels have skeleton loaders; no console
errors in production build.

**Validation Commands:**
```bash
cd ui && npm run build && npx @next/bundle-analyzer
npx tsc --noEmit
```

---

### P146 — Systemd Timer Audit and Concurrency Safety
**Risk:** High | **Dependencies:** P140, P124

**Objective:** Audit all 24 systemd timers for: offset staggering,
RandomizedDelaySec settings, exclusive resource contention, and missing
After=/Wants= dependencies. Document the timer conflict matrix.

**Done Criteria:** All 24 timers have staggered offsets; no two timers touching
the same LanceDB table fire within 30s of each other; timer health verified by
`agents.timer_health` tool; `systemd/TIMER_SCHEDULE.md` added.

---

### P147 — Security Audit Automation (ClamAV + CISA + NVD)
**Risk:** High | **Dependencies:** P143, P146

**Objective:** Build an automated security posture report combining: ClamAV
scan history, CVE scan results, CISA KEV matches, release watch alerts, and
dependency audit findings into a single scored posture report. Add a
`security.posture_report` MCP tool and a weekly Slack post.

**Done Criteria:** `security.posture_report` returns a JSON posture score
(0–100) with contributing factors; weekly insights timer triggers a Slack post;
report stored in LanceDB with timestamp.

---

### P148 — Provider Registry UI and API Key Rotation Workflow
**Risk:** High | **Dependencies:** P125, P145

**Objective:** Build the operational workflow for key rotation: detecting stale
keys (via `system.key_status`), prompting rotation through the UCC, validating
the new key against the provider's API before committing, and recording the
rotation event in the audit timeline. Supports all 6 cloud providers.

**Done Criteria:** UCC has a "Key Rotation" flow for each provider; rotation is
audited in the P126 timeline; stale keys (> 90 days) surface as warnings in the
morning briefing; rotation workflow has a dry-run mode.

---

### P149 — Gaming Profile Intelligence (MangoHud + PRIME Integration)
**Risk:** Low | **Dependencies:** P140

**Objective:** Integrate gaming profiles into the UCC: show active game
profiles, allow MangoHud preset switching, display GPU/CPU telemetry during
gaming sessions, and add PRIME mode status with safe mode guidance.
AGENT.md Rule #1 enforced: never suggest PRIME offload vars.

**Done Criteria:** UCC has a Gaming panel with profile list and GPU telemetry;
`gaming.profiles` and `gaming.mangohud_preset` are exposed in the UCC;
evidence artifacts under `docs/evidence/p149/`.

---

### P150 — Automated Dependency Update Workflow
**Risk:** Medium | **Dependencies:** P140, P147

**Objective:** Build an automated dependency update workflow that runs
`pip-audit` and `system.dep_scan` against proposed updates, checks for
breaking changes via `code.impact_analysis`, runs the full test suite, and
produces a merge-readiness report. Integrates with existing `dep-audit.timer`.

**Done Criteria:** `scripts/dep-update-check.py` produces a merge-readiness
report for each pending Dependabot PR; report covers vuln status, impact
analysis, and test result; script runs in CI.

---

### P151 — Conversation Memory Quality and Pruning
**Risk:** Medium | **Dependencies:** P141, P144

**Objective:** Implement quality scoring for memory entries (relevance decay,
deduplication, importance tagging) and add automatic pruning of low-quality
entries. Add a `memory.quality_report` and `memory.prune` MCP tool pair.

**Done Criteria:** Memory entries have quality scores; entries below threshold
(score < 0.3) are pruned weekly; `memory.quality_report` surfaces the
distribution; semantic retrieval accuracy improves measurably post-pruning.

---

### P152 — Morning Briefing Intelligence Upgrade
**Risk:** Low | **Dependencies:** P147, P151

**Objective:** Upgrade the morning briefing (9:30 AM daily) to include:
conversation memory context, pending phase pipeline status from Notion,
dependency update alerts, and a "top 3 action items" section generated by
the insights system.

**Done Criteria:** Morning briefing includes memory context, Notion phase
status, dependency alerts, and action items; briefing generation time < 10s;
output posted to Slack and stored in `system_insights` LanceDB table.

---

### P153 — Code Intelligence Index Quality
**Risk:** Medium | **Dependencies:** P141, P144

**Objective:** After GA with 2236+ tests and a full UI codebase, audit the
code index coverage. Add the `ui/` Next.js source to the index scope.
Implement an index health check in `agents.code_quality`.

**Done Criteria:** Code index covers `ai/`, `tests/`, `scripts/`, and `ui/`;
`code.dependency_graph` returns accurate results for key modules;
`agents.code_quality` includes index coverage as a health metric.

---

### P154 — Operational Runbook Library
**Risk:** Low | **Dependencies:** P132, P140

**Objective:** Create the library of concrete operational runbooks for known
scenarios: service restart, provider failover, API key rotation, ClamAV
quarantine handling, LanceDB corruption recovery, and Bazzite OS update.
Each runbook is a structured YAML/Markdown artifact with steps, safety checks,
and rollback.

**Done Criteria:** 8+ runbooks cover the most common operational scenarios;
runbooks are discoverable via `knowledge.rag_query`; critical runbooks are
linked from AGENT.md; runbook format is validated by a linter.

---

### P155 — Alert Deduplication and Noise Reduction
**Risk:** Medium | **Dependencies:** P147, P152

**Objective:** Extend `ai/security/alerts.py` (P27 deduplication logic) with
priority-based suppression and alert correlation (same CVE from multiple
sources = one alert). Add a `security.alert_noise_report`.

**Done Criteria:** Duplicate alerts (same finding, multiple sources) are merged
into one; low-priority alerts during off-hours are batched into daily digests;
alert signal-to-noise ratio improves by ≥ 50% vs. P27 baseline.

---

### P156 — External SSD Health Monitoring
**Risk:** High | **Dependencies:** P140

**Objective:** Add SMART health monitoring for the external 1.8 TB SanDisk at
`/var/mnt/ext-ssd` (holds all 28 LanceDB tables, LLM cache, and log archives).
Integrate into the daily health snapshot. Add a `system.storage_health` MCP
tool. Add low-space and SMART failure alerts.

**Done Criteria:** `system.storage_health` returns SMART data, mount status,
and available space for both SSDs; low-space (< 50 GB) triggers a security
alert; daily health snapshot includes storage health.

**Validation Commands:**
```bash
pytest tests/ -q --tb=short -k "storage or disk or health"
curl -s http://127.0.0.1:8766/health
```

---

### P157 — UI Accessibility and Keyboard Navigation Audit
**Risk:** Low | **Dependencies:** P145

**Objective:** Run a WCAG 2.1 AA audit of the UCC: keyboard navigation for all
interactive elements, focus trap in modals/drawers, color contrast verification
in both light and dark modes, screen reader landmark structure, and ARIA labels
for icon buttons.

**Done Criteria:** UCC passes WCAG 2.1 AA for all primary operator surfaces;
all interactive elements are keyboard-reachable; no color contrast failures
in either theme; accessibility evidence under `docs/evidence/p157/`.

---

### P158 — LLM Proxy Hardening and Rate Limit Enforcement
**Risk:** High | **Dependencies:** P130, P148

**Objective:** Harden `ai/llm_proxy.py` (port 8767): request validation,
response streaming error recovery, per-provider timeout enforcement, and rate
limit header injection. Ensure the proxy gracefully degrades when all providers
are in cooldown (structured 503 with retry-after).

**Done Criteria:** Proxy rejects invalid requests with structured errors; all
6 provider timeouts are enforced; rate limit headers are returned to clients;
degraded-mode returns a clear 503 with retry-after; proxy tests cover all
error paths.

---

### P159 — Bazzite AI Layer v2.0 Release Candidate
**Risk:** Critical | **Approval Required:** YES | **Dependencies:** P140–P158

**Objective:** The comprehensive v2.0 release candidate gate. Combines all
post-GA improvements into a verified, documented release. Produce: updated
AGENT.md with current counts, CHANGELOG.md v2.0 entry, architecture diagram
refresh, USER-GUIDE.md updates, final Notion ledger reconciliation, and a
v2.0 git tag.

**Done Criteria:** All P140–P158 phases are Done; AGENT.md counts are current;
architecture diagram reflects the post-GA system; v2.0 git tag is created;
final Notion phase ledger is reconciled; `ruff`, `pytest`, and UCC build all
pass clean; release candidate report produced.

**Note:** "Do not tag v2.0 unless all upstream phases are Done and the Notion
ledger shows no contradictions. Read P139's acceptance report first."

---

## Phase Sequencing Summary

```
P118 (DONE)
  └─ P119 Observability
       └─ P120 RBAC Foundation
            ├─ P121 Routing Intelligence (also needs P115, P116)
            │    └─ P122 Agent Orchestration
            │         └─ P132 HITL Runbooks
            │              └─ P154 Runbook Library
            ├─ P125 Provider Onboarding
            │    └─ P148 Key Rotation UI
            │         └─ P158 LLM Proxy Hardening
            └─ P126 Audit Timeline
                 └─ P127 MCP Policy-as-Code
                      └─ P128 Local Identity [APPROVAL GATE]
                           └─ P129 Context Isolation
                                └─ P139 GA Acceptance Gate [APPROVAL GATE]
                                     └─ P140 Stabilization Sprint
                                          ├─ P141 LanceDB Audit
                                          ├─ P142 Test Health
                                          ├─ P143 Threat Intel Hardening
                                          ├─ P146 Timer Audit
                                          ├─ P149 Gaming Integration
                                          ├─ P150 Dep Update Workflow
                                          ├─ P156 Storage Health
                                          │
                                          ├─ P144 RAG Quality        (P141, P143)
                                          ├─ P145 UCC Polish         (P123, P126, P129)
                                          ├─ P147 Security Automation (P143, P146)
                                          ├─ P151 Memory Quality     (P141, P144)
                                          ├─ P152 Briefing Upgrade   (P147, P151)
                                          ├─ P153 Code Intel         (P141, P144)
                                          ├─ P155 Alert Deduplication (P147, P152)
                                          ├─ P157 Accessibility      (P145)
                                          │
                                          └─ P159 v2.0 Release Candidate [APPROVAL GATE]
```

---
*Document generated: 2026-04-16 | Bazzite AI Layer | Based on P118 final state*
*CC prompt numbering continues from 100 | All prompts start with /feature-dev*
