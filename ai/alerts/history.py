"""Alert history tracking for desktop notifications."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

ALERT_HISTORY_DB = Path.home() / "security" / "alert-history.db"


def _init_db(db_path: Path) -> None:
    """Initialize the alert history database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                rule_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                urgency TEXT NOT NULL,
                acknowledged INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()


def record_alert(
    rule_id: str,
    event_type: str,
    title: str,
    body: str,
    urgency: str,
) -> None:
    """Record an alert to the history database."""
    db_path = ALERT_HISTORY_DB
    _init_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO alert_history (timestamp, rule_id, event_type, title, body, urgency)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (datetime.now().timestamp(), rule_id, event_type, title, body, urgency),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent alerts."""
    db_path = ALERT_HISTORY_DB
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, timestamp, rule_id, event_type, title, body, urgency, acknowledged
            FROM alert_history ORDER BY timestamp DESC LIMIT ?
        """,
            (limit,),
        )

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "rule_id": row[2],
                "event_type": row[3],
                "title": row[4],
                "body": row[5],
                "urgency": row[6],
                "acknowledged": bool(row[7]),
            }
            for row in cursor.fetchall()
        ]
    finally:
        conn.close()


def get_unacknowledged() -> list[dict[str, Any]]:
    """Get unacknowledged alerts."""
    db_path = ALERT_HISTORY_DB
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("""
            SELECT id, timestamp, rule_id, event_type, title, body, urgency
            FROM alert_history WHERE acknowledged = 0 ORDER BY timestamp DESC
        """)

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "rule_id": row[2],
                "event_type": row[3],
                "title": row[4],
                "body": row[5],
                "urgency": row[6],
            }
            for row in cursor.fetchall()
        ]
    finally:
        conn.close()


def acknowledge(alert_id: int) -> None:
    """Mark an alert as acknowledged."""
    db_path = ALERT_HISTORY_DB
    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE alert_history SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
    finally:
        conn.close()
