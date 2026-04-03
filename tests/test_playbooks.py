"""Unit tests for ai/threat_intel/playbooks.py - Response playbooks for threat findings."""

import json

import pytest

from ai.threat_intel.playbooks import (
    ActionStep,
    RecommendedAction,
    get_response_plan,
)


class TestActionStep:
    """Test ActionStep data model."""

    def test_creates_action_step_with_defaults(self):
        """ActionStep uses default values for optional fields."""
        step = ActionStep(
            step_number=1,
            action="Verify status",
            description="Check if CVE is in KEV catalog",
        )

        assert step.step_number == 1
        assert step.action == "Verify status"
        assert step.description == "Check if CVE is in KEV catalog"
        assert step.tool is None
        assert step.urgency == "medium"
        assert step.automated is False

    def test_creates_action_step_with_all_fields(self):
        """ActionStep accepts all optional fields."""
        step = ActionStep(
            step_number=2,
            action="Run scan",
            description="Execute security scan",
            tool="security.cve_check",
            urgency="high",
            automated=True,
        )

        assert step.tool == "security.cve_check"
        assert step.urgency == "high"
        assert step.automated is True


class TestRecommendedAction:
    """Test RecommendedAction data model."""

    def test_creates_recommended_action_with_minimal_fields(self):
        """RecommendedAction works with minimal required fields."""
        action = RecommendedAction(
            finding_type="cve",
            finding_id="CVE-2026-12345",
            urgency="high",
            summary="Critical vulnerability found",
        )

        assert action.finding_type == "cve"
        assert action.finding_id == "CVE-2026-12345"
        assert action.urgency == "high"
        assert action.summary == "Critical vulnerability found"
        assert action.action_steps == []
        assert action.risk_factors == []
        assert action.compensating_controls == []
        assert action.generated_at is not None

    def test_to_dict_serialization(self):
        """RecommendedAction.to_dict() produces valid JSON-serializable dict."""
        step = ActionStep(
            step_number=1,
            action="Test",
            description="Test step",
            tool="test.tool",
            urgency="low",
            automated=True,
        )

        action = RecommendedAction(
            finding_type="malware",
            finding_id="abc123",
            urgency="critical",
            summary="Malware detected",
            action_steps=[step],
            risk_factors=["High severity"],
            compensating_controls=["Quarantine confirmed"],
        )

        result = action.to_dict()

        assert result["finding_type"] == "malware"
        assert result["finding_id"] == "abc123"
        assert result["urgency"] == "critical"
        assert result["summary"] == "Malware detected"
        assert len(result["action_steps"]) == 1
        assert result["action_steps"][0]["step"] == 1
        assert result["action_steps"][0]["action"] == "Test"
        assert result["action_steps"][0]["automated"] is True
        assert "High severity" in result["risk_factors"]
        assert "Quarantine confirmed" in result["compensating_controls"]

        # Should be JSON-serializable
        json_str = json.dumps(result)
        assert json_str is not None


class TestKEVCVEPlaybook:
    """Test playbook for KEV (Known Exploited Vulnerability) CVEs."""

    def test_kev_cve_with_high_cvss(self):
        """KEV CVE with CVSS >= 9.0 returns critical urgency."""
        response = get_response_plan(
            "cve",
            "CVE-2026-99999",
            metadata={
                "cvss": 9.8,
                "in_kev": True,
                "affected_packages": ["kernel", "systemd"],
            },
        )

        assert response.urgency == "critical"
        assert response.finding_type == "cve"
        assert response.finding_id == "CVE-2026-99999"
        assert "KEV CVE" in response.summary
        assert len(response.action_steps) > 0

        # Should have KEV verification step
        step_actions = [s.action for s in response.action_steps]
        assert any("KEV" in action for action in step_actions)

        # Should have Fedora updates check
        assert any("Fedora" in action for action in step_actions)

    def test_kev_cve_includes_affected_packages(self):
        """KEV CVE playbook includes affected packages in action steps."""
        packages = ["kernel-core", "firefox", "chromium"]
        response = get_response_plan(
            "cve",
            "CVE-2026-88888",
            metadata={
                "cvss": 9.5,
                "in_kev": True,
                "affected_packages": packages,
            },
        )

        # Should have package update step
        step_descriptions = [s.description for s in response.action_steps]
        package_update_step = any(
            any(pkg in desc for pkg in packages) for desc in step_descriptions
        )
        assert package_update_step

    def test_kev_cve_without_packages(self):
        """KEV CVE playbook works when affected_packages is empty."""
        response = get_response_plan(
            "cve",
            "CVE-2026-77777",
            metadata={
                "cvss": 9.0,
                "in_kev": True,
                "affected_packages": [],
            },
        )

        assert response.urgency == "critical"
        assert len(response.action_steps) > 0


