"""Token budget system with atomic persistence (Phase 23: Token Budget).

Manages daily token budgets across priority tiers with atomic writes.
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from ai.config import CONFIGS_DIR
from ai.metrics import record_metric

logger = logging.getLogger(__name__)

# Data directory for budget usage files
_DATA_DIR = Path.home() / ".local" / "share" / "bazzite-ai"
_USAGE_PREFIX = "budget-usage-"

_ALWAYS_RUN_PRIORITIES = {0, 1}


class BudgetExhaustedError(Exception):
    """Raised when a non-priority task class exceeds its daily token limit."""

    pass


class TokenBudget:
    """Token budget manager with daily usage tracking."""

    def __init__(self, config_path: str | None = None):
        """Initialize TokenBudget.

        Args:
            config_path: Path to token-budget.json config. Defaults to configs/token-budget.json.
        """
        if config_path is None:
            config_path = str(CONFIGS_DIR / "token-budget.json")
        self.config = self._load_config(config_path)
        self.usage = self._load_daily_usage()

    def _load_config(self, path: str) -> dict:
        """Load token-budget.json.

        Args:
            path: Path to config file.

        Returns:
            Parsed config dict.

        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"Token budget config not found: {path}")
        return json.loads(config_file.read_text())

    def _usage_file_path(self) -> Path:
        """Get the path to today's usage file."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return _DATA_DIR / f"{_USAGE_PREFIX}{today}.json"

    def _load_daily_usage(self) -> dict:
        """Load today's usage file.

        Returns:
            Usage dict keyed by tier name, or empty dict if file doesn't exist.
            Returns {} if file date != today (daily reset logic).
        """
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        usage_path = self._usage_file_path()

        if not usage_path.exists():
            return {}

        try:
            data = json.loads(usage_path.read_text())
            # Check if file is from today - if not, reset
            mtime = datetime.fromtimestamp(usage_path.stat().st_mtime, UTC)
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            if mtime < today_start:
                return {}
            return data
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_daily_usage(self) -> None:
        """ATOMIC write: write to .tmp path, then os.replace() to final path."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        usage_path = self._usage_file_path()
        tmp_path = usage_path.with_suffix(".json.tmp")

        try:
            tmp_path.write_text(json.dumps(self.usage))
            os.replace(tmp_path, usage_path)
        except OSError as e:
            logger.error("Failed to write usage file: %s", e)

    def can_spend(self, task_class: str, estimated_tokens: int) -> bool:
        """Check if this task_class has budget remaining.

        Args:
            task_class: Budget tier name (security, scheduled, interactive, coding).
            estimated_tokens: Estimated tokens for this operation.

        Returns:
            True if budget available. Priority 0 (security) and 1 (scheduled) always return True.
        """
        tier = self.config["tiers"].get(task_class)
        if tier is None:
            logger.warning("Unknown task class: %s", task_class)
            return True

        priority = tier.get("priority", 3)
        if priority in _ALWAYS_RUN_PRIORITIES:
            return True

        daily_limit = tier.get("daily_token_limit", 0)
        if daily_limit <= 0:
            return True

        used = self.usage.get(task_class, 0)
        can_spend = (used + estimated_tokens) <= daily_limit
        if not can_spend:
            record_metric("budget", "budget_exhausted", 1.0, tags={"task_class": task_class})
        return can_spend

    def record_spend(self, task_class: str, tokens: int, cost_usd: float = 0.0) -> None:
        """Record token usage.

        Args:
            task_class: Budget tier name.
            tokens: Number of tokens spent.
            cost_usd: Optional cost in USD (stored for observability, not used in budget calc).
        """
        if task_class not in self.config["tiers"]:
            logger.warning("Unknown task class for spend: %s", task_class)
            return

        self.usage[task_class] = self.usage.get(task_class, 0) + tokens
        self._save_daily_usage()
        record_metric("budget", "budget_spend", float(tokens), tags={"task_class": task_class})

    def get_status(self) -> dict:
        """Get budget status for all tiers.

        Returns:
            Dict keyed by tier name, each with:
              used, limit, remaining_pct, priority, warn (bool), halt (bool)
        """
        halt_at_pct = self.config.get("halt_all_at_pct", 95)
        warn_at_pct = self.config.get("warn_at_pct", 80)
        result = {}

        for tier_name, tier_config in self.config["tiers"].items():
            limit = tier_config.get("daily_token_limit", 0)
            used = self.usage.get(tier_name, 0)
            remaining_pct = ((limit - used) / limit * 100) if limit > 0 else 100
            warn = used >= (limit * warn_at_pct / 100) if limit > 0 else False
            halt = used >= (limit * halt_at_pct / 100) if limit > 0 else False

            result[tier_name] = {
                "used": used,
                "limit": limit,
                "remaining_pct": remaining_pct,
                "priority": tier_config.get("priority", 3),
                "warn": warn,
                "halt": halt,
            }

        return result


_instance: TokenBudget | None = None


def get_budget(config_path: str | None = None) -> TokenBudget:
    """Module-level singleton accessor.

    Args:
        config_path: Optional path to token-budget.json.

    Returns:
        TokenBudget instance (singleton for process lifetime).
    """
    global _instance
    if _instance is None:
        _instance = TokenBudget(config_path)
    return _instance


def classify_task(task_type: str, source: str = "") -> str:
    """Map (task_type, source) to budget tier name.

    Args:
        task_type: LLM task type (fast, reason, batch, code).
        source: Optional source identifier.

    Returns:
        One of: "security", "scheduled", "interactive", "coding"
    """
    source_lower = source.lower()
    task_type_lower = task_type.lower()

    if "security" in source_lower or "threat" in source_lower or "cve" in source_lower:
        return "security"

    if task_type_lower == "batch" or "scheduled" in source_lower or "timer" in source_lower:
        return "scheduled"

    if task_type_lower == "code":
        return "coding"

    if task_type_lower in ("fast", "reason"):
        return "interactive"

    return "interactive"
