# P101 — MCP Tool Governance + Analytics Platform

**Status**: Planned  
**Dependencies**: P100, P76, P96  
**Risk Tier**: High  
**Backend**: opencode  
**Estimated Effort**: 3-4 sessions  

## Objective

Implement comprehensive governance, analytics, and lifecycle management for the 133 MCP tools in the Bazzite AI Layer. Enable tool usage optimization, security auditing, performance monitoring, and systematic tool lifecycle management to ensure the MCP bridge remains maintainable, secure, and performant as the system scales.

## Background & Motivation

### Current State
- **133 MCP tools** available across 12 categories (security, system, code, workflow, etc.)
- Tools added organically across phases P19-P100
- No centralized tool usage analytics or governance
- Limited visibility into tool performance, error rates, or usage patterns
- No systematic tool versioning or deprecation process
- Tool security auditing is manual and ad-hoc

### Pain Points
1. **Tool Sprawl**: 133 tools with varying documentation quality and maintenance status
2. **No Usage Insights**: Unknown which tools are heavily used vs. orphaned
3. **Security Gaps**: No automated tool permission auditing or access pattern analysis
4. **Performance Blindness**: No visibility into tool latency, error rates, or resource consumption
5. **Lifecycle Chaos**: No process for tool versioning, deprecation, or retirement

### Strategic Value
- **Operational Excellence**: Data-driven tool optimization and maintenance prioritization
- **Security Posture**: Proactive identification of over-privileged or misused tools
- **Cost Optimization**: Identify and remove unused tools, optimize hot paths
- **Developer Experience**: Better tool discoverability and usage guidance

## Scope

### In Scope

#### 1. Tool Analytics Engine
- Real-time tool usage tracking (invocations, latency, errors)
- Usage pattern analysis (frequency, time-of-day, user-agent)
- Tool dependency mapping (which tools call other tools)
- Cost attribution (token usage per tool, provider costs)

#### 2. Governance Framework
- Tool categorization and tagging system
- Permission audit and least-privilege analysis
- Tool security scoring (based on access patterns, data exposure)
- Allowlist/denylist management with automated enforcement

#### 3. Lifecycle Management
- Tool versioning scheme and API compatibility tracking
- Deprecation workflow with migration path generation
- Tool health monitoring (availability, error rates)
- Automated tool retirement for unused/abandoned tools

#### 4. Monitoring & Alerting
- Tool performance dashboards
- Anomaly detection for unusual tool usage patterns
- Error rate alerting with automatic circuit breaker triggers
- Weekly tool health reports

### Out of Scope
- New tool creation (covered by existing `system.create_tool`)
- Tool functionality changes (only governance/analytics)
- External MCP server integration (future phase)
- Tool marketplace or sharing (future phase)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Bridge (ai/mcp_bridge/)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Tool       │  │   Tool       │  │   Tool           │  │
│  │   Registry   │  │   Router     │  │   Handlers       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼──────────────────┼────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              P101 Tool Governance Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Usage      │  │   Governance │  │   Lifecycle      │  │
│  │   Analytics  │  │   Engine     │  │   Manager        │  │
│  │   Service    │  │              │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                  │              │
│  ┌──────▼─────────────────▼──────────────────▼──────────┐  │
│  │           Tool Governance Database                   │  │
│  │  ├─ tool_usage_metrics (LanceDB)                    │  │
│  │  ├─ tool_governance_policies (JSON)                 │  │
│  │  ├─ tool_lifecycle_state (LanceDB)                  │  │
│  │  └─ tool_audit_logs (JSONL)                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Implementation

### New Files

