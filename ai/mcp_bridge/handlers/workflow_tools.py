"""MCP workflow tools for orchestrating multi-agent workflows."""

import json
import logging
import uuid
from datetime import UTC, datetime

from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("workflow_tools")


async def workflow_list(params: dict) -> dict:
    """List all registered workflow definitions."""
    from ai.workflows.definitions import WORKFLOW_REGISTRY

    return {
        "workflows": [
            {"name": name, "description": wf["description"], "step_count": len(wf["steps"])}
            for name, wf in WORKFLOW_REGISTRY.items()
        ]
    }


async def workflow_run(params: dict) -> dict:
    """Trigger a named workflow. Logs run to workflow_runs table."""

    from ai.rag.store import VectorStore
    from ai.workflows.definitions import WORKFLOW_REGISTRY
    from ai.workflows.runner import WorkflowRunner

    name = params.get("name")
    triggered_by = params.get("triggered_by", "mcp")

    if name not in WORKFLOW_REGISTRY:
        return {"error": f"Unknown workflow: {name}"}

    run_id = str(uuid.uuid4())
    started_at = datetime.now(UTC).isoformat()

    store = VectorStore()
    schemas = store._get_schemas()

    try:
        run_record = {
            "run_id": run_id,
            "workflow_name": name,
            "triggered_by": triggered_by,
            "started_at": started_at,
            "completed_at": "",
            "status": "running",
            "step_count": len(WORKFLOW_REGISTRY[name]["steps"]),
            "steps_completed": 0,
            "result_summary": "{}",
            "error": "",
            "vector": _embed_workflow_status(name, "running"),
        }
        table = store._ensure_table("workflow_runs", schemas["workflow_runs"])
        table.add([run_record])
    except Exception:
        logger.exception("Failed to log workflow run start")

    runner = WorkflowRunner()
    result = await runner.run_plan(WORKFLOW_REGISTRY[name]["steps"])

    completed_at = datetime.now(UTC).isoformat()
    steps_completed = sum(1 for s in result["steps"].values() if s.get("status") == "complete")

    result_summary = json.dumps({k: v.get("status") for k, v in result["steps"].items()})

    try:
        table = store._ensure_table("workflow_runs", schemas["workflow_runs"])
        table.update(
            f"run_id = '{run_id}'",
            {
                "completed_at": completed_at,
                "status": result["status"],
                "steps_completed": steps_completed,
                "result_summary": result_summary,
                "vector": _embed_workflow_status(name, result["status"]),
            },
        )
    except Exception:
        logger.exception("Failed to update workflow run status")

    return {
        "workflow": name,
        "status": result["status"],
        "run_id": run_id,
        "steps": result["steps"],
    }


async def workflow_status(params: dict) -> dict:
    """Get last run result for a workflow from workflow_runs table."""
    from ai.rag.store import VectorStore

    name = params.get("name")
    if not name:
        return {"error": "Missing required parameter: name"}

    store = VectorStore()
    try:
        schemas = store._get_schemas()
        table = store._ensure_table("workflow_runs", schemas["workflow_runs"])
        df = table.to_pandas()
        if df.empty:
            return {"runs": []}

        filtered = df[df["workflow_name"] == name].sort_values("started_at", ascending=False)
        if filtered.empty:
            return {"runs": []}

        latest = filtered.iloc[0]
        return {
            "runs": [
                {
                    "run_id": latest["run_id"],
                    "workflow_name": latest["workflow_name"],
                    "status": latest["status"],
                    "started_at": latest["started_at"],
                    "completed_at": latest["completed_at"],
                    "step_count": latest["step_count"],
                    "steps_completed": latest["steps_completed"],
                    "error": latest["error"],
                }
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def workflow_agents(params: dict) -> dict:
    """List all registered agents and their supported task types."""
    from ai.orchestration import get_default_bus

    bus = get_default_bus()
    agents = await bus.list_agents()

    result_agents = []
    for agent_name in agents:
        handler = await bus.registry.get(agent_name)
        if handler:
            result_agents.append(
                {
                    "name": agent_name,
                    "task_types": _get_task_types_for_agent(agent_name),
                }
            )

    return {"agents": result_agents}


def _get_task_types_for_agent(agent_name: str) -> list[str]:
    """Get supported task types for an agent by class lookup."""
    agent_task_types = {
        "security": ["scan_ioc", "run_audit", "check_cve_freshness"],
        "code_quality": ["lint_check", "ast_query", "suggest_refactor"],
        "performance": ["profile_tool", "detect_regression", "tune_cache"],
        "knowledge": ["store_insight", "retrieve_context", "summarize_session"],
        "timer_sentinel": ["check_timers", "alert_stale", "reschedule"],
    }
    return agent_task_types.get(agent_name, [])


async def workflow_handoff(params: dict) -> dict:
    """Manually dispatch a task message to a named agent."""
    from ai.orchestration import AgentMessage, get_default_bus

    agent = params.get("agent")
    task_type = params.get("task_type")
    if not agent or not task_type:
        return {"error": "Missing required parameters: agent, task_type"}

    msg = AgentMessage(
        source_agent="mcp_user",
        target_agent=agent,
        task_type=task_type,
        payload=params.get("payload", {}),
        priority=params.get("priority", 0),
    )

    result = await get_default_bus().dispatch(msg)
    return {"success": result.success, "data": result.data, "error": result.error}


async def workflow_history(params: dict) -> dict:
    """Query workflow_runs table. Params: workflow_name (optional), limit (default 10)."""
    from ai.rag.store import VectorStore

    workflow_name = params.get("workflow_name")
    limit = params.get("limit", 10)

    store = VectorStore()
    try:
        schemas = store._get_schemas()
        table = store._ensure_table("workflow_runs", schemas["workflow_runs"])
        df = table.to_pandas()
        if df.empty:
            return {"runs": []}

        if workflow_name:
            df = df[df["workflow_name"] == workflow_name]

        df = df.sort_values("started_at", ascending=False).head(limit)

        runs = []
        for _, row in df.iterrows():
            runs.append(
                {
                    "run_id": row["run_id"],
                    "workflow_name": row["workflow_name"],
                    "triggered_by": row["triggered_by"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "step_count": row["step_count"],
                    "steps_completed": row["steps_completed"],
                    "error": row["error"],
                }
            )
        return {"runs": runs}
    except Exception as e:
        return {"error": str(e)}


def _embed_workflow_status(workflow_name: str, status: str) -> list[float]:
    """Generate a simple embedding for workflow status."""
    try:
        return embed(f"{workflow_name} {status}")
    except Exception:
        return [0.0] * 384
