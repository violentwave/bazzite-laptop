"""Settings and Secrets Service with PIN-gated access control.

P81 — PIN-Gated Settings + Secrets Service

Provides:
- PIN authentication and verification
- Masked secret management
- Audit logging for all sensitive operations
- Atomic writes to keys.env
- Provider state refresh hooks

Security model:
- PIN is hashed with bcrypt and stored in ~/.config/bazzite-ai/settings.db
- Secrets are never returned in full to the browser
- All reveal/update operations require fresh PIN verification
- Audit log tracks: unlock, reveal, replace, add, delete, failure
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from ai.config import APP_NAME, KEYS_ENV, SECURITY_DIR

logger = logging.getLogger(APP_NAME)

# ── Constants ────────────────────────────────────────────────────────────────

SETTINGS_DB = Path.home() / ".config" / "bazzite-ai" / "settings.db"
AUDIT_LOG_FILE = SECURITY_DIR / "settings-audit.jsonl"

PIN_HASH_KEY = "pin_hash"
PIN_SALT_KEY = "pin_salt"
PIN_ATTEMPTS_KEY = "pin_attempts"
PIN_LOCKED_UNTIL_KEY = "pin_locked_until"

MAX_PIN_ATTEMPTS = 3
PIN_LOCKOUT_DURATION = 300  # 5 minutes in seconds

# Masked display: first 4 + ... + last 4
MASKED_LENGTH = 4


class AuditAction(Enum):
    """Types of actions that are audited."""

    UNLOCK = "unlock"
    REVEAL = "reveal"
    REPLACE = "replace"
    ADD = "add"
    DELETE = "delete"
    FAILURE = "failure"
    LOCKOUT = "lockout"


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: str
    action: str
    key_name: str | None
    success: bool
    details: str | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "key_name": self.key_name,
            "success": self.success,
            "details": self.details,
        }


@dataclass
class SecretEntry:
    """A secret with its metadata."""

    name: str
    value: str | None  # None if not revealed
    masked_value: str
    category: str
    last_modified: str | None
    is_set: bool


# ── PIN Management ───────────────────────────────────────────────────────────


class PINManager:
    """Manages PIN authentication with bcrypt-like hashing."""

    def __init__(self, db_path: Path = SETTINGS_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the settings database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def _hash_pin(self, pin: str, salt: str | None = None) -> tuple[str, str]:
        """Hash a PIN with PBKDF2. Returns (hash, salt)."""
        if salt is None:
            salt = secrets.token_hex(16)

        # Use PBKDF2 with SHA256
        hash_value = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # iterations
        ).hex()

        return hash_value, salt

    def _get_setting(self, key: str) -> str | None:
        """Get a setting from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _set_setting(self, key: str, value: str) -> None:
        """Set a setting in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def is_pin_set(self) -> bool:
        """Check if a PIN has been configured."""
        return self._get_setting(PIN_HASH_KEY) is not None

    def setup_pin(self, pin: str) -> bool:
        """Set up a new PIN. Returns True if successful."""
        if len(pin) < 4 or len(pin) > 6:
            raise ValueError("PIN must be 4-6 digits")

        if not pin.isdigit():
            raise ValueError("PIN must contain only digits")

        pin_hash, salt = self._hash_pin(pin)
        self._set_setting(PIN_HASH_KEY, pin_hash)
        self._set_setting(PIN_SALT_KEY, salt)
        self._set_setting(PIN_ATTEMPTS_KEY, "0")
        self._set_setting(PIN_LOCKED_UNTIL_KEY, "0")

        logger.info("PIN setup completed")
        return True

    def verify_pin(self, pin: str) -> bool:
        """Verify a PIN. Handles lockout logic."""
        # Check if locked
        locked_until = int(self._get_setting(PIN_LOCKED_UNTIL_KEY) or "0")
        if locked_until > time.time():
            remaining = locked_until - time.time()
            logger.warning("PIN verification blocked: locked for %d more seconds", remaining)
            return False

        # Get stored hash and salt
        stored_hash = self._get_setting(PIN_HASH_KEY)
        salt = self._get_setting(PIN_SALT_KEY)

        if not stored_hash or not salt:
            logger.error("PIN not configured")
            return False

        # Hash provided PIN and compare
        provided_hash, _ = self._hash_pin(pin, salt)

        if hmac.compare_digest(provided_hash, stored_hash):
            # Success - reset attempts
            self._set_setting(PIN_ATTEMPTS_KEY, "0")
            return True
        else:
            # Failure - increment attempts
            attempts = int(self._get_setting(PIN_ATTEMPTS_KEY) or "0")
            attempts += 1
            self._set_setting(PIN_ATTEMPTS_KEY, str(attempts))

            if attempts >= MAX_PIN_ATTEMPTS:
                # Lock out
                lockout_until = int(time.time() + PIN_LOCKOUT_DURATION)
                self._set_setting(PIN_LOCKED_UNTIL_KEY, str(lockout_until))
                logger.warning("PIN locked out due to %d failed attempts", attempts)

            return False

    def get_lockout_status(self) -> dict:
        """Get current lockout status."""
        locked_until = int(self._get_setting(PIN_LOCKED_UNTIL_KEY) or "0")
        attempts = int(self._get_setting(PIN_ATTEMPTS_KEY) or "0")

        is_locked = locked_until > time.time()
        remaining = max(0, locked_until - time.time()) if is_locked else 0

        return {
            "is_locked": is_locked,
            "remaining_seconds": int(remaining),
            "failed_attempts": attempts,
            "max_attempts": MAX_PIN_ATTEMPTS,
        }

    def change_pin(self, old_pin: str, new_pin: str) -> bool:
        """Change the PIN. Requires old PIN verification."""
        if not self.verify_pin(old_pin):
            return False

        return self.setup_pin(new_pin)


# ── Audit Logging ───────────────────────────────────────────────────────────


class AuditLogger:
    """Logs all sensitive settings operations."""

    def __init__(self, log_file: Path = AUDIT_LOG_FILE):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: AuditAction,
        key_name: str | None = None,
        success: bool = True,
        details: str | None = None,
    ) -> None:
        """Log an audit entry."""
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            action=action.value,
            key_name=key_name,
            success=success,
            details=details,
        )

        # Append to JSONL file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        # Also log to standard logger
        log_msg = f"Audit: {action.value} key={key_name} success={success}"
        if success:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

    def get_recent(self, limit: int = 100) -> list[dict]:
        """Get recent audit entries."""
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        # Return most recent first
        return list(reversed(entries[-limit:]))


# ── Secrets Service ─────────────────────────────────────────────────────────


class SecretsService:
    """Manages secrets with masked display and PIN-gated access."""

    # Define which keys are considered secrets
    SECRET_KEYS = {
        "GROQ_API_KEY": "LLM Provider",
        "GEMINI_API_KEY": "LLM Provider",
        "MISTRAL_API_KEY": "LLM Provider",
        "OPENROUTER_API_KEY": "LLM Provider",
        "CEREBRAS_API_KEY": "LLM Provider",
        "ZAI_API_KEY": "LLM Provider",
        "ANTHROPIC_API_KEY": "LLM Provider",
        "COHERE_API_KEY": "LLM Provider",
        "HF_TOKEN": "Storage",
        "GITHUB_TOKEN": "Code Quality",
        "CLOUDFLARE_API_TOKEN": "LLM Provider",
        "DEEPSEEK_API_TOKEN": "LLM Provider",
        "VT_API_KEY": "Threat Intel",
        "ABUSEIPDB_KEY": "Threat Intel",
        "OTX_API_KEY": "Threat Intel",
        "NVD_API_KEY": "Threat Intel",
        "GREYNOISE_KEY": "Threat Intel",
        "HYBRID_ANALYSIS_KEY": "Threat Intel",
        "R2_ACCESS_KEY_ID": "Storage",
        "R2_SECRET_ACCESS_KEY": "Storage",
        "SENTRY_DSN": "Monitoring",
        "SEMGREP_APP_TOKEN": "Code Quality",
        "SLACK_BOT_TOKEN": "Integration",
        "SLACK_APP_TOKEN": "Integration",
        "SLACK_SIGNING_SECRET": "Integration",
        "NOTION_API_KEY": "Integration",
        "NOTION_PHASE_DATABASE_ID": "Integration",
    }

    def __init__(
        self,
        keys_env: Path = KEYS_ENV,
        pin_manager: PINManager | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        self.keys_env = keys_env
        self.pin_manager = pin_manager or PINManager()
        self.audit = audit_logger or AuditLogger()

    def _read_keys_file(self) -> dict[str, str]:
        """Read all keys from keys.env."""
        keys = {}
        if self.keys_env.exists():
            with open(self.keys_env, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if key:
                        keys[key] = value
        return keys

    def _write_keys_file(self, keys: dict[str, str]) -> None:
        """Write all keys to keys.env atomically."""
        import os
        import tempfile

        # Ensure directory exists
        self.keys_env.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file then rename for atomicity
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.keys_env.parent),
            prefix=".keys-env-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("# Bazzite AI API Keys - Auto-generated\n")
                f.write(f"# Last updated: {datetime.utcnow().isoformat()}\n\n")

                # Write keys grouped by category
                categories: dict[str, list[tuple[str, str]]] = {}
                for key, value in sorted(keys.items()):
                    category = self.SECRET_KEYS.get(key, "Other")
                    if category not in categories:
                        categories[category] = []
                    categories[category].append((key, value))

                for category, items in sorted(categories.items()):
                    f.write(f"# {category}\n")
                    for key, value in items:
                        f.write(f'{key}="{value}"\n')
                    f.write("\n")

            os.rename(tmp_path, str(self.keys_env))

            # Set restrictive permissions
            os.chmod(self.keys_env, 0o600)

        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _mask_value(self, value: str) -> str:
        """Create a masked version of a secret value."""
        if len(value) <= 8:
            return "****"
        return value[:MASKED_LENGTH] + "..." + value[-MASKED_LENGTH:]

    def list_secrets(self, include_values: bool = False) -> list[SecretEntry]:
        """List all secrets. If include_values is False, returns masked values."""
        keys = self._read_keys_file()
        entries = []

        for key_name, category in self.SECRET_KEYS.items():
            value = keys.get(key_name)
            is_set = value is not None and value != ""

            entry = SecretEntry(
                name=key_name,
                value=value if include_values else None,
                masked_value=self._mask_value(value) if is_set else "not set",
                category=category,
                last_modified=None,  # Could track this with file stats
                is_set=is_set,
            )
            entries.append(entry)

        return entries

    def get_secret(self, key_name: str, pin: str) -> SecretEntry | None:
        """Get a single secret with full value (requires PIN)."""
        # Verify PIN
        if not self.pin_manager.verify_pin(pin):
            self.audit.log(
                AuditAction.REVEAL, key_name, success=False, details="PIN verification failed"
            )
            return None

        keys = self._read_keys_file()
        value = keys.get(key_name)

        if value is None:
            self.audit.log(AuditAction.REVEAL, key_name, success=False, details="Key not found")
            return None

        entry = SecretEntry(
            name=key_name,
            value=value,
            masked_value=self._mask_value(value),
            category=self.SECRET_KEYS.get(key_name, "Other"),
            last_modified=None,
            is_set=True,
        )

        self.audit.log(AuditAction.REVEAL, key_name, success=True)
        return entry

    def set_secret(self, key_name: str, value: str, pin: str) -> bool:
        """Set or update a secret (requires PIN)."""
        # Verify PIN
        if not self.pin_manager.verify_pin(pin):
            self.audit.log(
                AuditAction.REPLACE if key_name in self.SECRET_KEYS else AuditAction.ADD,
                key_name,
                success=False,
                details="PIN verification failed",
            )
            return False

        # Read current keys
        keys = self._read_keys_file()

        # Determine action
        action = AuditAction.REPLACE if key_name in keys and keys[key_name] else AuditAction.ADD

        # Update key
        keys[key_name] = value

        # Write back
        self._write_keys_file(keys)

        self.audit.log(action, key_name, success=True)

        # Trigger provider refresh hook (placeholder for P82)
        self._trigger_provider_refresh(key_name)

        return True

    def delete_secret(self, key_name: str, pin: str) -> bool:
        """Delete a secret (requires PIN)."""
        # Verify PIN
        if not self.pin_manager.verify_pin(pin):
            self.audit.log(
                AuditAction.DELETE, key_name, success=False, details="PIN verification failed"
            )
            return False

        # Read current keys
        keys = self._read_keys_file()

        if key_name not in keys:
            self.audit.log(AuditAction.DELETE, key_name, success=False, details="Key not found")
            return False

        # Delete key
        del keys[key_name]

        # Write back
        self._write_keys_file(keys)

        self.audit.log(AuditAction.DELETE, key_name, success=True)

        # Trigger provider refresh hook (placeholder for P82)
        self._trigger_provider_refresh(key_name)

        return True

    def _trigger_provider_refresh(self, key_name: str) -> None:
        """Trigger a provider refresh when LLM keys change.

        Calls P82 provider_service to refresh provider discovery.
        """
        llm_keys = {
            "GROQ_API_KEY",
            "GEMINI_API_KEY",
            "MISTRAL_API_KEY",
            "OPENROUTER_API_KEY",
            "CEREBRAS_API_KEY",
            "ZAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "COHERE_API_KEY",
            "CLOUDFLARE_API_TOKEN",
            "DEEPSEEK_API_TOKEN",
        }

        if key_name in llm_keys:
            logger.info("Provider refresh triggered for %s", key_name)
            try:
                from ai.provider_service import trigger_provider_refresh

                trigger_provider_refresh(key_name)
            except Exception as e:
                logger.warning("Provider refresh failed: %s", e)


# ── Public API ──────────────────────────────────────────────────────────────


# Singleton instances
_pin_manager: PINManager | None = None
_secrets_service: SecretsService | None = None
_audit_logger: AuditLogger | None = None


def get_pin_manager() -> PINManager:
    """Get or create the PIN manager singleton."""
    global _pin_manager
    if _pin_manager is None:
        _pin_manager = PINManager()
    return _pin_manager


def get_secrets_service() -> SecretsService:
    """Get or create the secrets service singleton."""
    global _secrets_service
    if _secrets_service is None:
        _secrets_service = SecretsService(
            pin_manager=get_pin_manager(),
            audit_logger=get_audit_logger(),
        )
    return _secrets_service


def get_audit_logger() -> AuditLogger:
    """Get or create the audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def unlock_settings(pin: str) -> dict:
    """Attempt to unlock settings with PIN.

    Returns status dict with success, lockout info, and audit trail.
    """
    pm = get_pin_manager()
    audit = get_audit_logger()

    # Check lockout first
    lockout = pm.get_lockout_status()
    if lockout["is_locked"]:
        return {
            "success": False,
            "error": "PIN locked due to failed attempts",
            "lockout": lockout,
        }

    # Verify PIN
    success = pm.verify_pin(pin)

    if success:
        audit.log(AuditAction.UNLOCK, success=True)
        return {
            "success": True,
            "session_duration": 300,  # 5 minutes
            "lockout": pm.get_lockout_status(),
        }
    else:
        audit.log(AuditAction.UNLOCK, success=False)
        return {
            "success": False,
            "error": "Invalid PIN",
            "lockout": pm.get_lockout_status(),
        }
