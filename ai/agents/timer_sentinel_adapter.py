"""BaseAgent adapter for timer sentinel agent."""

import asyncio
import time

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType


class TimerSentinelAgent(BaseAgent):
    """Adapter wrapping ai.agents.timer_sentinel for orchestration bus."""

    name = "timer_sentinel"
    supported_task_types = [
        TaskType.CHECK_TIMERS,
        TaskType.ALERT_STALE,
        TaskType.RESCHEDULE,
    ]

    async def handle(self, message: AgentMessage) -> AgentResult:
        start_time = time.monotonic()
        try:
            if message.task_type == TaskType.CHECK_TIMERS:
                from ai.agents.timer_sentinel import check_timers

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, check_timers)
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.ALERT_STALE:
                from ai.agents.timer_sentinel import check_timers

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, check_timers)
                stale_timers = result.get("stale", [])
                if stale_timers:
                    alert_msg = f"Stale timers detected: {', '.join(stale_timers)}"
                else:
                    alert_msg = "No stale timers"
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data={"alert": alert_msg, "stale_count": len(stale_timers)},
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.RESCHEDULE:
                timer_name = message.payload.get("timer_name", "")
                if not timer_name:
                    return AgentResult(
                        correlation_id=message.correlation_id,
                        source_agent=self.name,
                        success=False,
                        data={},
                        error="No timer_name provided in payload",
                        duration_seconds=time.monotonic() - start_time,
                    )
                try:
                    import subprocess

                    result = subprocess.run(
                        ["systemctl", "start", timer_name],
                        capture_output=True,
                        timeout=10,
                    )
                    success = result.returncode == 0
                    output = result.stdout.decode("utf-8", errors="replace").strip()
                    error = (
                        result.stderr.decode("utf-8", errors="replace").strip()
                        if result.returncode != 0
                        else None
                    )
                    return AgentResult(
                        correlation_id=message.correlation_id,
                        source_agent=self.name,
                        success=success,
                        data={"timer": timer_name, "started": success, "output": output},
                        error=error,
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
