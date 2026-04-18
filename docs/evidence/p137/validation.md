# P137 Validation Evidence — Deployment Profiles and Environment Packaging

**Phase:** P137 — Deployment Profiles and Environment Packaging
**Date:** 2026-04-17

## Validation Commands Run

```bash
ruff check scripts/ ai/ tests/
.venv/bin/python -m pytest tests/test_deployment_profiles.py -q
cd ui && npm run build
```

## Results

### Test Results

```
.....................                                           [100%]
21 passed in 1.50s
```

### Test Coverage

| Test Class | Test Count | Status |
|-----------|----------|--------|
| TestProfileLoading | 3 | Pass |
| TestProfileValidation | 5 | Pass |
| TestFailClosed | 4 | Pass |
| TestKeyPresence | 2 | Pass |
| TestWorkbenchConfig | 3 | Pass |
| TestSummary | 1 | Pass |
| TestSafetyProofs | 3 | Pass |

### Ruff Lint

```
All checks passed!
```

### UI Build

```
✓ Compiled successfully in 3.8s
✓ Generating static pages (4/4) in 639ms
```

## Implementation Artifacts

| Artifact | Path |
|----------|------|
| Deployment module | ai/deployment_profiles.py |
| Test suite | tests/test_deployment_profiles.py |
| Profile docs | docs/deploy/profiles.md |
| Phase plan | docs/P137_PLAN.md |

## Profiles Implemented

| Profile | Mode | Services | Validation Checks |
|---------|------|----------|----------------|
| Local Only | local-only | bazzite-llm-proxy, bazzite-mcp-bridge | MCP, LLM health, repo root, venv |
| Security Autopilot | security-autopilot | + local-only | + API keys |
| Agent Workbench | agent-workbench | + local-only | + workbench config |

## Safety Proofs Verified

| Proof | Verification |
|-------|------------|
| No secrets in output | Key presence shows only "configured" not values |
| Fail closed | Missing services/ports/health fails with FAIL status |
| No auto-start | Profiles require explicit operator startup |
| Critical checks required | service, mcp, llm, repo, venv are critical |

## Result: PASS

- 21 tests pass
- Ruff passes
- UI build passes
- Three profiles implemented (local-only, security-autopilot, agent-workbench)
- Fail-closed validation working
- No secrets exposed in output
- Startup/shutdown/troubleshooting documented