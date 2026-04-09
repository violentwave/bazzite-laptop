"""BaseAgent adapter for knowledge storage agent."""

import asyncio
import time

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType


class KnowledgeStorageAgent(BaseAgent):
    """Adapter wrapping ai.agents.knowledge_storage for orchestration bus."""

    name = "knowledge"
    supported_task_types = [
        TaskType.STORE_INSIGHT,
        TaskType.RETRIEVE_CONTEXT,
        TaskType.SUMMARIZE_SESSION,
    ]

    async def handle(self, message: AgentMessage) -> AgentResult:
        start_time = time.monotonic()
        try:
            if message.task_type == TaskType.STORE_INSIGHT:
                from ai.agents.knowledge_storage import run_storage_check

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_storage_check)
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.RETRIEVE_CONTEXT:
                query = message.payload.get("query", "")
                try:
                    from ai.rag.query import rag_query

                    result = await rag_query(query, use_llm=False)
                    result = {"answer": result.answer, "sources": result.sources}
                except ImportError:
                    result = {"error": "rag_query not implemented", "query": query}
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data=result,
                    duration_seconds=time.monotonic() - start_time,
                )
            elif message.task_type == TaskType.SUMMARIZE_SESSION:
                session_id = message.payload.get("session_id", "")
                try:
                    from ai.learning.session_summary import summarize_session

                    result = await summarize_session(session_id)
                except ImportError:
                    result = {"error": "session summary not implemented", "session_id": session_id}
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