class TestGenericCVEPlaybook:
    """Test playbook for non-KEV CVEs."""

    def test_medium_severity_cve(self):
        """Non-KEV CVE with CVSS 7.0-9.0 returns medium urgency."""
        response = get_response_plan(
            "cve",
            "CVE-2026-11111",
            metadata={
                "cvss": 7.5,
                "in_kev": False,
                "affected_packages": ["nginx"],
            },
        )

        assert response.urgency == "medium"
        assert response.finding_type == "cve"
        assert len(response.action_steps) > 0

    def test_low_severity_cve(self):
        """Non-KEV CVE with CVSS < 7.0 returns low urgency."""
        response = get_response_plan(
            "cve",
            "CVE-2026-22222",
            metadata={
                "cvss": 5.0,
                "in_kev": False,
            },
        )

        assert response.urgency == "low"

    def test_cve_without_metadata(self):
        """CVE playbook works with minimal metadata."""
        response = get_response_plan("cve", "CVE-2026-33333", metadata={})

        assert response.finding_type == "cve"
        assert response.urgency in ("low", "medium", "high", "critical")


class TestMalwarePlaybook:
    """Test playbook for malicious file hashes."""

    def test_malware_hash_playbook(self):
        """Malware hash returns high urgency response plan."""
        response = get_response_plan(
            "malware",
            "abc123def456",
            metadata={
                "family": "Emotet",
                "detection_ratio": "45/70",
            },
        )

        assert response.urgency == "high"
        assert response.finding_type == "malware"
        assert "Emotet" in response.summary
        assert len(response.action_steps) > 0

        # Should have sandbox analysis step
        step_actions = [s.action for s in response.action_steps]
        assert any("sandbox" in action.lower() for action in step_actions)

        # Should have IOC correlation step
        assert any("IOC" in action or "correlate" in action.lower() for action in step_actions)

    def test_malware_without_family(self):
        """Malware playbook works when family is unknown."""
        response = get_response_plan(
            "malware",
            "deadbeef1234",
            metadata={
                "detection_ratio": "10/70",
            },
        )

        assert response.urgency == "high"
        assert "unknown" in response.summary.lower()


class TestSuspiciousIPPlaybook:
    """Test playbook for suspicious IP addresses."""

    def test_high_abuse_score_ip(self):
        """IP with abuse score > 70 returns high urgency."""
        response = get_response_plan(
            "suspicious_ip",
            "192.0.2.100",
            metadata={
                "abuse_score": 85,
                "ports": [22, 80, 443],
            },
        )

        assert response.urgency == "high"
        assert response.finding_type == "suspicious_ip"
        assert len(response.action_steps) > 0

        # Should have threat intel lookup
        step_actions = [s.action for s in response.action_steps]
        assert any(
            "threat" in action.lower() or "intelligence" in action.lower()
            for action in step_actions
        )

    def test_medium_abuse_score_ip(self):
        """IP with abuse score <= 70 returns medium urgency."""
        response = get_response_plan(
            "suspicious_ip",
            "198.51.100.50",
            metadata={
                "abuse_score": 50,
                "ports": [],
            },
        )

        assert response.urgency == "medium"

    def test_ip_with_open_ports(self):
        """IP playbook includes port review when ports are provided."""
        response = get_response_plan(
            "suspicious_ip",
            "203.0.113.10",
            metadata={
                "abuse_score": 75,
                "ports": [3389, 445, 135],
            },
        )

        # Should have service review step
        step_descriptions = [s.description for s in response.action_steps]
        assert any("3389" in desc or "445" in desc or "135" in desc for desc in step_descriptions)


