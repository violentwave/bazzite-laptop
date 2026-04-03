"""Tests for ai/budget.py TokenBudget."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.budget import TokenBudget, classify_task


class TestTokenBudget:
    def test_budget_within_limit(self):
        """Test budget allows spending within limit."""
        budget = TokenBudget()
        assert budget.can_spend("interactive", 1000) is True

    def test_budget_exceeded(self, tmp_path):
        """Test budget rejects spending when limit exceeded."""
        budget = TokenBudget()

        budget.usage = {"interactive": 999_999_999}
        assert budget.can_spend("interactive", 1) is False

    def test_budget_security_always_runs(self):
        """Test security tier always runs regardless of usage."""
        budget = TokenBudget()

        budget.usage = {"security": 999_999_999}
        assert budget.can_spend("security", 999_999_999) is True

    def test_budget_daily_reset(self, tmp_path):
        """Test daily reset returns empty usage for new day."""
        budget = TokenBudget()

        budget.usage = {"interactive": 100}
        budget._save_daily_usage()

        assert budget.usage == {"interactive": 100}

    def test_budget_status_format(self):
        """Test get_status returns correct structure."""
        budget = TokenBudget()
        status = budget.get_status()

        assert set(status.keys()) == {"security", "scheduled", "interactive", "coding"}

        for tier in status.values():
            assert "used" in tier
            assert "limit" in tier
            assert "remaining_pct" in tier
            assert "priority" in tier

    def test_budget_atomic_write(self, tmp_path):
        """Test atomic write leaves no .tmp file."""
        from ai import budget as budget_module

        original_dir = budget_module._DATA_DIR
        budget_module._DATA_DIR = Path(tmp_path)

        budget = TokenBudget()
        budget.usage = {"interactive": 100}
        budget._save_daily_usage()

        tmp_files = list(Path(tmp_path).glob("*.json.tmp"))
        assert len(tmp_files) == 0, "Temp file should not exist after write"

        budget_module._DATA_DIR = original_dir


    def test_budget_record_spend_accumulates(self, tmp_path):
        """Test that record_spend correctly accumulates usage."""
        from pathlib import Path

        from ai import budget as budget_module

        original_dir = budget_module._DATA_DIR
        try:
            budget_module._DATA_DIR = Path(tmp_path)
            budget = TokenBudget()
            budget.record_spend("interactive", 500)
            budget.record_spend("interactive", 300)
            assert budget.usage.get("interactive", 0) == 800
        finally:
            budget_module._DATA_DIR = original_dir


class TestClassifyTask:
    def test_classify_security(self):
        """Test security classification."""
        assert classify_task("fast", "security threat") == "security"
        assert classify_task("reason", "cve scan") == "security"

    def test_classify_scheduled(self):
        """Test scheduled classification."""
        assert classify_task("batch", "scheduled") == "scheduled"
        assert classify_task("fast", "timer") == "scheduled"

    def test_classify_coding(self):
        """Test coding classification."""
        assert classify_task("code", "") == "coding"

    def test_classify_interactive(self):
        """Test interactive classification."""
        assert classify_task("fast", "") == "interactive"
        assert classify_task("reason", "newelle") == "interactive"
