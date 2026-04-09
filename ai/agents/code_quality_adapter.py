"""BaseAgent adapter for code quality agent."""

import asyncio
import time

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType


class CodeQualityAgent(BaseAgent):
    """Adapter wrapping ai.agents.code_quality_agent for orchestration bus."""

    name = "code_quality"
    supported_task_types = [
        TaskType.LINT_CHECK,
        TaskType.AST_QUERY,
        TaskType.SUGGEST_REFACTOR,
    ]

    async def handle(self, message: AgentMessage) -> AgentResult:
        start_time = time.monotonic()
        try:
            if message.task_type == TaskType.LINT_CHECK:
                from ai.agents.code_quality_agent import run_code_check

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_code_check)
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.AST_QUERY:
                code = message.payload.get("code", "")
                query = message.payload.get("query", "")
                try:
                    from ai.code_analysis.ast_utils import parse_and_query

                    result = await parse_and_query(code, query)
                except ImportError:
                    result = {"error": "ast_utils not implemented", "code": code, "query": query}
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.SUGGEST_REFACTOR:
                file_path = message.payload.get("file_path", "")
                try:
                    from ai.code_analysis.refactor import suggest_refactor

                    result = await suggest_refactor(file_path)
                except ImportError:
                    result = {"error": "refactor module not implemented", "file_path": file_path}
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
