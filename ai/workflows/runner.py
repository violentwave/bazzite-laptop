"""Workflow runner with ReAct-style tool chaining."""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING

logger = logging.getLogger("ai.workflows")

if TYPE_CHECKING:
    from ai.orchestration import AgentResult


class WorkflowRunner:
    """ReAct-style multi-tool execution."""

    def __init__(self, max_iterations: int = 10, timeout_seconds: int = 120):
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds

    async def run(
        self,
        user_message: str,
        tools: list[dict] | None = None,
        task_type: str = "fast",
    ) -> dict:
        """Execute a workflow with tool calls."""
        start_time = time.time()
        tools_called = []
        iterations = 0

        messages = [{"role": "user", "content": user_message}]

        while iterations < self.max_iterations:
            if time.time() - start_time > self.timeout_seconds:
                logger.warning("Workflow timeout reached")
                break

            try:
                response = await self._call_llm(messages, tools, task_type)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break

            if not response.get("tool_calls"):
                return {
                    "response": response.get("content", ""),
                    "tools_called": tools_called,
                    "iterations": iterations,
                }

            for tool_call in response["tool_calls"]:
                try:
                    result = await self._execute_tool(tool_call)
                    tools_called.append(tool_call["name"])
                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_call["name"],
                            "content": result,
                        }
                    )
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_call["name"],
                            "content": f"Error: {e}",
                        }
                    )

            iterations += 1

        return {
            "response": "Workflow incomplete - max iterations or timeout",
            "tools_called": tools_called,
            "iterations": iterations,
        }

    async def run_plan(self, plan: list[dict], workflow_name: str = "", run_id: str = "") -> dict:
        """Execute a predefined plan with dependencies."""
        results = {}
        completed = set()

        if not run_id:
            run_id = str(uuid.uuid4())

        try:
            from ai.orchestration.observer import get_observer

            observer = get_observer()
        except Exception:
            observer = None

        for step in plan:
            step_id = step.get("id", str(hash(str(step))))
            depends_on = step.get("depends_on", [])

            if any(dep not in completed for dep in depends_on):
                results[step_id] = {"status": "skipped", "reason": "dependencies not met"}
                continue

            step_name = step.get("name", step_id)
            tool_called = step.get("tool", step.get("agent", ""))
            agent_name = step.get("agent", "workflow_runner")

            obs_step_id = None
            if observer and workflow_name:
                try:
                    obs_step_id = observer.record_step_start(
                        run_id=run_id,
                        workflow_name=workflow_name,
                        step_name=step_name,
                        tool_called=tool_called,
                        agent_name=agent_name,
                    )
                except Exception:
                    observer = None

            try:
                if step.get("agent"):
                    agent_result = await self._execute_agent_step(step, results)
                    results[step_id] = {
                        "status": "complete" if agent_result.success else "failed",
                        "result": agent_result.data,
                        "error": agent_result.error,
                    }
                    step_status = "success" if agent_result.success else "failed"
                    if agent_result.success:
                        completed.add(step_id)
                    elif step.get("abort_on_error"):
                        break
                else:
                    try:
                        tool = step.get("tool")
                        args = step.get("args", {})

                        if tool == "llm":
                            result = await self._call_llm_direct(args.get("prompt", ""))
                        else:
                            result = await self._execute_tool({"name": tool, "arguments": args})

                        results[step_id] = {"status": "complete", "result": result}
                        completed.add(step_id)
                        step_status = "success"
                    except Exception as e:
                        results[step_id] = {"status": "failed", "error": str(e)}
                        step_status = "failed"
                        if step.get("abort_on_error", False):
                            break
            except Exception as e:
                results[step_id] = {"status": "failed", "error": str(e)}
                step_status = "failed"

            if observer and obs_step_id:
                try:
                    output = results[step_id].get("result")
                    error = results[step_id].get("error")
                    observer.record_step_end(
                        step_id=obs_step_id,
                        status=step_status,
                        output=output,
                        error=error,
                    )
                except Exception:
                    logger.debug("Failed to record step end for %s", step_id)

        status = (
            "complete"
            if all(r.get("status") == "complete" for r in results.values())
            else "partial"
        )
        return {"steps": results, "status": status, "run_id": run_id}

    async def _execute_agent_step(self, step: dict, results: dict) -> AgentResult:
        """Execute an agent-dispatched step via OrchestrationBus."""
        from ai.orchestration import AgentMessage, get_default_bus

        bus = get_default_bus()

        payload = step.get("args", {})
        if step.get("payload_from") and step["payload_from"] in results:
            upstream = results[step["payload_from"]]
            if upstream.get("status") == "complete":
                payload["upstream_result"] = upstream.get("result")

        msg = AgentMessage(
            source_agent="workflow_runner",
            target_agent=step["agent"],
            task_type=step["task_type"],
            payload=payload,
        )

        return await bus.dispatch(msg)

    async def _call_llm(
        self, messages: list[dict], tools: list[dict] | None, task_type: str
    ) -> dict:
        """Call LLM via router."""
        try:
            from ai.router import route_chat

            result = await route_chat(
                messages=messages,
                tools=tools,
                model="fast" if task_type == "fast" else "balanced",
                parallel_tool_calls=False,
            )
            return result
        except Exception as e:
            logger.error(f"route_chat failed: {e}")
            raise

    async def _call_llm_direct(self, prompt: str) -> str:
        """Direct LLM call."""
        try:
            from ai.router import route_query

            result = await route_query(prompt, model="fast")
            return result
        except Exception as e:
            logger.error(f"route_query failed: {e}")
            raise

    async def _execute_tool(self, tool_call: dict) -> str:
        """Execute a tool call."""
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        try:
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"execute_tool failed: {e}")
            raise

    def _handle_error(self, step: dict, error: Exception, strategy: str = "skip") -> None:
        """Handle workflow errors."""
        if strategy == "retry":
            logger.info(f"Retrying step after error: {error}")
        elif strategy == "skip":
            logger.warning(f"Skipping step due to error: {error}")
        elif strategy == "abort":
            raise error


async def execute_workflow(user_message: str, task_type: str = "fast") -> dict:
    """Execute a workflow."""
    runner = WorkflowRunner()
    return await runner.run(user_message, task_type=task_type)
