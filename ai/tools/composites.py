"""Composite tool patterns."""

import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger("ai.tools")


async def _error_result(msg: str) -> str:
    """Return an error string as a coroutine (used as fallback in parallel dispatch)."""
    return msg


class CompositeToolFactory:
    """Factory for creating composite tools from multiple sub-tools."""

    def __init__(self):
        self._composites: dict[str, Callable] = {}

    def create_composite(
        self,
        name: str,
        description: str,
        sub_tools: list[dict],
    ) -> Callable:
        """Create a composite function that calls multiple tools."""

        async def composite_func(**kwargs) -> dict:
            parallel_tasks = []
            sequential_results = {}

            for sub in sub_tools:
                tool_name = sub.get("tool")
                tool_args = sub.get("args", {})
                is_parallel = sub.get("parallel", False)

                for k, v in kwargs.items():
                    if k not in tool_args:
                        tool_args[k] = v

                if is_parallel:
                    parallel_tasks.append((tool_name, tool_args))
                else:
                    try:
                        from ai.mcp_bridge.tools import execute_tool

                        result = await execute_tool(tool_name, tool_args)
                        sequential_results[tool_name] = result
                    except Exception as e:
                        logger.error(f"Tool {tool_name} failed: {e}")
                        sequential_results[tool_name] = f"Error: {e}"

            if parallel_tasks:
                tasks = []
                for tool_name, tool_args in parallel_tasks:
                    try:
                        from ai.mcp_bridge.tools import execute_tool

                        tasks.append(execute_tool(tool_name, tool_args))
                    except Exception as e:
                        err = f"Error: {e}"
                        logger.error(f"Tool {tool_name} failed: {e}")
                        tasks.append(_error_result(err))

                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                for (tool_name, _), result in zip(parallel_tasks, parallel_results, strict=False):
                    sequential_results[tool_name] = result

            return {
                "composite": name,
                "results": sequential_results,
            }

        return composite_func


_factory_instance: CompositeToolFactory | None = None


def get_composite_factory() -> CompositeToolFactory:
    """Get singleton CompositeToolFactory."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = CompositeToolFactory()
    return _factory_instance
