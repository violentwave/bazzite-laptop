"""FastMCP server for the Newelle MCP bridge.

Exposes 52 tools + 1 health endpoint on localhost.
NEVER bind to 0.0.0.0. NEVER import ai.router (it loads all keys unscoped).

Tool Filtering:
    This server supports server-side tool filtering via ai.mcp_bridge.tool_filter.
    The ToolFilter class provides namespace-based and semantic filtering to reduce
    tool selection overhead as the tool count grows. Use get_filter() to obtain
    filtered tool lists for specific contexts.
"""

import logging

import yaml

from ai.budget import get_budget
from ai.config import CONFIGS_DIR, load_keys
from ai.learning import retrieve_similar_tasks

logger = logging.getLogger("ai.mcp_bridge")

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = int(__import__("os").environ.get("MCP_BRIDGE_PORT", "8766"))

# Number of tools in the allowlist (excludes health endpoint itself)
_TOOL_COUNT = 57


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
        "security.alert_summary": {"readOnlyHint": True, "idempotentHint": True},
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
        "agents.timer_health": {"readOnlyHint": True, "idempotentHint": True},
        # ── observability ────────────────────────────────────────────────────
        "system.token_report": {"readOnlyHint": True, "idempotentHint": True},
        "system.pipeline_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.budget_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.metrics_summary": {"readOnlyHint": True, "idempotentHint": True},
        # ── threat intel correlation ─────────────────────────────────────────
        "security.correlate": {"readOnlyHint": True, "openWorldHint": True},
        "security.recommend_action": {"readOnlyHint": True, "idempotentHint": True},
        "knowledge.pattern_search": {"readOnlyHint": True},
        "knowledge.task_patterns": {"readOnlyHint": True},
        "memory.search": {"readOnlyHint": True},
        "system.provider_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.weekly_insights": {"readOnlyHint": True, "idempotentHint": True},
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
        elif tool_name == "knowledge.pattern_search":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_pattern_search(
                query: str,
                language: str | None = None,
                domain: str | None = None,
                limit: int = 5,
                _tn=tool_name,
            ):
                from ai.rag.pattern_query import search_patterns

                results = search_patterns(
                    query=query,
                    language=language,
                    domain=domain,
                    limit=limit,
                )
                formatted = []
                for r in results:
                    formatted.append(
                        {
                            "title": r.get("title", ""),
                            "language": r.get("language", ""),
                            "domain": r.get("domain", ""),
                            "tags": r.get("tags", []),
                            "content": (r.get("content", "") or "")[:2000],
                        }
                    )
                output = str(formatted)
                if len(output) > 4096:
                    output = output[:4096] + "... [truncated]"
                return output

        elif tool_name == "knowledge.task_patterns":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_task_patterns(
                query: str,
                top_k: int = 3,
                _tn=tool_name,
            ):
                try:
                    results = retrieve_similar_tasks(query, top_k=top_k)
                    if results:
                        msg = f"Found {len(results)} similar past task(s)"
                    else:
                        msg = (
                            "No similar past tasks found yet. "
                            "Use log-task-success.py to build the knowledge base."
                        )
                    return {
                        "tasks": results,
                        "count": len(results),
                        "message": msg,
                    }
                except Exception as e:
                    return {"error": str(e), "tasks": [], "count": 0}

        elif tool_name == "memory.search":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_memory_search(
                query: str,
                top_k: int = 5,
                _tn=tool_name,
            ):
                try:
                    from ai.memory import get_memory

                    result = get_memory().search_memories(query=query, top_k=top_k)
                    return {"results": result, "query": query}
                except Exception as e:
                    return {"error": str(e), "results": "[]"}

        elif tool_name == "system.budget_status":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_budget_status(_tn=tool_name):
                try:
                    status = get_budget().get_status()
                    warnings = [
                        f"{tier} at {info['remaining_pct']:.1f}% remaining"
                        for tier, info in status.items()
                        if info.get("warn")
                    ]
                    return {
                        "tiers": status,
                        "warnings": warnings,
                        "reset": "midnight UTC",
                    }
                except Exception as e:
                    return {"error": str(e), "tiers": {}, "warnings": []}

        elif tool_name == "system.metrics_summary":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_metrics_summary(
                hours: int = 24,
                metric_type: str | None = None,
                _tn=tool_name,
            ):
                try:
                    from ai.metrics import get_recorder

                    recorder = get_recorder()
                    result = recorder.query_summary(hours=hours, metric_type=metric_type)
                    return result
                except Exception as e:
                    return {"error": str(e), "count": 0, "mean": 0.0}

        elif tool_name == "system.provider_status":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_provider_status(_tn=tool_name):
                try:
                    from ai.provider_intel import get_intel

                    result = get_intel().get_status()
                    return result
                except Exception as e:
                    return {"error": str(e), "providers": {}}

        elif tool_name == "system.weekly_insights":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_weekly_insights(
                limit: int = 4,
                _tn=tool_name,
            ):
                try:
                    from ai.insights import InsightsEngine

                    engine = InsightsEngine()
                    insights = engine.get_latest_insights(limit=limit)
                    return {"insights": insights, "count": len(insights)}
                except Exception as e:
                    return {"error": str(e), "insights": [], "count": 0}

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
