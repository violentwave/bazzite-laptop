"""Dependency vulnerability auditing using pip-audit.

Provides structured vulnerability scanning for Python dependencies,
writing JSON reports atomically and integrating with P37 alerting.
"""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.config import APP_NAME, SECURITY_DIR

logger = logging.getLogger(APP_NAME)

DEPAUDIT_REPORT_PREFIX = "dep-audit"
SBOM_PREFIX = "sbom"
RETENTION_DAYS = 90


@dataclass
class Vulnerability:
    """Single vulnerability details."""

    id: str
    description: str
    severity: str
    fix_versions: list[str]


@dataclass
class Package:
    """Package with vulnerability details."""

    name: str
    version: str
    vulns: list[Vulnerability]
    fix_versions: list[str]


@dataclass
class DepAuditResult:
    """Result of dependency audit."""

    vulnerable: int
    fixed: int
    packages: list[Package]
    generated_at: str
    sbom_path: str | None = None


def run_dep_audit(requirements_path: Path | None = None) -> DepAuditResult:
    """Run pip-audit and return structured findings.

    Args:
        requirements_path: Optional path to requirements.txt. If None, audits current venv.

    Returns:
        DepAuditResult with vulnerability summary.
    """
    venv_python = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"
    if not venv_python.exists():
        logger.warning("No .venv found, pip-audit may use system Python")
        venv_python = "python"

    cmd = [
        str(venv_python),
        "-m",
        "pip_audit",
        "--format=json",
        "--progress-spinner=off",
    ]
    if requirements_path and requirements_path.exists():
        cmd += ["-r", str(requirements_path)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode not in (0, 1):
            logger.error("pip-audit failed: %s", result.stderr)
            return DepAuditResult(
                vulnerable=0,
                fixed=0,
                packages=[],
                generated_at=datetime.now(UTC).isoformat(),
            )
    except subprocess.TimeoutExpired:
        logger.error("pip-audit timed out after 300s")
        return DepAuditResult(
            vulnerable=0,
            fixed=0,
            packages=[],
            generated_at=datetime.now(UTC).isoformat(),
        )
    except FileNotFoundError:
        logger.error("pip-audit not found in .venv")
        return DepAuditResult(
            vulnerable=0,
            fixed=0,
            packages=[],
            generated_at=datetime.now(UTC).isoformat(),
        )

    return _parse_pip_audit_output(result.stdout)


def _parse_pip_audit_output(json_output: str) -> DepAuditResult:
    """Parse pip-audit JSON output into structured result."""
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        logger.error("Failed to parse pip-audit JSON")
        return DepAuditResult(
            vulnerable=0,
            fixed=0,
            packages=[],
            generated_at=datetime.now(UTC).isoformat(),
        )

    vulnerable = 0
    fixed = 0
    packages: list[Package] = []

    deps = data.get("dependencies", [])
    for dep in deps:
        vulns = []
        for v in dep.get("vulns", []):
            vuln = Vulnerability(
                id=v.get("id", ""),
                description=v.get("description", ""),
                severity=v.get("severity", "unknown"),
                fix_versions=v.get("fix_versions", []),
            )
            vulns.append(vuln)

        if vulns:
            vulnerable += 1
        elif dep.get("version") and not vulns:
            fixed += 1

        if vulns or dep.get("version"):
            packages.append(
                Package(
                    name=dep.get("name", ""),
                    version=dep.get("version", ""),
                    vulns=vulns,
                    fix_versions=dep.get("fix_versions", []),
                )
            )

    return DepAuditResult(
        vulnerable=vulnerable,
        fixed=fixed,
        packages=packages,
        generated_at=datetime.now(UTC).isoformat(),
    )


def write_report(result: DepAuditResult) -> tuple[Path, bool]:
    """Write audit result to JSON file atomically and dispatch alert if vulnerabilities found.

    Args:
        result: The audit result to write.

    Returns:
        Tuple of (Path to the written file, whether alert was dispatched).
    """
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    output_path = SECURITY_DIR / f"{DEPAUDIT_REPORT_PREFIX}-{today}.json"

    data = {
        "vulnerable": result.vulnerable,
        "fixed": result.fixed,
        "packages": [
            {
                "name": p.name,
                "version": p.version,
                "vulns": [
                    {
                        "id": v.id,
                        "description": v.description,
                        "severity": v.severity,
                        "fix_versions": v.fix_versions,
                    }
                    for v in p.vulns
                ],
                "fix_versions": p.fix_versions,
            }
            for p in result.packages
        ],
        "generated_at": result.generated_at,
    }

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=output_path.parent,
        prefix=".dep-audit-",
        suffix=".tmp",
        delete=False,
    ) as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        temp_path = Path(f.name)

    os.replace(temp_path, output_path)
    logger.info("Wrote dep-audit report to %s", output_path)

    alert_dispatched = False
    if result.vulnerable > 0:
        try:
            from ai.workflows.triggers import EventBus

            bus = EventBus()
            bus.publish("dep_vuln_found", {"vulnerable": result.vulnerable})
            alert_dispatched = True
            logger.info(
                "Dispatched dep_vuln_found alert for %d vulnerable packages", result.vulnerable
            )
        except Exception as e:
            logger.warning("Failed to dispatch dep_vuln_found alert: %s", e)

    return output_path, alert_dispatched


