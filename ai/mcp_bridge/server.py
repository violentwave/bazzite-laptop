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


def _count_tools() -> int:
    """Count tools dynamically from allowlist at import time."""
    try:
        from pathlib import Path

        cfg = Path(__file__).parent.parent.parent / "configs" / "mcp-bridge-allowlist.yaml"
        with open(cfg) as f:
            data = yaml.safe_load(f)
        return len(data.get("tools", {}))
    except Exception:
        return 0


# Number of tools in the allowlist (excludes health endpoint itself)
_TOOL_COUNT = _count_tools()


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
        "knowledge.session_history": {"readOnlyHint": True},
        "memory.search": {"readOnlyHint": True},
        "system.provider_status": {"readOnlyHint": True, "idempotentHint": True},
        "system.weekly_insights": {"readOnlyHint": True, "idempotentHint": True},
        "system.insights": {"readOnlyHint": False, "idempotentHint": False},
        "system.dep_audit": {"readOnlyHint": True, "idempotentHint": True},
        "system.dep_audit_history": {"readOnlyHint": True, "idempotentHint": True},
        "system.perf_metrics": {"readOnlyHint": True, "idempotentHint": True},
        # ── Slack integration ───────────────────────────────────────────────────
        "slack.list_channels": {"readOnlyHint": True, "idempotentHint": True},
        "slack.list_users": {"readOnlyHint": True, "idempotentHint": True},
        "slack.get_history": {"readOnlyHint": True, "idempotentHint": True},
        "slack.post_message": {
            "readOnlyHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
        # ── collaboration ──────────────────────────────────────────────────────
        "collab.queue_status": {"readOnlyHint": True, "idempotentHint": True},
        "collab.add_task": {"readOnlyHint": False, "idempotentHint": False},
        "collab.search_knowledge": {"readOnlyHint": True, "idempotentHint": True},
        # ── code intelligence ─────────────────────────────────────────────────
        "code.impact_analysis": {"readOnlyHint": True, "idempotentHint": True},
        "code.dependency_graph": {"readOnlyHint": True, "idempotentHint": True},
        "code.find_callers": {"readOnlyHint": True, "idempotentHint": True},
        "code.suggest_tests": {"readOnlyHint": True, "idempotentHint": True},
        "code.complexity_report": {"readOnlyHint": True, "idempotentHint": True},
        "code.class_hierarchy": {"readOnlyHint": True, "idempotentHint": True},
        # ── workflows ─────────────────────────────────────────────────────────
        "workflow.run": {"readOnlyHint": False, "idempotentHint": False},
        "workflow.list": {"readOnlyHint": True, "idempotentHint": True},
        # ── dynamic tools ─────────────────────────────────────────────────────
        "system.create_tool": {
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": True,
        },
        "system.list_dynamic_tools": {"readOnlyHint": True, "idempotentHint": True},
        # ── alerts ────────────────────────────────────────────────────────────
        "system.alert_history": {"readOnlyHint": True, "idempotentHint": True},
        "system.alert_rules": {"readOnlyHint": True, "idempotentHint": True},
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
                    from ai.insights import get_engine

                    insights = get_engine().get_cached_insights(kind="weekly")[:limit]
                    return {"insights": insights, "count": len(insights)}
                except Exception as e:
                    return {"error": str(e), "insights": [], "count": 0}

        elif tool_name == "system.alert_history":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_alert_history(
                limit: int = 20,
                _tn=tool_name,
            ):
                try:
                    from ai.alerts.history import get_recent

                    alerts = get_recent(limit=limit)
                    return {"alerts": alerts, "count": len(alerts)}
                except Exception as e:
                    return {"error": str(e), "alerts": [], "count": 0}

        elif tool_name == "system.alert_rules":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_alert_rules(_tn=tool_name):
                try:
                    from ai.alerts.rules import get_rules_engine

                    rules = get_rules_engine().get_all_rules()
                    return {
                        "rules": [
                            {
                                "rule_id": r.rule_id,
                                "event_type": r.event_type,
                                "title": r.title,
                                "urgency": r.urgency,
                                "cooldown_seconds": r.cooldown_seconds,
                                "enabled": r.enabled,
                            }
                            for r in rules
                        ],
                        "count": len(rules),
                    }
                except Exception as e:
                    return {"error": str(e), "rules": [], "count": 0}

        elif tool_name == "knowledge.session_history":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_session_history(
                query: str,
                limit: int = 5,
                _tn=tool_name,
            ):
                try:
                    from ai.config import PROJECT_ROOT
                    from ai.learning.handoff_parser import parse_handoff

                    entries = parse_handoff(PROJECT_ROOT / "HANDOFF.md")

                    if not entries:
                        return {"sessions": [], "count": 0}

                    # Simple text-based search on parsed handoff entries
                    # Filter entries that match the query terms
                    query_terms = query.lower().split()
                    scored_entries = []

                    for entry in entries:
                        done_tasks = " ".join(entry.done_tasks)
                        open_tasks = " ".join(entry.open_tasks)
                        text = f"{entry.agent} {entry.summary} {done_tasks} {open_tasks}".lower()
                        score = sum(1 for term in query_terms if term in text)
                        if score > 0:
                            scored_entries.append((score, entry))

                    # Sort by score descending, then by timestamp descending
                    scored_entries.sort(key=lambda x: (-x[0], x[1].timestamp), reverse=False)

                    # Take top results
                    top_entries = scored_entries[:limit]

                    results = [
                        {
                            "timestamp": entry.timestamp,
                            "agent": entry.agent,
                            "summary": entry.summary,
                            "done_tasks": entry.done_tasks,
                            "open_tasks": entry.open_tasks,
                        }
                        for _, entry in top_entries
                    ]

                    return {"sessions": results, "count": len(results)}
                except Exception as e:
                    return {"error": str(e), "sessions": [], "count": 0}

        elif tool_name == "collab.queue_status":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_queue_status(_tn=tool_name):
                try:
                    from ai.collab.task_queue import get_queue

                    queue = get_queue()
                    status = queue.get_queue_status()
                    return status
                except Exception as e:
                    return {"error": str(e), "status": {}}

        elif tool_name == "collab.add_task":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_add_task(
                title: str,
                task_type: str,
                description: str = "",
                priority: int = 3,
                _tn=tool_name,
            ):
                try:
                    from ai.collab.task_queue import TaskType, get_queue

                    queue = get_queue()
                    task_type_enum = TaskType(task_type)
                    task_id = queue.add_task(
                        title=title,
                        task_type=task_type_enum,
                        description=description,
                        priority=priority,
                    )
                    return {"task_id": task_id, "status": "added"}
                except Exception as e:
                    return {"error": str(e), "task_id": None}

        elif tool_name == "collab.search_knowledge":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_search_knowledge(
                query: str,
                top_k: int = 5,
                _tn=tool_name,
            ):
                try:
                    from ai.collab.knowledge_base import get_agent_knowledge

                    kb = get_agent_knowledge()
                    results = kb.query_knowledge(query=query, top_k=top_k)
                    return {"results": results, "query": query, "count": len(results)}
                except Exception as e:
                    return {"error": str(e), "results": [], "count": 0}

        elif tool_name == "code.impact_analysis":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_impact_analysis(
                changed_files: str,
                include_tests: bool = True,
                max_depth: int = 3,
                _tn=tool_name,
            ):
                try:
                    from ai.code_intel.store import get_code_store

                    store = get_code_store()
                    files = [f.strip() for f in changed_files.split(",") if f.strip()]
                    result = store.query_impact(
                        files,
                        max_depth=max_depth,
                        include_tests=include_tests,
                    )
                    return result
                except Exception as e:
                    return {"error": str(e), "impact": {}}

        elif tool_name == "code.dependency_graph":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_dependency_graph(
                module: str,
                direction: str = "both",
                max_depth: int = 3,
                _tn=tool_name,
            ):
                try:
                    from ai.code_intel.store import get_code_store

                    store = get_code_store()
                    return store.query_dependency_graph(
                        module, direction=direction, max_depth=max_depth
                    )
                except Exception as e:
                    return {
                        "error": str(e),
                        "module": module,
                        "direction": direction,
                        "dependencies": [],
                        "dependents": [],
                        "edges": [],
                        "circular": [],
                    }

        elif tool_name == "code.find_callers":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_find_callers(
                function_name: str,
                include_indirect: bool = True,
                _tn=tool_name,
            ):
                try:
                    from ai.code_intel.store import get_code_store

                    store = get_code_store()
                    callers = store.find_callers(function_name, include_indirect)
                    return {"function": function_name, "callers": callers}
                except Exception as e:
                    return {"error": str(e), "callers": []}

        elif tool_name == "code.suggest_tests":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_suggest_tests(
                changed_files: str,
                _tn=tool_name,
            ):
                try:
                    from ai.code_intel.store import get_code_store

                    store = get_code_store()
                    files = [f.strip() for f in changed_files.split(",")]
                    tests = store.suggest_tests(files)
                    return {"files": files, "suggested_tests": tests}
                except Exception as e:
                    return {"error": str(e), "suggested_tests": []}

        elif tool_name == "code.complexity_report":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_complexity_report(
                target: str | None = None,
                threshold: int = 10,
                _tn=tool_name,
            ):
                try:
                    from ai.code_intel.store import get_code_store

                    store = get_code_store()
                    report = store.get_complexity_report(target, threshold)
                    return report
                except Exception as e:
                    return {"error": str(e), "complexity": []}

        elif tool_name == "code.class_hierarchy":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_class_hierarchy(
                class_name: str,
                _tn=tool_name,
            ):
                try:
                    from ai.code_intel.store import get_code_store

                    store = get_code_store()
                    hierarchy = store.get_class_hierarchy(class_name)
                    return {"class": class_name, "hierarchy": hierarchy}
                except Exception as e:
                    return {"error": str(e), "hierarchy": {}}

        elif tool_name == "workflow.list":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_workflow_list(_tn=tool_name):
                try:
                    from ai.workflows.definitions import get_workflow_store

                    store = get_workflow_store()
                    workflows = store.list_workflows()
                    return {"workflows": workflows, "count": len(workflows)}
                except Exception as e:
                    return {"error": str(e), "workflows": [], "count": 0}

        elif tool_name == "workflow.run":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_workflow_run(
                workflow_id: str | None = None,
                steps: str | None = None,
                _tn=tool_name,
            ):
                try:
                    import asyncio
                    import json

                    from ai.workflows.runner import get_runner

                    runner = get_runner()
                    if steps:
                        step_list = json.loads(steps)
                        result = asyncio.run(runner.run_plan(step_list))
                    elif workflow_id:
                        from ai.workflows.definitions import get_workflow_store

                        store = get_workflow_store()
                        wf = store.get_workflow(workflow_id)
                        if wf:
                            result = asyncio.run(runner.run_plan(wf.get("steps", [])))
                        else:
                            return {"error": f"Workflow {workflow_id} not found"}
                    else:
                        return {"error": "Either workflow_id or steps required"}
                    return result
                except Exception as e:
                    return {"error": str(e)}

        elif tool_name == "system.create_tool":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_create_tool(
                name: str,
                description: str,
                handler_code: str,
                parameters: str | None = None,
                _tn=tool_name,
            ):
                try:
                    import json

                    from ai.tools.builder import get_builder

                    builder = get_builder()
                    params = json.loads(parameters) if parameters else None
                    result = builder.create_tool(
                        name=name,
                        description=description,
                        handler_code=handler_code,
                        parameters=params,
                    )
                    return result
                except Exception as e:
                    return {"error": str(e), "status": "failed"}

        elif tool_name == "system.list_dynamic_tools":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_list_dynamic_tools(_tn=tool_name):
                try:
                    from ai.tools.builder import get_builder

                    builder = get_builder()
                    tools = builder.list_dynamic_tools()
                    return {"tools": tools, "count": len(tools)}
                except Exception as e:
                    return {"error": str(e), "tools": [], "count": 0}

        elif tool_name == "system.dep_audit":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_dep_audit(_tn=tool_name):
                try:
                    from ai.system.depaudit import get_latest_report

                    result = get_latest_report()
                    if result:
                        return {
                            "vulnerable": result.vulnerable,
                            "fixed": result.fixed,
                            "packages": [
                                {
                                    "name": p.name,
                                    "version": p.version,
                                    "vulns": [
                                        {"id": v.id, "severity": v.severity} for v in p.vulns
                                    ],
                                }
                                for p in result.packages
                            ],
                            "generated_at": result.generated_at,
                        }
                    return {"error": "No audit report found", "vulnerable": 0}
                except Exception as e:
                    return {"error": str(e), "vulnerable": 0}

        elif tool_name == "system.dep_audit_history":

            @mcp.tool(name=tool_name, description=description, annotations=ann)
            async def _handler_dep_audit_history(
                limit: int = 30,
                _tn=tool_name,
            ):
                try:
                    from ai.system.depaudit import get_report_history

                    history = get_report_history(limit=limit)
                    return {"reports": history, "count": len(history)}
                except Exception as e:
                    return {"error": str(e), "reports": [], "count": 0}

        # Built-in health tool (MCP protocol)

    @mcp.tool(name="health", description="Bridge health check")
    async def _health():
        return await health_check()

    # Plain HTTP health endpoint (for curl/monitoring)
    @mcp.custom_route("/health", methods=["GET"])
    async def _http_health(request):
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok", "tools": _TOOL_COUNT, "service": "bazzite-mcp-bridge"})

    # Performance metrics tool
    @mcp.tool(
        name="system.perf_metrics",
        description="Get performance metrics for tracked functions (calls, latency, errors)",
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def _handler_perf_metrics(function: str | None = None, reset: bool = False):
        try:
            from ai.metrics import get_metrics, reset_metrics

            if reset:
                reset_metrics(function)
                return {"status": "reset", "function": function}

            if function:
                return {function: get_metrics(function)}
            return get_metrics()
        except Exception as e:
            return {"error": str(e)}

    # Slack tools
    @mcp.tool(
        name="slack.list_channels",
        description="List Slack channels",
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def _slack_list_channels(limit: int = 100):
        from ai.slack.handlers import handle_slack_list_channels

        return await handle_slack_list_channels({"limit": limit})

    @mcp.tool(
        name="slack.list_users",
        description="List Slack users",
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def _slack_list_users():
        from ai.slack.handlers import handle_slack_list_users

        return await handle_slack_list_users({})

    @mcp.tool(
        name="slack.get_history",
        description="Get Slack channel history",
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def _slack_get_history(channel: str, limit: int = 100):
        from ai.slack.handlers import handle_slack_get_history

        return await handle_slack_get_history({"channel": channel, "limit": limit})

    @mcp.tool(
        name="slack.post_message",
        description="Post a message to Slack",
        annotations={"readOnlyHint": False, "idempotentHint": False, "openWorldHint": True},
    )
    async def _slack_post_message(channel: str, text: str, thread_ts: str | None = None):
        from ai.slack.handlers import handle_slack_post_message

        return await handle_slack_post_message(
            {"channel": channel, "text": text, "thread_ts": thread_ts}
        )

    return mcp
