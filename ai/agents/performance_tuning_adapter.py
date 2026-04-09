"""BaseAgent adapter for performance tuning agent."""

import asyncio
import time

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType


class PerformanceTuningAgent(BaseAgent):
    """Adapter wrapping ai.agents.performance_tuning for orchestration bus."""

    name = "performance"
    supported_task_types = [
        TaskType.PROFILE_TOOL,
        TaskType.DETECT_REGRESSION,
        TaskType.TUNE_CACHE,
    ]

    async def handle(self, message: AgentMessage) -> AgentResult:
        start_time = time.monotonic()
        try:
            if message.task_type == TaskType.PROFILE_TOOL:
                from ai.agents.performance_tuning import run_tuning

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_tuning)
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.DETECT_REGRESSION:
                baseline_file = message.payload.get("baseline_file", "")
                current_file = message.payload.get("current_file", "")
                try:
                    from ai.perf.regression import detect_regression

                    result = await detect_regression(baseline_file, current_file)
                except ImportError:
                    result = {
                        "error": "regression detection not implemented",
                        "baseline": baseline_file,
                        "current": current_file,
                    }
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.TUNE_CACHE:
                try:
                    from ai.cache.tuning import tune_cache

                    result = await tune_cache()
                except ImportError:
                    result = {"error": "cache tuning not implemented"}
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            else:
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=False,
                    data={},
                    error=f"Unsupported task type: {message.task_type}",
                    duration_seconds=time.monotonic() - start_time,
                )
        except Exception as e:
            return AgentResult(
                correlation_id=message.correlation_id,
                source_agent=self.name,
                success=False,
                data={},
                error=str(e),
                duration_seconds=time.monotonic() - start_time,
            )
