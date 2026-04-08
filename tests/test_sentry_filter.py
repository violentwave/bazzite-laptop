"""Tests for Sentry before_send filter in ai/router.py."""

import os
from unittest.mock import patch


def test_sentry_before_send_filters_pytest():
    """Events with PYTEST_CURRENT_TEST should be filtered out."""
    from ai.router import _sentry_before_send

    # With PYTEST_CURRENT_TEST set, should return None (drop event)
    with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}):
        event = {"event_id": "test"}
        result = _sentry_before_send(event, {})
        assert result is None


def test_sentry_before_send_filters_ci():
    """Events with CI set should be filtered out."""
    from ai.router import _sentry_before_send

    # With CI set, should return None (drop event)
    with patch.dict(os.environ, {"CI": "true"}):
        event = {"event_id": "test"}
        result = _sentry_before_send(event, {})
        assert result is None


def test_sentry_before_send_allows_normal_events():
    """Normal events without pytest/CI should be allowed through."""
    from ai.router import _sentry_before_send

    # Without special env vars, should return the event unchanged
    with patch.dict(os.environ, {}, clear=True):
        event = {"event_id": "test", "level": "error"}
        result = _sentry_before_send(event, {})
        assert result == event


def test_sentry_before_send_preserves_event_data():
    """The before_send function should not modify allowed events."""
    from ai.router import _sentry_before_send

    original_event = {"event_id": "test123", "level": "error", "message": "test message"}
    event_copy = original_event.copy()

    with patch.dict(os.environ, {}, clear=True):
        result = _sentry_before_send(original_event, {})
        # Should return the same event object (not modified)
        assert result is original_event
        # Original event should be unchanged
        assert original_event == event_copy
