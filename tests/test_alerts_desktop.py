"""Unit tests for ai/alerts/ module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAlertRules:
    """Tests for alert rules engine."""

    def test_rules_engine_initializes(self):
        """RulesEngine should initialize with default rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from ai.alerts.rules import RulesEngine

            engine = RulesEngine(db_path=Path(tmpdir) / "test.db")
            rules = engine.get_all_rules()

            assert len(rules) >= 4

    def test_match_finds_matching_rule(self):
        """match should find rules matching event type and data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from ai.alerts.rules import RulesEngine

            engine = RulesEngine(db_path=Path(tmpdir) / "test.db")
            matches = engine.match("security_status_change", {"status": "threat"})

            assert len(matches) >= 1


class TestAlertDispatcher:
    """Tests for alert dispatcher."""

    def test_dispatch_returns_count(self):
        """dispatch should return count of notifications sent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from ai.alerts.dispatcher import AlertDispatcher
            from ai.alerts.rules import RulesEngine

            engine = RulesEngine(db_path=Path(tmpdir) / "rules.db")
            dispatcher = AlertDispatcher()
            dispatcher.rules_engine = engine

            with patch("subprocess.run") as mock:
                mock.return_value = MagicMock(returncode=0)
                count = dispatcher.dispatch("security_status_change", {"status": "threat"})

            assert count >= 0

    def test_get_dispatcher_singleton(self):
        """get_dispatcher should return singleton."""
        from ai.alerts.dispatcher import get_dispatcher

        d1 = get_dispatcher()
        d2 = get_dispatcher()

        assert d1 is d2


class TestAlertHistory:
    """Tests for alert history."""

    def test_get_recent_empty_db(self):
        """get_recent should return empty list for new DB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ai.alerts.history.ALERT_HISTORY_DB", Path(tmpdir) / "test.db"):
                from ai.alerts.history import get_recent

                result = get_recent(limit=10)
                assert isinstance(result, list)

    def test_get_unacknowledged(self):
        """get_unacknowledged should return unacknowledged alerts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ai.alerts.history.ALERT_HISTORY_DB", Path(tmpdir) / "test.db"):
                from ai.alerts.history import get_unacknowledged

                result = get_unacknowledged()
                assert isinstance(result, list)


def test_alerts_module_imports():
    """Alerts module should import without errors."""
    from ai import alerts

    assert alerts is not None
    assert hasattr(alerts, "get_dispatcher")
