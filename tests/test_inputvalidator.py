"""Tests for InputValidator - Phase 19 validation behaviors."""

import pytest

from ai.security.inputvalidator import InputValidator


class TestInputValidatorImport:
    """Basic import and instantiation tests."""

    def test_import(self):
        assert InputValidator is not None

    def test_from_default_config(self):
        v = InputValidator.from_default_config()
        assert v is not None
        assert v._max_length == 10000

    def test_from_config_dict(self):
        v = InputValidator.from_config_dict({"max_input_length": 500})
        assert v._max_length == 500


class TestBasicValidation:
    """Basic validation smoke tests."""

    def test_clean_input_passes(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("normal text string")
        assert ok is True
        assert violations == []

    def test_clean_hash_passes(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        assert ok is True


class TestSQLInjection:
    """SQL injection pattern detection."""

    @pytest.mark.parametrize(
        "payload",
        [
            "test' OR 1=1 --",
            "test' OR '1'='1",
            "admin'--",
            "UNION SELECT * FROM users",
            "DROP TABLE users",
            "' OR 1=1",
            "; DROP TABLE--",
        ],
    )
    def test_sql_injection_blocked(self, payload):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input(payload)
        assert ok is False
        assert len(violations) > 0

    def test_normal_sql_keywords_pass(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("SELECT name FROM users WHERE id = 1")
        assert ok is True


class TestCommandInjection:
    """Command injection pattern detection."""

    @pytest.mark.parametrize(
        "payload",
        [
            "test; rm -rf",
            "test && ls",
            "test || cat /etc/passwd",
            "test | grep",
            "$(whoami)",
            "`id`",
            "echo $HOME",
        ],
    )
    def test_command_injection_blocked(self, payload):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input(payload)
        assert ok is False
        assert "command_injection_markers" in violations or "forbidden_pattern" in violations

    def test_normal_command_words_pass(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("run the command to check status")
        assert ok is True


class TestForbiddenPatterns:
    """Destructive command patterns."""

    @pytest.mark.parametrize(
        "payload",
        [
            "rm -rf /",
            "mkfs /dev/sda",
            "dd if=/dev/zero of=/dev/sda",
            "chmod 777 /tmp",
        ],
    )
    def test_forbidden_pattern_blocked(self, payload):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input(payload)
        assert ok is False
        assert "forbidden_pattern" in violations


class TestPathTraversal:
    """Path traversal detection."""

    @pytest.mark.parametrize(
        "path",
        [
            "../../etc/passwd",
            "/etc/passwd",
            "/proc/self/cmdline",
            "/boot/vmlinuz",
            "~/../../etc/passwd",
        ],
    )
    def test_path_traversal_blocked(self, path):
        v = InputValidator.from_default_config()
        ok = v.validate_path(path)
        assert ok is False

    def test_allowed_paths_pass(self):
        v = InputValidator.from_default_config()
        ok = v.validate_path("/var/home/lch/projects/bazzite-laptop/README.md")
        assert ok is True
        ok = v.validate_path("/var/log/system-health/test.log")
        assert ok is True


class TestSecretRedaction:
    """Secret/API key redaction."""

    def test_openai_key_redacted(self):
        v = InputValidator.from_default_config()
        text = "API key: sk-1234567890abcdefghijklmnop"
        redacted = v.redact_secrets(text)
        assert "sk-" not in redacted or "REDACTED" in redacted

    def test_github_token_redacted(self):
        v = InputValidator.from_default_config()
        text = "token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        redacted = v.redact_secrets(text)
        assert "ghp_" not in redacted or "REDACTED" in redacted

    def test_generic_api_key_redacted(self):
        v = InputValidator.from_default_config()
        text = "api_key=mysecretkey123"
        redacted = v.redact_secrets(text)
        assert "mysecretkey123" not in redacted

    def test_bearer_token_redacted(self):
        v = InputValidator.from_default_config()
        text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        redacted = v.redact_secrets(text)
        assert "REDACTED" in redacted

    def test_redaction_preserves_context(self):
        v = InputValidator.from_default_config()
        text = "Please use API key sk-abc123 for testing"
        redacted = v.redact_secrets(text)
        assert "Please use" in redacted
        assert "for testing" in redacted


class TestMaxInputLength:
    """Max input length enforcement."""

    def test_long_input_rejected(self):
        v = InputValidator.from_config_dict({"max_input_length": 100})
        long_text = "x" * 200
        ok, violations = v.validate_input(long_text)
        assert ok is False
        assert any("max_input_length" in v for v in violations)

    def test_short_input_passes(self):
        v = InputValidator.from_config_dict({"max_input_length": 100})
        short_text = "x" * 50
        ok, violations = v.validate_input(short_text)
        assert ok is True


class TestHighRiskTools:
    """High-risk tool behavior."""

    def test_high_risk_tool_flagged(self):
        v = InputValidator.from_default_config()
        args = {"file_path": "../../etc/passwd"}
        ok, violations = v.validate_tool_args("security.sandbox_submit", args)
        assert ok is False

    def test_normal_tool_passes(self):
        v = InputValidator.from_default_config()
        args = {"query": "normal search"}
        ok, violations = v.validate_tool_args("system.disk_usage", args)
        assert ok is True


class TestToolArgsValidation:
    """Tool argument validation."""

    def test_string_arg_validated(self):
        v = InputValidator.from_default_config()
        args = {"query": "test' OR 1=1 --"}
        ok, violations = v.validate_tool_args("system.disk_usage", args)
        assert ok is False

    def test_path_arg_validated(self):
        v = InputValidator.from_default_config()
        args = {"path": "../../etc/passwd"}
        ok, violations = v.validate_tool_args("security.run_scan", args)
        assert ok is False

    def test_nested_dict_validated(self):
        v = InputValidator.from_default_config()
        args = {"nested": {"value": "test; rm -rf"}}
        ok, violations = v.validate_tool_args("system.disk_usage", args)
        assert ok is False


class TestSafetyRulesConfig:
    """Safety rules configuration loading."""

    def test_config_loaded(self):
        v = InputValidator.from_default_config()
        assert v._max_length == 10000
        assert v._high_risk is not None
        assert "security.sandbox_submit" in v._high_risk
        assert v._log_violations is True
        assert v._block is True

    def test_custom_config(self):
        config = {
            "max_input_length": 5000,
            "high_risk_tools": ["custom.tool"],
            "log_violations": False,
        }
        v = InputValidator.from_config_dict(config)
        assert v._max_length == 5000
        assert "custom.tool" in v._high_risk
        assert v._log_violations is False


class TestReadOnlyTools:
    """Read-only tools validation behavior."""

    def test_read_only_tools_validated_by_default(self):
        v = InputValidator.from_config_dict({"read_only_tools_skip_validation": False})
        args = {"query": "test' OR 1=1 --"}
        ok, violations = v.validate_tool_args("system.disk_usage", args)
        assert ok is False


class TestEdgeCases:
    """Edge case handling."""

    def test_empty_input_passes(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("")
        assert ok is True

    def test_whitespace_only_passes(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("   ")
        assert ok is True

    def test_none_input_handled(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("None")
        assert ok is True

    def test_unicode_input_passes(self):
        v = InputValidator.from_default_config()
        ok, violations = v.validate_input("Héllo Wörld 🚀")
        assert ok is True

    def test_path_with_double_dot_mid_string(self):
        v = InputValidator.from_default_config()
        ok = v.validate_path("/home/user/../etc/passwd")
        assert ok is False
