"""BaseAgent adapter for security audit agent."""

import asyncio
import time

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType


class SecurityAuditAgent(BaseAgent):
    """Adapter wrapping ai.agents.security_audit for orchestration bus."""

    name = "security"
    supported_task_types = [
        TaskType.SCAN_IOC,
        TaskType.RUN_AUDIT,
        TaskType.CHECK_CVE_FRESHNESS,
    ]

    async def handle(self, message: AgentMessage) -> AgentResult:
        start_time = time.monotonic()
        try:
            if message.task_type == TaskType.RUN_AUDIT:
                from ai.agents.security_audit import run_audit

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_audit)
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.SCAN_IOC:
                ioc = message.payload.get("ioc", "")
                if not ioc:
                    return AgentResult(
                        correlation_id=message.correlation_id,
                        source_agent=self.name,
                        success=False,
                        data={},
                        error="No IOC provided in payload",
                        duration_seconds=time.monotonic() - start_time,
                    )
                try:
                    from ai.threat_intel.lookup import lookup_ioc

                    result = await lookup_ioc(ioc)
                except ImportError:
                    result = {"error": "lookup_ioc not implemented", "ioc": ioc}
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.CHECK_CVE_FRESHNESS:
                try:
                    from ai.security.alerts import check_freshness

                    result = await check_freshness()
                except ImportError:
                    result = {"error": "check_freshness not implemented"}
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
