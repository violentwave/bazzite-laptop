"""Local identity model for P128.

This module provides local-only identity, step-up security, and trusted-device
management without cloud authentication.

P80 Truth Reconciliation:
- Original P80 was planned as auth/2FA/recovery/Gmail - never fully implemented
- Chat Workspace was originally P80 but reconciled to P83
- P81 implemented PIN-gated settings (ai/settings_service.py)
- P128 reconciles P80 by implementing local-only identity layer on top of P81 PIN
"""

from __future__ import annotations

import logging
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

IDENTITY_DB = Path.home() / ".config" / "bazzite-ai" / "identity.db"

STEP_UP_SESSION_KEY = "step_up_session"
TRUSTED_DEVICE_KEY = "trusted_device"
IDENTITY_LOCKED_UNTIL = "identity_locked_until"
IDENTITY_FAILED_ATTEMPTS = "identity_failed_attempts"


class StepUpLevel(StrEnum):
    """Step-up authentication levels."""

    NONE = "none"
    PIN = "pin"
    STEP_UP = "step_up"


class StepUpStatus(StrEnum):
    """Step-up challenge status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    LOCKED = "locked"


@dataclass
class LocalIdentity:
    """Local operator identity state."""

    operator_id: str = "local_operator"
    step_up_level: StepUpLevel = StepUpLevel.NONE
    step_up_expires_at: datetime | None = None
    trusted_device: bool = False
    trusted_device_expires_at: datetime | None = None
    locked_until: datetime | None = None
    failed_attempts: int = 0
    last_step_up: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class StepUpChallenge:
    """Step-up challenge for privileged operations."""

    challenge_id: str
    operation: str
    status: StepUpStatus
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None


@dataclass
class TrustedDevice:
    """Trusted device marker."""

    device_id: str
    created_at: datetime
    expires_at: datetime | None = None
    last_used: datetime | None = None
    revoked: bool = False


STEP_UP_DURATION_SECONDS = 900  # 15 minutes
TRUSTED_DEVICE_DURATION_SECONDS = 86400  # 24 hours
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes


class LocalIdentityManager:
    """Manages local identity, step-up, and trusted devices."""

    def __init__(self, db_path: Path = IDENTITY_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize identity database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identity (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_up_challenges (
                    challenge_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    completed_at TEXT,
                    failure_reason TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trusted_devices (
                    device_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_used TEXT,
                    revoked INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def _get_setting(self, key: str) -> str | None:
        """Get a setting from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM identity WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _set_setting(self, key: str, value: str) -> None:
        """Set a setting in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO identity (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def is_step_up_active(self) -> bool:
        """Check if step-up is currently active."""
        expires = self._get_setting(STEP_UP_SESSION_KEY)
        if expires is None:
            return False

        try:
            expires_at = datetime.fromisoformat(expires)
            return expires_at > datetime.now(UTC)
        except (ValueError, TypeError):
            return False

    def get_step_up_expires_at(self) -> datetime | None:
        """Get step-up expiration time."""
        expires = self._get_setting(STEP_UP_SESSION_KEY)
        if expires is None:
            return None

        try:
            return datetime.fromisoformat(expires)
        except (ValueError, TypeError):
            return None

    def start_step_up(self) -> str:
        """Start a step-up challenge. Returns challenge ID."""
        if self.is_locked():
            raise PermissionError("Identity is locked due to failed attempts")

        challenge_id = f"stepup-{secrets.token_hex(12)}"
        now = datetime.now(UTC)
        from datetime import timedelta

        expires = now + timedelta(seconds=STEP_UP_DURATION_SECONDS)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO step_up_challenges
                (challenge_id, operation, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    challenge_id,
                    "step_up",
                    StepUpStatus.PENDING.value,
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
            conn.commit()

        return challenge_id

    def complete_step_up(self, challenge_id: str, pin: str) -> bool:
        """Complete step-up with PIN verification."""
        from ai.settings_service import PINManager

        pm = PINManager()
        if not pm.is_pin_set():
            raise PermissionError("PIN not configured")

        if not pm.verify_pin(pin):
            self._record_failed_attempt()
            self._update_challenge_status(challenge_id, StepUpStatus.FAILED, "Invalid PIN")
            return False

        now = datetime.now(UTC)
        from datetime import timedelta

        expires = now + timedelta(seconds=STEP_UP_DURATION_SECONDS)
        self._set_setting(STEP_UP_SESSION_KEY, expires.isoformat())
        self._set_setting(IDENTITY_FAILED_ATTEMPTS, "0")

        self._update_challenge_status(challenge_id, StepUpStatus.SUCCESS)
        logger.info("Step-up completed successfully")
        return True

    def _update_challenge_status(
        self, challenge_id: str, status: StepUpStatus, failure_reason: str | None = None
    ) -> None:
        """Update challenge status."""
        with sqlite3.connect(self.db_path) as conn:
            if status == StepUpStatus.SUCCESS:
                conn.execute(
                    "UPDATE step_up_challenges SET status = ?, "
                    "completed_at = ? WHERE challenge_id = ?",
                    (status.value, datetime.now(UTC).isoformat(), challenge_id),
                )
            elif failure_reason:
                conn.execute(
                    "UPDATE step_up_challenges SET status = ?, "
                    "failure_reason = ? WHERE challenge_id = ?",
                    (status.value, failure_reason, challenge_id),
                )
            else:
                conn.execute(
                    "UPDATE step_up_challenges SET status = ? WHERE challenge_id = ?",
                    (status.value, challenge_id),
                )
            conn.commit()

    def _record_failed_attempt(self) -> None:
        """Record a failed step-up attempt."""
        attempts = int(self._get_setting(IDENTITY_FAILED_ATTEMPTS) or "0") + 1
        self._set_setting(IDENTITY_FAILED_ATTEMPTS, str(attempts))

        if attempts >= MAX_FAILED_ATTEMPTS:
            from datetime import timedelta

            lockout = datetime.now(UTC) + timedelta(seconds=LOCKOUT_DURATION_SECONDS)
            self._set_setting(IDENTITY_LOCKED_UNTIL, lockout.isoformat())
            logger.warning(f"Identity locked after {attempts} failed attempts")

    def is_locked(self) -> bool:
        """Check if identity is locked due to failed attempts."""
        locked_until = self._get_setting(IDENTITY_LOCKED_UNTIL)
        if locked_until is None:
            return False

        try:
            lock_time = datetime.fromisoformat(locked_until)
            return lock_time > datetime.now(UTC)
        except (ValueError, TypeError):
            return False

    def get_locked_until(self) -> datetime | None:
        """Get lockout expiration time."""
        locked_until = self._get_setting(IDENTITY_LOCKED_UNTIL)
        if locked_until is None:
            return None

        try:
            return datetime.fromisoformat(locked_until)
        except (ValueError, TypeError):
            return None

    def get_failed_attempts(self) -> int:
        """Get number of failed attempts."""
        return int(self._get_setting(IDENTITY_FAILED_ATTEMPTS) or "0")

    def create_trusted_device(self) -> str:
        """Create a new trusted device marker. Returns device ID."""
        if self.is_locked():
            raise PermissionError("Cannot create trusted device while locked")

        device_id = f"device-{secrets.token_hex(16)}"
        now = datetime.now(UTC)
        from datetime import timedelta

        expires = now + timedelta(seconds=TRUSTED_DEVICE_DURATION_SECONDS)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO trusted_devices
                (device_id, created_at, expires_at) VALUES (?, ?, ?)""",
                (device_id, now.isoformat(), expires.isoformat()),
            )
            conn.commit()

        return device_id

    def is_device_trusted(self, device_id: str) -> bool:
        """Check if a device is trusted and not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT expires_at, revoked FROM trusted_devices WHERE device_id = ?",
                (device_id,),
            )
            row = cursor.fetchone()
            if not row or row[1] == 1:
                return False

            try:
                expires = datetime.fromisoformat(row[0])
                return expires > datetime.now(UTC)
            except (ValueError, TypeError):
                return False

    def revoke_trusted_device(self, device_id: str) -> bool:
        """Revoke a trusted device."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT revoked FROM trusted_devices WHERE device_id = ?", (device_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            conn.execute("UPDATE trusted_devices SET revoked = 1 WHERE device_id = ?", (device_id,))
            conn.commit()
        return True

    def get_trusted_devices(self) -> list[TrustedDevice]:
        """Get all active trusted devices."""
        devices = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT device_id, created_at, expires_at, last_used, revoked "
                "FROM trusted_devices WHERE revoked = 0"
            )
            for row in cursor:
                try:
                    expires_at = datetime.fromisoformat(row[2]) if row[2] else None
                    if expires_at and expires_at < datetime.now(UTC):
                        continue
                    devices.append(
                        TrustedDevice(
                            device_id=row[0],
                            created_at=datetime.fromisoformat(row[1]),
                            expires_at=expires_at,
                            last_used=datetime.fromisoformat(row[3]) if row[3] else None,
                        )
                    )
                except (ValueError, TypeError):
                    continue
        return devices

    def clear_step_up(self) -> None:
        """Clear step-up session."""
        self._set_setting(STEP_UP_SESSION_KEY, "")

    def get_identity_state(self) -> LocalIdentity:
        """Get current identity state."""
        return LocalIdentity(
            operator_id="local_operator",
            step_up_level=StepUpLevel.STEP_UP if self.is_step_up_active() else StepUpLevel.NONE,
            step_up_expires_at=self.get_step_up_expires_at(),
            trusted_device=len(self.get_trusted_devices()) > 0,
            locked_until=self.get_locked_until(),
            failed_attempts=self.get_failed_attempts(),
        )


