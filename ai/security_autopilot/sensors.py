"""Safe adapters for collecting Security Autopilot sensor signals."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass
class SensorSnapshot:
    """Result of one safe sensor read."""

    sensor: str
    status: str
    payload: dict[str, Any]
    collected_at: str = field(default_factory=_utc_now)
    error: str = ""


class BazziteSensorAdapter:
    """Collect signals from existing Bazzite tools via an injected fetcher.

    The adapter is intentionally read-only and only references approved P119
    signals. It does not execute commands or remediation actions.
    """

    DEFAULT_SENSORS: tuple[tuple[str, dict[str, Any]], ...] = (
        ("security.status", {}),
        ("security.last_scan", {}),
        ("security.cve_check", {}),
        ("security.alert_summary", {}),
        ("security.threat_summary", {}),
        ("system.dep_audit", {}),
        ("system.fedora_updates", {}),
        ("system.release_watch", {}),
        ("system.service_status", {}),
        ("logs.anomalies", {}),
        ("agents.security_audit", {}),
        ("agents.timer_health", {}),
    )

    def __init__(
        self,
        fetcher: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        self._fetcher = fetcher

    def collect(self, sensor: str, params: dict[str, Any] | None = None) -> SensorSnapshot:
        """Collect a single sensor signal with error isolation."""

        params = params or {}
        if self._fetcher is None:
            return SensorSnapshot(
                sensor=sensor,
                status="unavailable",
                payload={},
                error="no fetcher configured",
            )

        try:
            raw = self._fetcher(sensor, params)
            payload = raw if isinstance(raw, dict) else {"value": raw}
            return SensorSnapshot(sensor=sensor, status="ok", payload=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sensor read failed for %s: %s", sensor, exc)
            return SensorSnapshot(
                sensor=sensor,
                status="error",
                payload={},
                error=str(exc),
            )

    def collect_all(
        self,
        sensors: tuple[tuple[str, dict[str, Any]], ...] | None = None,
    ) -> list[SensorSnapshot]:
        """Collect all configured sensors in sequence."""

        selected = sensors or self.DEFAULT_SENSORS
        return [self.collect(sensor=name, params=params) for name, params in selected]
