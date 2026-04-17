"""Local identity and step-up security for P128.

This module provides:
- Local-only identity management (no cloud auth)
- Step-up challenge for privileged operations
- Trusted device markers
- Lockout/recovery behavior
- P127 policy integration

P80 Truth Reconciliation:
- Original P80 planned as auth/2FA/recovery/Gmail - never fully implemented
- Chat Workspace originally P80 but reconciled to P83
- P81 (PIN-gated settings) is the foundation
- P128 builds on P81 PIN to provide step-up for all privileged operations
"""

from ai.identity.models import (
    LocalIdentity,
    LocalIdentityManager,
    StepUpChallenge,
    StepUpLevel,
    StepUpStatus,
    TrustedDevice,
    check_privileged_operation,
    complete_step_up,
    get_identity_manager,
    require_step_up,
    reset_identity_manager,
)

__all__ = [
    "LocalIdentity",
    "LocalIdentityManager",
    "StepUpChallenge",
    "StepUpLevel",
    "StepUpStatus",
    "TrustedDevice",
    "check_privileged_operation",
    "complete_step_up",
    "get_identity_manager",
    "require_step_up",
    "reset_identity_manager",
]
