"""Alert rules engine for desktop notifications."""

import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

ALERT_RULES_DB = Path.home() / "security" / "alert-rules.db"


@dataclass
class AlertRule:
    """Alert rule definition."""

    rule_id: str
    event_type: str
    condition_key: str
    condition_value: str
    title: str
    body_template: str
    urgency: str
    cooldown_seconds: int
    enabled: bool = True


class RulesEngine:
    """Engine for evaluating alert rules."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or ALERT_RULES_DB
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the rules database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    condition_key TEXT,
                    condition_value TEXT,
                    title TEXT NOT NULL,
                    body_template TEXT NOT NULL,
                    urgency TEXT DEFAULT 'normal',
                    cooldown_seconds INTEGER DEFAULT 300,
                    enabled INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_cooldowns (
                    rule_id TEXT PRIMARY KEY,
                    last_triggered REAL NOT NULL
                )
            """)
            self._ensure_default_rules(conn)
            conn.commit()
        finally:
            conn.close()

    def _ensure_default_rules(self, conn: sqlite3.Connection) -> None:
        """Ensure default alert rules exist."""
        default_rules = [
            (
                "security_threat_found",
                "security_status_change",
                "status",
                "threat",
                "Security Threat Detected",
                "Threat found: {detail}",
                "critical",
                300,
            ),
            (
                "timer_stale",
                "timer_status",
                "status",
                "stale",
                "Timer Stale",
                "Timer {timer_name} is stale",
                "normal",
                3600,
            ),
            (
                "kev_cve_detected",
                "kev_cve_detected",
                "type",
                "kev",
                "KEV CVE Detected",
                "Known Exploited Vulnerability: {cve_id}",
                "critical",
                86400,
            ),
            (
                "anomaly_detected",
                "anomaly_detected",
                "type",
                "anomaly",
                "Anomaly Detected",
                "System anomaly: {detail}",
                "normal",
                900,
            ),
            (
                "dep_vuln_found",
                "dep_vuln_found",
                "vulnerable",
                None,
                "Python Dependency Vulnerability",
                "{vulnerable} vulnerable package(s) found — run system.dep_audit for details",
                "critical",
                86400,
            ),
        ]

        for rule_id, event_type, key, value, title, body, urgency, cooldown in default_rules:
            conn.execute(
                """
                INSERT OR IGNORE INTO alert_rules
                (rule_id, event_type, condition_key, condition_value,
                 title, body_template, urgency, cooldown_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (rule_id, event_type, key, value, title, body, urgency, cooldown),
            )

    def match(self, event_type: str, data: dict[str, Any]) -> list[AlertRule]:
        """Find rules that match the given event type and data."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT rule_id, event_type, condition_key, condition_value,
                       title, body_template, urgency, cooldown_seconds, enabled
                FROM alert_rules WHERE event_type = ? AND enabled = 1
            """,
                (event_type,),
            )

            matching_rules = []
            now = time.time()

            for row in cursor.fetchall():
                rule_id, et, key, value, title, body, urgency, cooldown, enabled = row

                # Check cooldown
                cursor2 = conn.execute(
                    "SELECT last_triggered FROM alert_cooldowns WHERE rule_id = ?", (rule_id,)
                )
                row2 = cursor2.fetchone()
                if row2 and (now - row2[0]) < cooldown:
                    continue

                # Simple condition check
                if key and value:
                    if data.get(key) != value:
                        continue

                matching_rules.append(
                    AlertRule(
                        rule_id=rule_id,
                        event_type=et,
                        condition_key=key or "",
                        condition_value=value or "",
                        title=title,
                        body_template=body,
                        urgency=urgency,
                        cooldown_seconds=cooldown,
                        enabled=bool(enabled),
                    )
                )

            return matching_rules
        finally:
            conn.close()

    def record_trigger(self, rule_id: str) -> None:
        """Record that a rule was triggered (for cooldown tracking)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO alert_cooldowns (rule_id, last_triggered)
                VALUES (?, ?)
            """,
                (rule_id, time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_rules(self) -> list[AlertRule]:
        """Get all configured rules."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT rule_id, event_type, condition_key, condition_value,
                       title, body_template, urgency, cooldown_seconds, enabled
                FROM alert_rules
            """)
            return [
                AlertRule(
                    rule_id=row[0],
                    event_type=row[1],
                    condition_key=row[2] or "",
                    condition_value=row[3] or "",
                    title=row[4],
                    body_template=row[5],
                    urgency=row[6],
                    cooldown_seconds=row[7],
                    enabled=bool(row[8]),
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()


def get_rules_engine() -> RulesEngine:
    """Get singleton RulesEngine."""
    global _rules_engine
    if _rules_engine is None:
        _rules_engine = RulesEngine()
    return _rules_engine


_rules_engine: RulesEngine | None = None
