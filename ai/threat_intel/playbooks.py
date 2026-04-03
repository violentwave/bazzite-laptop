"""Response playbooks for threat findings.

Provides recommended response steps based on threat type, severity, and
available context. Designed for recommendation only - no auto-remediation.

Usage:
    from ai.threat_intel.playbooks import get_response_plan, RecommendedAction
    response = get_response_plan("cve", "CVE-2026-12345")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

# ── Data Models ─────────────────────────────────────────────────────────────────


@dataclass
class ActionStep:
    """A single step in a response plan."""

    step_number: int
    action: str
    description: str
    tool: str | None = None
    urgency: str = "medium"  # low, medium, high, critical
    automated: bool = False


@dataclass
class RecommendedAction:
    """Structured response plan for a threat finding."""

    finding_type: str  # cve, malware, suspicious_ip, suspicious_url
    finding_id: str
    urgency: str  # low, medium, high, critical
    summary: str
    action_steps: list[ActionStep] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    compensating_controls: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "finding_type": self.finding_type,
            "finding_id": self.finding_id,
            "urgency": self.urgency,
            "summary": self.summary,
            "action_steps": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "description": s.description,
                    "tool": s.tool,
                    "urgency": s.urgency,
                    "automated": s.automated,
                }
                for s in self.action_steps
            ],
            "risk_factors": self.risk_factors,
            "compensating_controls": self.compensating_controls,
            "generated_at": self.generated_at,
        }


# ── Playbook Templates ──────────────────────────────────────────────────────────


def _playbook_kev_cve(cve_id: str, cvss: float, packages: list[str]) -> RecommendedAction:
    """Playbook for KEV CVE (Known Exploited Vulnerability)."""
    steps = [
        ActionStep(
            step_number=1,
            action="Verify KEV status",
            description=f"Confirm {cve_id} is in CISA KEV catalog",
            tool="security.cve_check",
            urgency="critical",
            automated=True,
        ),
        ActionStep(
            step_number=2,
            action="Check Fedora updates",
            description="Check if security patch is available via Bodhi",
            tool="system.fedora_updates",
            urgency="high",
            automated=True,
        ),
        ActionStep(
            step_number=3,
            action="Assess exploitability",
            description="Check for public exploits (Metasploit, POC)",
            tool=None,
            urgency="high",
            automated=False,
        ),
        ActionStep(
            step_number=4,
            action="Apply mitigations",
            description="Implement compensating controls if no patch available",
            tool=None,
            urgency="high",
            automated=False,
        ),
    ]

    if packages:
        steps.append(
            ActionStep(
                step_number=5,
                action="Update affected packages",
                description=f"Update: {', '.join(packages[:3])}",
                tool="system.fedora_updates",
                urgency="critical",
                automated=False,
            )
        )

    return RecommendedAction(
        finding_type="cve",
        finding_id=cve_id,
        urgency="critical" if cvss >= 9.0 else "high",
        summary=f"KEV CVE {cve_id} requires immediate attention",
        action_steps=steps,
        risk_factors=[
            f"CVSS {cvss:.1f} - Critical severity",
            "In CISA KEV - actively exploited",
            f"Affects packages: {', '.join(packages[:3]) if packages else 'unknown'}",
        ],
        compensating_controls=[
            "Network segmentation",
            "Enhanced monitoring",
            "Limit exposed services",
            "Web application firewall",
        ],
    )


def _playbook_malware_hash(hash_value: str, family: str, detection: str) -> RecommendedAction:
    """Playbook for malicious file hash in quarantine."""
    steps = [
        ActionStep(
            step_number=1,
            action="Analyze in sandbox",
            description="Submit to Hybrid Analysis for behavior analysis",
            tool="security.sandbox_submit",
            urgency="high",
            automated=True,
        ),
        ActionStep(
            step_number=2,
            action="Check for related IOCs",
            description="Search for IPs/URLs associated with this malware family",
            tool="security.correlate",
            urgency="high",
            automated=True,
        ),
        ActionStep(
            step_number=3,
            action="Block network IOCs",
            description="Add related IPs/URLs to firewall blocklist",
            tool=None,
            urgency="medium",
            automated=False,
        ),
        ActionStep(
            step_number=4,
            action="Scan for persistence",
            description="Check for scheduled tasks, services, startup items",
            tool="security.health_snapshot",
            urgency="high",
            automated=False,
        ),
        ActionStep(
            step_number=5,
            action="Review recent files",
            description="Check for similar files downloaded recently",
            tool=None,
            urgency="medium",
            automated=False,
        ),
    ]

    return RecommendedAction(
        finding_type="malware",
        finding_id=hash_value,
        urgency="high",
        summary=f"Malicious file detected: {family or 'unknown family'}",
        action_steps=steps,
        risk_factors=[
            f"Family: {family or 'unknown'}",
            f"Detection: {detection}",
            "Potential for lateral movement",
            "May indicate initial access vector",
        ],
        compensating_controls=[
            "Quarantine confirmed",
            "Block related domains",
            "Monitor for beaconing",
            "Review email/attachment logs",
        ],
    )


def _playbook_suspicious_ip(ip: str, abuse_score: int, ports: list[int]) -> RecommendedAction:
    """Playbook for suspicious IP."""
    steps = [
        ActionStep(
            step_number=1,
            action="Gather threat intelligence",
            description="Query multiple threat sources for IP reputation",
            tool="security.ip_lookup",
            urgency="medium",
            automated=True,
        ),
        ActionStep(
            step_number=2,
            action="Check associated URLs",
            description="Find URLs linked to this IP for pattern analysis",
            tool="security.correlate",
            urgency="medium",
            automated=True,
        ),
        ActionStep(
            step_number=3,
            action="Check GreyNoise context",
            description="Determine if IP is threat actor or benign",
            tool="security.ip_lookup",
            urgency="medium",
            automated=True,
        ),
        ActionStep(
            step_number=4,
            action="Block at firewall",
            description="Add IP to drop list if confirmed malicious",
            tool=None,
            urgency="high" if abuse_score > 70 else "medium",
            automated=False,
        ),
    ]

    if ports:
        steps.append(
            ActionStep(
                step_number=5,
                action="Review exposed services",
                description=f"Check what's listening on: {ports[:3]}",
                tool="security.health_snapshot",
                urgency="medium",
                automated=False,
            )
        )

    return RecommendedAction(
        finding_type="suspicious_ip",
        finding_id=ip,
        urgency="high" if abuse_score > 70 else "medium",
        summary=f"Suspicious IP detected with score {abuse_score}",
        action_steps=steps,
        risk_factors=[
            f"Abuse score: {abuse_score}/100",
            f"Open ports: {len(ports)}",
            "Possible command and control",
            "Potential scanning activity",
        ],
        compensating_controls=[
            "Firewall rate limiting",
            "IDS/IPS monitoring",
            "Geo-blocking non-essential",
        ],
    )


def _playbook_suspicious_url(url: str, threat_type: str, malware_family: str) -> RecommendedAction:
    """Playbook for suspicious URL."""
    steps = [
        ActionStep(
            step_number=1,
            action="Analyze URL",
            description="Check URL reputation and categorization",
            tool="security.url_lookup",
            urgency="medium",
            automated=True,
        ),
        ActionStep(
            step_number=2,
            action="Check for hashes",
            description="Look up any executable links from this URL",
            tool="security.correlate",
            urgency="high",
            automated=True,
        ),
        ActionStep(
            step_number=3,
            action="Block domain",
            description="Add domain to blocklist if malicious",
            tool=None,
            urgency="high" if threat_type == "malware" else "medium",
            automated=False,
        ),
        ActionStep(
            step_number=4,
            action="Notify users",
            description="Alert users who may have visited this URL",
            tool=None,
            urgency="medium",
            automated=False,
        ),
    ]

    return RecommendedAction(
        finding_type="suspicious_url",
        finding_id=url,
        urgency="high" if threat_type == "malware" else "medium",
        summary=f"Suspicious URL: {threat_type or 'unknown'}",
        action_steps=steps,
        risk_factors=[
            f"Threat type: {threat_type or 'unknown'}",
            f"Malware family: {malware_family or 'unknown'}",
            "Potential phishing or malware delivery",
        ],
        compensating_controls=[
            "DNS sinkhole",
            "Browser isolation",
            "URL filtering",
        ],
    )


def _playbook_generic_cve(cve_id: str, cvss: float, packages: list[str]) -> RecommendedAction:
    """Playbook for non-KEV CVE."""
    steps = [
        ActionStep(
            step_number=1,
            action="Check CVE details",
            description=f"Review {cve_id} from NVD for affected versions",
            tool="security.cve_check",
            urgency="medium",
            automated=True,
        ),
        ActionStep(
            step_number=2,
            action="Check Fedora updates",
            description="See if patch is available in stable repos",
            tool="system.fedora_updates",
            urgency="medium",
            automated=True,
        ),
        ActionStep(
            step_number=3,
            action="Plan remediation",
            description="Schedule update window if patch available",
            tool=None,
            urgency="low",
            automated=False,
        ),
    ]

    return RecommendedAction(
        finding_type="cve",
        finding_id=cve_id,
        urgency="medium" if cvss >= 7.0 else "low",
        summary=f"CVE {cve_id} with CVSS {cvss:.1f}",
        action_steps=steps,
        risk_factors=[
            f"CVSS {cvss:.1f}",
            f"Affects: {', '.join(packages[:3]) if packages else 'unknown packages'}",
        ],
        compensating_controls=[
            "Monitor for patches",
            "Reduce attack surface",
            "Enable SELinux",
        ],
    )


# ── Main Entry Point ───────────────────────────────────────────────────────────


def get_response_plan(
    finding_type: str, finding_id: str, metadata: dict[str, Any] | None = None
) -> RecommendedAction:
    """Get recommended response plan for a threat finding.

    Args:
        finding_type: Type of finding - "cve", "malware", "suspicious_ip", "suspicious_url"
        finding_id: The identifier (CVE ID, hash, IP, URL)
        metadata: Optional additional context (cvss, family, abuse_score, etc.)

    Returns:
        RecommendedAction with response steps and urgency
    """
    if metadata is None:
        metadata = {}

    if finding_type == "cve":
        cvss_raw = metadata.get("cvss_score", metadata.get("cvss", 0))
        try:
            cvss = float(cvss_raw)
        except (TypeError, ValueError):
            cvss = 0.0
        in_kev = metadata.get("in_kev", False)
        packages = metadata.get("affected_packages", [])

        if in_kev or cvss >= 9.0:
            return _playbook_kev_cve(finding_id, cvss, packages)
        else:
            return _playbook_generic_cve(finding_id, cvss, packages)

    elif finding_type == "malware":
        family = metadata.get("family", "")
        detection = metadata.get("detection_ratio", "")
        return _playbook_malware_hash(finding_id, family, detection)

    elif finding_type == "suspicious_ip":
        abuse_score = metadata.get("abuse_score", 0)
        ports = metadata.get("ports", [])
        return _playbook_suspicious_ip(finding_id, abuse_score, ports)

    elif finding_type == "suspicious_url":
        threat_type = metadata.get("threat_type", "")
        malware_family = metadata.get("malware_family", "")
        return _playbook_suspicious_url(finding_id, threat_type, malware_family)

    # Fallback for unknown types
    return RecommendedAction(
        finding_type=finding_type,
        finding_id=finding_id,
        urgency="low",
        summary=f"Unknown finding type: {finding_type}",
        action_steps=[
            ActionStep(
                step_number=1,
                action="Investigate manually",
                description="Review finding in detail",
                tool=None,
                urgency="low",
                automated=False,
            )
        ],
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate response playbooks for threats")
    parser.add_argument(
        "finding_type", choices=["cve", "malware", "suspicious_ip", "suspicious_url"]
    )
    parser.add_argument("finding_id", help="Finding identifier (CVE ID, hash, IP, URL)")
    parser.add_argument("--cvss", type=float, default=0, help="CVSS score for CVE")
    parser.add_argument("--in-kev", action="store_true", help="CVE is in KEV catalog")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    metadata = {}
    if args.finding_type == "cve":
        metadata = {"cvss": args.cvss, "in_kev": args.in_kev}

    response = get_response_plan(args.finding_type, args.finding_id, metadata)

    if args.json:
        print(json.dumps(response.to_dict(), indent=2))
    else:
        print(f"Finding: {response.finding_type} / {response.finding_id}")
        print(f"Urgency: {response.urgency}")
        print(f"Summary: {response.summary}")
        print("\nAction Steps:")
        for step in response.action_steps:
            print(f"  {step.step_number}. [{step.urgency}] {step.action}")
            print(f"     {step.description}")

    import sys  # noqa: PLC0415
    sys.exit(0)


if __name__ == "__main__":
    main()


# Alias for backward-compatible imports
get_playbook = get_response_plan