class TestSuspiciousURLPlaybook:
    """Test playbook for suspicious URLs."""

    def test_malware_url(self):
        """URL with malware threat type returns high urgency."""
        response = get_response_plan(
            "suspicious_url",
            "http://evil.example.com/payload.exe",
            metadata={
                "threat_type": "malware",
                "malware_family": "TrickBot",
            },
        )

        assert response.urgency == "high"
        assert response.finding_type == "suspicious_url"
        assert "malware" in response.summary.lower()

    def test_phishing_url(self):
        """URL with phishing threat type returns medium urgency."""
        response = get_response_plan(
            "suspicious_url",
            "http://phish.example.com/login",
            metadata={
                "threat_type": "phishing",
            },
        )

        assert response.urgency == "medium"

    def test_url_without_metadata(self):
        """URL playbook works without metadata."""
        response = get_response_plan(
            "suspicious_url",
            "http://suspicious.example.com",
            metadata={},
        )

        assert response.finding_type == "suspicious_url"
        assert len(response.action_steps) > 0


class TestFallbackPlaybook:
    """Test fallback playbook for unknown finding types."""

    def test_unknown_finding_type(self):
        """Unknown finding type returns low urgency fallback plan."""
        response = get_response_plan(
            "unknown_type",
            "unknown-id",
            metadata={},
        )

        assert response.finding_type == "unknown_type"
        assert response.finding_id == "unknown-id"
        assert response.urgency == "low"
        assert "Unknown finding type" in response.summary
        assert len(response.action_steps) > 0
        assert response.action_steps[0].action == "Investigate manually"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_metadata(self):
        """get_response_plan() handles None metadata."""
        response = get_response_plan("cve", "CVE-2026-00000", metadata=None)

        assert response.finding_type == "cve"
        assert response.urgency in ("low", "medium", "high", "critical")

    def test_malformed_metadata(self):
        """get_response_plan() handles malformed metadata gracefully."""
        response = get_response_plan(
            "cve",
            "CVE-2026-44444",
            metadata={"cvss": "not_a_number", "packages": None},
        )

        # Should not crash
        assert response.finding_type == "cve"

    def test_negative_abuse_score(self):
        """IP playbook handles negative abuse scores."""
        response = get_response_plan(
            "suspicious_ip",
            "192.0.2.1",
            metadata={"abuse_score": -10},
        )

        assert response.urgency == "medium"

    def test_very_high_cvss(self):
        """CVE playbook handles CVSS scores > 10."""
        response = get_response_plan(
            "cve",
            "CVE-2026-55555",
            metadata={"cvss": 15.0, "in_kev": True},
        )

        assert response.urgency == "critical"

    def test_empty_string_metadata_values(self):
        """Playbook handles empty string metadata values."""
        response = get_response_plan(
            "malware",
            "hash123",
            metadata={"family": "", "detection": ""},
        )

        assert response.urgency == "high"
        assert "unknown" in response.summary.lower()

    def test_many_affected_packages(self):
        """KEV CVE playbook handles very long package lists."""
        packages = [f"package{i}" for i in range(100)]
        response = get_response_plan(
            "cve",
            "CVE-2026-66666",
            metadata={"cvss": 9.0, "in_kev": True, "affected_packages": packages},
        )

        # Should only show first 3 packages in descriptions
        package_mentions = 0
        for step in response.action_steps:
            if any(f"package{i}" in step.description for i in range(10)):
                package_mentions += 1

        assert package_mentions > 0


class TestCLI:
    """Test CLI entry point."""

    def test_cli_with_json_output(self, capsys):
        """CLI with --json flag outputs valid JSON."""
        import sys

        from ai.threat_intel.playbooks import main

        with pytest.raises(SystemExit):
            sys.argv = [
                "playbooks.py",
                "cve",
                "CVE-2026-12345",
                "--cvss",
                "7.5",
                "--json",
            ]
            main()

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["finding_type"] == "cve"
        assert result["finding_id"] == "CVE-2026-12345"

    def test_cli_with_text_output(self, capsys):
        """CLI without --json flag outputs human-readable text."""
        import sys

        from ai.threat_intel.playbooks import main

        with pytest.raises(SystemExit):
            sys.argv = ["playbooks.py", "malware", "abc123"]
            main()

        captured = capsys.readouterr()
        assert "Finding:" in captured.out
        assert "Urgency:" in captured.out
        assert "Action Steps:" in captured.out

    def test_cli_with_kev_flag(self, capsys):
        """CLI --in-kev flag marks CVE as in KEV catalog."""
        import sys

        from ai.threat_intel.playbooks import main

        with pytest.raises(SystemExit):
            sys.argv = [
                "playbooks.py",
                "cve",
                "CVE-2026-99999",
                "--cvss",
                "9.0",
                "--in-kev",
                "--json",
            ]
            main()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["urgency"] == "critical"
