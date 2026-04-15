"""MCP tool handlers for P105 federation tools.

Provides handlers for:
- tool.federation.discover
- tool.federation.list_servers
- tool.federation.inspect_server
- tool.federation.audit
- tool.federation.trust_score
- tool.federation.disable
"""

from __future__ import annotations

import json
import logging

from ai.mcp_bridge.federation import (
    ExternalServerDiscovery,
    FederationAuditor,
    FederationPolicy,
    TrustScorer,
)

logger = logging.getLogger("ai.mcp_bridge.tool_federation_handlers")

_discovery_instance: ExternalServerDiscovery | None = None
_trust_scorer_instance: TrustScorer | None = None
_policy_instance: FederationPolicy | None = None
_auditor_instance: FederationAuditor | None = None


def _get_discovery() -> ExternalServerDiscovery:
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = ExternalServerDiscovery()
    return _discovery_instance


def _get_trust_scorer() -> TrustScorer:
    global _trust_scorer_instance
    if _trust_scorer_instance is None:
        _discovery_instance = _get_discovery()
        _trust_scorer_instance = TrustScorer(_discovery_instance)
    return _trust_scorer_instance


def _get_policy() -> FederationPolicy:
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = FederationPolicy(allow_remote_execution=False)
    return _policy_instance


def _get_auditor() -> FederationAuditor:
    global _auditor_instance
    if _auditor_instance is None:
        _auditor_instance = FederationAuditor()
    return _auditor_instance


async def handle_tool_federation_discover(args: dict) -> str:
    """Discover external MCP server.

    Args:
        args: Dict with url, name, description

    Returns:
        JSON string with discovery result
    """
    try:
        url = args.get("url", "")
        if not url:
            return json.dumps({"status": "error", "error": "url is required"})

        name = args.get("name")
        description = args.get("description", "")

        discovery = _get_discovery()
        identity = await discovery.discover_server(url, name, description)

        result = {
            "status": "success",
            "server": {
                "server_id": identity.server_id,
                "name": identity.name,
                "url": identity.url,
                "description": identity.description,
                "capabilities": [c.value for c in identity.capabilities],
                "trust_state": identity.trust_state.value,
            },
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error discovering server: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_federation_list_servers(args: dict) -> str:
    """List all discovered servers.

    Args:
        args: Dict (no required fields)

    Returns:
        JSON string with server list
    """
    try:
        discovery = _get_discovery()
        servers = discovery.list_discovered()

        result = {
            "status": "success",
            "count": len(servers),
            "servers": [
                {
                    "server_id": s.server_id,
                    "name": s.name,
                    "url": s.url,
                    "trust_state": s.trust_state.value,
                    "capabilities": [c.value for c in s.capabilities],
                    "last_seen": s.last_seen.isoformat(),
                }
                for s in servers
            ],
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error listing servers: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_federation_inspect_server(args: dict) -> str:
    """Inspect external MCP server details.

    Args:
        args: Dict with server_id

    Returns:
        JSON string with server details
    """
    try:
        server_id = args.get("server_id", "")
        if not server_id:
            return json.dumps({"status": "error", "error": "server_id is required"})

        discovery = _get_discovery()
        server = discovery.get_server(server_id)

        if not server:
            return json.dumps({"status": "error", "error": f"Server not found: {server_id}"})

        result = {
            "status": "success",
            "server": {
                "server_id": server.server_id,
                "name": server.name,
                "url": server.url,
                "version": server.version,
                "description": server.description,
                "capabilities": [c.value for c in server.capabilities],
                "trust_state": server.trust_state.value,
                "first_seen": server.first_seen.isoformat(),
                "last_seen": server.last_seen.isoformat(),
                "last_verified": server.last_verified.isoformat() if server.last_verified else None,
            },
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error inspecting server: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_federation_audit(args: dict) -> str:
    """Get federation audit log.

    Args:
        args: Dict with optional server_id and limit

    Returns:
        JSON string with audit entries
    """
    try:
        server_id = args.get("server_id")
        limit = args.get("limit", 100)

        auditor = _get_auditor()
        entries = auditor.get_audit_log(server_id, limit)

        result = {
            "status": "success",
            "count": len(entries),
            "entries": [
                {
                    "id": e.id,
                    "server_id": e.server_id,
                    "action": e.action,
                    "decision": e.decision.value,
                    "reasons": e.reasons,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in entries
            ],
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_federation_trust_score(args: dict) -> str:
    """Calculate trust score for server.

    Args:
        args: Dict with server_id

    Returns:
        JSON string with trust score
    """
    try:
        server_id = args.get("server_id", "")
        if not server_id:
            return json.dumps({"status": "error", "error": "server_id is required"})

        discovery = _get_discovery()
        server = discovery.get_server(server_id)

        if not server:
            return json.dumps({"status": "error", "error": f"Server not found: {server_id}"})

        scorer = _get_trust_scorer()
        trust_score = scorer.compute_trust_score(server_id)

        result = {
            "status": "success",
            "server_id": server_id,
            "overall_score": trust_score.overall_score,
            "factors": trust_score.factors,
            "trust_state": scorer.determine_trust_state(trust_score).value,
            "last_calculated": trust_score.last_calculated.isoformat(),
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error computing trust score: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_federation_disable(args: dict) -> str:
    """Disable/remove external MCP server from federation.

    Args:
        args: Dict with server_id

    Returns:
        JSON string with result
    """
    try:
        server_id = args.get("server_id", "")
        if not server_id:
            return json.dumps({"status": "error", "error": "server_id is required"})

        discovery = _get_discovery()
        removed = discovery.remove_server(server_id)

        if removed:
            policy = _get_policy()
            result_policy = policy.evaluate_action(server_id, "disable")
            auditor = _get_auditor()
            auditor.log_action(
                server_id=server_id,
                action="disable",
                decision=result_policy.decision,
                reasons=result_policy.reasons,
            )

            return json.dumps({"status": "success", "message": f"Server {server_id} disabled"})

        return json.dumps({"status": "error", "error": f"Server not found: {server_id}"})

    except Exception as e:
        logger.error(f"Error disabling server: {e}")
        return json.dumps({"status": "error", "error": str(e)})
