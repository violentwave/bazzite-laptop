"""Comprehensive tests for ai/threat_intel/playbooks.py - response planning."""

import json

from ai.threat_intel.playbooks import (
    ActionStep,
    RecommendedAction,
    _playbook_generic_cve,
    _playbook_kev_cve,
    _playbook_malware_hash,
    _playbook_suspicious_ip,
    _playbook_suspicious_url,
    get_response_plan,
)


class TestActionStep:
    """Test ActionStep dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        step = ActionStep(
            step_number=1,
            action="Test action",
            description="Test description"
        )

        assert step.step_number == 1
        assert step.tool is None
        assert step.urgency == "medium"
        assert step.automated is False

    def test_custom_values(self):
        """Should accept custom values."""
        step = ActionStep(
            step_number=5,
            action="Deploy patch",
            description="Apply security update",
            tool="system.fedora_updates",
            urgency="critical",
            automated=True
        )

        assert step.urgency == "critical"
        assert step.automated is True


class TestRecommendedAction:
    """Test RecommendedAction dataclass."""

    def test_to_dict_serialization(self):
        """Should serialize to dict for JSON output."""
        action = RecommendedAction(
            finding_type="cve",
            finding_id="CVE-2026-12345",
            urgency="high",
            summary="Critical vulnerability",
            action_steps=[
                ActionStep(1, "Verify", "Check status", tool="cve_check", urgency="high")
            ],
            risk_factors=["CVSS 9.0", "Publicly exploited"],
            compensating_controls=["Firewall rules", "IDS monitoring"]
        )

        result = action.to_dict()

        assert result["finding_type"] == "cve"
        assert result["finding_id"] == "CVE-2026-12345"
        assert result["urgency"] == "high"
        assert len(result["action_steps"]) == 1
        assert result["action_steps"][0]["step"] == 1
        assert len(result["risk_factors"]) == 2
        assert "generated_at" in result

    def test_generated_at_is_iso_format(self):
        """generated_at should be ISO format timestamp."""
        action = RecommendedAction(
            finding_type="cve",
            finding_id="CVE-2026-1",
            urgency="low",
            summary="Test"
        )

        # Should be parseable as ISO timestamp
        from datetime import datetime
        dt = datetime.fromisoformat(action.generated_at.replace("Z", "+00:00"))
        assert dt is not None


class TestKEVCVEPlaybook:
    """Test KEV CVE playbook generation."""

    def test_critical_urgency_for_high_cvss(self):
        """Should set critical urgency for CVSS >= 9.0."""
        plan = _playbook_kev_cve("CVE-2026-9999", cvss=9.5, packages=["nginx"])

        assert plan.urgency == "critical"
        assert plan.finding_type == "cve"
        assert "KEV" in plan.summary

    def test_high_urgency_for_medium_cvss(self):
        """Should set high urgency for CVSS < 9.0."""
        plan = _playbook_kev_cve("CVE-2026-8888", cvss=7.5, packages=["apache"])

        assert plan.urgency == "high"

    def test_includes_affected_packages(self):
        """Should include affected packages in steps."""
        packages = ["nginx", "apache", "mysql"]
        plan = _playbook_kev_cve("CVE-2026-1", cvss=9.0, packages=packages)

        # Should have update step with packages
        update_step = next((s for s in plan.action_steps if "Update" in s.action), None)
        assert update_step is not None
        assert "nginx" in update_step.description

    def test_includes_kev_verification_step(self):
        """Should include KEV verification as first step."""
        plan = _playbook_kev_cve("CVE-2026-1", cvss=9.0, packages=[])

        assert plan.action_steps[0].action == "Verify KEV status"
        assert plan.action_steps[0].urgency == "critical"

    def test_risk_factors_include_cvss(self):
        """Risk factors should include CVSS score."""
        plan = _playbook_kev_cve("CVE-2026-1", cvss=9.2, packages=["test"])

        assert any("9.2" in factor for factor in plan.risk_factors)
        assert any("KEV" in factor for factor in plan.risk_factors)


class TestMalwarePlaybook:
    """Test malware hash playbook generation."""

    def test_urgency_is_high(self):
        """Malware findings should have high urgency."""
        plan = _playbook_malware_hash("abc123", family="Eicar", detection="10/72")

        assert plan.urgency == "high"

    def test_includes_sandbox_analysis(self):
        """Should include sandbox analysis step."""
        plan = _playbook_malware_hash("abc123", family="", detection="")

        sandbox_step = plan.action_steps[0]
        assert "sandbox" in sandbox_step.action.lower()
        assert "Hybrid Analysis" in sandbox_step.description

    def test_includes_family_in_summary(self):
        """Should include malware family in summary."""
        plan = _playbook_malware_hash("deadbeef", family="Emotet", detection="")

        assert "Emotet" in plan.summary

    def test_handles_unknown_family(self):
        """Should handle missing family gracefully."""
        plan = _playbook_malware_hash("abc", family="", detection="15/72")

        assert "unknown family" in plan.summary

    def test_risk_factors_include_detection(self):
        """Should include detection ratio in risk factors."""
        plan = _playbook_malware_hash("abc", family="Test", detection="15/72")

        assert any("15/72" in factor for factor in plan.risk_factors)


class TestSuspiciousIPPlaybook:
    """Test suspicious IP playbook generation."""

    def test_high_urgency_for_high_abuse_score(self):
        """abuse_score > 70 should trigger high urgency."""
        plan = _playbook_suspicious_ip("1.2.3.4", abuse_score=85, ports=[22, 80])

        assert plan.urgency == "high"

    def test_medium_urgency_for_low_abuse_score(self):
        """abuse_score <= 70 should trigger medium urgency."""
        plan = _playbook_suspicious_ip("1.2.3.4", abuse_score=50, ports=[])

        assert plan.urgency == "medium"

    def test_includes_port_review_when_ports_present(self):
        """Should add port review step when ports are provided."""
        plan = _playbook_suspicious_ip("1.2.3.4", abuse_score=60, ports=[22, 80, 443])

        port_step = next(
            (s for s in plan.action_steps if "exposed services" in s.action.lower()),
            None
        )
        assert port_step is not None
        assert "22" in port_step.description

    def test_no_port_step_when_no_ports(self):
        """Should not include port step when ports list is empty."""
        plan = _playbook_suspicious_ip("1.2.3.4", abuse_score=60, ports=[])

        port_step = next(
            (s for s in plan.action_steps if "exposed services" in s.action.lower()),
            None
        )
        assert port_step is None

    def test_includes_greynoise_check(self):
        """Should include GreyNoise context check."""
        plan = _playbook_suspicious_ip("1.2.3.4", abuse_score=60, ports=[])

        greynoise_step = next(
            (s for s in plan.action_steps if "GreyNoise" in s.action),
            None
        )
        assert greynoise_step is not None


class TestSuspiciousURLPlaybook:
    """Test suspicious URL playbook generation."""

    def test_high_urgency_for_malware_type(self):
        """threat_type='malware' should trigger high urgency."""
        plan = _playbook_suspicious_url(
            "http://evil.com",
            threat_type="malware",
            malware_family="Emotet"
        )

        assert plan.urgency == "high"

    def test_medium_urgency_for_other_types(self):
        """Other threat types should trigger medium urgency."""
        plan = _playbook_suspicious_url(
            "http://phish.com",
            threat_type="phishing",
            malware_family=""
        )

        assert plan.urgency == "medium"

    def test_includes_malware_family_in_risks(self):
        """Should include malware family in risk factors."""
        plan = _playbook_suspicious_url(
            "http://test.com",
            threat_type="malware",
            malware_family="TrickBot"
        )

        assert any("TrickBot" in factor for factor in plan.risk_factors)


class TestGenericCVEPlaybook:
    """Test non-KEV CVE playbook."""

    def test_medium_urgency_for_high_cvss(self):
        """CVSS >= 7.0 should trigger medium urgency."""
        plan = _playbook_generic_cve("CVE-2026-1", cvss=7.5, packages=["test"])

        assert plan.urgency == "medium"

    def test_low_urgency_for_low_cvss(self):
        """CVSS < 7.0 should trigger low urgency."""
        plan = _playbook_generic_cve("CVE-2026-2", cvss=5.0, packages=["test"])

        assert plan.urgency == "low"

    def test_fewer_steps_than_kev(self):
        """Generic CVE should have fewer steps than KEV CVE."""
        plan = _playbook_generic_cve("CVE-2026-1", cvss=7.0, packages=["test"])

        assert len(plan.action_steps) <= 4


class TestGetResponsePlan:
    """Test main entry point for playbook selection."""

    def test_routes_to_kev_playbook_when_in_kev(self):
        """Should use KEV playbook when in_kev=True."""
        plan = get_response_plan(
            "cve",
            "CVE-2026-1",
            metadata={"cvss": 7.0, "in_kev": True, "affected_packages": []}
        )

        assert "KEV" in plan.summary

    def test_routes_to_kev_playbook_for_critical_cvss(self):
        """Should use KEV playbook for CVSS >= 9.0 even if not in KEV."""
        plan = get_response_plan(
            "cve",
            "CVE-2026-1",
            metadata={"cvss": 9.5, "in_kev": False, "affected_packages": []}
        )

        assert plan.urgency == "critical"

    def test_routes_to_generic_cve_for_medium_cvss(self):
        """Should use generic CVE playbook for medium CVSS."""
        plan = get_response_plan(
            "cve",
            "CVE-2026-1",
            metadata={"cvss": 6.0, "in_kev": False, "affected_packages": []}
        )

        assert plan.urgency == "low"

    def test_routes_to_malware_playbook(self):
        """Should route to malware playbook for finding_type='malware'."""
        plan = get_response_plan(
            "malware",
            "abc123",
            metadata={"family": "Test", "detection_ratio": "10/72"}
        )

        assert plan.finding_type == "malware"

    def test_routes_to_ip_playbook(self):
        """Should route to IP playbook for finding_type='suspicious_ip'."""
        plan = get_response_plan(
            "suspicious_ip",
            "1.2.3.4",
            metadata={"abuse_score": 85, "ports": [22]}
        )

        assert plan.finding_type == "suspicious_ip"

    def test_routes_to_url_playbook(self):
        """Should route to URL playbook for finding_type='suspicious_url'."""
        plan = get_response_plan(
            "suspicious_url",
            "http://evil.com",
            metadata={"threat_type": "malware", "malware_family": "Test"}
        )

        assert plan.finding_type == "suspicious_url"

    def test_handles_unknown_finding_type(self):
        """Should provide fallback playbook for unknown types."""
        plan = get_response_plan(
            "unknown_type",
            "test-id",
            metadata={}
        )

        assert plan.finding_type == "unknown_type"
        assert plan.urgency == "low"
        assert "Unknown finding type" in plan.summary

    def test_handles_missing_metadata(self):
        """Should handle None metadata gracefully."""
        plan = get_response_plan("cve", "CVE-2026-1", metadata=None)

        # Should not crash and should use defaults
        assert plan.finding_type == "cve"

    def test_handles_invalid_cvss_type(self):
        """Should handle non-numeric CVSS gracefully."""
        plan = get_response_plan(
            "cve",
            "CVE-2026-1",
            metadata={"cvss": "invalid", "in_kev": False}
        )

        # Should default to 0.0 and use generic playbook
        assert plan.urgency == "low"

    def test_handles_cvss_as_cvss_score_key(self):
        """Should accept both 'cvss' and 'cvss_score' keys."""
        plan = get_response_plan(
            "cve",
            "CVE-2026-1",
            metadata={"cvss_score": 9.0, "in_kev": False}
        )

        assert plan.urgency == "critical"


class TestToDict:
    """Test JSON serialization."""

    def test_json_serializable(self):
        """to_dict() output should be JSON serializable."""
        plan = get_response_plan(
            "cve",
            "CVE-2026-1",
            metadata={"cvss": 9.0, "in_kev": True, "affected_packages": ["nginx"]}
        )

        result_dict = plan.to_dict()
        # Should not raise
        json_str = json.dumps(result_dict, indent=2)
        assert len(json_str) > 0

    def test_includes_all_fields(self):
        """to_dict() should include all relevant fields."""
        plan = get_response_plan("malware", "abc123", metadata={"family": "Test"})
        result = plan.to_dict()

        assert "finding_type" in result
        assert "finding_id" in result
        assert "urgency" in result
        assert "summary" in result
        assert "action_steps" in result
        assert "risk_factors" in result
        assert "compensating_controls" in result
        assert "generated_at" in result

    def test_action_steps_are_dicts(self):
        """Action steps should be serialized as dicts."""
        plan = get_response_plan("cve", "CVE-2026-1", metadata={"cvss": 9.0, "in_kev": True})
        result = plan.to_dict()

        for step in result["action_steps"]:
            assert isinstance(step, dict)
            assert "step" in step
            assert "action" in step
            assert "description" in step
