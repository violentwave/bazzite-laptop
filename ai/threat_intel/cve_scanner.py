"""CVE vulnerability scanner.

Scans installed packages (rpm, flatpak, pip venv) against NVD, OSV, and
CISA KEV.  All API calls go through RateLimiter.

Usage:
    from ai.threat_intel.cve_scanner import scan_cves
    summary = scan_cves()

CLI:
    python -m ai.threat_intel.cve_scanner
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess  # nosec B404
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import requests

from ai.config import APP_NAME, SECURITY_DIR, get_key, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Constants ─────────────────────────────────────────────────────────────────

CVE_REPORTS_DIR = SECURITY_DIR / "cve-reports"
_KEV_CACHE_PATH = CVE_REPORTS_DIR / "kev-cache.json"
_KEV_CACHE_TTL_HOURS = 168  # 7 days
_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)
_NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_OSV_QUERY_URL = "https://api.osv.dev/v1/query"
_SUBPROCESS_TIMEOUT = 30


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass
class PackageInfo:
    """A single installed package."""

    name: str
    version: str
    source: str  # "rpm", "flatpak", "pip"


@dataclass
class CVEEntry:
    """A matched CVE for an installed package."""

    cve_id: str
    description: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"
    cvss_score: float
    package_name: str
    package_version: str
    source: str  # "nvd" or "osv"
    in_kev: bool = False
    kev_due_date: str = ""


@dataclass
class ScanReport:
    """Aggregated scan results."""

    scan_date: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat()
    )
    packages_scanned: int = 0
    total_cves: int = 0
    high_severity: int = 0
    kev_cves: int = 0
    osv_fallback_used: bool = False
    cves: list[CVEEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ── Package Enumeration ────────────────────────────────────────────────────────


def _enum_rpm() -> list[PackageInfo]:
    """List installed RPM packages via rpm -qa."""
    try:
        result = subprocess.run(
            ["rpm", "-qa", "--queryformat", "%{NAME} %{VERSION}\n"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        packages = []
        for line in result.stdout.splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                packages.append(PackageInfo(parts[0], parts[1], "rpm"))
        return packages
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("rpm enumeration failed: %s", e)
        return []


def _enum_flatpak() -> list[PackageInfo]:
    """List installed Flatpak applications via flatpak list."""
    try:
        result = subprocess.run(
            ["flatpak", "list", "--columns=application,version"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        packages = []
        for line in result.stdout.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                packages.append(PackageInfo(parts[0], parts[1], "flatpak"))
        return packages
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("flatpak enumeration failed: %s", e)
        return []


def _enum_pip() -> list[PackageInfo]:
    """List pip packages from the project venv."""
    venv_pip = Path(__file__).parents[2] / ".venv" / "bin" / "pip"
    pip_cmd = str(venv_pip) if venv_pip.exists() else "pip"
    try:
        result = subprocess.run(
            [pip_cmd, "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        return [
            PackageInfo(pkg["name"], pkg["version"], "pip")
            for pkg in json.loads(result.stdout or "[]")
        ]
    except (subprocess.SubprocessError, FileNotFoundError,
            json.JSONDecodeError, KeyError) as e:
        logger.warning("pip enumeration failed: %s", e)
        return []


def enumerate_packages() -> list[PackageInfo]:
    """Enumerate all installed packages from rpm, flatpak, and pip."""
    packages: list[PackageInfo] = []
    packages.extend(_enum_rpm())
    packages.extend(_enum_flatpak())
    packages.extend(_enum_pip())
    return packages


# ── CISA KEV Cache ────────────────────────────────────────────────────────────


def _load_kev_cache() -> dict[str, str]:
    """Return CISA KEV CVE IDs mapped to due dates, fetching fresh when stale."""
    CVE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def _parse(data: dict) -> dict[str, str]:
        return {
            v["cveID"]: v.get("dueDate", "")
            for v in data.get("vulnerabilities", [])
        }

    if _KEV_CACHE_PATH.exists():
        age_hours = (time.time() - _KEV_CACHE_PATH.stat().st_mtime) / 3600
        if age_hours < _KEV_CACHE_TTL_HOURS:
            try:
                return _parse(json.loads(_KEV_CACHE_PATH.read_text()))
            except (json.JSONDecodeError, KeyError):
                pass

    try:
        resp = requests.get(_KEV_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        tmp = _KEV_CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.rename(_KEV_CACHE_PATH)
        return _parse(data)
    except requests.RequestException as e:
        logger.warning("CISA KEV fetch failed: %s — using stale/empty cache", e)

    if _KEV_CACHE_PATH.exists():
        try:
            return _parse(json.loads(_KEV_CACHE_PATH.read_text()))
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


# ── NVD Lookup ────────────────────────────────────────────────────────────────


def _nvd_severity(metrics: dict) -> tuple[str, float]:
    """Extract the highest-available CVSS severity label and score."""
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key, [])
        if entries:
            cvss = entries[0].get("cvssData", {})
            score = float(cvss.get("baseScore", 0.0))
            severity = cvss.get("baseSeverity", "UNKNOWN").upper()
            return severity, score
    return "UNKNOWN", 0.0


def _lookup_nvd(
    package: PackageInfo,
    rate_limiter: RateLimiter,
) -> list[CVEEntry]:
    """Query NVD CVE 2.0 API for CVEs matching the package name."""
    if not rate_limiter.can_call("nvd_cve"):
        logger.info("NVD rate limited, skipping %s", package.name)
        return []

    api_key = get_key("NVD_API_KEY")
    headers = {"apiKey": api_key} if api_key else {}
    params = {"keywordSearch": package.name, "resultsPerPage": 20}

    try:
        resp = requests.get(
            _NVD_BASE_URL, headers=headers, params=params, timeout=30
        )
        rate_limiter.record_call("nvd_cve")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("NVD request failed for %s: %s", package.name, e)
        return []

    cves = []
    for item in data.get("vulnerabilities", []):
        cve_data = item.get("cve", {})
        cve_id = cve_data.get("id", "")
        if not cve_id:
            continue
        descs = cve_data.get("descriptions", [])
        desc = next(
            (d["value"] for d in descs if d.get("lang") == "en"), ""
        )[:200]
        severity, score = _nvd_severity(cve_data.get("metrics", {}))
        cves.append(CVEEntry(
            cve_id=cve_id,
            description=desc,
            severity=severity,
            cvss_score=score,
            package_name=package.name,
            package_version=package.version,
            source="nvd",
        ))
    return cves


# ── OSV Lookup ────────────────────────────────────────────────────────────────


def _lookup_osv(package: PackageInfo) -> list[CVEEntry]:
    """Query OSV for vulnerabilities in a PyPI package."""
    try:
        payload = {
            "package": {"name": package.name, "ecosystem": "PyPI"},
            "version": package.version,
        }
        resp = requests.post(_OSV_QUERY_URL, json=payload, timeout=30)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("OSV request failed for %s: %s", package.name, e)
        return []

    cves = []
    for vuln in data.get("vulns", []):
        vuln_id = vuln.get("id", "")
        aliases = vuln.get("aliases", [])
        cve_id = next((a for a in aliases if a.startswith("CVE-")), vuln_id)
        details = vuln.get("details", "")[:200]
        severity, score = "UNKNOWN", 0.0
        for sev in vuln.get("severity", []):
            if sev.get("type") == "CVSS_V3":
                try:
                    score = float(sev.get("score", 0.0))
                    if score >= 9.0:
                        severity = "CRITICAL"
                    elif score >= 7.0:
                        severity = "HIGH"
                    elif score >= 4.0:
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"
                except (TypeError, ValueError):
                    pass
                break
        cves.append(CVEEntry(
            cve_id=cve_id,
            description=details,
            severity=severity,
            cvss_score=score,
            package_name=package.name,
            package_version=package.version,
            source="osv",
        ))
    return cves


# ── Report Writer ─────────────────────────────────────────────────────────────


def _write_report(report: ScanReport) -> Path:
    """Atomic write of the report JSON to ~/security/cve-reports/."""
    CVE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = CVE_REPORTS_DIR / f"cve-{date.today().isoformat()}.json"
    data = {
        "scan_date": report.scan_date,
        "packages_scanned": report.packages_scanned,
        "total_cves": report.total_cves,
        "high_severity": report.high_severity,
        "kev_cves": report.kev_cves,
        "kev_matches": report.kev_cves,
        "osv_fallback_used": report.osv_fallback_used,
        "errors": report.errors,
        "cves": [
            {
                "cve_id": c.cve_id,
                "description": c.description,
                "severity": c.severity,
                "cvss_score": c.cvss_score,
                "package_name": c.package_name,
                "package_version": c.package_version,
                "source": c.source,
                "in_kev": c.in_kev,
                "exploited_in_wild": c.in_kev,
                "kev_due_date": c.kev_due_date,
            }
            for c in report.cves
        ],
    }
    tmp = report_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(report_path)
    return report_path


# ── Orchestration ─────────────────────────────────────────────────────────────


def scan_cves(
    rate_limiter: RateLimiter | None = None,
) -> dict:
    """Scan installed packages for CVEs.

    Steps:
        1. Enumerate packages (rpm, flatpak, pip)
        2. Load CISA KEV (cached 24 h)
        3. Query NVD for each unique package name
        4. Query OSV for each pip package
        5. Overlay KEV matches
        6. Deduplicate and write report
        7. Return compact MCP summary

    Args:
        rate_limiter: Injectable RateLimiter; defaults to shared instance.

    Returns:
        Dict with packages_scanned, total_cves, high_severity, kev_cves.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    report = ScanReport()
    packages = enumerate_packages()
    report.packages_scanned = len(packages)

    kev_data = _load_kev_cache()

    seen_nvd: set[str] = set()
    nvd_found_packages: set[str] = set()
    all_cves: list[CVEEntry] = []
    osv_fallback_used = False

    for pkg in packages:
        if pkg.name not in seen_nvd:
            seen_nvd.add(pkg.name)
            nvd_results = _lookup_nvd(pkg, rate_limiter)
            if nvd_results:
                nvd_found_packages.add(pkg.name)
            all_cves.extend(nvd_results)

        if pkg.source == "pip" and pkg.name not in nvd_found_packages:
            osv_results = _lookup_osv(pkg)
            if osv_results:
                osv_fallback_used = True
            all_cves.extend(osv_results)

    for cve in all_cves:
        if cve.cve_id in kev_data:
            cve.in_kev = True
            cve.kev_due_date = kev_data[cve.cve_id]

    seen: set[tuple[str, str]] = set()
    unique: list[CVEEntry] = []
    for cve in all_cves:
        key = (cve.cve_id, cve.package_name)
        if key not in seen:
            seen.add(key)
            unique.append(cve)

    report.cves = unique
    report.total_cves = len(unique)
    report.high_severity = sum(
        1 for c in unique if c.severity in ("CRITICAL", "HIGH")
    )
    report.kev_cves = sum(1 for c in unique if c.in_kev)
    report.osv_fallback_used = osv_fallback_used

    try:
        _write_report(report)
    except OSError as e:
        logger.warning("Failed to write CVE report: %s", e)
        report.errors.append(str(e))

    return {
        "packages_scanned": report.packages_scanned,
        "total_cves": report.total_cves,
        "high_severity": report.high_severity,
        "kev_cves": report.kev_cves,
        "kev_matches": report.kev_cves,
        "osv_fallback_used": report.osv_fallback_used,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for CVE scanning."""
    parser = argparse.ArgumentParser(
        description="Scan installed packages for CVEs (NVD / OSV / CISA KEV)"
    )
    parser.parse_args()

    load_keys()
    setup_logging()

    summary = scan_cves()
    print(json.dumps(summary, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
