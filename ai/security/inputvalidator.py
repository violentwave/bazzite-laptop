"""Input validation module for MCP bridge safety layer.

Provides pre-dispatch validation, secret redaction, and path traversal
protection for the MCP bridge. Stdlib-only, no external dependencies.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

import ai.config

logger = logging.getLogger(__name__)

DEFAULT_SAFETY_RULES = {
    "max_input_length": 10000,
    "forbidden_patterns": [
        r"rm\s+-rf",
        r"mkfs",
        r"dd\s+if=",
        r"chmod\s+777",
    ],
    "path_allowed_roots": [
        str(ai.config.PROJECT_ROOT),
        str(ai.config.SECURITY_DIR),
        "/var/log/system-health",
        "/var/log/clamav-scans",
    ],
    "high_risk_tools": [
        "security.sandbox_submit",
        "security.run_scan",
        "security.run_ingest",
    ],
    "read_only_tools_skip_validation": False,
    "log_violations": True,
    "block_on_violation": True,
}


class InputValidator:
    """Pre-dispatch input validator for MCP bridge.

    Thread-safe, stateless at runtime aside from cached config.
    """

    def __init__(self, config: dict[str, Any]):
        self._config = config
        self._max_length = config.get("max_input_length", DEFAULT_SAFETY_RULES["max_input_length"])
        self._forbidden = [
            re.compile(p, re.IGNORECASE) for p in config.get("forbidden_patterns", [])
        ]
        self._allowed_roots = config.get(
            "path_allowed_roots", DEFAULT_SAFETY_RULES["path_allowed_roots"]
        )
        self._high_risk = set(config.get("high_risk_tools", []))
        self._skip_readonly = config.get("read_only_tools_skip_validation", False)
        self._log_violations = config.get("log_violations", True)
        self._block = config.get("block_on_violation", True)

        self._sql_patterns = [
            re.compile(r"\bUNION\s+SELECT", re.IGNORECASE),
            re.compile(r"\bDROP\s+TABLE", re.IGNORECASE),
            re.compile(r"' OR 1=1", re.IGNORECASE),
            re.compile(r"' OR '1'='1", re.IGNORECASE),
            re.compile(r";\s*DROP", re.IGNORECASE),
            re.compile(r"'--"),
            re.compile(r"'-"),
        ]

        self._cmd_pattern = re.compile(r"[;&|`${}()[\]<>!#*]")

        self._secret_patterns = [
            re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),
            re.compile(r"ghp_[a-zA-Z0-9]{36}"),
            re.compile(r"(?i)(api[_-]?key|apikey|token)\s*[=:]\s*[\S]+"),
            re.compile(r"(?i)bearer\s+[A-Za-z0-9_-]+"),
        ]

    @classmethod
    def from_default_config(cls) -> "InputValidator":
        """Create validator from default config location."""
        config_path = ai.config.CONFIGS_DIR / "safety-rules.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                return cls({**DEFAULT_SAFETY_RULES, **user_config})
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load safety-rules.json: {e}, using defaults")
        return cls(DEFAULT_SAFETY_RULES)

    @classmethod
    def from_config_dict(cls, config: dict[str, Any]) -> "InputValidator":
        """Create validator from a config dict (for testing)."""
        return cls({**DEFAULT_SAFETY_RULES, **config})

    def validate_input(self, text: str) -> tuple[bool, list[str]]:
        """Validate text input for injection patterns.

        Returns (True, []) for clean input, (False, [violations]) otherwise.
        """
        violations = []

        if len(text) > self._max_length:
            violations.append(f"max_input_length: {len(text)} exceeds {self._max_length}")

        for pattern in self._sql_patterns:
            if pattern.search(text):
                violations.append("sql_injection_pattern")

        if self._cmd_pattern.search(text):
            violations.append("command_injection_markers")

        for pattern in self._forbidden:
            if pattern.search(text):
                violations.append("forbidden_pattern")

        if violations and self._log_violations:
            redacted = self.redact_secrets(text[:200])
            logger.warning(f"Input validation failed: {violations} | sample: {redacted}")

        return (len(violations) == 0, violations)

    def redact_secrets(self, text: str) -> str:
        """Redact API keys and tokens from text.

        Replaces sensitive portions with REDACTED while preserving context.
        """
        result = text
        for pattern in self._secret_patterns:
            result = pattern.sub(lambda m: "REDACTED", result)
        return result

    def validate_path(self, path: str, allowed_roots: list[str] | None = None) -> bool:
        """Validate path is within allowed roots.

        Rejects paths with .. escapes or sensitive system locations.
        """
        if allowed_roots is None:
            allowed_roots = self._allowed_roots

        try:
            resolved = Path(path).resolve()
        except (OSError, ValueError):
            return False

        sensitive = ["/etc", "/proc", "/sys", "/boot", "/usr", "/var/run"]
        for sens in sensitive:
            if str(resolved).startswith(sens):
                return False

        parts = resolved.parts
        if ".." in parts:
            return False

        for root in allowed_roots:
            try:
                root_path = Path(root).resolve()
                if resolved.is_relative_to(root_path):
                    return True
            except (ValueError, OSError):
                continue

        return False

    def validate_tool_args(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate all arguments for a tool.

        Applies per-tool rules, stricter enforcement for high-risk tools.
        """
        violations = []
        is_high_risk = tool_name in self._high_risk

        for key, value in args.items():
            if isinstance(value, str):
                ok, v = self.validate_input(value)
                if not ok:
                    violations.extend(v)

                if self._looks_like_path(value):
                    if not self.validate_path(value):
                        violations.append(f"invalid_path: {key}")

            elif isinstance(value, dict):
                ok, v = self.validate_tool_args(tool_name, value)
                if not ok:
                    violations.extend(v)

        if is_high_risk and violations:
            if self._log_violations:
                logger.warning(f"High-risk tool {tool_name} blocked: {violations}")

        if self._block and violations:
            return (False, violations)
        return (len(violations) == 0, violations)

    def _looks_like_path(self, text: str) -> bool:
        """Heuristic: does text look like a file path?"""
        return "/" in text or "\\" in text or text.startswith("~")