def generate_sbom() -> Path:
    """Generate CycloneDX-lite SBOM from pip list.

    Returns:
        Path to the generated SBOM file.
    """
    venv_python = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"

    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        packages = json.loads(result.stdout)
    except Exception as e:
        logger.error("Failed to generate SBOM: %s", e)
        raise

    from importlib.metadata import version as get_version

    components = []
    for pkg in packages:
        name = pkg["name"]
        ver = pkg["version"]

        try:
            license_str = get_version(name).metadata.get("License-Expression")
            if not license_str:
                license_str = get_version(name).metadata.get("License")
        except Exception:
            license_str = None

        components.append(
            {
                "name": name,
                "version": ver,
                "purl": f"pkg:pypi/{name}@{ver}",
                "licenses": [{"license": {"id": license_str}}] if license_str else [],
            }
        )

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "tools": [{"name": "bazzite-sbom-generator", "version": "1.0"}],
        },
        "components": components,
    }

    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    sbom_path = SECURITY_DIR / f"{SBOM_PREFIX}-{today}.json"

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=sbom_path.parent,
        prefix=".sbom-",
        suffix=".tmp",
        delete=False,
    ) as f:
        json.dump(sbom, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        temp_path = Path(f.name)

    os.replace(temp_path, sbom_path)
    logger.info("Generated SBOM at %s", sbom_path)

    return sbom_path


def prune_old_reports() -> None:
    """Remove reports older than RETENTION_DAYS."""
    cutoff = datetime.now(UTC).timestamp() - (RETENTION_DAYS * 86400)

    for pattern in [DEPAUDIT_REPORT_PREFIX, SBOM_PREFIX]:
        for f in SECURITY_DIR.glob(f"{pattern}-*.json"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                logger.info("Pruned old report: %s", f.name)


def get_latest_report() -> DepAuditResult | None:
    """Read the most recent audit report."""
    reports = sorted(SECURITY_DIR.glob(f"{DEPAUDIT_REPORT_PREFIX}-*.json"))
    if not reports:
        return None

    latest = reports[-1]
    try:
        data = json.loads(latest.read_text())
        packages = []
        for p in data.get("packages", []):
            packages.append(
                Package(
                    name=p["name"],
                    version=p["version"],
                    vulns=[Vulnerability(**v) for v in p.get("vulns", [])],
                    fix_versions=p.get("fix_versions", []),
                )
            )
        return DepAuditResult(
            vulnerable=data.get("vulnerable", 0),
            fixed=data.get("fixed", 0),
            packages=packages,
            generated_at=data.get("generated_at", ""),
        )
    except Exception:
        return None


def get_report_history(limit: int = 30) -> list[dict[str, Any]]:
    """List recent audit reports.

    Args:
        limit: Maximum number of reports to return.

    Returns:
        List of report metadata dictionaries.
    """
    reports = sorted(SECURITY_DIR.glob(f"{DEPAUDIT_REPORT_PREFIX}-*.json"), reverse=True)
    history = []

    for report in reports[:limit]:
        try:
            data = json.loads(report.read_text())
            history.append(
                {
                    "filename": report.name,
                    "date": report.stem.replace(f"{DEPAUDIT_REPORT_PREFIX}-", ""),
                    "vulnerable": data.get("vulnerable", 0),
                    "fixed": data.get("fixed", 0),
                    "packages": len(data.get("packages", [])),
                    "generated_at": data.get("generated_at", ""),
                }
            )
        except Exception as e:
            logger.warning("Skipping unreadable report %s: %s", report.name, e)
            continue

    return history
