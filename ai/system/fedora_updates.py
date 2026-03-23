"""Fedora/Bodhi update awareness module.

Queries the Fedora Bodhi API for pending updates relevant to this
Bazzite 43 (Fedora 41 base) system.

Usage:
    python -m ai.system.fedora_updates [--check]
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess  # nosec B404
from datetime import UTC, datetime, timedelta

import requests

from ai.config import APP_NAME, SECURITY_DIR, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Constants ─────────────────────────────────────────────────────────────────

FEDORA_UPDATES_PATH = SECURITY_DIR / "fedora-updates.json"
_BODHI_BASE = "https://bodhi.fedoraproject.org/updates/"
_FEDORA_RELEASE = "F41"
_SUBPROCESS_TIMEOUT = 30


# ── Package Enumeration ────────────────────────────────────────────────────────


def _get_installed_rpms() -> set[str]:
    """Return set of installed RPM package names."""
    try:
        result = subprocess.run(  # nosec B603,B607
            ["rpm", "-qa", "--queryformat", "%{NAME}\n"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("rpm enumeration failed: %s", e)
        return set()


# ── Bodhi API ─────────────────────────────────────────────────────────────────


def _fetch_updates(
    status: str,
    rate_limiter: RateLimiter,
    submitted_since: str | None = None,
) -> list[dict]:
    """Fetch updates from Bodhi for F41.

    Args:
        status: 'testing' or 'stable'
        rate_limiter: Rate limiter instance.
        submitted_since: ISO date string filter for stable updates.

    Returns:
        List of raw Bodhi update dicts.
    """
    if not rate_limiter.can_call("bodhi"):
        logger.info("Bodhi rate limited, skipping %s updates", status)
        return []

    params: dict = {
        "releases": _FEDORA_RELEASE,
        "status": status,
        "rows_per_page": 20,
    }
    if submitted_since:
        params["submitted_since"] = submitted_since

    try:
        resp = requests.get(_BODHI_BASE, params=params, timeout=30)
        rate_limiter.record_call("bodhi")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json().get("updates", [])
    except requests.RequestException as e:
        logger.warning("Bodhi request failed (%s): %s", status, e)
        return []


def _parse_update(raw: dict) -> dict:
    """Extract relevant fields from a Bodhi update."""
    return {
        "alias": raw.get("alias", ""),
        "title": raw.get("title", ""),
        "type": raw.get("type", ""),
        "severity": raw.get("severity", "unspecified"),
        "status": raw.get("status", ""),
        "date_submitted": (raw.get("date_submitted") or "")[:10],
        "url": f"https://bodhi.fedoraproject.org/updates/{raw.get('alias', '')}",
        "packages": [
            b.get("name", "") for b in raw.get("builds", []) if b.get("name")
        ],
    }


# ── Orchestration ─────────────────────────────────────────────────────────────


def check_updates(rate_limiter: RateLimiter | None = None) -> dict:
    """Fetch Fedora updates, filter by security and installed packages.

    Returns:
        Summary dict with security_count, relevant_count, critical_count.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    installed_rpms = _get_installed_rpms()
    seven_days_ago = (datetime.now(tz=UTC) - timedelta(days=7)).strftime("%Y-%m-%d")

    raw_testing = _fetch_updates("testing", rate_limiter)
    raw_stable = _fetch_updates("stable", rate_limiter, submitted_since=seven_days_ago)

    all_updates = [_parse_update(u) for u in raw_testing + raw_stable]

    security_updates = [u for u in all_updates if u["type"] == "security"]
    relevant_updates = [
        u for u in all_updates
        if u["type"] != "security" and installed_rpms & set(u["packages"])
    ]

    critical_count = sum(
        1 for u in security_updates if u["severity"] == "critical"
    )

    report = {
        "checked_at": datetime.now(tz=UTC).isoformat(),
        "fedora_release": _FEDORA_RELEASE,
        "security_updates": [
            {k: v for k, v in u.items() if k != "packages"}
            for u in security_updates
        ],
        "relevant_updates": relevant_updates,
        "summary": {
            "security_count": len(security_updates),
            "relevant_count": len(relevant_updates),
            "critical_count": critical_count,
        },
    }

    _write_report(report)
    return report["summary"]


def _write_report(data: dict) -> None:
    """Atomic write to ~/security/fedora-updates.json."""
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = FEDORA_UPDATES_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(FEDORA_UPDATES_PATH)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check Fedora/Bodhi updates for Bazzite"
    )
    parser.add_argument("--check", action="store_true", help="Run update check")
    parser.parse_args()

    load_keys()
    setup_logging()

    summary = check_updates()
    print(json.dumps(summary, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
