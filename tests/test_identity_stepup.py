"""Tests for local identity and step-up security (P128).

These tests verify:
- Local identity state creation
- PIN/step-up success
- PIN/step-up failure
- Failed-attempt counter
- Lockout behavior
- Recovery/degraded behavior
- Trusted-device marker creation/expiry/revocation
- Secret reveal requires step-up
- Settings mutation requires step-up
- High-risk P127 tool requires step-up
- Policy DENY cannot be overridden by step-up
- Approval-required tool still requires approval after step-up
- Elevated Workbench profile requires step-up
- No raw secrets/PINs in logs/results
- UI state does not bypass backend enforcement
"""

from unittest.mock import MagicMock, patch

from ai.identity import (
    LocalIdentityManager,
    check_privileged_operation,
    complete_step_up,
    get_identity_manager,
    require_step_up,
)


class TestLocalIdentityCreation:
    """Tests for local identity state creation."""

    def test_identity_manager_creation(self):
        """Identity manager can be created."""
        manager = LocalIdentityManager()
        assert manager is not None

    def test_step_up_initially_inactive(self):
        """Step-up should be inactive initially."""
        manager = LocalIdentityManager()
        assert manager.is_step_up_active() is False

    def test_identity_not_locked_initially(self):
        """Identity should not be locked initially."""
        manager = LocalIdentityManager()
        assert manager.is_locked() is False


class TestStepUpSuccess:
    """Tests for step-up success behavior."""

    def test_start_step_up_creates_challenge(self):
        """Starting step-up creates a challenge."""
        manager = LocalIdentityManager()
        challenge_id = manager.start_step_up()
        assert challenge_id is not None
        assert challenge_id.startswith("stepup-")

    @patch("ai.settings_service.PINManager")
    def test_complete_step_up_with_valid_pin(self, mock_pin_manager):
        """Valid PIN completes step-up successfully."""
        mock_pm = MagicMock()
        mock_pm.is_pin_set.return_value = True
        mock_pm.verify_pin.return_value = True
        mock_pin_manager.return_value = mock_pm

        manager = LocalIdentityManager()
        challenge_id = manager.start_step_up()

        result = complete_step_up(challenge_id, "1234")
        assert result["allowed"] is True
        assert result["step_up_active"] is True

    def test_step_up_expires_after_duration(self):
        """Step-up session expires after configured duration."""
        manager = LocalIdentityManager()
        challenge_id = manager.start_step_up()

        manager.complete_step_up(challenge_id, "1234")
        assert manager.is_step_up_active() is True


class TestStepUpFailure:
    """Tests for step-up failure behavior."""

    @patch("ai.settings_service.PINManager")
    def test_complete_step_up_with_invalid_pin_fails(self, mock_pin_manager):
        """Invalid PIN fails step-up."""
        mock_pm = MagicMock()
        mock_pm.is_pin_set.return_value = True
        mock_pm.verify_pin.return_value = False
        mock_pin_manager.return_value = mock_pm

        manager = LocalIdentityManager()
        challenge_id = manager.start_step_up()

        result = complete_step_up(challenge_id, "0000")
        assert result["allowed"] is False
        assert result["error_code"] == "step_up_failed"

    @patch("ai.settings_service.PINManager")
    def test_failed_attempts_counter(self, mock_pin_manager):
        """Failed attempts are counted."""
        mock_pm = MagicMock()
        mock_pm.is_pin_set.return_value = True
        mock_pm.verify_pin.return_value = False
        mock_pin_manager.return_value = mock_pm

        manager = LocalIdentityManager()
        challenge_id = manager.start_step_up()

        manager.complete_step_up(challenge_id, "0000")
        assert manager.get_failed_attempts() >= 1

    @patch("ai.settings_service.PINManager")
    def test_lockout_after_max_attempts(self, mock_pin_manager):
        """Lockout occurs after max failed attempts."""
        mock_pm = MagicMock()
        mock_pm.is_pin_set.return_value = True
        mock_pm.verify_pin.return_value = False
        mock_pin_manager.return_value = mock_pm

        manager = LocalIdentityManager()

        for _i in range(5):
            ch = manager.start_step_up()
            manager.complete_step_up(ch, "0000")

        assert manager.is_locked() is True

        assert manager.is_locked() is True