```
ai/mcp_bridge/governance/
├── __init__.py
├── analytics.py           # Usage tracking and metrics collection
├── governance_engine.py   # Policy enforcement and auditing
├── lifecycle.py           # Versioning, deprecation, retirement
├── models.py              # Pydantic models for governance entities
├── monitoring.py          # Health checks and alerting
└── reports.py             # Report generation

ai/mcp_bridge/tools_governance/
├── __init__.py
├── tool_analytics.py      # MCP tool: query analytics
├── tool_governance.py     # MCP tool: governance operations
├── tool_lifecycle.py      # MCP tool: lifecycle management
└── tool_monitoring.py     # MCP tool: monitoring queries

tests/test_mcp_governance/
├── test_analytics.py
├── test_governance_engine.py
├── test_lifecycle.py
└── test_monitoring.py

docs/
├── P101_PLAN.md           # This document
├── P101_COMPLETION_REPORT.md  # Generated on completion
└── TOOL_GOVERNANCE_GUIDE.md   # Operational guide
```

### Key Components

#### 1. Usage Analytics Service (`analytics.py`)

```python
class ToolUsageAnalytics:
    """Tracks and analyzes MCP tool usage patterns."""
    
    async def record_invocation(self, tool_name: str, context: InvocationContext) -> None:
        """Record a tool invocation with timing and outcome."""
        
    async def get_usage_summary(self, time_range: TimeRange) -> UsageSummary:
        """Get aggregated usage statistics."""
        
    async def get_tool_rankings(self, metric: str = "invocations") -> List[ToolRanking]:
        """Rank tools by various metrics (usage, errors, latency)."""
        
    async def detect_anomalies(self, tool_name: Optional[str] = None) -> List[Anomaly]:
        """Detect unusual usage patterns using statistical analysis."""
```

**Metrics Tracked**:
- Invocation count (total, per-tool, per-category)
- Latency percentiles (p50, p95, p99)
- Error rates and error type breakdown
- Token usage and cost attribution
- Unique callers and session patterns
- Time-of-day and day-of-week patterns

#### 2. Governance Engine (`governance_engine.py`)

```python
class ToolGovernanceEngine:
    """Enforces governance policies and performs security audits."""
    
    async def audit_tool_permissions(self, tool_name: str) -> PermissionAudit:
        """Audit tool against least-privilege principles."""
        
    async def evaluate_security_score(self, tool_name: str) -> SecurityScore:
        """Calculate security score based on access patterns and data exposure."""
        
    async def enforce_policy(self, tool_name: str, policy: GovernancePolicy) -> EnforcementResult:
        """Apply governance policy to tool."""
        
    async def generate_compliance_report(self) -> ComplianceReport:
        """Generate system-wide governance compliance report."""
```

**Governance Policies**:
- **Category Restrictions**: Tools in `security.*` require elevated session
- **Rate Limiting**: Per-tool invocation limits per minute/hour
- **Data Exposure**: Tools accessing secrets flagged for review
- **Access Patterns**: Tools with unusual access patterns trigger audit
- **Deprecation**: Deprecated tools blocked or warned

#### 3. Lifecycle Manager (`lifecycle.py`)

```python
class ToolLifecycleManager:
    """Manages tool versioning, deprecation, and retirement."""
    
    async def register_version(self, tool_name: str, version: str, 
                               compatibility: CompatibilityInfo) -> None:
        """Register a new tool version."""
        
    async def deprecate_tool(self, tool_name: str, 
                            migration_path: MigrationPath,
                            sunset_date: datetime) -> None:
        """Mark tool as deprecated with migration guidance."""
        
    async def retire_tool(self, tool_name: str, 
                         archive_data: bool = True) -> None:
        """Permanently retire a tool."""
        
    async def get_lifecycle_state(self, tool_name: str) -> LifecycleState:
        """Get current lifecycle state of a tool."""
```

**Lifecycle States**:
- `active`: Fully supported and recommended
- `deprecated`: Still works but migration recommended
- `legacy`: Maintenance only, no new features
- `retired`: Unavailable, archived for reference

#### 4. Monitoring & Alerting (`monitoring.py`)

