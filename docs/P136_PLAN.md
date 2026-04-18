# P136 Plan — Retention, Privacy, and Export Controls

## Objective

Add retention policy enforcement, privacy redaction (PII, secrets, paths), and export controls for Security Autopilot data, Agent Workbench artifacts, provenance, memory, and audit events.

## Dependencies

- P126 (Provenance Chain)
- P129 (Context Isolation)
- P133 (Audit & Compliance Logging)

## Risk Tier

**medium** — Data management and redaction.

## Execution Mode

**bounded** — Retention and export controlled by policy rules.

## Scope Boundaries

### Implement (in scope)
- Retention policies for 7 data classes (security_findings, incidents, plans, audit_logs, agent_artifacts, knowledge_base, provenance)
- Redaction for secrets, PII, file paths
- Export bundle generation with metadata and integrity
- Safe deletion workflows with verification
- Context isolation respecting P129 boundaries

### Do NOT implement (out of scope)
- Automated pruning of acceptance evidence
- Export secrets/API keys to UI/logs
- P137, P138, or P139 features

## Implementation Shape

### Modules Created/Modified

| Module | Purpose |
|--------|---------|
| `ai/retention_privacy.py` | Retention policy manager, redaction engine, export bundle generator |

### Data Classes

| Class ID | Name | Description |
|----------|------|-------------|
| security_findings | Security Findings | Scan results, CVE reports, threat intel |
| incidents | Security Incidents | Active and resolved security incidents |
| plans | Remediation Plans | Planned actions and tracking |
| audit_logs | Audit Events | Compliance audit trail |
| agent_artifacts | Agent Workbench | Agent-generated content |
| knowledge_base | Knowledge Base | RAG vector store content |
| provenance | Provenance Chain | Provenance records |

### Retention Rules

| Data Class | Retention | Auto-Delete | Encryption |
|------------|-----------|-------------|------------|
| security_findings | 90 days | yes | at-rest |
| incidents | 365 days | no | at-rest |
| plans | 180 days | yes | at-rest |
| audit_logs | 730 days | yes | at-rest |
| agent_artifacts | 90 days | yes | at-rest |
| knowledge_base | 365 days | no | at-rest |
| provenance | 365 days | no | at-rest |

### Redaction Patterns

| Pattern Type | Matches |
|--------------|---------|
| secrets | api_key:, token:, sk-*, xoxb-* |
| paths | /home/*, /var/home/*, /root/* |
| pii | SSN patterns, email patterns |

### Export Config

| Field | Description |
|-------|-------------|
| include_metadata | Include export timestamp, source, version |
| redact_sensitive | Apply redaction before export |
| verify_integrity | SHA256 hash verification |
| format | JSON or CSV |

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_retention_privacy.py -q
ruff check ai/ tests/
```

## Done Criteria

- [ ] All 24 retention privacy tests pass
- [ ] Ruff check passes
- [ ] Retention rules cover all 7 data classes
- [ ] Redaction handles secrets, PII, paths
- [ ] Export includes metadata and integrity
- [ ] Safe deletion with verification
- [ ] Context isolation respected