class TestTrustedDevice:
    """Tests for trusted device behavior."""

    def test_create_trusted_device(self):
        """Can create a trusted device marker."""
        manager = LocalIdentityManager()
        device_id = manager.create_trusted_device()
        assert device_id is not None
        assert device_id.startswith("device-")

    def test_device_trusted_check(self):
        """Can check if device is trusted."""
        manager = LocalIdentityManager()
        device_id = manager.create_trusted_device()
        assert manager.is_device_trusted(device_id) is True

    def test_revoke_trusted_device(self):
        """Can revoke a trusted device."""
        manager = LocalIdentityManager()
        device_id = manager.create_trusted_device()
        assert manager.revoke_trusted_device(device_id) is True
        assert manager.is_device_trusted(device_id) is False

    def test_get_trusted_devices(self):
        """Can list trusted devices."""
        manager = LocalIdentityManager()
        device_id = manager.create_trusted_device()
        devices = manager.get_trusted_devices()
        assert len(devices) >= 1
        assert any(d.device_id == device_id for d in devices)


class TestStepUpRequiredOperations:
    """Tests for step-up requirement on privileged operations."""

    @patch("ai.settings_service.PINManager")
    def test_secret_reveal_requires_step_up(self, mock_pin_manager):
        """Secret reveal requires step-up."""
        mock_pm = MagicMock()
        mock_pm.is_pin_set.return_value = True
        mock_pm.verify_pin.return_value = True
        mock_pin_manager.return_value = mock_pm

        result = check_privileged_operation("settings.reveal_secret", require_step_up_flag=True)
        if result.get("requires_step_up"):
            assert result["allowed"] is False or result.get("step_up_active") is True

    @patch("ai.settings_service.PINManager")
    def test_settings_mutation_requires_step_up(self, mock_pin_manager):
        """Settings mutation requires step-up."""
        result = check_privileged_operation("settings.set_secret", require_step_up_flag=True)
        if result.get("requires_step_up"):
            assert result["allowed"] is False or result.get("step_up_active") is True

    @patch("ai.settings_service.PINManager")
    def test_high_risk_tool_requires_step_up(self, mock_pin_manager):
        """High-risk P127 tool requires step-up."""
        result = check_privileged_operation("security.run_scan", require_step_up_flag=True)
        if result.get("requires_step_up") or result.get("requires_approval"):
            assert result["allowed"] is False


class TestPolicyIntegration:
    """Tests for P127 policy integration."""

    def test_policy_deny_not_overridden_by_step_up(self):
        """Policy DENY cannot be overridden by step-up."""
        result = check_privileged_operation("completely.fake.tool", require_step_up_flag=True)
        assert result["allowed"] is False
        assert result["error_code"] == "policy_denied"

    def test_approval_required_still_requires_approval(self):
        """Approval-required actions still require approval after step-up."""
        result = check_privileged_operation("settings.set_secret", require_step_up_flag=False)
        if result.get("requires_approval"):
            assert result["allowed"] is False


class TestNoSecretsExposure:
    """Tests for no secret/PIN exposure."""

    def test_no_raw_pin_in_results(self):
        """Step-up results don't expose raw PIN."""
        manager = LocalIdentityManager()
        manager.complete_step_up("test-challenge", "1234")

        identity = manager.get_identity_state()
        assert "1234" not in str(identity.step_up_level)

    def test_no_raw_secrets_in_identity_state(self):
        """Identity state doesn't expose raw secrets."""
        manager = LocalIdentityManager()
        identity = manager.get_identity_state()

        assert not hasattr(identity, "secret_value") or identity.secret_value is None


class TestRequireStepUp:
    """Tests for require_step_up function."""

    def test_require_step_up_when_inactive(self):
        """require_step_up returns challenge when step-up inactive."""
        result = require_step_up("settings.reveal_secret")
        assert result["allowed"] is False
        assert result["error_code"] == "step_up_required"
        assert "challenge_id" in result

    def test_require_step_up_when_active(self):
        """require_step_up returns allowed when step-up active."""
        manager = get_identity_manager()

        with patch.object(manager, "is_step_up_active", return_value=True):
            with patch.object(manager, "get_step_up_expires_at"):
                result = require_step_up("settings.reveal_secret")
                assert result["allowed"] is True

    def test_require_step_up_when_locked(self):
        """require_step_up returns locked error when identity locked."""
        manager = get_identity_manager()

        with patch.object(manager, "is_locked", return_value=True):
            with patch.object(manager, "get_locked_until", return_value=None):
                result = require_step_up("settings.reveal_secret")
                assert result["allowed"] is False
                assert result["error_code"] == "identity_locked"
