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
import asyncio
import json
import logging
import re
import sys
from datetime import UTC, datetime
from functools import lru_cache

import requests
import vt
from OTXv2 import OTXv2

from ai.config import APP_NAME, ENRICHED_HASHES, get_key, load_keys, setup_logging
from ai.metrics import track_performance
from ai.rate_limiter import RateLimiter
from ai.threat_intel.models import ThreatReport

logger = logging.getLogger(APP_NAME)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


# ── Client Caching ────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _get_vt_client():
    api_key = get_key("VT_API_KEY")
    return vt.Client(api_key, timeout=10) if api_key else None


@lru_cache(maxsize=1)
def _get_otx_client():
    api_key = get_key("OTX_API_KEY")
    return OTXv2(api_key) if api_key else None


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
            file_obj = client.get_object(f"/files/{sha256}")

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
        resp = requests.get(url, headers=headers, timeout=5)
        rate_limiter.record_call("otx")
        resp.raise_for_status()
        data = resp.json()

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

        tags = list(dict.fromkeys(tags))

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
        resp = requests.post(url, data=post_data, timeout=5)
        rate_limiter.record_call("malwarebazaar")
        resp.raise_for_status()
        data = resp.json()

        status = data.get("query_status", "")
        if status in ("hash_not_found", "no_results"):
            return None

        entries = data.get("data", [])
        entry = entries[0] if entries else {}

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
            risk_level="high" if family else "low",
            description=f"MalwareBazaar: {family or 'unknown malware'}"[:200],
            tags=list(tags),
            timestamp=datetime.now(tz=UTC).isoformat(),
            raw_data=entry,
        )
    except requests.exceptions.RequestException as e:
        logger.warning("MalwareBazaar request error for %s: %s", sha256[:16], e)
        return None
    except Exception:
        logger.exception("Unexpected error during MalwareBazaar lookup for %s", sha256[:16])
        return None


# ── Async Parallel Lookup ────────────────────────────────────────────────────


