"""FastMCP server for the Newelle MCP bridge.

Exposes 46 tools + 1 health endpoint on localhost.
NEVER bind to 0.0.0.0. NEVER import ai.router (it loads all keys unscoped).
"""

import logging

import yaml

from ai.config import CONFIGS_DIR, load_keys

logger = logging.getLogger("ai.mcp_bridge")

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = int(__import__("os").environ.get("MCP_BRIDGE_PORT", "8766"))

# Number of tools in the allowlist (excludes health endpoint itself)
_TOOL_COUNT = 48


def _assert_localhost(bind: str) -> None:
    """Refuse to start on non-localhost addresses."""
    if bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(f"MCP bridge must bind to localhost only, got '{bind}'")


def _load_tool_defs() -> dict:
    """Load tool definitions from the allowlist YAML."""
    allowlist_path = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"
    with open(allowlist_path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("tools", {})


async def health_check() -> dict:
    """Health endpoint handler."""
    return {
        "status": "ok",
        "tools": _TOOL_COUNT,
    }


def create_app():
    """Create and configure the FastMCP application.

    Raises:
        RuntimeError: If key loading fails.
    """
    from fastmcp import FastMCP  # noqa: PLC0415
    from fastmcp.server.middleware import PingMiddleware  # noqa: PLC0415

    if not load_keys(scope="threat_intel"):
        raise RuntimeError("MCP bridge startup guard: key loading failed")

    mcp = FastMCP("bazzite-mcp-bridge")
    mcp.add_middleware(PingMiddleware(interval_ms=25000))

    _ANNOTATIONS: dict[str, dict] = {
        # ── read-only local (deterministic, no side-effects) ─────────────
        "system.disk_usage": {"readOnlyHint": True, "idempotentHint": True},
        "system.cpu_temps": {"readOnlyHint": True, "idempotentHint": True},
        "system.gpu_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.gpu_perf": {"readOnlyHint": True, "idempotentHint": True},
        "system.gpu_health": {"readOnlyHint": True, "idempotentHint": True},
        "system.memory_usage": {"readOnlyHint": True, "idempotentHint": True},
        "system.uptime": {"readOnlyHint": True, "idempotentHint": True},
        "system.service_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.llm_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.key_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.llm_models": {"readOnlyHint": True, "idempotentHint": True},
        "system.mcp_manifest": {"readOnlyHint": True, "idempotentHint": True},
        "system.release_watch": {"readOnlyHint": True, "idempotentHint": True},
        "system.fedora_updates": {"readOnlyHint": True, "idempotentHint": True},
        "system.pkg_intel": {"readOnlyHint": True, "idempotentHint": True},
        "system.cache_stats": {"readOnlyHint": True, "idempotentHint": True},
        "security.status": {"readOnlyHint": True, "idempotentHint": True},
        "security.last_scan": {"readOnlyHint": True, "idempotentHint": True},
        "security.health_snapshot": {"readOnlyHint": True, "idempotentHint": True},
        "security.threat_summary": {"readOnlyHint": True, "idempotentHint": True},
        "logs.health_trend": {"readOnlyHint": True, "idempotentHint": True},
        "logs.scan_history": {"readOnlyHint": True, "idempotentHint": True},
        "logs.anomalies": {"readOnlyHint": True, "idempotentHint": True},
        "logs.stats": {"readOnlyHint": True, "idempotentHint": True},
        "gaming.profiles": {"readOnlyHint": True, "idempotentHint": True},
        "code.search": {"readOnlyHint": True, "idempotentHint": True},
        # ── read-only external (calls internet APIs) ──────────────────────
        "security.threat_lookup": {"readOnlyHint": True, "openWorldHint": True},
        "security.ip_lookup": {"readOnlyHint": True, "openWorldHint": True},
        "security.url_lookup": {"readOnlyHint": True, "openWorldHint": True},
        "security.cve_check": {"readOnlyHint": True, "openWorldHint": True},
        # ── read-only LLM-backed (local reads, LLM synthesis) ────────────
        "knowledge.rag_query": {"readOnlyHint": True},
        "knowledge.rag_qa": {"readOnlyHint": True},
        "logs.search": {"readOnlyHint": True},
        "code.rag_query": {"readOnlyHint": True},
        # ── triggers / writes (side-effects, safe to retry) ──────────────
        "security.run_scan": {"readOnlyHint": False, "idempotentHint": True},
        "security.run_health": {"readOnlyHint": False, "idempotentHint": True},
        "security.run_ingest": {"readOnlyHint": False, "idempotentHint": True},
        "knowledge.ingest_docs": {"readOnlyHint": False, "idempotentHint": True},
        "gaming.mangohud_preset": {"readOnlyHint": False, "idempotentHint": True},
        # ── destructive external ──────────────────────────────────────────
        "security.sandbox_submit": {"destructiveHint": True, "openWorldHint": True},
        # ── agent composite (read-only orchestration) ─────────────────────
        "agents.security_audit": {"readOnlyHint": True, "idempotentHint": True},
        "agents.performance_tuning": {"readOnlyHint": True, "idempotentHint": True},
        "agents.knowledge_storage": {"readOnlyHint": True, "idempotentHint": True},
        "agents.code_quality": {"readOnlyHint": True, "idempotentHint": True},
        # ── observability ────────────────────────────────────────────────────
        "system.token_report": {"readOnlyHint": True, "idempotentHint": True},
        # ── threat intel correlation ─────────────────────────────────────────
        "security.correlate": {"readOnlyHint": True, "openWorldHint": True},
        "security.recommend_action": {"readOnlyHint": True, "idempotentHint": True},
    }

    # Load tool definitions from the allowlist
    tool_defs = _load_tool_defs()

    # Register each allowlisted tool
    from ai.mcp_bridge.tools import execute_tool  # noqa: PLC0415

    for tool_name, tool_def in tool_defs.items():
        description = tool_def.get("description", tool_name)
        arg_defs = tool_def.get("args")
        ann = _ANNOTATIONS.get(tool_name)

        # FastMCP 3.x does not support **kwargs in tool functions.
        # Build explicit-arg handlers for tools that accept arguments.
        if arg_defs is None:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler(_tn=tool_name):
                return await execute_tool(_tn, {})
        elif "hash" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_hash(hash: str, _tn=tool_name):
                return await execute_tool(_tn, {"hash": hash})
        elif "question" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_question(question: str, _tn=tool_name):
                return await execute_tool(_tn, {"question": question})
        elif "game" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_game(game: str, _tn=tool_name):
                return await execute_tool(_tn, {"game": game})
        elif "query" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_query(query: str, _tn=tool_name):
                return await execute_tool(_tn, {"query": query})
        elif "scan_type" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_scan(scan_type: str = "quick", _tn=tool_name):
                return await execute_tool(_tn, {"scan_type": scan_type})
        elif "ip" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_ip(ip: str, _tn=tool_name):
                return await execute_tool(_tn, {"ip": ip})
        elif "url" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_url(url: str, _tn=tool_name):
                return await execute_tool(_tn, {"url": url})
        elif "file_path" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_file_path(file_path: str, _tn=tool_name):
                return await execute_tool(_tn, {"file_path": file_path})
        elif "ioc" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_ioc(ioc: str, ioc_type: str, _tn=tool_name):
                return await execute_tool(_tn, {"ioc": ioc, "ioc_type": ioc_type})
        elif "finding_type" in arg_defs:

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_finding(finding_type: str, finding_id: str, _tn=tool_name):
                return await execute_tool(
                    _tn, {"finding_type": finding_type, "finding_id": finding_id}
                )  # noqa: E501

        # Built-in health tool (MCP protocol)

    @mcp.tool(name="health", description="Bridge health check")
    async def _health():
        return await health_check()

    # Plain HTTP health endpoint (for curl/monitoring)
    @mcp.custom_route("/health", methods=["GET"])
    async def _http_health(request):
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok", "tools": _TOOL_COUNT, "service": "bazzite-mcp-bridge"})

    return mcp
