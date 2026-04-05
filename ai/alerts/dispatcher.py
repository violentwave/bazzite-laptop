"""Alert dispatcher for desktop notifications."""

import logging
import subprocess
from typing import Any

from ai.alerts.rules import get_rules_engine
from ai.config import APP_NAME
from ai.workflows.triggers import EventBus

logger = logging.getLogger(APP_NAME)


class AlertDispatcher:
    """Dispatches alerts to the desktop via notify-send."""

    def __init__(self):
        self.rules_engine = get_rules_engine()
        self._event_bus = None

    def dispatch(self, event_type: str, data: dict[str, Any]) -> int:
        """Dispatch an alert for the given event.

        Returns the number of notifications sent.
        """
        rules = self.rules_engine.match(event_type, data)
        sent = 0

        for rule in rules:
            try:
                body = rule.body_template.format(**data)
                urgency_map = {"low": "low", "normal": "normal", "critical": "critical"}
                urgency = urgency_map.get(rule.urgency, "normal")

                result = subprocess.run(
                    [
                        "notify-send",
                        "--urgency",
                        urgency,
                        "--app-name",
                        "Bazzite AI",
                        rule.title,
                        body,
                    ],
                    capture_output=True,
                    check=False,
                )
                if result.returncode == 0:
                    self.rules_engine.record_trigger(rule.rule_id)
                    sent += 1
                    logger.info("Alert sent: %s - %s", rule.title, body)
                else:
                    logger.warning("notify-send failed: %s", result.stderr.decode())
            except Exception as e:
                logger.error("Failed to send alert: %s", e)

        return sent

    def subscribe_to_event_bus(self, event_bus: EventBus) -> None:
        """Subscribe to the EventBus for event-driven alerts."""
        self._event_bus = event_bus
        event_bus.subscribe("security_status_change", self._handle_security)
        event_bus.subscribe("timer_status", self._handle_timer)
        event_bus.subscribe("kev_cve_detected", self._handle_cve)
        event_bus.subscribe("anomaly_detected", self._handle_anomaly)

    def _handle_security(self, data: dict[str, Any]) -> None:
        self.dispatch("security_status_change", data)

    def _handle_timer(self, data: dict[str, Any]) -> None:
        self.dispatch("timer_status", data)

    def _handle_cve(self, data: dict[str, Any]) -> None:
        self.dispatch("kev_cve_detected", data)

    def _handle_anomaly(self, data: dict[str, Any]) -> None:
        self.dispatch("anomaly_detected", data)


_dispatcher: AlertDispatcher | None = None


def get_dispatcher() -> AlertDispatcher:
    """Get singleton AlertDispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = AlertDispatcher()
    return _dispatcher