def _run_in_executor(func, *args):
    """Run a synchronous function in the default executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args)


async def _parallel_lookup_all(sha256: str, rate_limiter: RateLimiter) -> list[ThreatReport | None]:
    """Run all provider lookups in parallel using asyncio.gather.

    Returns a list of (vt_result, otx_result, mb_result) in that order.
    """
    vt_task = _run_in_executor(_lookup_virustotal, sha256, rate_limiter)
    otx_task = _run_in_executor(_lookup_otx, sha256, rate_limiter)
    mb_task = _run_in_executor(_lookup_malwarebazaar, sha256, rate_limiter)

    return await asyncio.gather(vt_task, otx_task, mb_task)


def _append_enriched(report: ThreatReport) -> None:
    """Append a report to the enriched hashes JSONL file."""
    try:
        ENRICHED_HASHES.parent.mkdir(parents=True, exist_ok=True)
        with open(ENRICHED_HASHES, "a") as f:
            f.write(report.to_jsonl() + "\n")
    except OSError as e:
        logger.warning("Could not write to enriched hashes file: %s", e)


def _merge_reports(reports: list[ThreatReport | None], sha256: str) -> ThreatReport:
    """Merge multiple provider results into a single ThreatReport.

    Priority: VirusTotal > OTX > MalwareBazaar > none
    """
    vt_result, otx_result, mb_result = reports

    if vt_result and vt_result.has_data:
        return vt_result
    if otx_result and otx_result.has_data:
        return otx_result
    if mb_result and mb_result.has_data:
        return mb_result

    return ThreatReport(
        hash=sha256,
        source="none",
        description="No threat intelligence data found",
        timestamp=datetime.now(tz=UTC).isoformat(),
    )


# ── Public API ────────────────────────────────────────────────────────────────


@track_performance
def lookup_hash(
    sha256: str,
    rate_limiter: RateLimiter | None = None,
    parallel: bool = False,
) -> ThreatReport:
    """Perform a cascading hash threat lookup.

    Cascade order:
      1. VirusTotal — primary (detection ratio, family, tags)
      2. OTX AlienVault — fallback (pulse count, community intel)
      3. MalwareBazaar — tertiary (signature, file type)

    When parallel=True (default), all three providers are queried
    concurrently using asyncio.gather for faster response times.

    Args:
        sha256: The SHA256 hash to look up.
        rate_limiter: Injectable RateLimiter instance for testability.
        parallel: Run provider lookups in parallel (default True).

    Returns:
        ThreatReport with results. source="none" if hash is invalid or all
        providers return no data.
    """
    sha256 = sha256.strip().lower()
    if not _SHA256_RE.match(sha256):
        return ThreatReport(
            hash=sha256,
            source="none",
            description="Invalid SHA256 hash",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    if rate_limiter is None:
        rate_limiter = RateLimiter()

    if parallel:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                reports = loop.run_until_complete(_parallel_lookup_all(sha256, rate_limiter))
                loop.close()
            else:
                reports = loop.run_until_complete(_parallel_lookup_all(sha256, rate_limiter))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                reports = loop.run_until_complete(_parallel_lookup_all(sha256, rate_limiter))
            finally:
                loop.close()

        return _merge_reports(reports, sha256)

    # Cascading mode: MB → OTX → VT (cheapest first, stop on hit)
    mb_result = _lookup_malwarebazaar(sha256, rate_limiter)
    if mb_result and mb_result.has_data:
        _append_enriched(mb_result)
        return mb_result

    otx_result = _lookup_otx(sha256, rate_limiter)
    if otx_result and otx_result.has_data:
        _append_enriched(otx_result)
        return otx_result

    vt_result = _lookup_virustotal(sha256, rate_limiter)
    if vt_result and vt_result.has_data:
        _append_enriched(vt_result)
        return vt_result

    return ThreatReport(
        hash=sha256,
        source="none",
        description="No threat intelligence data found",
        timestamp=datetime.now(tz=UTC).isoformat(),
    )

    if rate_limiter is None:
        rate_limiter = RateLimiter()

    if parallel:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                reports = loop.run_until_complete(_parallel_lookup_all(sha256, rate_limiter))
                loop.close()
            else:
                reports = loop.run_until_complete(_parallel_lookup_all(sha256, rate_limiter))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                reports = loop.run_until_complete(_parallel_lookup_all(sha256, rate_limiter))
            finally:
                loop.close()

        return _merge_reports(reports, sha256)

    vt_result = _lookup_virustotal(sha256, rate_limiter)
    if vt_result and vt_result.has_data:
        return vt_result

    otx_result = _lookup_otx(sha256, rate_limiter)
    if otx_result and otx_result.has_data:
        return otx_result

    mb_result = _lookup_malwarebazaar(sha256, rate_limiter)
    if mb_result and mb_result.has_data:
        return mb_result

    return ThreatReport(
        hash=sha256,
        source="none",
        description="No threat intelligence data found",
        timestamp=datetime.now(tz=UTC).isoformat(),
    )


def lookup_hashes(
    hashes: list[str],
    rate_limiter: RateLimiter | None = None,
    parallel: bool = False,
) -> list[ThreatReport]:
    """Perform lookups for multiple hashes.

    Args:
        hashes: List of SHA256 hashes to look up.
        rate_limiter: Injectable RateLimiter instance.
        parallel: Run provider lookups in parallel for each hash.

    Returns:
        List of ThreatReport objects, one per input hash.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    return [lookup_hash(h, rate_limiter=rate_limiter, parallel=parallel) for h in hashes]


def log_enriched_report(report: ThreatReport) -> None:
    """Append a report to the enriched hashes JSONL log."""
    if not report.has_data:
        return

    ENRICHED_HASHES.parent.mkdir(parents=True, exist_ok=True)
    with open(ENRICHED_HASHES, "a") as f:
        f.write(report.to_jsonl() + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for hash threat lookups."""
    parser = argparse.ArgumentParser(
        description="Threat intelligence lookup (VT + OTX + MalwareBazaar)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hash", help="Single SHA256 hash to look up")
    group.add_argument("--batch", action="store_true", help="Read hashes from stdin (one per line)")
    parser.add_argument(
        "--no-parallel", action="store_true", help="Run lookups sequentially (default: parallel)"
    )
    args = parser.parse_args()

    load_keys()
    setup_logging()

    if args.batch:
        hashes = [line.strip() for line in sys.stdin if line.strip()]
        reports = lookup_hashes(hashes, parallel=not args.no_parallel)
        for report in reports:
            print(json.dumps(json.loads(report.to_jsonl()), indent=2))
            if report.has_data:
                log_enriched_report(report)
    else:
        report = lookup_hash(args.hash, parallel=not args.no_parallel)
        print(json.dumps(json.loads(report.to_jsonl()), indent=2))
        if report.has_data:
            log_enriched_report(report)

        if report.risk_level in ("high", "medium"):
            sys.exit(1)


if __name__ == "__main__":
    main()
