"""Tests for P105 External MCP Federation.

Tests federation models, discovery, trust scoring, policy, and handlers.
"""

from datetime import datetime, timedelta

import pytest

from ai.mcp_bridge.federation import (
    ExternalServerDiscovery,
    FederationAuditor,
    FederationPolicy,
    TrustScorer,
)
from ai.mcp_bridge.federation.models import (
    CapabilityMap,
    ExternalServerIdentity,
    ExternalToolDefinition,
    FederationAuditEntry,
    PolicyDecision,
    ServerToolManifest,
    TrustScore,
    TrustState,
)


class TestFederationModels:
    """Tests for federation models."""

    def test_external_server_identity(self):
        identity = ExternalServerIdentity(
            server_id="test123",
            name="Test Server",
            url="https://example.com/mcp",
            trust_state=TrustState.UNKNOWN,
        )
        assert identity.server_id == "test123"
        assert identity.trust_state == TrustState.UNKNOWN

    def test_trust_state_values(self):
        assert TrustState.UNKNOWN.value == "unknown"
        assert TrustState.PENDING.value == "pending"
        assert TrustState.VERIFIED.value == "verified"
        assert TrustState.SUSPECTED.value == "suspected"
        assert TrustState.BLOCKED.value == "blocked"

    def test_policy_decision_values(self):
        assert PolicyDecision.ALLOW.value == "allow"
        assert PolicyDecision.DENY.value == "deny"
        assert PolicyDecision.AUDIT.value == "audit"
        assert PolicyDecision.QUARANTINE.value == "quarantine"

    def test_external_tool_definition(self):
        tool = ExternalToolDefinition(
            name="test.tool",
            description="A test tool",
            input_schema={"type": "object"},
            annotations={"readOnly": True},
        )
        assert tool.name == "test.tool"

    def test_server_tool_manifest(self):
        manifest = ServerToolManifest(
            server_id="test123",
            tools=[
                ExternalToolDefinition(name="tool1", description="First tool"),
                ExternalToolDefinition(name="tool2", description="Second tool"),
            ],
        )
        assert len(manifest.tools) == 2

    def test_capability_map(self):
        cap_map = CapabilityMap(
            server_id="test123",
            tools_count=10,
            has_destructive_tools=False,
            has_system_tools=True,
        )
        assert cap_map.tools_count == 10

    def test_trust_score(self):
        score = TrustScore(
            server_id="test123",
            overall_score=75.0,
            factors={"https": 50.0, "verified": 25.0},
        )
        assert score.overall_score == 75.0

    def test_federation_audit_entry(self):
        entry = FederationAuditEntry(
            server_id="test123",
            action="discover",
            decision=PolicyDecision.ALLOW,
        )
        assert entry.decision == PolicyDecision.ALLOW


class TestExternalServerDiscovery:
    """Tests for ExternalServerDiscovery."""

    @pytest.fixture
    def discovery(self):
        return ExternalServerDiscovery()

    def test_validate_server_url_valid(self, discovery):
        valid, error = discovery.validate_server_url("https://example.com/mcp")
        assert valid is True
        assert error == ""

    def test_validate_server_url_invalid(self, discovery):
        valid, error = discovery.validate_server_url("not-a-url")
        assert valid is False
        assert "URL" in error

    def test_validate_server_url_empty(self, discovery):
        valid, error = discovery.validate_server_url("")
        assert valid is False
        assert "required" in error.lower()

    def test_compute_server_id(self, discovery):
        server_id1 = discovery.compute_server_id("https://example.com/mcp")
        server_id2 = discovery.compute_server_id("https://example.com/mcp")
        assert server_id1 == server_id2
        assert len(server_id1) == 16

    def test_validate_tool_definition_valid(self, discovery):
        tool = {"name": "test.tool", "description": "A test"}
        valid, error = discovery.validate_tool_definition(tool)
        assert valid is True
        assert error == ""

    def test_validate_tool_definition_no_name(self, discovery):
        tool = {"description": "A test"}
        valid, error = discovery.validate_tool_definition(tool)
        assert valid is False
        assert "name" in error.lower()

    def test_validate_tool_definition_long_name(self, discovery):
        tool = {"name": "a" * 200}
        valid, error = discovery.validate_tool_definition(tool)
        assert valid is False
        assert "exceeds" in error.lower()

    def test_validate_manifest_valid(self, discovery):
        manifest = {
            "tools": [
                {"name": "tool1", "description": "First"},
                {"name": "tool2", "description": "Second"},
            ]
        }
        valid, errors = discovery.validate_manifest(manifest, "test123")
        assert valid is True
        assert errors == []

    def test_validate_manifest_too_many_tools(self, discovery):
        manifest = {"tools": [{"name": f"tool{i}"} for i in range(600)]}
        valid, errors = discovery.validate_manifest(manifest, "test123")
        assert valid is False
        assert "Too many" in errors[0]

    @pytest.mark.asyncio
    async def test_discover_server(self, discovery):
        identity = await discovery.discover_server("https://example.com/mcp", "Test Server")
        assert identity.server_id is not None
        assert identity.name == "Test Server"
        assert identity.url == "https://example.com/mcp"

    def test_list_discovered_empty(self, discovery):
        servers = discovery.list_discovered()
        assert servers == []

    def test_get_server_not_found(self, discovery):
        server = discovery.get_server("nonexistent")
        assert server is None

    def test_remove_server(self, discovery):
        discovery._discovered_servers["test123"] = ExternalServerIdentity(
            server_id="test123", name="Test", url="https://example.com"
        )
        removed = discovery.remove_server("test123")
        assert removed is True


