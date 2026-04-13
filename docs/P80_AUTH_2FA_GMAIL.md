# P80 — Auth, 2FA, Recovery, Gmail Notifications

**Status**: Planned  
**Dependencies**: P79  
**Risk Tier**: Critical  
**Backend**: opencode  

## Objective

Implement the authentication foundation for the Bazzite Control Console including PIN-based access control, two-factor authentication (2FA) setup, account recovery mechanisms, and Gmail notification integration for security events.

## Summary / Scope

This phase establishes the security foundation for the settings and privileged operations. All subsequent sensitive operations (API key management, dangerous actions) depend on this authentication layer.

**Key Features**:
- PIN enrollment and first-time setup
- PIN unlock flow for sensitive settings
- TOTP-based 2FA setup and verification
- Account recovery procedures
- Gmail SMTP integration for notifications
- Failed attempt alerting

## Prerequisites

- P79 (Shell Bootstrap) must be complete
- Gmail account for notification sending
- Secure storage for encrypted secrets

## Implementation Notes

**Note**: The Chat Workspace implementation was originally marked as "P80" in early commits but has been reconciled to P83 per the current working roadmap. This document reserves P80 for authentication infrastructure per the revised phase ordering.

## Dependencies

- Backend secrets service for encrypted storage
- Gmail API or SMTP credentials
- TOTP library (e.g., `pyotp` for Python backend)

## Related Phases

- **P81** → PIN-Gated Settings + Secrets Service (depends on P80 auth layer)
- **P83** → Chat + MCP Workspace Integration (reconciled from original P80)

## References

- P77 — UI Architecture (Security model section)
- P78 — Midnight Glass Design System (Settings surfaces)
- docs/P83_CHAT_WORKSPACE.md — Reconciled chat implementation
