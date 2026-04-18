# P138 Validation Evidence — Browser/Service Canary Release Automation

**Phase:** P138 — Browser/Service Canary Release Automation
**Date:** 2026-04-18

## Validation Commands Run

```bash
curl -s http://127.0.0.1:8766/health
curl -s http://127.0.0.1:8767/health
cd ui && npm run build
.venv/bin/python -m pytest tests/test_canary.py -q
```

## Results

### Health Endpoints

```
MCP bridge (8766): {"status":"ok","tools":193,"service":"bazzite-mcp-bridge"}
LLM proxy (8767): {"status":"ok","service":"bazzite-llm-proxy"}
```

### UI Build

```
✓ Compiled successfully in 3.8s
✓ Generating static pages (4/4) in 692ms
```

### Test Results

```
35 passed in 1.27s (canary + deployment profiles)
```

## Implementation Artifacts

| Artifact | Path |
|----------|------|
| Canary module | ai/canary.py |
| Operator script | scripts/canary.sh |
| Test suite | tests/test_canary.py |
| Phase plan | docs/P138_PLAN.md |

## Canary Stages Implemented

| Stage | Check | Status |
|-------|-------|--------|
| preflight | deploy-services.sh | Pass |
| preflight | profile validation | Pass |
| service_health | LLM proxy health | Pass |
| service_health | MCP bridge health | Pass |
| service_health | bazzite-llm-proxy service | Pass |
| service_health | bazzite-mcp-bridge service | Pass |
| mcp_tools | MCP allowlist | Pass |
| mcp_tools | port 8766 listening | Pass |
| ui_build | npm build | Pass |
| policy_gates | security policy | Pass |

## Safety Proofs Verified

| Proof | Verification |
|-------|------------|
| Non-destructive | Canary only reads/validates, never modifies |
| No approval bypass | Policy gates enforced as check |
| Secrets redacted | Helper function implemented |
| Fail-closed | Missing checks return FAIL |

## Evidence Bundle

Generates:
- `canary-bundle.json` — full JSON results
- `canary-summary.txt` — failure summary with troubleshooting commands

## Result: PASS

- Canaries tests: 14 passed
- Deployment profiles: 21 passed  
- All health endpoints: responding
- UI build: successful
- Policy gates: present
- Evidence bundle: generated