```python
class ToolMonitor:
    """Monitors tool health and triggers alerts."""
    
    async def health_check(self, tool_name: str) -> HealthStatus:
        """Perform health check on a tool."""
        
    async def check_circuit_breaker(self, tool_name: str) -> CircuitBreakerState:
        """Check if circuit breaker should trip."""
        
    async def generate_health_report(self) -> HealthReport:
        """Generate comprehensive health report."""
```

**Circuit Breaker Rules**:
- Trip after 10 errors in 60 seconds
- Half-open after 5 minutes
- Full close after 5 consecutive successes

### MCP Tools Added

| Tool | Category | Description |
|------|----------|-------------|
| `tool.analytics.summary` | Tool Governance | Get usage summary for time range |
| `tool.analytics.ranking` | Tool Governance | Get tool rankings by metric |
| `tool.analytics.trends` | Tool Governance | Get usage trend analysis |
| `tool.governance.audit` | Tool Governance | Run permission/security audit |
| `tool.governance.score` | Tool Governance | Get tool security score |
| `tool.governance.policies` | Tool Governance | List/manage governance policies |
| `tool.lifecycle.status` | Tool Governance | Get tool lifecycle state |
| `tool.lifecycle.deprecate` | Tool Governance | Deprecate a tool |
| `tool.lifecycle.versions` | Tool Governance | List tool versions |
| `tool.monitoring.health` | Tool Governance | Get tool health status |
| `tool.monitoring.alerts` | Tool Governance | Get active alerts |
| `tool.monitoring.report` | Tool Governance | Generate monitoring report |

### Database Schema

**tool_usage_metrics (LanceDB)**:
```python
class ToolUsageMetric(BaseModel):
    timestamp: datetime
    tool_name: str
    category: str
    invocations: int
    avg_latency_ms: float
    p95_latency_ms: float
    error_count: int
    error_rate: float
    unique_callers: int
    token_usage: int
    cost_usd: float
```

**tool_lifecycle_state (LanceDB)**:
```python
class ToolLifecycleState(BaseModel):
    tool_name: str
    current_state: LifecycleState  # active, deprecated, legacy, retired
    version: str
    introduced_at: datetime
    deprecated_at: Optional[datetime]
    sunset_date: Optional[datetime]
    retired_at: Optional[datetime]
    replacement_tool: Optional[str]
    migration_guide: Optional[str]
```

**tool_governance_policies (JSON)**:
```json
{
  "policies": [
    {
      "id": "security-tools-restricted",
      "applies_to": "security.*",
      "rules": [
        {"type": "require_session_level", "min_level": "elevated"},
        {"type": "rate_limit", "max_invocations_per_hour": 100}
      ]
    },
    {
      "id": "shell-gateway-audit",
      "applies_to": "shell.*",
      "rules": [
        {"type": "audit_all_invocations"},
        {"type": "require_approval", "for_commands": ["sudo", "rm -rf"]}
      ]
    }
  ]
}
```

## Integration Points

### 1. MCP Bridge Integration

Modify `ai/mcp_bridge/server.py` to inject governance hooks:

```python
class GovernanceMiddleware:
    """Middleware for governance enforcement."""
    
    async def before_invoke(self, tool_name: str, arguments: dict) -> None:
        # Check circuit breaker
        # Validate against policies
        # Log invocation start
        
    async def after_invoke(self, tool_name: str, result: Any, 
                          duration_ms: float, error: Optional[Exception]) -> None:
        # Record metrics
        # Update circuit breaker
        # Check for anomalies
```

### 2. Phase Control Integration

Tool governance runs as background service:
- Hourly: Usage aggregation and anomaly detection
- Daily: Health checks and report generation
- Weekly: Full governance audit
- On-demand: Policy enforcement and lifecycle transitions

### 3. Console Integration

New "Tool Governance" panel in the console:
- Tool usage dashboard
- Active alerts view
- Policy management interface
- Lifecycle management UI

## Validation Strategy

### Automated Tests (40+ tests)

