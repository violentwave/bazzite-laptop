#!/usr/bin/env python3
"""Evaluate security alerts and write ~/security/alerts.json."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.security.alerts import run_alert_evaluation

if __name__ == "__main__":
    result = run_alert_evaluation()
    print(
        f"Alerts: {result['critical']} critical, {result['high']} high, {result['medium']} medium"
    )
    print(f"Stale scans: {len(result.get('stale_scans', []))}")
