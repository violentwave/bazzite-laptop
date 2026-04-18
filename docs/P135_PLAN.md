# P135 Plan — Integration Governance for Notion, Slack, and GitHub Actions

## Objective

Govern Notion, Slack, and GitHub action integrations so cross-tool updates, comments, phase rows, Slack notifications, and repo operations are scoped, audited, and policy-aware.

## Dependencies

- P52 (Slack + Notion Integrations)
- P55 (Phase Control)
- P127 (MCP Policy-as-Code)
- P132 (Human-in-the-loop Orchestration Runbooks)

## Risk Tier

**medium** — Integration governance involves cross-tool mutation permissions.

## Execution Mode

**bounded** — Default-deny for unknown actions, policy checks for mutations.

## Approval Required

**no** — Bounded mode with default deny.

## Scope Boundaries

### Implement (in scope)
- Integration action registry with risk metadata
- Default deny for unknown actions
- Scope/attribution requirements for mutations
- Redaction for sensitive content in outbound payloads
- Policy checks before mutation-capable cross-tool actions

### Do NOT implement (out of scope)
- P136, P138, or P139 features
- Mass-edit or broad broadcast without explicit policy
- New integration systems beyond Notion/Slack/GitHub

## Implementation Shape

### Modules Created/Modified

| Module | Purpose |
|--------|---------|
| `ai/integration_governance.py` | Governance registry, action definitions, evaluation |
| `ai/notion/handlers.py` | Added governance checks to existing handlers |
| `ai/slack/handlers.py` | Added governance checks and redaction |

### Integration Actions

| System | Action IDs |
|--------|----------|
| Notion | notion.search, notion.get_page, notion.get_page_content, notion.query_database, notion.update_row, notion.create_page |
| Slack | slack.list_channels, slack.list_users, slack.post_message, slack.get_history, slack.broadcast |
| GitHub | github.pr_create, github.issue_create, github.workflow_trigger |

### Risk Mapping

| Risk Tier | Actions | Requirement |
|-----------|---------|-------------|
| Low | read-only, list | Auto-approved |
| Medium | scoped mutations | Phase/workflow context required |
| High | broad/broadcast/destructive | Approval + scope required |

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_integration_governance.py tests/test_phase_control*.py -q
ruff check ai/ tests/
```

## Done Criteria

- [ ] 26 governance tests pass
- [ ] 57 phase control regression tests pass
- [ ] Ruff check passes
- [ ] Unknown actions default deny
- [ ] Mutations require scope/attribution
- [ ] Outbound payloads redact sensitive content
- [ ] Existing integration behavior preserved