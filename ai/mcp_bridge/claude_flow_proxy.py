"""Stdio-to-HTTP proxy for claude-flow MCP server.

Claude-flow's MCP server uses stdio transport. Newelle only supports
HTTP streamable transport. This proxy bridges the two:

    claude-flow (stdio) ←→ proxy (HTTP on localhost:8768) ←→ Newelle

Usage:
    python -m ai.mcp_bridge.claude_flow_proxy --port 8768

The proxy spawns claude-flow's MCP server as a subprocess, communicates
via stdin/stdout (JSON-RPC), and exposes it as an HTTP endpoint.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger("ai.mcp_bridge.claude_flow_proxy")

DEFAULT_PORT = int(os.environ.get("CLAUDE_FLOW_MCP_PORT", "8768"))
CLAUDE_FLOW_BIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "node_modules", ".bin", "claude-flow",
)


class StdioMCPProxy:
    """Proxy between an HTTP server and a stdio MCP subprocess."""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the claude-flow MCP subprocess."""
        # claude-flow auto-detects MCP mode when stdin is piped (not a TTY)
        # Using "mcp start" explicitly ensures MCP mode even with piped stdin
        cmd = [CLAUDE_FLOW_BIN, "mcp", "start"]
        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            )
            logger.info("claude-flow MCP subprocess started (PID %d)", self._process.pid)
        except FileNotFoundError:
            logger.error("claude-flow not found at %s", CLAUDE_FLOW_BIN)
            raise

    async def send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request to the stdio subprocess and return the response."""
        if self._process is None or self._process.poll() is not None:
            await self.start()

        async with self._lock:
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
            }
            if params:
                request["params"] = params

            line = json.dumps(request) + "\n"
            try:
                self._process.stdin.write(line.encode())
                self._process.stdin.flush()

                # Read response line
                loop = asyncio.get_event_loop()
                response_line = await loop.run_in_executor(
                    None, self._process.stdout.readline
                )
                if not response_line:
                    return {"error": {"code": -32603, "message": "No response from claude-flow"}}

                return json.loads(response_line.decode())
            except (BrokenPipeError, OSError) as e:
                logger.error("claude-flow MCP communication error: %s", e)
                self._process = None
                return {"error": {"code": -32603, "message": str(e)}}

    def stop(self) -> None:
        """Stop the subprocess."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None


def create_app(proxy: StdioMCPProxy):
    """Create the HTTP proxy app."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def mcp_handler(request: Request):
        """Forward JSON-RPC requests to claude-flow stdio."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )

        method = body.get("method", "")
        params = body.get("params")
        request_id = body.get("id")

        result = await proxy.send_request(method, params)

        # Preserve the original request ID
        if request_id is not None:
            result["id"] = request_id

        return JSONResponse(result)

    async def health(request: Request):
        running = proxy._process is not None and proxy._process.poll() is None
        return JSONResponse({
            "status": "ok" if running else "degraded",
            "claude_flow": "running" if running else "stopped",
        })

    return Starlette(routes=[
        Route("/mcp", mcp_handler, methods=["POST"]),
        Route("/health", health, methods=["GET"]),
    ])


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Claude-Flow MCP stdio-to-HTTP proxy")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.bind not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError("Must bind to localhost only")

    logging.basicConfig(level=logging.INFO)
    logger.info("Claude-flow MCP proxy starting on %s:%d", args.bind, args.port)

    proxy = StdioMCPProxy()
    app = create_app(proxy)

    try:
        uvicorn.run(app, host=args.bind, port=args.port)
    finally:
        proxy.stop()


if __name__ == "__main__":
    main()