```python
# Test analytics accuracy
async def test_usage_tracking_accuracy():
    """Verify usage metrics are accurately recorded."""
    
# Test policy enforcement
async def test_policy_enforcement():
    """Verify governance policies are correctly enforced."""
    
# Test lifecycle transitions
async def test_lifecycle_transitions():
    """Verify tool lifecycle state transitions work correctly."""
    
# Test circuit breaker
async def test_circuit_breaker():
    """Verify circuit breaker trips and recovers correctly."""
```

### Validation Commands

```bash
# Lint new code
ruff check ai/mcp_bridge/governance/ tests/test_mcp_governance/

# Run governance tests
python -m pytest tests/test_mcp_governance/ -v

# Run full suite
python -m pytest tests/ -x -q --tb=short

# Verify MCP tools added
python -c "from ai.mcp_bridge.tools import TOOL_HANDLERS; print(f'Tools: {len(TOOL_HANDLERS)}')"

# Check governance integration
rg -n "GovernanceMiddleware|ToolUsageAnalytics|ToolGovernanceEngine" ai/mcp_bridge/
```

## Deliverables

### Code
- [ ] `ai/mcp_bridge/governance/` module (6 files, ~1500 lines)
- [ ] `ai/mcp_bridge/tools_governance/` MCP tools (12 tools)
- [ ] Tests in `tests/test_mcp_governance/` (40+ tests)

### Documentation
- [ ] `docs/P101_PLAN.md` (this document)
- [ ] `docs/P101_COMPLETION_REPORT.md` (post-completion)
- [ ] `docs/TOOL_GOVERNANCE_GUIDE.md` (operational guide)
- [ ] Updated `docs/AGENT.md` with governance section

### Data
- [ ] Initial tool catalog with lifecycle states
- [ ] Governance policies configuration
- [ ] Baseline usage metrics (from P100 data)

### Artifacts
- [ ] Tool usage dashboard (console)
- [ ] Weekly governance report (automated)
- [ ] Tool security audit report

## Done Criteria

1. **Analytics**: All 133 tools have usage tracking with 24h of metrics
2. **Governance**: Security audit completed for all tools, policies enforced
3. **Lifecycle**: All tools categorized with lifecycle state documented
4. **Monitoring**: Health checks running, circuit breakers functional
5. **Integration**: Console panel displays tool governance data
6. **Tests**: 40+ tests passing, coverage >85%
7. **Docs**: PLAN, COMPLETION_REPORT, and operational guide written
8. **Handoff**: Updated with P101 completion and next phase recommendations

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance overhead from tracking | Medium | Async logging, batched writes, configurable sampling |
| False positives in anomaly detection | Medium | Statistical thresholds, manual review for critical alerts |
| Tool retirement breaks workflows | High | Deprecation period (30 days), migration guides, communication |
| Policy misconfiguration blocks tools | High | Dry-run mode, staged rollout, override capabilities |

## Dependencies

- **P100**: Browser connectivity ensures console can display governance UI
- **P76**: Ingestion reliability patterns for governance data persistence
- **P96**: Figma integration patterns for tool categorization metadata

## Timeline Estimate

| Component | Sessions | Files | Lines |
|-----------|----------|-------|-------|
| Core governance module | 1 | 6 | ~800 |
| MCP tools integration | 1 | 5 | ~400 |
| Console integration | 1 | 3 | ~300 |
| Tests & validation | 1 | 4 | ~600 |
| Documentation | 0.5 | 3 | ~500 |
| **Total** | **4** | **21** | **~2600** |

## Future Work (Post-P101)

- P102: Dynamic tool discovery and auto-registration
- P103: Tool marketplace and sharing
- P104: External MCP server federation
- P105: Tool performance optimization based on analytics

## References

- [MCP Best Practices 2025](https://thenewstack.io/15-best-practices-for-building-mcp-servers-in-production/)
- P76: Ingestion Reliability patterns
- P96: Figma integration patterns
- P100: Browser connectivity implementation