_identity_manager: LocalIdentityManager | None = None


def get_identity_manager() -> LocalIdentityManager:
    """Get or create global identity manager."""
    global _identity_manager
    if _identity_manager is None:
        _identity_manager = LocalIdentityManager()
    return _identity_manager


def require_step_up(operation: str) -> dict:
    """Require step-up for a privileged operation."""
    manager = get_identity_manager()

    if manager.is_locked():
        locked_until = manager.get_locked_until()
        return {
            "allowed": False,
            "error": "Identity locked",
            "error_code": "identity_locked",
            "locked_until": locked_until.isoformat() if locked_until else None,
            "failed_attempts": manager.get_failed_attempts(),
            "operator_action": "Wait for lockout to expire or recover via system reset",
        }

    if manager.is_step_up_active():
        return {
            "allowed": True,
            "step_up_active": True,
            "expires_at": manager.get_step_up_expires_at().isoformat(),
        }

    challenge_id = manager.start_step_up()
    return {
        "allowed": False,
        "error": "Step-up required",
        "error_code": "step_up_required",
        "challenge_id": challenge_id,
        "operation": operation,
        "operator_action": "Enter your PIN to complete step-up for this privileged operation",
    }


def complete_step_up(challenge_id: str, pin: str) -> dict:
    """Complete step-up with PIN."""
    manager = get_identity_manager()

    try:
        success = manager.complete_step_up(challenge_id, pin)
        if success:
            return {
                "allowed": True,
                "step_up_active": True,
                "expires_at": manager.get_step_up_expires_at().isoformat(),
            }
        return {
            "allowed": False,
            "error": "Invalid PIN",
            "error_code": "step_up_failed",
            "failed_attempts": manager.get_failed_attempts(),
            "locked_until": manager.get_locked_until().isoformat() if manager.is_locked() else None,
        }
    except PermissionError as e:
        return {"allowed": False, "error": str(e), "error_code": "step_up_error"}