class TestTrustScorer:
    """Tests for TrustScorer."""

    @pytest.fixture
    def discovery(self):
        return ExternalServerDiscovery()

    @pytest.fixture
    def scorer(self, discovery):
        return TrustScorer(discovery)

    def test_compute_trust_score_default(self, scorer, discovery):
        identity = ExternalServerIdentity(
            server_id="test123",
            name="Test",
            url="https://example.com",
            trust_state=TrustState.UNKNOWN,
        )
        discovery._discovered_servers["test123"] = identity

        score = scorer.compute_trust_score("test123")
        assert score.server_id == "test123"
        assert 0 <= score.overall_score <= 100
        assert "https" in score.factors

    def test_compute_trust_score_with_https(self, scorer, discovery):
        identity = ExternalServerIdentity(
            server_id="test123",
            name="Test",
            url="https://example.com",
            trust_state=TrustState.VERIFIED,
        )
        identity.first_seen = datetime.utcnow() - timedelta(days=30)
        identity.last_verified = datetime.utcnow() - timedelta(hours=12)
        discovery._discovered_servers["test123"] = identity

        score = scorer.compute_trust_score("test123")
        assert score.factors["https"] == 50.0

    def test_determine_trust_state_verified(self, scorer):
        trust_score = TrustScore(server_id="test", overall_score=75.0, factors={})
        state = scorer.determine_trust_state(trust_score)
        assert state == TrustState.VERIFIED

    def test_determine_trust_state_blocked(self, scorer):
        trust_score = TrustScore(server_id="test", overall_score=10.0, factors={})
        state = scorer.determine_trust_state(trust_score)
        assert state == TrustState.BLOCKED


class TestFederationPolicy:
    """Tests for FederationPolicy."""

    @pytest.fixture
    def policy(self):
        return FederationPolicy(allow_remote_execution=False)

    def test_evaluate_action_default_deny(self, policy):
        result = policy.evaluate_action("test123", "execute")
        assert result.decision == PolicyDecision.DENY

    def test_evaluate_action_allow_high_trust(self, policy):
        trust = TrustScore(server_id="test123", overall_score=80.0, factors={})
        result = policy.evaluate_action("test123", "inspect", trust)
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_action_low_trust_quarantine(self, policy):
        trust = TrustScore(server_id="test123", overall_score=15.0, factors={})
        result = policy.evaluate_action("test123", "inspect", trust)
        assert result.decision == PolicyDecision.QUARANTINE

    def test_evaluate_action_blocked_system_tools(self, policy):
        cap_map = CapabilityMap(
            server_id="test123",
            has_system_tools=True,
            has_destructive_tools=False,
        )
        result = policy.evaluate_action("test123", "inspect", None, cap_map)
        assert result.decision == PolicyDecision.DENY

    def test_check_tool_execution_disabled(self, policy):
        allowed, reason = policy.check_tool_execution("test123", "some.tool")
        assert allowed is False
        assert "disabled" in reason.lower()

    def test_check_tool_execution_system_tools(self, policy):
        policy_with_exec = FederationPolicy(allow_remote_execution=True)
        allowed, reason = policy_with_exec.check_tool_execution("test123", "system.update")
        assert allowed is False
        assert "system" in reason.lower()


class TestFederationAuditor:
    """Tests for FederationAuditor."""

    @pytest.fixture
    def auditor(self):
        return FederationAuditor()

    def test_log_action(self, auditor):
        entry = auditor.log_action(
            server_id="test123",
            action="discover",
            decision=PolicyDecision.ALLOW,
            reasons=["Test reason"],
        )
        assert entry.server_id == "test123"
        assert entry.decision == PolicyDecision.ALLOW

    def test_get_audit_log_empty(self, auditor):
        entries = auditor.get_audit_log()
        assert entries == []

    def test_get_audit_log_filtered(self, auditor):
        auditor.log_action("test1", "a1", PolicyDecision.ALLOW)
        auditor.log_action("test2", "a2", PolicyDecision.DENY)

        entries = auditor.get_audit_log("test1")
        assert len(entries) == 1
        assert entries[0].server_id == "test1"


class TestToolFederationHandlers:
    """Tests for MCP tool handlers."""

    def test_handler_imports(self):
        from ai.mcp_bridge.tool_federation_handlers import (
            handle_tool_federation_audit,
            handle_tool_federation_disable,
            handle_tool_federation_discover,
            handle_tool_federation_inspect_server,
            handle_tool_federation_list_servers,
            handle_tool_federation_trust_score,
        )

        assert callable(handle_tool_federation_discover)
        assert callable(handle_tool_federation_list_servers)
        assert callable(handle_tool_federation_inspect_server)
        assert callable(handle_tool_federation_audit)
        assert callable(handle_tool_federation_trust_score)
        assert callable(handle_tool_federation_disable)
