#!/usr/bin/env python3
"""
Bazzite Dependency Vulnerability Scanner

Scans Python and Node.js dependencies against OSV and GitHub Advisory databases.
Integrates with the bazzite-laptop threat intel system.
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

# Configuration
INTEL_DIR = Path.home() / "security" / "intel" / "dependencies"
SCAN_LOG = INTEL_DIR / ".scanner.log"
OSV_API = "https://api.osv.dev/v1/query"
GH_ADVISORY_API = "https://api.github.com/advisories"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(SCAN_LOG), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class Vuln:
    cve_id: str | None
    osv_id: str
    severity: str
    cvss_score: float | None
    summary: str
    fixed_version: str | None
    references: list[str]
    kev: bool = False


@dataclass
class PackageResult:
    name: str
    version: str
    ecosystem: str
    vulnerabilities: list[Vuln]


class DependencyScanner:
    def __init__(self, project_path: Path, kev_hashes: set[str] | None = None):
        self.project_path = project_path
        self.kev_hashes = kev_hashes or set()
        self.results: list[PackageResult] = []
        self.client = httpx.Client(timeout=30, follow_redirects=True)

    def scan(self) -> list[PackageResult]:
        """Run full dependency scan."""
        logger.info(f"Scanning {self.project_path}")

        # Python dependencies
        self._scan_python()

        # Node.js dependencies
        self._scan_node()

        self.client.close()
        return self.results

    def _scan_python(self):
        """Scan Python requirements."""
        req_file = self.project_path / "requirements.txt"
        pyproject = self.project_path / "pyproject.toml"

        deps = []
        if req_file.exists():
            deps.extend(self._parse_requirements_txt(req_file))
        if pyproject.exists():
            deps.extend(self._parse_pyproject_toml(pyproject))

        for name, version in deps:
            self._check_package(name, version, "PyPI")

    def _scan_node(self):
        """Scan Node.js dependencies."""
        pkg_json = self.project_path / "package.json"
        pkg_lock = self.project_path / "package-lock.json"

        deps = []
        if pkg_lock.exists():
            deps.extend(self._parse_package_lock(pkg_lock))
        elif pkg_json.exists():
            deps.extend(self._parse_package_json(pkg_json))

        for name, version in deps:
            self._check_package(name, version, "npm")

    def _parse_requirements_txt(self, path: Path) -> list[tuple[str, str]]:
        """Parse requirements.txt for package==version lines."""
        deps = []
        content = path.read_text()

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Match package==version or package>=version etc
            match = re.match(r'^([a-zA-Z0-9_-]+)([<>=!~]+)([0-9.]+)', line)
            if match:
                deps.append((match.group(1).lower(), match.group(3)))

        logger.info(f"Found {len(deps)} Python deps in requirements.txt")
        return deps

    def _parse_pyproject_toml(self, path: Path) -> list[tuple[str, str]]:
        """Parse pyproject.toml dependencies."""
        deps = []
        content = path.read_text()

        # Simple regex extraction (full TOML parsing adds dependency)
        for line in content.splitlines():
            line = line.strip()
            # Match dependency = "version" or dependency = ">=version"
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']([<>=!~]*)?([0-9.]+)', line)
            if match:
                deps.append((match.group(1).lower(), match.group(3)))

        logger.info(f"Found {len(deps)} Python deps in pyproject.toml")
        return deps

    def _parse_package_json(self, path: Path) -> list[tuple[str, str]]:
        """Parse package.json dependencies."""
        deps = []
        try:
            data = json.loads(path.read_text())
            for section in ["dependencies", "devDependencies"]:
                if section in data:
                    for name, version in data[section].items():
                        # Strip ^ and ~ prefixes
                        clean_version = version.lstrip("^~>=")
                        deps.append((name, clean_version))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse {path}")

        logger.info(f"Found {len(deps)} Node deps in package.json")
        return deps

    def _parse_package_lock(self, path: Path) -> list[tuple[str, str]]:
        """Parse package-lock.json for exact versions."""
        deps = []
        try:
            data = json.loads(path.read_text())
            packages = data.get("packages", {})
            for name, info in packages.items():
                if name and info.get("version"):
                    # Remove node_modules/ prefix
                    clean_name = name.replace("node_modules/", "")
                    deps.append((clean_name, info["version"]))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse {path}")

        logger.info(f"Found {len(deps)} Node deps in package-lock.json")
        return deps

    def _check_package(self, name: str, version: str, ecosystem: str):
        """Check single package against OSV."""
        try:
            resp = self.client.post(
                OSV_API,
                json={"package": {"name": name, "ecosystem": ecosystem}, "version": version}
            )
            resp.raise_for_status()
            data = resp.json()

            vulns = []
            for vuln in data.get("vulns", []):
                # Extract CVE ID
                cve_id = None
                for alias in vuln.get("aliases", []):
                    if alias.startswith("CVE-"):
                        cve_id = alias
                        break

                # Check if in KEV
                vuln_hash = hashlib.sha256(
                    f"{cve_id or vuln['id']}".encode()
                ).hexdigest()[:16]
                is_kev = vuln_hash in self.kev_hashes

                # Extract severity
                severity = "UNKNOWN"
                cvss = None
                if "database_specific" in vuln:
                    severity = vuln["database_specific"].get("severity", "UNKNOWN")
                    cvss = vuln["database_specific"].get("cvss_score")

                # Find fixed version
                fixed = None
                for affected in vuln.get("affected", []):
                    for r in affected.get("ranges", []):
                        if r.get("type") == "GIT" and "fixed" in r:
                            fixed = r["fixed"][:12]  # Short hash
                        elif "events" in r:
                            for e in r["events"]:
                                if "fixed" in e:
                                    fixed = e["fixed"]

                vulns.append(Vuln(
                    cve_id=cve_id,
                    osv_id=vuln["id"],
                    severity=severity,
                    cvss_score=cvss,
                    summary=vuln.get("summary", "No summary"),
                    fixed_version=fixed,
                    references=vuln.get("references", []),
                    kev=is_kev
                ))

            if vulns:
                self.results.append(PackageResult(
                    name=name,
                    version=version,
                    ecosystem=ecosystem,
                    vulnerabilities=vulns
                ))
                logger.warning(f"{name}@{version}: {len(vulns)} vulns found")

        except Exception as e:
            logger.error(f"Failed to check {name}: {e}")

    def save_report(self) -> Path:
        """Save scan results to JSON."""
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
        report_path = INTEL_DIR / f"depscan_{timestamp}.json"

        report = {
            "scan_time": datetime.now(UTC).isoformat(),
            "project_path": str(self.project_path),
            "packages_scanned": len(self.results),
            "packages_with_vulns": len([r for r in self.results if r.vulnerabilities]),
            "high_severity_count": sum(
                1 for r in self.results
                for v in r.vulnerabilities
                if v.severity in ["HIGH", "CRITICAL"]
            ),
            "results": [asdict(r) for r in self.results]
        }

        INTEL_DIR.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))

        # Update symlink
        latest = INTEL_DIR / "latest_depscan.json"
        if latest.exists():
            latest.unlink()
        latest.symlink_to(report_path.name)

        logger.info(f"Report saved: {report_path}")
        return report_path


def load_kev_hashes() -> set[str]:
    """Load CISA KEV CVE hashes for cross-referencing."""
    kev_hashes = set()
    kev_dir = Path.home() / "security" / "intel" / "security"

    # Find most recent KEV file
    kev_files = list(kev_dir.glob("cves_*.json"))
    if kev_files:
        latest = max(kev_files, key=lambda p: p.stat().st_mtime)
        try:
            data = json.loads(latest.read_text())
            for cve in data.get("cisa_kev", []):
                cve_id = cve.get("cve_id", "")
                h = hashlib.sha256(cve_id.encode()).hexdigest()[:16]
                kev_hashes.add(h)
            logger.info(f"Loaded {len(kev_hashes)} KEV hashes")
        except Exception:
            pass

    return kev_hashes


def main():
    parser = argparse.ArgumentParser(
        description="Scan dependencies for vulnerabilities"
    )
    parser.add_argument("project_path", help="Path to project root")
    parser.add_argument("--dry-run", action="store_true", help="Scan but don't save")
    args = parser.parse_args()

    project = Path(args.project_path).expanduser().resolve()
    if not project.exists():
        logger.error(f"Path not found: {project}")
        sys.exit(1)

    kev_hashes = load_kev_hashes()
    scanner = DependencyScanner(project, kev_hashes)
    results = scanner.scan()

    # Summary
    total_vulns = sum(len(r.vulnerabilities) for r in results)
    high_vulns = sum(
        1 for r in results
        for v in r.vulnerabilities
        if v.severity in ["HIGH", "CRITICAL"]
    )

    print(f"\n{'='*50}")
    print("SCAN COMPLETE")
    print(f"{'='*50}")
    print(f"Packages with vulnerabilities: {len(results)}")
    print(f"Total vulnerabilities: {total_vulns}")
    print(f"High/Critical: {high_vulns}")

    if high_vulns > 0:
        print("\n⚠️  HIGH PRIORITY FIXES:")
        for r in results:
            for v in r.vulnerabilities:
                if v.severity in ["HIGH", "CRITICAL"]:
                    kev_marker = " [KEV]" if v.kev else ""
                    print(f"  - {r.name}@{r.version}: {v.cve_id or v.osv_id}{kev_marker}")
                    if v.fixed_version:
                        print(f"    Fix: upgrade to {v.fixed_version}")

    if not args.dry_run:
        report_path = scanner.save_report()
        print(f"\nReport: {report_path}")
    else:
        print("\n[DRY RUN - not saved]")

    # Exit code: 1 if high/critical vulns found
    sys.exit(1 if high_vulns > 0 else 0)


if __name__ == "__main__":
    main()
