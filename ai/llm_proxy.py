"""Lightweight OpenAI-compatible proxy for the LiteLLM router.

Exposes /v1/chat/completions on localhost so Newelle can use our full
provider fallback chain (Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras).

This runs as a SEPARATE process from the MCP bridge (which must never
import ai.router to avoid key scope widening). Start it with:

    python -m ai.llm_proxy --port 8767

Or via the launch script:

    bash scripts/start-llm-proxy.sh
"""

import argparse
import json
import logging
import os
import threading
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("ai.llm_proxy")

# Module-level aliases — populated lazily on first use.
# Defined here so patch("ai.llm_proxy.route_chat") works in tests.
try:
    from ai.rag.memory import retrieve_relevant_context, store_interaction
    from ai.router import (
        get_cost_stats,
        get_health_snapshot,
        get_usage_stats,
        route_chat,
        route_query_stream,
    )
except Exception:  # noqa: BLE001
    route_chat = None  # type: ignore[assignment]
    route_query_stream = None  # type: ignore[assignment]
    get_health_snapshot = None  # type: ignore[assignment]
    get_usage_stats = None  # type: ignore[assignment]
    get_cost_stats = None  # type: ignore[assignment]
    retrieve_relevant_context = None  # type: ignore[assignment]
    store_interaction = None  # type: ignore[assignment]

DEFAULT_PORT = int(os.environ.get("LLM_PROXY_PORT", "8767"))
_LLM_STATUS_FILE = Path.home() / "security" / "llm-status.json"
_STATUS_WRITE_INTERVAL_S = 300  # 5 minutes
_status_timer: threading.Timer | None = None


def _write_llm_status() -> None:
    """Write LLM routing status to ~/security/llm-status.json atomically."""
    import yaml  # noqa: PLC0415

    from ai.config import LITELLM_CONFIG  # noqa: PLC0415

    try:
        with open(LITELLM_CONFIG) as f:
            cfg = yaml.safe_load(f) or {}
        models: dict[str, str] = {}
        for entry in cfg.get("model_list", []):
            name = entry.get("model_name", "")
            if name and name not in models:
                models[name] = entry.get("litellm_params", {}).get("model", "?")

        status = {
            "updated_at": datetime.now(UTC).isoformat(),
            "providers": get_health_snapshot(),
            "usage": get_cost_stats(),
            "generated_at": datetime.now(UTC).isoformat(),
            "models": {k: models.get(k, "?") for k in ("fast", "reason", "batch", "code")},
        }
        tmp = _LLM_STATUS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(status, indent=2))
        tmp.rename(_LLM_STATUS_FILE)
    except Exception as e:
        logger.warning("Failed to write LLM status: %s", e)


def _schedule_status_writer() -> None:
    """Write status immediately, then reschedule every 5 minutes.

    Uses a module-level timer reference so repeated calls cancel the pending
    timer instead of spawning a second parallel chain.
    """
    global _status_timer  # noqa: PLW0603
    if _status_timer is not None:
        _status_timer.cancel()
    _write_llm_status()
    _status_timer = threading.Timer(_STATUS_WRITE_INTERVAL_S, _schedule_status_writer)
    _status_timer.daemon = True
    _status_timer.start()


def _assert_localhost(bind: str) -> None:
    if bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(f"LLM proxy must bind to localhost only, got '{bind}'")


async def _stream_response(task_type: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream from the router, yielding SSE-formatted chunks."""
    async for chunk in route_query_stream(task_type, messages):
        data = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": f"bazzite-router/{task_type}",
            "choices": [{
                "index": 0,
                "delta": {"content": chunk},
                "finish_reason": None,
            }],
        }
        yield f"data: {json.dumps(data)}\n\n"

    # Final chunk with finish_reason
    final = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": f"bazzite-router/{task_type}",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }],
    }
    yield f"data: {json.dumps(final)}\n\n"
    yield "data: [DONE]\n\n"


def create_app():
    """Create the FastAPI/Starlette proxy app."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse, StreamingResponse
    from starlette.routing import Route

    async def chat_completions(request: Request):
        """OpenAI-compatible /v1/chat/completions endpoint."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": {"message": "Invalid JSON"}}, status_code=400)

        messages = body.get("messages", [])
        model = body.get("model", "fast")
        stream = body.get("stream", False)

        # Map model names to router task types
        task_map = {
            "auto": "fast",
            "fast": "fast",
            "reason": "reason",
            "batch": "batch",
            "code": "code",
            # Common model names → fast task type
            "gpt-4o-mini": "fast",
            "gpt-4o": "reason",
            "llama-3.3-70b": "fast",
            "deepseek-chat": "reason",
        }
        task_type = task_map.get(model, "fast")

        # Opt-in conversation memory: inject past context before routing
        user_message = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        if user_message and os.environ.get("ENABLE_CONVERSATION_MEMORY", "").lower() == "true":
            try:
                contexts = retrieve_relevant_context(user_message)
                if contexts:
                    context_text = (
                        "Relevant context from past conversations:\n" + "\n".join(contexts)
                    )
                    messages = list(messages)
                    if messages and messages[0].get("role") == "system":
                        messages[0] = {
                            **messages[0],
                            "content": context_text + "\n\n" + messages[0]["content"],
                        }
                    else:
                        messages.insert(0, {"role": "system", "content": context_text})
            except Exception as _mem_exc:  # noqa: BLE001
                logger.debug("Memory retrieval skipped: %s", _mem_exc)

        if stream:
            return StreamingResponse(
                _stream_response(task_type, messages),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )

        # Non-streaming — pass full messages to preserve multi-turn history
        try:
            result = await route_chat(task_type, messages)

            # Store interaction in conversation memory after successful response
            if user_message and os.environ.get("ENABLE_CONVERSATION_MEMORY", "").lower() == "true":
                try:
                    store_interaction(user_message, result[:200], task_type)
                except Exception as _mem_exc:  # noqa: BLE001
                    logger.debug("Memory storage skipped: %s", _mem_exc)

            return JSONResponse({
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": f"bazzite-router/{task_type}",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
        except Exception as e:
            logger.error("Router query failed: %s", e)
            return JSONResponse(
                {"error": {"message": str(e)}},
                status_code=500,
            )

    async def list_models(request: Request):
        """OpenAI-compatible /v1/models endpoint."""
        models = [
            {"id": "fast", "object": "model", "owned_by": "bazzite-router"},
            {"id": "reason", "object": "model", "owned_by": "bazzite-router"},
            {"id": "batch", "object": "model", "owned_by": "bazzite-router"},
            {"id": "code", "object": "model", "owned_by": "bazzite-router"},
            {"id": "auto", "object": "model", "owned_by": "bazzite-router"},
        ]
        return JSONResponse({"object": "list", "data": models})

    async def health(request: Request):
        return JSONResponse({"status": "ok", "service": "bazzite-llm-proxy"})

    return Starlette(routes=[
        Route("/v1/chat/completions", chat_completions, methods=["POST"]),
        Route("/v1/models", list_models, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
    ])


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Bazzite LLM Router Proxy")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    _assert_localhost(args.bind)

    logging.basicConfig(level=logging.INFO)
    _schedule_status_writer()
    logger.info("LLM proxy starting on %s:%d", args.bind, args.port)
    logger.info("Provider chain: Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras")

    app = create_app()
    uvicorn.run(app, host=args.bind, port=args.port)


if __name__ == "__main__":
    main()
