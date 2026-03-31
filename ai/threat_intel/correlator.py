"""Threat intelligence correlation engine.

Cross-references IOCs (hash, IP, URL, CVE) across existing lookup modules
to build a correlation graph. Uses static MITRE ATT&CK mapping.

Usage:
    from ai.threat_intel.correlator import correlate_ioc, CorrelationReport
    report = correlate_ioc("abc123...", "hash")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ai.config import APP_NAME, CONFIGS_DIR
from ai.threat_intel.cve_scanner import scan_cves
from ai.threat_intel.ioc_lookup import lookup_url
from ai.threat_intel.ip_lookup import lookup_ip
from ai.threat_intel.lookup import lookup_hash

logger = logging.getLogger(APP_NAME)

# ── MITRE ATT&CK Mapping ───────────────────────────────────────────────────────


def _load_mitre_map() -> dict[str, dict[str, str]]:
    """Load static MITRE ATT&CK mapping from config."""
    try:
        path = CONFIGS_DIR / "mitre-attack-map.json"
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load MITRE ATT&CK map: %s", e)
    return {}


_MITRE_MAP = _load_mitre_map()


# ── Data Models ─────────────────────────────────────────────────────────────────


@dataclass
class LinkedIOC:
    """A single linked IOC within a correlation report."""

    ioc: str
    ioc_type: str
    source: str
    relationship: str  # "related", "parent", "child", "observed"
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationReport:
    """Structured correlation report for an IOC.

    Contains the primary IOC, linked IOCs from cross-referencing,
    MITRE ATT&CK technique mappings, and confidence scores.
    """

    primary_ioc: str
    primary_type: str
    linked_iocs: list[LinkedIOC] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    risk_level: str = "unknown"  # low, medium, high, critical
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    raw_findings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "primary_ioc": self.primary_ioc,
            "primary_type": self.primary_type,
            "linked_iocs": [
                {
                    "ioc": li.ioc,
                    "type": li.ioc_type,
                    "source": li.source,
                    "relationship": li.relationship,
                    "confidence": li.confidence,
                    "metadata": li.metadata,
                }
                for li in self.linked_iocs
            ],
            "mitre_techniques": self.mitre_techniques,
            "overall_confidence": self.overall_confidence,
            "risk_level": self.risk_level,
            "generated_at": self.generated_at,
        }

    @property
    def has_correlations(self) -> bool:
        """True if any linked IOCs were found."""
        return len(self.linked_iocs) > 0


# ── Correlation Logic ───────────────────────────────────────────────────────────


def _map_mitre_for_ioc(ioc_type: str, metadata: dict[str, Any]) -> list[str]:
    """Map IOC metadata to MITRE ATT&CK techniques."""
    techniques = []

    if ioc_type == "hash":
        tags = metadata.get("tags", [])
        family = metadata.get("family", "")
        if any("ransomware" in t.lower() for t in tags):
            techniques.append("T1486")
        if any("trojan" in t.lower() for t in tags):
            techniques.append("T1059")
        if family:
            for ioc_type_key, mappings in _MITRE_MAP.items():
                if ioc_type_key == "hash":
                    for family_pattern, tech in mappings.items():
                        if family_pattern.lower() in family.lower():
                            techniques.append(tech)

    elif ioc_type == "ip":
        score = metadata.get("abuse_score", 0)
        classification = metadata.get("greynoise_classification", "")
        if score > 70:
            techniques.append("T1072")
        if classification == "malicious":
            techniques.append("T1190")
        if metadata.get("ports"):
            techniques.append("T1043")

    elif ioc_type == "url":
        if metadata.get("threat_type"):
            techniques.append("T1102")
        if metadata.get("malware_family"):
            techniques.append("T1588")

    elif ioc_type == "cve":
        cvss = metadata.get("cvss_score", 0)
        if cvss >= 9.0:
            techniques.append("T1190")
        elif cvss >= 7.0:
            techniques.append("T1210")

    return list(set(techniques))[:5]  # Limit to 5 techniques


def _calculate_risk_level(ioc_type: str, confidence: float, metadata: dict[str, Any]) -> str:
    """Calculate risk level based on IOC type and metadata."""
    if ioc_type == "cve":
        cvss = metadata.get("cvss_score", 0)
        if cvss >= 9.0:
            return "critical"
        elif cvss >= 7.0:
            return "high"
        elif cvss >= 4.0:
            return "medium"
        return "low"

    if ioc_type == "hash":
        detection = metadata.get("detection_ratio", "")
        if detection and "/" in detection:
            try:
                parts = detection.split("/")
                ratio = int(parts[0]) / int(parts[1])
                if ratio > 0.5:
                    return "critical"
                elif ratio > 0.2:
                    return "high"
                elif ratio > 0.05:
                    return "medium"
            except (ValueError, IndexError):
                pass

    if ioc_type == "ip":
        if confidence > 0.8:
            return "high"
        elif confidence > 0.5:
            return "medium"
        return "low"

    if ioc_type == "url":
        if metadata.get("threat_type") == "malware":
            return "high"
        elif metadata.get("threat_type"):
            return "medium"
        return "low"

    return "unknown"


def correlate_ioc(ioc: str, ioc_type: str) -> CorrelationReport:
    """Correlate an IOC across threat intel sources.

    Args:
        ioc: The IOC value (hash, IP, URL, or CVE ID)
        ioc_type: Type of IOC - "hash", "ip", "url", or "cve"

    Returns:
        CorrelationReport with linked IOCs and MITRE mappings
    """
    linked: list[LinkedIOC] = []
    raw_findings: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

    if ioc_type == "hash":
        report = lookup_hash(ioc)
        if report and report.has_data:
            metadata = {
                "family": report.family,
                "tags": report.tags,
                "detection_ratio": report.detection_ratio,
                "risk_level": report.risk_level,
                "description": report.description,
            }
            linked.append(
                LinkedIOC(
                    ioc=ioc,
                    ioc_type="hash",
                    source=report.source,
                    relationship="primary",
                    confidence=0.9 if report.source != "none" else 0.0,
                    metadata=metadata,
                )
            )
            raw_findings["hash_lookup"] = {
                "source": report.source,
                "family": report.family,
                "detection": report.detection_ratio,
            }

    elif ioc_type == "ip":
        result = lookup_ip(ioc)
        if result:
            metadata = {
                "abuse_score": result.abuse_score,
                "greynoise_classification": result.greynoise_classification,
                "recommendation": result.recommendation,
                "ports": result.ports,
                "vulns": result.vulns,
            }
            linked.append(
                LinkedIOC(
                    ioc=ioc,
                    ioc_type="ip",
                    source="abuseipdb" if result.abuse_score else "none",
                    relationship="primary",
                    confidence=min(result.abuse_score / 100, 1.0) if result.abuse_score else 0.0,
                    metadata=metadata,
                )
            )
            raw_findings["ip_lookup"] = {
                "abuse_score": result.abuse_score,
                "classification": result.greynoise_classification,
            }

    elif ioc_type == "url":
        result = lookup_url(ioc)
        if result:
            metadata = {
                "threat_type": result.threat_type,
                "malware_family": result.malware_family,
                "risk_level": result.risk_level,
                "tags": result.tags,
            }
            linked.append(
                LinkedIOC(
                    ioc=ioc,
                    ioc_type="url",
                    source=result.source,
                    relationship="primary",
                    confidence=0.7 if result.threat_type else 0.0,
                    metadata=metadata,
                )
            )
            raw_findings["url_lookup"] = {
                "threat_type": result.threat_type,
                "malware_family": result.malware_family,
            }

    elif ioc_type == "cve":
        cves = scan_cves()
        for finding in cves.get("findings", []):
            if ioc.upper() in finding.get("cve_id", "").upper():
                metadata = {
                    "cvss_score": finding.get("cvss", 0),
                    "severity": finding.get("severity", ""),
                    "description": finding.get("description", ""),
                    "in_kev": finding.get("in_kev", False),
                    "affected_packages": finding.get("affected_packages", []),
                }
                linked.append(
                    LinkedIOC(
                        ioc=ioc,
                        ioc_type="cve",
                        source="nvd",
                        relationship="primary",
                        confidence=0.8 if finding.get("cvss", 0) > 0 else 0.0,
                        metadata=metadata,
                    )
                )
                raw_findings["cve_lookup"] = {
                    "cvss": finding.get("cvss"),
                    "in_kev": finding.get("in_kev"),
                }
                break

    techniques = _map_mitre_for_ioc(ioc_type, metadata)
    confidence = sum(li.confidence for li in linked) / max(len(linked), 1) if linked else 0.0
    risk = _calculate_risk_level(ioc_type, confidence, metadata)

    return CorrelationReport(
        primary_ioc=ioc,
        primary_type=ioc_type,
        linked_iocs=linked,
        mitre_techniques=techniques,
        overall_confidence=confidence,
        risk_level=risk,
        raw_findings=raw_findings,
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Correlate threat intelligence IOCs")
    parser.add_argument("ioc", help="IOC value (hash, IP, URL, CVE ID)")
    parser.add_argument(
        "--type",
        "-t",
        choices=["hash", "ip", "url", "cve"],
        default="hash",
        help="IOC type",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )
    args = parser.parse_args()

    report = correlate_ioc(args.ioc, args.type)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Primary IOC: {report.primary_ioc} ({report.primary_type})")
        print(f"Risk Level: {report.risk_level}")
        print(f"Confidence: {report.overall_confidence:.2f}")
        print(f"Linked IOCs: {len(report.linked_iocs)}")
        print(f"MITRE Techniques: {', '.join(report.mitre_techniques) or 'none'}")


if __name__ == "__main__":
    main()
