"""IP reputation lookup engine.

Cascade: AbuseIPDB (primary score) → GreyNoise community (tiebreaker when
score is 30-70) → Shodan InternetDB (port/vuln enrichment, always).

Designed for testability: all provider functions accept an injectable
rate_limiter parameter.  NEVER returns actual key values.

Usage:
    from ai.threat_intel.ip_lookup import lookup_ip
    report = lookup_ip("1.2.3.4")

CLI:
    python -m ai.threat_intel.ip_lookup --ip 1.2.3.4
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import requests as _requests_module

from ai.cache import JsonFileCache
from ai.config import APP_NAME, get_key, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# Module-level HTTP session with connection pooling
_http_session = _requests_module.Session()
_http_session.headers.update({"User-Agent": "Bazzite-AI/1.0"})
_adapter = _requests_module.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=0)
_http_session.mount("https://", _adapter)
_http_session.mount("http://", _adapter)


class _RequestsProxy:
    """Routes requests.get/post through the module session while remaining patchable.

    Tests patch ``ai.threat_intel.ip_lookup.requests.get``; assigning the proxy to
    the name ``requests`` keeps those patch targets intact while the real traffic
    goes through the pooled session.
    """

    get = _http_session.get
    post = _http_session.post
    exceptions = _requests_module.exceptions


requests = _RequestsProxy()

_ip_cache = JsonFileCache(
    Path.home() / "security" / "ip-cache",
    default_ttl=86400,  # 24 hours
)


# ── Data Model ────────────────────────────────────────────────────────────────


@dataclass
class IPReport:
    """Structured IP reputation report.

    Populated by provider lookup functions in this module.
    """

    ip: str
    source: str = ""
    abuse_score: int = -1
    greynoise_classification: str = ""
    recommendation: str = ""
    ports: list[int] = field(default_factory=list)
    vulns: list[str] = field(default_factory=list)
    description: str = ""
    timestamp: str = ""
    raw_data: dict = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        """True if this report contains actual reputation data."""
        return bool(self.source) and self.source != "none"

    def to_json(self) -> str:
        """Serialize to a JSON string (excludes raw_data)."""
        data = {
            "ip": self.ip,
            "source": self.source,
            "abuse_score": self.abuse_score,
            "greynoise_classification": self.greynoise_classification,
            "recommendation": self.recommendation,
            "ports": self.ports,
            "vulns": self.vulns,
            "description": self.description,
            "timestamp": self.timestamp or datetime.now(tz=UTC).isoformat(),
        }
        return json.dumps(data)


# ── Input Validation ──────────────────────────────────────────────────────────


def _validate_ip(ip: str) -> str | None:
    """Validate and normalize an IP address string.

    Returns the normalized IP string, or None if the address is invalid,
    private, or loopback.
    """
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    if addr.is_private or addr.is_loopback:
        return None
    return str(addr)


# ── Provider Functions (private) ──────────────────────────────────────────────


def _lookup_abuseipdb(ip: str, rate_limiter: RateLimiter) -> int | None:
    """Query AbuseIPDB for an abuse confidence score (0-100).

    Returns the integer score, or None on rate-limit, missing key, or error.
    """
    if not rate_limiter.can_call("abuseipdb"):
        logger.info("AbuseIPDB rate limited, skipping")
        return None

    api_key = get_key("ABUSEIPDB_KEY")
    if not api_key:
        logger.debug("ABUSEIPDB_KEY not configured, skipping AbuseIPDB lookup")
        return None

    try:
        url = "https://api.abuseipdb.com/api/v2/check"
        headers = {"Key": api_key, "Accept": "application/json"}
        params = {"ipAddress": ip, "maxAgeInDays": 90}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        rate_limiter.record_call("abuseipdb")
        resp.raise_for_status()
        data = resp.json()
        score = data.get("data", {}).get("abuseConfidenceScore")
        if score is None:
            return None
        return int(score)
    except requests.exceptions.RequestException as e:
        logger.warning("AbuseIPDB request error for %s: %s", ip, e)
        return None
    except Exception:
        logger.exception("Unexpected error during AbuseIPDB lookup for %s", ip)
        return None


def _lookup_greynoise(ip: str, rate_limiter: RateLimiter) -> str | None:
    """Query GreyNoise community endpoint for IP classification.

    Returns the classification string ("malicious", "benign", "unknown"),
    or None on rate-limit, missing key, or request error.
    """
    if not rate_limiter.can_call("greynoise"):
        logger.info("GreyNoise rate limited, skipping")
        return None

    api_key = get_key("GREYNOISE_KEY")
    if not api_key:
        logger.debug("GREYNOISE_KEY not configured, skipping GreyNoise lookup")
        return None

    try:
        url = f"https://api.greynoise.io/v3/community/{ip}"
        headers = {"key": api_key, "Accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=10)
        rate_limiter.record_call("greynoise")
        if resp.status_code == 404:
            return "unknown"
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("classification", "unknown"))
    except requests.exceptions.RequestException as e:
        logger.warning("GreyNoise request error for %s: %s", ip, e)
        return None
    except Exception:
        logger.exception("Unexpected error during GreyNoise lookup for %s", ip)
        return None


def _enrich_shodan(ip: str) -> dict:
    """Query Shodan InternetDB for open ports and known vulns (no API key).

    Always returns a dict with "ports" and "vulns" keys; never raises.
    """
    try:
        url = f"https://internetdb.shodan.io/{ip}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return {"ports": [], "vulns": []}
        resp.raise_for_status()
        data = resp.json()
        return {
            "ports": data.get("ports", []),
            "vulns": data.get("vulns", []),
        }
    except requests.exceptions.RequestException as e:
        logger.warning("Shodan InternetDB request error for %s: %s", ip, e)
        return {"ports": [], "vulns": []}
    except Exception:
        logger.exception("Unexpected error during Shodan InternetDB lookup for %s", ip)
        return {"ports": [], "vulns": []}


# ── Recommendation Logic ──────────────────────────────────────────────────────


def _make_recommendation(score: int, greynoise: str | None) -> str:
    """Derive a human-readable recommendation from score and GreyNoise data.

    Args:
        score: AbuseIPDB confidence score (0-100).
        greynoise: GreyNoise classification or None if not available.

    Returns:
        One of: "block on firewall", "likely malicious", "known scanner",
        "suspicious", "low risk".
    """
    if score >= 80:
        return "block on firewall"
    if 50 <= score <= 79:
        if greynoise == "benign":
            return "known scanner"
        return "likely malicious"
    if 30 <= score <= 49:
        return "suspicious"
    return "low risk"


# ── Orchestration ─────────────────────────────────────────────────────────────


def lookup_ip(
    ip: str,
    rate_limiter: RateLimiter | None = None,
) -> IPReport:
    """Perform a cascading IP reputation lookup.

    Cascade order:
      1. AbuseIPDB — primary score (0-100)
      2. GreyNoise community — tiebreaker when score is 30-70
      3. Shodan InternetDB — port/vuln enrichment, always queried

    Args:
        ip: The IP address to look up (IPv4 or IPv6).
        rate_limiter: Injectable RateLimiter instance for testability.

    Returns:
        IPReport with results. source="none" if IP is invalid/private or all
        providers fail.
    """
    validated = _validate_ip(ip)
    if validated is None:
        return IPReport(
            ip=ip,
            source="none",
            description="Invalid, private, or loopback IP address",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    cache_key = f"ip:{validated}"
    cached = _ip_cache.get(cache_key)
    if cached is not None:
        logger.info("Threat cache hit for %s", validated)
        return IPReport(**cached)

    if rate_limiter is None:
        rate_limiter = RateLimiter()

    # Step 1: AbuseIPDB (primary)
    abuse_score = _lookup_abuseipdb(validated, rate_limiter)

    # Step 2: GreyNoise (tiebreaker — only when score is in ambiguous 30-70 range)
    greynoise_classification = ""
    if abuse_score is not None and 30 <= abuse_score <= 70:
        gn = _lookup_greynoise(validated, rate_limiter)
        if gn is not None:
            greynoise_classification = gn

    # Step 3: Shodan InternetDB (enrichment, always)
    shodan = _enrich_shodan(validated)

    if abuse_score is None:
        return IPReport(
            ip=validated,
            source="none",
            ports=shodan["ports"],
            vulns=shodan["vulns"],
            description="No abuse data available",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    recommendation = _make_recommendation(
        abuse_score, greynoise_classification or None
    )
    sources = ["abuseipdb"]
    if greynoise_classification:
        sources.append("greynoise")

    description_parts = [f"AbuseIPDB score: {abuse_score}"]
    if greynoise_classification:
        description_parts.append(f"GreyNoise: {greynoise_classification}")

    report = IPReport(
        ip=validated,
        source="+".join(sources),
        abuse_score=abuse_score,
        greynoise_classification=greynoise_classification,
        recommendation=recommendation,
        ports=shodan["ports"],
        vulns=shodan["vulns"],
        description=", ".join(description_parts)[:200],
        timestamp=datetime.now(tz=UTC).isoformat(),
        raw_data={"shodan": shodan},
    )
    _ip_cache.set(cache_key, json.loads(report.to_json()))
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for IP reputation lookups."""
    parser = argparse.ArgumentParser(
        description="IP reputation lookup (AbuseIPDB + GreyNoise + Shodan)"
    )
    parser.add_argument("--ip", required=True, help="IP address to look up")
    args = parser.parse_args()

    load_keys()
    setup_logging()

    report = lookup_ip(args.ip)
    print(json.dumps(json.loads(report.to_json()), indent=2))  # noqa: T201

    if report.recommendation in ("block on firewall", "likely malicious"):
        sys.exit(1)


if __name__ == "__main__":
    main()
