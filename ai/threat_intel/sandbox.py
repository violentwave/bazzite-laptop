"""Hybrid Analysis sandbox submission.

Path-validates the file under ~/security/quarantine/, then performs a hash
check before submitting so quota is not wasted on already-analysed samples.

Usage:
    from ai.threat_intel.sandbox import submit_file
    report = submit_file("~/security/quarantine/suspect.exe")

CLI:
    python -m ai.threat_intel.sandbox --file ~/security/quarantine/test.exe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from ai.config import APP_NAME, SECURITY_DIR, get_key, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Constants ─────────────────────────────────────────────────────────────────

_QUARANTINE_DIR = SECURITY_DIR / "quarantine"
_HA_BASE = "https://www.hybrid-analysis.com/api/v2"
_USER_AGENT = "Falcon Sandbox"
_ENVIRONMENT_ID = 120  # Windows 10 64-bit


# ── Data Model ────────────────────────────────────────────────────────────────


@dataclass
class SandboxReport:
    """Result of a Hybrid Analysis sandbox lookup or submission."""

    file_path: str
    sha256: str = ""
    # "cached" | "submitted" | "rate_limited" | "error"
    status: str = ""
    verdict: str = ""
    threat_score: int = -1
    threat_level: str = ""
    analysis_start_time: str = ""
    job_id: str = ""
    description: str = ""
    timestamp: str = ""

    def to_json(self) -> str:
        """Serialize to JSON string (safe fields only)."""
        return json.dumps({
            "file_path": self.file_path,
            "sha256": self.sha256,
            "status": self.status,
            "verdict": self.verdict,
            "threat_score": self.threat_score,
            "threat_level": self.threat_level,
            "analysis_start_time": self.analysis_start_time,
            "job_id": self.job_id,
            "description": self.description,
            "timestamp": self.timestamp or datetime.now(tz=UTC).isoformat(),
        })


# ── Path Validation ───────────────────────────────────────────────────────────


def _validate_path(file_path: str) -> Path | None:
    """Resolve and verify the file is under ~/security/quarantine/.

    Rejects traversal attempts, missing files, and non-files.

    Returns:
        Resolved Path if valid, None otherwise.
    """
    try:
        resolved = Path(file_path).expanduser().resolve()
    except (ValueError, OSError):
        return None

    quarantine = _QUARANTINE_DIR.resolve()
    try:
        resolved.relative_to(quarantine)
    except ValueError:
        return None

    if not resolved.exists() or not resolved.is_file():
        return None

    return resolved


# ── Crypto ────────────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    """Compute SHA256 digest of a file in 64 KiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:  # noqa: PTH123
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── API Helpers ───────────────────────────────────────────────────────────────


def _headers(api_key: str) -> dict:
    return {
        "api-key": api_key,
        "User-Agent": _USER_AGENT,
        "Accept": "application/json",
    }


def _search_hash(sha256: str, api_key: str) -> dict | None:
    """POST /api/v2/search/hash — return first matching result or None."""
    try:
        resp = requests.post(
            f"{_HA_BASE}/search/hash",
            headers=_headers(api_key),
            data={"hash": sha256},
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0]
        return None
    except requests.RequestException as e:
        logger.warning("Hybrid Analysis hash search failed: %s", e)
        return None


def _submit(path: Path, api_key: str) -> dict | None:
    """POST /api/v2/submit/file (multipart) — return submission dict or None."""
    try:
        with open(path, "rb") as fh:  # noqa: PTH123
            resp = requests.post(
                f"{_HA_BASE}/submit/file",
                headers=_headers(api_key),
                files={"file": (path.name, fh, "application/octet-stream")},
                data={"environment_id": _ENVIRONMENT_ID},
                timeout=60,
            )
        if resp.status_code in (400, 422):
            logger.warning("HA submission rejected (%d): %s",
                           resp.status_code, resp.text[:200])
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("Hybrid Analysis submission failed: %s", e)
        return None


# ── Orchestration ─────────────────────────────────────────────────────────────


def submit_file(
    file_path: str,
    rate_limiter: RateLimiter | None = None,
) -> SandboxReport:
    """Submit a quarantine file to Hybrid Analysis for sandbox analysis.

    Steps:
        1. Validate path resolves under ~/security/quarantine/
        2. Compute SHA256
        3. Search existing analysis (hash-first to avoid quota waste)
        4. If no cached result and rate allows, submit the file

    Args:
        file_path: Path string (may use ~/… prefix; must resolve to quarantine).
        rate_limiter: Injectable RateLimiter for testability.

    Returns:
        SandboxReport with status "cached", "submitted", "rate_limited",
        or "error".
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    report = SandboxReport(
        file_path=file_path,
        timestamp=datetime.now(tz=UTC).isoformat(),
    )

    # Step 1: path validation
    resolved = _validate_path(file_path)
    if resolved is None:
        report.status = "error"
        report.description = (
            "Invalid path: must be an existing file under ~/security/quarantine/"
        )
        return report

    # Step 2: API key
    api_key = get_key("HYBRID_ANALYSIS_KEY")
    if not api_key:
        report.status = "error"
        report.description = "HYBRID_ANALYSIS_KEY not configured"
        return report

    # Step 3: hash
    report.sha256 = _sha256(resolved)

    # Step 4: rate check before any network call
    if not rate_limiter.can_call("hybrid_analysis"):
        report.status = "rate_limited"
        report.description = "Hybrid Analysis rate limit reached"
        return report

    # Step 5: hash-first lookup
    existing = _search_hash(report.sha256, api_key)
    rate_limiter.record_call("hybrid_analysis")

    if existing:
        report.status = "cached"
        report.verdict = str(existing.get("verdict", ""))
        report.threat_score = int(existing.get("threat_score") or -1)
        report.threat_level = str(existing.get("threat_level_human", ""))
        report.analysis_start_time = str(existing.get("analysis_start_time", ""))
        report.description = f"Existing analysis found (verdict: {report.verdict})"
        return report

    # Step 6: submit (re-check rate limit)
    if not rate_limiter.can_call("hybrid_analysis"):
        report.status = "rate_limited"
        report.description = "Rate limit reached before submission"
        return report

    result = _submit(resolved, api_key)
    rate_limiter.record_call("hybrid_analysis")

    if result is None:
        report.status = "error"
        report.description = "File submission failed"
        return report

    report.status = "submitted"
    report.job_id = str(result.get("job_id", ""))
    report.description = f"Submitted for analysis (job_id: {report.job_id})"
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for sandbox submission."""
    parser = argparse.ArgumentParser(
        description="Submit a quarantine file to Hybrid Analysis sandbox"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the file (must be under ~/security/quarantine/)",
    )
    args = parser.parse_args()

    load_keys()
    setup_logging()

    report = submit_file(args.file)
    print(json.dumps(json.loads(report.to_json()), indent=2))  # noqa: T201

    if report.status == "error":
        import sys  # noqa: PLC0415
        sys.exit(1)


if __name__ == "__main__":
    main()
