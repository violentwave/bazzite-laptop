"""Core threat intelligence lookup engine.

Implements cascading hash lookups across VirusTotal, OTX AlienVault, and
MalwareBazaar. Designed for testability: all provider functions accept an
injectable rate_limiter parameter.

Usage:
    from ai.threat_intel.lookup import lookup_hash, lookup_hashes
    report = lookup_hash("abc123...")
    reports = lookup_hashes(["abc123...", "def456..."])

CLI:
    python -m ai.threat_intel --hash <sha256>
    echo -e "hash1\\nhash2" | python -m ai.threat_intel --batch
"""

import argparse
import functools
import json
import logging
import re
import signal
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime

import requests
import vt

from ai.config import APP_NAME, ENRICHED_HASHES, get_key, load_keys, setup_logging
from ai.rate_limiter import RateLimiter
from ai.threat_intel.models import ThreatReport

logger = logging.getLogger(APP_NAME)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


# ── Timeout Context Manager ──


class LookupTimeoutError(Exception):
    """Raised when the overall lookup cascade exceeds the time limit."""


@contextmanager
def _lookup_timeout(seconds: int = 30):
    """Context manager that raises LookupTimeoutError after `seconds`."""
    def _handler(signum, frame):
        raise LookupTimeoutError(f"Lookup timed out after {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# ── Retry Decorator (available but not applied) ──


def _retry_on_failure(max_retries: int = 1, backoff: float = 2.0):
    """Decorator that retries provider functions on transient failures."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(sha256: str, rate_limiter: RateLimiter) -> ThreatReport | None:
            for attempt in range(max_retries + 1):
                result = fn(sha256, rate_limiter)
                if result is not None:
                    return result
                if attempt < max_retries:
                    wait = backoff * (attempt + 1)
                    logger.info("Retrying %s in %.1fs (attempt %d/%d)",
                                fn.__name__, wait, attempt + 2, max_retries + 1)
                    time.sleep(wait)
            return None
        return wrapper
    return decorator


# ── Provider Functions (private) ──


def _lookup_virustotal(sha256: str, rate_limiter: RateLimiter) -> ThreatReport | None:
    """Look up a hash on VirusTotal using the vt-py SDK."""
    if not rate_limiter.can_call("virustotal"):
        logger.info("VT rate limited, skipping")
        return None

    api_key = get_key("VT_API_KEY")
    if not api_key:
        logger.debug("VT_API_KEY not configured, skipping VT lookup")
        return None

    try:
        with vt.Client(api_key, timeout=10) as client:
            try:
                file_obj = client.get_object(f"/files/{sha256}")
            except vt.error.APIError as e:
                if "NotFoundError" in str(e):
                    raise
                # Single retry on transient VT API errors
                logger.info("VT API error, retrying once...")
                time.sleep(1)
                try:
                    file_obj = client.get_object(f"/files/{sha256}")
                except vt.error.APIError as retry_e:
                    logger.warning("VT retry failed for %s: %s", sha256[:16], retry_e)
                    return None

        rate_limiter.record_call("virustotal")

        stats = file_obj.get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        undetected = stats.get("undetected", 0)
        harmless = stats.get("harmless", 0)

        total = malicious + undetected + harmless
        detection_ratio = f"{malicious}/{total}" if total > 0 else "0/0"

        if malicious == 0:
            risk_level = "clean"
        elif malicious <= 5:
            risk_level = "low"
        elif malicious <= 20:
            risk_level = "medium"
        else:
            risk_level = "high"

        threat_class = file_obj.get("popular_threat_classification", {})
        family = threat_class.get("suggested_threat_label", "") or ""

        categories = threat_class.get("popular_threat_category", [])
        category = categories[0].get("value", "") if categories else ""

        tags = file_obj.get("tags", []) or []
        filename = file_obj.get("meaningful_name", "") or ""

        return ThreatReport(
            hash=sha256,
            filename=filename,
            source="virustotal",
            family=family,
            category=category,
            detection_ratio=detection_ratio,
            risk_level=risk_level,
            description=f"VirusTotal: {detection_ratio} detections"[:200],
            tags=list(tags),
            vt_link=f"https://www.virustotal.com/gui/file/{sha256}",
            timestamp=datetime.now(tz=UTC).isoformat(),
            raw_data={"last_analysis_stats": stats},
        )
    except vt.error.APIError as e:
        logger.warning("VT API error for %s: %s", sha256[:16], e)
        return None
    except Exception:
        logger.exception("Unexpected error during VT lookup for %s", sha256[:16])
        return None


def _lookup_otx(sha256: str, rate_limiter: RateLimiter) -> ThreatReport | None:
    """Look up a hash on OTX AlienVault using raw requests."""
    if not rate_limiter.can_call("otx"):
        logger.info("OTX rate limited, skipping")
        return None

    api_key = get_key("OTX_API_KEY")
    if not api_key:
        logger.debug("OTX_API_KEY not configured, skipping OTX lookup")
        return None

    try:
        url = f"https://otx.alienvault.com/api/v1/indicators/file/{sha256}/general"
        headers = {"X-OTX-API-KEY": api_key}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
        except requests.exceptions.ConnectionError:
            # Single retry on connection error
            logger.info("OTX connection error, retrying once...")
            time.sleep(1)
            try:
                resp = requests.get(url, headers=headers, timeout=5)
            except requests.exceptions.RequestException as e:
                logger.warning("OTX retry failed for %s: %s", sha256[:16], e)
                return None
        rate_limiter.record_call("otx")  # count the call even if status is error
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, dict):
            logger.warning("OTX returned non-dict response for %s", sha256[:16])
            return None

        pulse_info = data.get("pulse_info", {})
        pulse_count = pulse_info.get("count", 0)
        if pulse_count == 0:
            return None

        pulses = pulse_info.get("pulses", [])
        family = ""
        tags: list[str] = []
        for pulse in pulses:
            if not family:
                families = pulse.get("malware_families", [])
                if families:
                    family = families[0].get("display_name", "") or ""
            tags.extend(pulse.get("tags", []))

        tags = list(dict.fromkeys(tags))  # deduplicate preserving order

        if pulse_count <= 2:
            risk_level = "low"
        elif pulse_count <= 10:
            risk_level = "medium"
        else:
            risk_level = "high"

        description = data.get("general", {}).get("description", "") or ""
        description = description[:200]

        return ThreatReport(
            hash=sha256,
            source="otx",
            family=family,
            risk_level=risk_level,
            description=description or f"OTX: {pulse_count} pulses reference this hash",
            tags=tags,
            timestamp=datetime.now(tz=UTC).isoformat(),
            raw_data=data,
        )
    except requests.exceptions.RequestException as e:
        logger.warning("OTX request error for %s: %s", sha256[:16], e)
        return None
    except Exception:
        logger.exception("Unexpected error during OTX lookup for %s", sha256[:16])
        return None


def _lookup_malwarebazaar(sha256: str, rate_limiter: RateLimiter) -> ThreatReport | None:
    """Look up a hash on MalwareBazaar using form-encoded POST.

    MalwareBazaar public API requires no API key.
    """
    if not rate_limiter.can_call("malwarebazaar"):
        logger.info("MalwareBazaar rate limited, skipping")
        return None

    try:
        url = "https://mb-api.abuse.ch/api/v1/"
        post_data = {"query": "get_info", "hash": sha256}
        try:
            resp = requests.post(url, data=post_data, timeout=5)  # data= NOT json=
        except requests.exceptions.ConnectionError:
            # Single retry on connection error
            logger.info("MalwareBazaar connection error, retrying once...")
            time.sleep(1)
            try:
                resp = requests.post(url, data=post_data, timeout=5)
            except requests.exceptions.RequestException as e:
                logger.warning("MalwareBazaar retry failed for %s: %s", sha256[:16], e)
                return None
        rate_limiter.record_call("malwarebazaar")  # count the call even if status is error
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, dict):
            logger.warning("MalwareBazaar returned non-dict response for %s", sha256[:16])
            return None

        status = data.get("query_status", "")
        if status in ("hash_not_found", "no_results"):
            return None

        entries = data.get("data", [])
        if not isinstance(entries, list) or not entries:
            return None
        entry = entries[0]

        family = entry.get("signature", "") or ""
        filename = entry.get("file_name", "") or ""
        tags = entry.get("tags") or []
        file_type = entry.get("file_type", "") or ""

        return ThreatReport(
            hash=sha256,
            filename=filename,
            source="malwarebazaar",
            family=family,
            category=file_type,
            risk_level="high",  # present in MalwareBazaar = known malware
            description=f"MalwareBazaar: {family or 'unknown family'}"[:200],
            tags=list(tags),
            timestamp=datetime.now(tz=UTC).isoformat(),
            raw_data=data,
        )
    except requests.exceptions.RequestException as e:
        logger.warning("MalwareBazaar request error for %s: %s", sha256[:16], e)
        return None
    except Exception:
        logger.exception("Unexpected error during MalwareBazaar lookup for %s", sha256[:16])
        return None


# ── Orchestration Functions (public) ──


def lookup_hash(
    sha256: str,
    full: bool = False,
    rate_limiter: RateLimiter | None = None,
) -> ThreatReport:
    """Look up a single hash across threat intel providers.

    Args:
        sha256: The SHA256 hash to look up (64 hex chars).
        full: If True, query all providers (sequential stub; parallel later).
        rate_limiter: Injectable RateLimiter instance for testability.

    Returns:
        A ThreatReport with results, or source="none" if no data found.
    """
    if not _SHA256_RE.match(sha256):
        return ThreatReport(
            hash=sha256,
            source="none",
            description="Invalid SHA256 hash",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    if rate_limiter is None:
        rate_limiter = RateLimiter()

    providers = [_lookup_virustotal, _lookup_otx, _lookup_malwarebazaar]

    if full:
        # Full mode: call all providers, prefer VT data, merge tags
        try:
            with _lookup_timeout(30):
                results = [fn(sha256, rate_limiter) for fn in providers]
        except LookupTimeoutError:
            logger.warning("Lookup cascade timed out for %s (full mode)", sha256[:16])
            results = []
        valid = [r for r in results if r is not None and r.has_data]

        if not valid:
            return ThreatReport(
                hash=sha256,
                source="none",
                timestamp=datetime.now(tz=UTC).isoformat(),
            )

        # Prefer VT, then OTX, then MB as the base report
        report = valid[0]
        # Merge tags from all providers
        all_tags: list[str] = []
        for r in valid:
            all_tags.extend(r.tags)
        report.tags = list(dict.fromkeys(all_tags))

        _append_enriched(report)
        return report

    # Cascading mode: stop on first hit
    try:
        with _lookup_timeout(30):
            for fn in providers:
                result = fn(sha256, rate_limiter)
                if result is not None and result.has_data:
                    _append_enriched(result)
                    return result
    except LookupTimeoutError:
        logger.warning("Lookup cascade timed out for %s", sha256[:16])

    return ThreatReport(
        hash=sha256,
        source="none",
        timestamp=datetime.now(tz=UTC).isoformat(),
    )


def lookup_hashes(
    hashes: list[str],
    full: bool = False,
    rate_limiter: RateLimiter | None = None,
) -> list[ThreatReport]:
    """Look up multiple hashes, respecting rate limits between calls.

    Args:
        hashes: List of SHA256 hashes to look up.
        full: If True, query all providers for each hash.
        rate_limiter: Injectable RateLimiter instance for testability.

    Returns:
        List of ThreatReport objects, one per input hash.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    reports: list[ThreatReport] = []
    for sha256 in hashes:
        # Check if we need to wait for any provider's rate limits
        wait = max(
            rate_limiter.wait_time("virustotal"),
            rate_limiter.wait_time("otx"),
            rate_limiter.wait_time("malwarebazaar"),
        )
        if wait > 0:
            logger.info("Rate limited, waiting %.1fs before next lookup", wait)
            time.sleep(wait)

        reports.append(lookup_hash(sha256, full=full, rate_limiter=rate_limiter))

    return reports


def _append_enriched(report: ThreatReport) -> None:
    """Append a report to the enriched hashes JSONL file."""
    try:
        ENRICHED_HASHES.parent.mkdir(parents=True, exist_ok=True)
        with open(ENRICHED_HASHES, "a", encoding="utf-8") as f:
            f.write(report.to_jsonl() + "\n")
    except OSError as e:
        logger.warning("Could not write to enriched hashes file: %s", e)


# ── CLI Entry Point ──


def main() -> None:
    """CLI entry point for threat intelligence hash lookups."""
    parser = argparse.ArgumentParser(description="Threat intelligence hash lookup")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hash", help="Single SHA256 hash to look up")
    group.add_argument(
        "--batch", action="store_true", help="Read hashes from stdin (one per line)"
    )
    parser.add_argument(
        "--format", choices=["html", "json"], default="json", help="Output format"
    )
    parser.add_argument(
        "--full", action="store_true", help="Query all providers (not just first match)"
    )
    args = parser.parse_args()

    load_keys()
    setup_logging()

    if args.hash:
        hashes = [args.hash.strip()]
    else:
        hashes = [line.strip() for line in sys.stdin if line.strip()]

    reports = lookup_hashes(hashes, full=args.full)

    if args.format == "json":
        output = json.dumps([json.loads(r.to_jsonl()) for r in reports], indent=2)
        print(output)  # noqa: T201
    elif args.format == "html":
        from ai.threat_intel.formatters import format_html_section  # noqa: PLC0415

        print(format_html_section(reports))  # noqa: T201

    if any(r.has_data for r in reports):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
