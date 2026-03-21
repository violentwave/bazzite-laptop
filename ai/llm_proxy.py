"""Lightweight OpenAI-compatible proxy for the LiteLLM router.

Exposes /v1/chat/completions on localhost so Newelle can use our full
provider fallback chain (Gemini → Groq → Mistral → OpenRouter → g4f).

This runs as a SEPARATE process from the MCP bridge (which must never
import ai.router to avoid key scope widening). Start it with:

    python -m ai.llm_proxy --port 8767

Or via the launch script:

    bash scripts/start-llm-proxy.sh
"""

import argparse
import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncGenerator

logger = logging.getLogger("ai.llm_proxy")

DEFAULT_PORT = int(os.environ.get("LLM_PROXY_PORT", "8767"))


def _assert_localhost(bind: str) -> None:
    if bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(f"LLM proxy must bind to localhost only, got '{bind}'")


async def _stream_response(task_type: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream from the router, yielding SSE-formatted chunks."""
    from ai.router import route_query_stream  # noqa: PLC0415

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

        if stream:
            return StreamingResponse(
                _stream_response(task_type, messages),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )

        # Non-streaming
        try:
            from ai.router import route_query  # noqa: PLC0415

            prompt = messages[-1]["content"] if messages else ""
            result = route_query(task_type, prompt)
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
    logger.info("LLM proxy starting on %s:%d", args.bind, args.port)
    logger.info("Provider chain: Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras")

    app = create_app()
    uvicorn.run(app, host=args.bind, port=args.port)


if __name__ == "__main__":
    main()
