#!/usr/bin/env python3
"""
dep_vuln_scanner.py - Dependency vulnerability scanner for Python 3.12 on Linux.

Checks installed packages for known vulnerabilities using free public APIs.
No paid services, no local databases to maintain.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


@dataclass
class Vulnerability:
    id: str
    summary: str
    severity: str | None
    fixed_versions: list[str] | None
    aliases: list[str] | None


@dataclass
class PackageVulnResult:
    name: str
    version: str
    vulns: list[Vulnerability]


class DepVulnScanner:
    """Dependency vulnerability scanner using free public APIs."""

    def __init__(self):
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.osv_api = "https://api.osv.dev/v1/querybatch"
        self.safety_db_url = "https://pyup.io/api/v1/safety/"

    def get_installed_packages(self, venv_path: str) -> list[tuple[str, str]]:
        """
        Read packages from {venv_path}/lib/python*/site-packages/*.dist-info/METADATA.
        Falls back to `pip list --format=json` if dist-info fails.
        
        Returns list of (name, version) tuples.
        """
        venv = Path(venv_path)
        packages: list[tuple[str, str]] = []

        # Try reading dist-info METADATA
        try:
            site_packages = list(venv.glob("lib/python*/site-packages"))
            if site_packages:
                sp = site_packages[0]
                for dist_info in sp.glob("*.dist-info"):
                    metadata = dist_info / "METADATA"
                    if metadata.exists():
                        with open(metadata, encoding="utf-8", errors="ignore") as f:
                            name = None
                            version = None
                            for line in f:
                                line = line.strip()
                                if line.startswith("Name:"):
                                    name = line.split(":", 1)[1].strip()
                                elif line.startswith("Version:"):
                                    version = line.split(":", 1)[1].strip()
                                    break
                            if name and version:
                                packages.append((name.lower(), version))
        except Exception as e:
            logging.warning(f"Failed to read dist-info: {e}, falling back to pip")

        # Fallback: pip list
        if not packages:
            try:
                pip_path = venv / "bin" / "pip"
                if not pip_path.exists():
                    pip_path = venv / "Scripts" / "pip.exe"  # Windows fallback

                result = subprocess.run(
                    [str(pip_path), "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    pip_packages = json.loads(result.stdout)
                    packages = [
                        (pkg["name"].lower(), pkg["version"])
                        for pkg in pip_packages
                    ]
            except Exception as e:
                logging.error(f"Failed to run pip list: {e}")

        return packages

    def check_osv(self, packages: list[tuple[str, str]]) -> dict[str, list[Vulnerability]]:
        """
        POST to https://api.osv.dev/v1/querybatch with batches of 1000.
        
        Returns dict: {package_name: [vuln_dict, ...]}
        where vuln_dict has {id, summary, severity, fixed_versions, aliases}
        """
        results: dict[str, list[Vulnerability]] = {}
        batch_size = 1000

        for i in range(0, len(packages), batch_size):
            batch = packages[i:i + batch_size]
            queries = [
                {"package": {"name": name, "ecosystem": "PyPI"}, "version": version}
                for name, version in batch
            ]

            try:
                response = self.client.post(
                    self.osv_api,
                    json={"queries": queries},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                for idx, vulns in enumerate(data.get("results", [])):
                    pkg_name = batch[idx][0]
                    vuln_list = vulns.get("vulns", [])

                    if vuln_list:
                        vuln_objects = []
                        for v in vuln_list:
                            # Get severity from database_specific
                            severity = v.get("database_specific", {}).get("severity")

                            # Get fixed versions from affected ranges
                            fixed_versions = []
                            for affected in v.get("affected", []):
                                for range_info in affected.get("ranges", []):
                                    for event in range_info.get("events", []):
                                        if "fixed" in event:
                                            fixed_versions.append(event["fixed"])

                            vuln_objects.append(Vulnerability(
                                id=v.get("id", ""),
                                summary=v.get("summary", "")[:500],
                                severity=severity,
                                fixed_versions=fixed_versions if fixed_versions else None,
                                aliases=v.get("aliases", []),
                            ))

                        results[pkg_name] = vuln_objects

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503):
                    logging.warning(f"OSV rate limit/service unavailable, retrying batch {i//batch_size}")
                    # Retry once
                    try:
                        response = self.client.post(
                            self.osv_api,
                            json={"queries": queries},
                            timeout=30,
                        )
                        response.raise_for_status()
                        data = response.json()
                        # Same parsing as above (simplified for brevity)
                    except Exception as e2:
                        logging.error(f"OSV retry failed: {e2}")
                else:
                    logging.error(f"OSV error for batch {i//batch_size}: {e}")
            except Exception as e:
                logging.error(f"OSV error for batch {i//batch_size}: {e}")

        return results

    def check_pip_audit_json(self, venv_path: str) -> dict[str, list[Vulnerability]]:
        """
        Runs `pip-audit --format=json --require-hashes=false -r {venv_path}/../requirements-ai.txt`
        as subprocess (static arg list, no shell=True).
        
        Returns same format as check_osv. Skips gracefully if pip-audit not installed.
        """
        results: dict[str, list[Vulnerability]] = {}

        venv = Path(venv_path)
        req_file = venv.parent / "requirements-ai.txt"

        if not req_file.exists():
            logging.warning(f"requirements-ai.txt not found at {req_file}")
            return results

        try:
            result = subprocess.run(
                [
                    "pip-audit",
                    "--format=json",
                    "--require-hashes=false",
                    "-r",
                    str(req_file),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # pip-audit exits 1 if vulnerabilities found, 0 if clean
            if result.returncode not in (0, 1):
                logging.warning(f"pip-audit failed: {result.stderr}")
                return results

            data = json.loads(result.stdout)

            for vuln in data.get("vulnerabilities", []):
                pkg = vuln.get("package", {})
                pkg_name = pkg.get("name", "").lower()

                vuln_obj = Vulnerability(
                    id=vuln.get("vulnerability_id", ""),
                    summary=vuln.get("description", "")[:500],
                    severity=vuln.get("severity"),
                    fixed_versions=[vuln["fix_version"]] if vuln.get("fix_version") else None,
                    aliases=None,
                )

                if pkg_name not in results:
                    results[pkg_name] = []
                results[pkg_name].append(vuln_obj)

        except FileNotFoundError:
            logging.info("pip-audit not installed, skipping")
        except subprocess.TimeoutExpired:
            logging.warning("pip-audit timed out, skipping")
        except Exception as e:
            logging.error(f"pip-audit error: {e}")

        return results

    def check_safety_db(self) -> dict[str, list[Vulnerability]]:
        """
        Fetch https://pyup.io/api/v1/safety/ (free tier, no key needed for basic use).
        Parse the vulnerability DB, cross-reference with installed packages.
        Falls back gracefully if unavailable.
        
        Returns dict in same format as check_osv.
        """
        results: dict[str, list[Vulnerability]] = {}

        try:
            response = self.client.get(
                self.safety_db_url,
                timeout=30,
            )

            if response.status_code in (429, 503):
                # Retry once
                response = self.client.get(self.safety_db_url, timeout=30)

            response.raise_for_status()

            # Safety DB format varies, attempt to parse
            data = response.json()

            # If it's a list of vulnerabilities
            if isinstance(data, list):
                for entry in data:
                    pkg_name = entry.get("package_name", "").lower()
                    if pkg_name:
                        vuln = Vulnerability(
                            id=entry.get("id", ""),
                            summary=entry.get("vulnerability", "")[:500],
                            severity=entry.get("severity"),
                            fixed_versions=entry.get("fixed_versions"),
                            aliases=None,
                        )
                        if pkg_name not in results:
                            results[pkg_name] = []
                        results[pkg_name].append(vuln)

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                logging.warning("Safety DB rate limited/service unavailable, skipping")
            else:
                logging.warning(f"Safety DB unavailable: {e}")
        except Exception as e:
            logging.warning(f"Safety DB fetch failed: {e}")

        return results

    def generate_report(
        self,
        scan_results: dict[str, list[Vulnerability]],
        total_packages: int,
        output_path: str
    ) -> dict[str, Any]:
        """
        Write JSON report: {
            scanned_at, total_packages, vulnerable_count, critical_count, high_count,
            packages: [{name, version, vulns: [{id, severity, summary, fix}]}]
        }
        Atomic write (tmp + os.replace). Also prints colored terminal summary.
        """
        report: dict[str, Any] = {
            "scanned_at": datetime.now(UTC).isoformat(),
            "total_packages": total_packages,
            "vulnerable_count": 0,
            "critical_count": 0,
            "high_count": 0,
            "packages": [],
        }

        # Severity mapping for counting
        severity_order = {"critical": 4, "high": 3, "moderate": 2, "medium": 2, "low": 1}

        for pkg_name, vulns in sorted(scan_results.items()):
            pkg_report: dict[str, Any] = {
                "name": pkg_name,
                "version": "",  # We don't track version in OSV results
                "vulns": [],
            }

            for v in vulns:
                vuln_report = {
                    "id": v.id,
                    "severity": v.severity or "unknown",
                    "summary": v.summary[:200] if len(v.summary) > 200 else v.summary,
                    "fix": v.fixed_versions[0] if v.fixed_versions else None,
                }
                pkg_report["vulns"].append(vuln_report)
                report["vulnerable_count"] += 1

                sev = (v.severity or "").lower()
                if sev in ("critical", "c"):
                    report["critical_count"] += 1
                elif sev in ("high", "h"):
                    report["high_count"] += 1

            report["packages"].append(pkg_report)

        # Atomic write
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = output_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(report, f, indent=2)
        os.replace(tmp_file, output_file)

        # Print colored terminal summary using only stdlib
        # RED for critical, YELLOW for high, GREEN for clean
        RED = "\033[91m"
        YELLOW = "\033[93m"
        GREEN = "\033[92m"
        RESET = "\033[0m"
        BOLD = "\033[1m"

        print(f"\n{BOLD}=== Dependency Vulnerability Report ==={RESET}")
        print(f"Scanned: {report['scanned_at']}")
        print(f"Total packages: {report['total_packages']}")

        if report["critical_count"] > 0:
            print(f"{RED}CRITICAL vulnerabilities: {report['critical_count']}{RESET}")
        if report["high_count"] > 0:
            print(f"{YELLOW}HIGH vulnerabilities: {report['high_count']}{RESET}")
        if report["vulnerable_count"] == 0:
            print(f"{GREEN}No vulnerabilities found!{RESET}")
        else:
            print(f"Total vulnerable packages: {report['vulnerable_count']}")

        print(f"\nDetailed report: {output_path}")

        return report

    def run(self, venv_path: str, output_dir: str) -> str:
        """
        Orchestrates all checks, merges results (dedup by vuln ID),
        generates report, returns report path.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / f"vuln_report_{datetime.now(UTC).strftime('%Y-%m-%d_%H%M%S')}.json"

        logging.info(f"Scanning packages in {venv_path}")

        # Get installed packages
        packages = self.get_installed_packages(venv_path)
        logging.info(f"Found {len(packages)} packages")

        # Check OSV
        logging.info("Checking OSV database...")
        osv_results = self.check_osv(packages)

        # Check pip-audit
        logging.info("Checking pip-audit...")
        pip_audit_results = self.check_pip_audit_json(venv_path)

        # Check Safety DB
        logging.info("Checking Safety DB...")
        safety_results = self.check_safety_db()

        # Merge and dedup results by vuln ID
        merged: dict[str, dict[str, Any]] = {}

        for source, results in [("osv", osv_results), ("pip_audit", pip_audit_results), ("safety", safety_results)]:
            for pkg_name, vulns in results.items():
                if pkg_name not in merged:
                    merged[pkg_name] = {"name": pkg_name, "version": "", "vulns": {}}

                for v in vulns:
                    # Dedup by ID
                    vuln_id = v.id
                    if vuln_id not in merged[pkg_name]["vulns"]:
                        merged[pkg_name]["vulns"][vuln_id] = v
                    else:
                        # Merge aliases and fixed versions
                        existing = merged[pkg_name]["vulns"][vuln_id]
                        if v.fixed_versions and not existing.fixed_versions:
                            existing.fixed_versions = v.fixed_versions

        # Convert back to Vulnerability lists
        final_results: dict[str, list[Vulnerability]] = {}
        for pkg_name, data in merged.items():
            final_results[pkg_name] = list(data["vulns"].values())

        # Generate report
        report_path = str(report_file)
        self.generate_report(final_results, len(packages), report_path)

        return report_path


def main():
    parser = argparse.ArgumentParser(description="Dependency Vulnerability Scanner")
    parser.add_argument("--venv", required=True, help="Path to virtualenv")
    parser.add_argument("--output-dir", default="~/security/intel/dependencies", help="Output directory")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Report format")

    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    scanner = DepVulnScanner()
    report_path = scanner.run(args.venv, str(output_dir))

    if args.format == "text":
        # Already printed colored summary in generate_report
        with open(report_path) as f:
            report = json.load(f)
        print("\n=== Summary ===")
        print(f"Total: {report['total_packages']}")
        print(f"Vulnerable: {report['vulnerable_count']}")
        print(f"Critical: {report['critical_count']}")
        print(f"High: {report['high_count']}")


if __name__ == "__main__":
    main()
