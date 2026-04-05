"""Desktop alerting system for Bazzite AI layer.

Provides real-time notify-send desktop notifications for security events,
stale timers, and budget thresholds.
"""

from ai.alerts.dispatcher import AlertDispatcher, get_dispatcher
from ai.alerts.history import acknowledge, get_recent, get_unacknowledged
from ai.alerts.rules import AlertRule, RulesEngine

__all__ = [
    "AlertRule",
    "RulesEngine",
    "AlertDispatcher",
    "get_dispatcher",
    "get_recent",
    "get_unacknowledged",
    "acknowledge",
]
