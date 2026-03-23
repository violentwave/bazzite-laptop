"""URL and IOC threat lookup engine.

Cascade: URLhaus (primary) → ThreatFox (fallback if URLhaus misses) →
CIRCL Hashlookup (enrichment for payload hashes from URLhaus results).
All providers are public no-key APIs.

Designed for testability: all provider functions accept an injectable
rate_limiter parameter.

Usage:
    from ai.threat_intel.ioc_lookup import lookup_url
    report = lookup_url("http://example.com/evil.exe")

CLI:
    python -m ai.threat_intel.ioc_lookup --url http://example.com/evil.exe
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.parse
from dataclasses import dataclass, field
from datetime import UTC, datetime

import requests

from ai.config import APP_NAME, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)


# ── Data Model ────────────────────────────────────────────────────────────────


@dataclass
class IOCReport:
    """Structured URL/IOC reputation report.

    Populated by provider lookup functions in this module.
    """

    ioc: str
    source: str = ""
    threat_type: str = ""
    malware_family: str = ""
    risk_level: str = "unknown"
    tags: list[str] = field(default_factory=list)
    description: str = ""
    circl_hits: list[dict] = field(default_factory=list)
    timestamp: str = ""
    raw_data: dict = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        """True if this report contains actual threat intelligence data."""
        return bool(self.source) and self.source != "none"

    def to_json(self) -> str:
        """Serialize to a JSON string (excludes raw_data)."""
        data = {
            "ioc": self.ioc,
            "source": self.source,
            "threat_type": self.threat_type,
            "malware_family": self.malware_family,
            "risk_level": self.risk_level,
            "tags": self.tags,
            "description": self.description,
            "circl_hits": self.circl_hits,
            "timestamp": self.timestamp or datetime.now(tz=UTC).isoformat(),
        }
        return json.dumps(data)


# ── Input Validation ──────────────────────────────────────────────────────────


def _validate_url(url: str) -> str | None:
    """Validate a URL for lookup.

    Returns the stripped URL if valid (http/https/ftp with a netloc),
    or None if the URL is empty, schemeless, or structurally invalid.
    """
    url = url.strip()
    if not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return None
    if parsed.scheme not in ("http", "https", "ftp"):
        return None
    if not parsed.netloc:
        return None
    return url


# ── Provider Functions (private) ──────────────────────────────────────────────


def _lookup_urlhaus(url: str, rate_limiter: RateLimiter) -> dict | None:
    """Query URLhaus for a URL.

    Returns a dict with parsed fields, or None on miss, rate-limit, or error.
    Dict keys: threat_type, malware_family, tags, payload_hashes, risk_level, raw.
    """
    if not rate_limiter.can_call("urlhaus"):
        logger.info("URLhaus rate limited, skipping")
        return None

    try:
        resp = requests.post(
            "https://urlhaus-api.abuse.ch/v1/url/",
            data={"url": url},
            timeout=10,
        )
        rate_limiter.record_call("urlhaus")
        resp.raise_for_status()
        data = resp.json()

        status = data.get("query_status", "")
        if status in ("no_results", "invalid_url"):
            return None

        payloads = data.get("payloads") or []
        payload_hashes = [
            p["sha256_hash"]
            for p in payloads
            if isinstance(p, dict) and p.get("sha256_hash")
        ]

        malware_family = ""
        for p in payloads:
            sig = p.get("signature", "") or ""
            if sig:
                malware_family = sig
                break

        return {
            "threat_type": data.get("threat", "") or "",
            "malware_family": malware_family,
            "tags": list(data.get("tags") or []),
            "payload_hashes": payload_hashes,
            "risk_level": "high",
            "raw": data,
        }
    except requests.exceptions.RequestException as e:
        logger.warning("URLhaus request error for %s: %s", url[:40], e)
        return None
    except Exception:
        logger.exception("Unexpected error during URLhaus lookup for %s", url[:40])
        return None


def _lookup_threatfox(ioc: str, rate_limiter: RateLimiter) -> dict | None:
    """Query ThreatFox for any IOC.

    Returns a dict with parsed fields, or None on miss, rate-limit, or error.
    Dict keys: threat_type, malware_family, tags, confidence, risk_level, raw.
    """
    if not rate_limiter.can_call("threatfox"):
        logger.info("ThreatFox rate limited, skipping")
        return None

    try:
        resp = requests.post(
            "https://threatfox-api.abuse.ch/api/v1/",
            json={"query": "search_ioc", "search_term": ioc},
            timeout=10,
        )
        rate_limiter.record_call("threatfox")
        resp.raise_for_status()
        data = resp.json()

        if data.get("query_status") != "ok":
            return None

        entries = data.get("data") or []
        if not entries:
            return None

        entry = entries[0]
        confidence = int(entry.get("confidence_level", 0))

        if confidence >= 75:
            risk_level = "high"
        elif confidence >= 50:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "threat_type": entry.get("threat_type", "") or "",
            "malware_family": entry.get("malware", "") or "",
            "tags": list(entry.get("tags") or []),
            "confidence": confidence,
            "risk_level": risk_level,
            "raw": data,
        }
    except requests.exceptions.RequestException as e:
        logger.warning("ThreatFox request error for %s: %s", ioc[:40], e)
        return None
    except Exception:
        logger.exception("Unexpected error during ThreatFox lookup for %s", ioc[:40])
        return None


def _enrich_circl(sha256: str) -> dict:
    """Query CIRCL Hashlookup for a SHA256.

    No API key needed. Always returns a dict; never raises.
    Returns {} if the hash is not found or the request fails.
    """
    try:
        resp = requests.get(
            f"https://hashlookup.circl.lu/lookup/sha256/{sha256}",
            timeout=10,
        )
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        return {
            "sha256": sha256,
            "filename": data.get("FileName", "") or "",
            "trust": data.get("hashlookup:trust", -1),
        }
    except requests.exceptions.RequestException as e:
        logger.warning("CIRCL Hashlookup error for %s: %s", sha256[:16], e)
        return {}
    except Exception:
        logger.exception("Unexpected error during CIRCL lookup for %s", sha256[:16])
        return {}


# ── Orchestration ─────────────────────────────────────────────────────────────


def lookup_url(
    url: str,
    rate_limiter: RateLimiter | None = None,
) -> IOCReport:
    """Perform a cascading URL/IOC threat lookup.

    Cascade order:
      1. URLhaus — primary malware URL database
      2. ThreatFox — fallback if URLhaus returns no result
      3. CIRCL Hashlookup — enrichment for payload hashes in URLhaus results

    Args:
        url: The URL or IOC to look up.
        rate_limiter: Injectable RateLimiter instance for testability.

    Returns:
        IOCReport with results. source="none" if URL is invalid or all
        providers return no data.
    """
    validated = _validate_url(url)
    if validated is None:
        return IOCReport(
            ioc=url,
            source="none",
            description="Invalid URL",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    if rate_limiter is None:
        rate_limiter = RateLimiter()

    # Step 1: URLhaus (primary)
    uh_result = _lookup_urlhaus(validated, rate_limiter)

    # Step 2: ThreatFox (fallback — only if URLhaus has no result)
    tf_result = None
    if uh_result is None:
        tf_result = _lookup_threatfox(validated, rate_limiter)

    # Step 3: CIRCL Hashlookup (enrichment for URLhaus payload hashes)
    circl_hits: list[dict] = []
    if uh_result and uh_result.get("payload_hashes"):
        for sha256 in uh_result["payload_hashes"][:3]:
            hit = _enrich_circl(sha256)
            if hit:
                circl_hits.append(hit)

    primary = uh_result or tf_result
    if primary is None:
        return IOCReport(
            ioc=validated,
            source="none",
            description="No threat intelligence data found",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    source = "urlhaus" if uh_result else "threatfox"
    if circl_hits:
        source += "+circl"

    tags = list(dict.fromkeys(primary.get("tags", [])))

    parts = [primary.get("threat_type", "") or source]
    if primary.get("malware_family"):
        parts.append(primary["malware_family"])

    return IOCReport(
        ioc=validated,
        source=source,
        threat_type=primary.get("threat_type", ""),
        malware_family=primary.get("malware_family", ""),
        risk_level=primary.get("risk_level", "unknown"),
        tags=tags,
        description=", ".join(p for p in parts if p)[:200],
        circl_hits=circl_hits,
        timestamp=datetime.now(tz=UTC).isoformat(),
        raw_data=primary.get("raw", {}),
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for URL/IOC threat lookups."""
    parser = argparse.ArgumentParser(
        description="URL/IOC threat lookup (URLhaus + ThreatFox + CIRCL)"
    )
    parser.add_argument("--url", required=True, help="URL or IOC to look up")
    args = parser.parse_args()

    load_keys()
    setup_logging()

    report = lookup_url(args.url)
    print(json.dumps(json.loads(report.to_json()), indent=2))  # noqa: T201

    if report.risk_level == "high":
        sys.exit(1)


if __name__ == "__main__":
    main()