def check_privileged_operation(operation: str, require_step_up_flag: bool = True) -> dict:
    """Check if a privileged operation can proceed.

    Integrates with P127 policy engine:
    - If policy says DENY, step-up cannot override
    - If policy says ALLOW but operation is privileged, require step-up
    - If policy says APPROVAL_REQUIRED, still need approval after step-up
    """
    from ai.mcp_bridge.policy import PolicyDecision, evaluate_tool_policy

    policy_result = evaluate_tool_policy(operation)

    if policy_result.decision == PolicyDecision.DENY:
        return {
            "allowed": False,
            "error": f"Operation denied by policy: {policy_result.reason}",
            "error_code": "policy_denied",
            "policy_decision": policy_result.decision.value,
        }

    if policy_result.decision == PolicyDecision.APPROVAL_REQUIRED:
        return {
            "allowed": False,
            "error": f"Operation requires approval: {policy_result.reason}",
            "error_code": "approval_required",
            "policy_decision": policy_result.decision.value,
            "requires_step_up": require_step_up_flag,
            "requires_approval": True,
        }

    if require_step_up_flag and (
        policy_result.metadata
        and (
            policy_result.metadata.secret_access
            or policy_result.metadata.shell_access
            or policy_result.metadata.provider_mutation
            or policy_result.metadata.destructive
            or policy_result.metadata.risk_tier.value in ("high", "critical")
        )
    ):
        return require_step_up(operation)

    return {"allowed": True, "policy_decision": policy_result.decision.value}
