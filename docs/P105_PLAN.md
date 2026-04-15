# P105 Plan — External MCP Federation Governance

**Phase:** P105  
**Status:** Complete  
**Date:** 2026-04-15

## Overview

Design and implement a safe external MCP federation layer that can inventory, validate, score, and optionally proxy external MCP server/tool metadata without exposing secrets, executing untrusted tools by default, or bypassing local governance.

## Dependencies

- P101: MCP Tool Governance + Analytics Platform
- P102: Dynamic Tool Discovery
- P103: MCP Tool Marketplace
- P104: Advanced Tool Analytics + Optimization

## Deliverables

### Module: `ai/mcp_bridge/federation/`

| File | Purpose |
|------|----------|
| `models.py` | Federation models (ExternalServerIdentity, TrustState, CapabilityMap, etc.) |
| `discovery.py` | Read-only discovery/inventory of external MCP servers |
| `trust.py` | Trust scoring based on server characteristics |
| `policy.py` | Policy evaluation with default-deny, audit logging |
| `__init__.py` | Module exports |

### MCP Tools (6 new)

| Tool | Description |
|------|-------------|
| `tool.federation.discover` | Discover external MCP server by URL |
| `tool.federation.list_servers` | List all discovered external MCP servers |
| `tool.federation.inspect_server` | Inspect external MCP server details |
| `tool.federation.audit` | Get federation audit log |
| `tool.federation.trust_score` | Calculate trust score for external server |
| `tool.federation.disable` | Disable/remove external MCP server from federation |

### Total Tool Count

- Previous: 163 tools (P101-P104)
- New: 6 tools
- **Total: 169 tools**

### Tests

- `tests/test_p105_mcp_federation.py` - 35 test cases

## Implementation Details

### Read-Only Federation

- All discovery is read-only - does not execute remote tools
- External manifests validated as untrusted input
- URL validation, tool name validation, manifest size limits

### Trust Scoring

- HTTPS: +50 points if using HTTPS
- Verification: +30 for verified, -50 for blocked
- Transparency: +20 based on manifest completeness
- Capabilities: +/-30 based on tool analysis
- History: +20 based on server age and verification recency

### Policy Evaluation

- Default-deny policy for remote execution
- Quarantine for low trust (<20)
- Audit for medium trust (20-40)
- Allow for high trust (70+)
- System tools always denied

### Security Properties

- No API keys in code/tests/docs
- No service binding to 0.0.0.0
- Does not import ai.router from ai/mcp_bridge/
- Validates URLs, paths, schemas, sizes, timeouts

## Validation

```bash
# Ruff check
ruff check ai/mcp_bridge/federation/ tests/test_p105_mcp_federation.py

# Run tests
python -m pytest tests/test_p105_mcp_federation.py -v

# YAML validation
python3 -c "import yaml; yaml.safe_load(open('configs/mcp-bridge-allowlist.yaml'))"

# Integration tests
python -m pytest tests/test_p102_dynamic_tool_discovery.py tests/test_p103_tool_marketplace.py tests/test_p104_advanced_tool_analytics.py tests/test_p105_mcp_federation.py -q
```

## Notes

- Preserves P101 governance, P102 dynamic registry, P103 marketplace boundaries
- Default to read-only federation
- No remote tool execution unless explicitly safe-gated
- Audit log for all federation actions
