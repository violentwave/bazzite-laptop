"""Package intelligence via Google deps.dev API.

Supply-chain awareness: advisories, provenance, version freshness.

Usage:
    python -m ai.system.pkg_intel --package lancedb --version 0.29.0 --ecosystem pypi
    python -m ai.system.pkg_intel --scan requirements.txt
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import UTC, date, datetime
from pathlib import Path

import requests

from ai.config import APP_NAME, SECURITY_DIR, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Constants ─────────────────────────────────────────────────────────────────

_DEPS_DEV_BASE = "https://api.deps.dev/v3/systems"
PKG_INTEL_DIR = SECURITY_DIR


# ── deps.dev API ──────────────────────────────────────────────────────────────


def _fetch_package(
    ecosystem: str,
    package: str,
    rate_limiter: RateLimiter,
) -> dict | None:
    """Fetch package metadata (all versions) from deps.dev."""
    if not rate_limiter.can_call("deps_dev"):
        logger.info("deps.dev rate limited, skipping %s", package)
        return None

    url = f"{_DEPS_DEV_BASE}/{ecosystem}/packages/{package}"
    try:
        resp = requests.get(url, timeout=15)
        rate_limiter.record_call("deps_dev")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("deps.dev package fetch failed for %s: %s", package, e)
        return None


def _fetch_version(
    ecosystem: str,
    package: str,
    version: str,
    rate_limiter: RateLimiter,
) -> dict | None:
    """Fetch version-specific metadata from deps.dev."""
    if not rate_limiter.can_call("deps_dev"):
        return None

    url = f"{_DEPS_DEV_BASE}/{ecosystem}/packages/{package}/versions/{version}"
    try:
        resp = requests.get(url, timeout=15)
        rate_limiter.record_call("deps_dev")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("deps.dev version fetch failed for %s@%s: %s", package, version, e)
        return None


def _extract_package_info(
    pkg_data: dict | None,
    ver_data: dict | None,
    package: str,
    version: str,
) -> dict:
    """Merge package + version data into a normalized entry."""
    # Latest version from package metadata
    latest_version = ""
    if pkg_data:
        for v in pkg_data.get("versions", []):
            if v.get("isDefault"):
                latest_version = v.get("versionKey", {}).get("version", "")
                break

    licenses: list[str] = []
    advisory_keys: list[str] = []
    has_provenance = False
    source_repo = ""

    if ver_data:
        licenses = [lic.get("spdxExpression", "") for lic in ver_data.get("licenses", [])]
        advisory_keys = [
            a.get("sourceId", "") for a in ver_data.get("advisoryKeys", [])
        ]
        has_provenance = bool(ver_data.get("slsaProvenance"))
        for link in ver_data.get("links", []):
            if link.get("label") in ("SOURCE_REPO", "SOURCE"):
                source_repo = link.get("url", "")
                break

    is_latest = bool(latest_version and latest_version == version)

    return {
        "version": version,
        "is_latest": is_latest,
        "latest_version": latest_version,
        "licenses": [lic for lic in licenses if lic],
        "advisory_count": len(advisory_keys),
        "advisories": advisory_keys,
        "has_provenance": has_provenance,
        "source_repo": source_repo,
    }


# ── Requirements parsing ──────────────────────────────────────────────────────

_REQ_RE = re.compile(r"^([A-Za-z0-9_\-]+)[=><!\s]+([0-9][^\s;#]*)")


def _parse_requirements(path: Path) -> list[tuple[str, str]]:
    """Parse requirements.txt into (name, version) pairs."""
    packages = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-", "git+")):
            continue
        m = _REQ_RE.match(line)
        if m:
            packages.append((m.group(1), m.group(2).strip()))
    return packages


# ── Report ────────────────────────────────────────────────────────────────────


def _write_report(data: dict) -> Path:
    """Atomic write to ~/security/pkg-intel-YYYY-MM-DD.json."""
    PKG_INTEL_DIR.mkdir(parents=True, exist_ok=True)
    report_path = PKG_INTEL_DIR / f"pkg-intel-{date.today().isoformat()}.json"
    tmp = report_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(report_path)
    return report_path


def _latest_report() -> dict | None:
    """Return the most recent pkg-intel report, or None."""
    reports = sorted(PKG_INTEL_DIR.glob("pkg-intel-*.json"), reverse=True)
    if not reports:
        return None
    try:
        return json.loads(reports[0].read_text())
    except (json.JSONDecodeError, OSError):
        return None


# ── Single lookup ─────────────────────────────────────────────────────────────


def lookup_package(
    package: str,
    version: str,
    ecosystem: str = "pypi",
    rate_limiter: RateLimiter | None = None,
) -> dict:
    """Look up a single package on deps.dev.

    Returns:
        Package info dict.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    pkg_data = _fetch_package(ecosystem, package, rate_limiter)
    ver_data = _fetch_version(ecosystem, package, version, rate_limiter)
    return _extract_package_info(pkg_data, ver_data, package, version)


# ── Scan mode ─────────────────────────────────────────────────────────────────


def scan_requirements(
    req_path: Path,
    ecosystem: str = "pypi",
    rate_limiter: RateLimiter | None = None,
) -> dict:
    """Scan all packages in a requirements.txt against deps.dev.

    Returns:
        Summary dict with total_packages, with_advisories, outdated, with_provenance.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    packages = _parse_requirements(req_path)
    results: dict[str, dict] = {}

    for name, version in packages:
        pkg_data = _fetch_package(ecosystem, name, rate_limiter)
        ver_data = _fetch_version(ecosystem, name, version, rate_limiter)
        if pkg_data is None and ver_data is None:
            continue
        results[name] = _extract_package_info(pkg_data, ver_data, name, version)

    report = {
        "scanned_at": datetime.now(tz=UTC).isoformat(),
        "ecosystem": ecosystem,
        "packages": results,
        "summary": {
            "total_packages": len(results),
            "with_advisories": sum(1 for v in results.values() if v["advisory_count"] > 0),
            "outdated": sum(1 for v in results.values() if not v["is_latest"]),
            "with_provenance": sum(1 for v in results.values() if v["has_provenance"]),
        },
    }
    _write_report(report)
    return report["summary"]


# ── MCP handler ───────────────────────────────────────────────────────────────


def mcp_handler() -> dict:
    """MCP entry point: return the latest scan report."""
    report = _latest_report()
    if report is None:
        return {"error": "No scan report found. Run: python -m ai.system.pkg_intel --scan requirements.txt"}  # noqa: E501
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Package intelligence via deps.dev"
    )
    parser.add_argument("--package", help="Package name")
    parser.add_argument("--version", help="Package version")
    parser.add_argument("--ecosystem", default="pypi", help="Ecosystem (pypi, npm)")
    parser.add_argument("--scan", metavar="REQUIREMENTS", help="Scan requirements.txt")
    args = parser.parse_args()

    load_keys()
    setup_logging()

    if args.scan:
        summary = scan_requirements(Path(args.scan), ecosystem=args.ecosystem)
        print(json.dumps(summary, indent=2))  # noqa: T201
    elif args.package and args.version:
        result = lookup_package(args.package, args.version, ecosystem=args.ecosystem)
        print(json.dumps(result, indent=2))  # noqa: T201
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
