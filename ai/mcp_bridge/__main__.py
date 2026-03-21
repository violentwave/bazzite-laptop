"""python -m ai.mcp_bridge entry point."""

import argparse
import logging
import os
import signal
import sys

logger = logging.getLogger("ai.mcp_bridge")


def main() -> None:
    """Start the MCP bridge server."""
    parser = argparse.ArgumentParser(description="Bazzite MCP Bridge")
    parser.add_argument(
        "--bind",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_BRIDGE_PORT", "8766")),
        help="Port (default: 8766)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    from ai.config import load_keys  # noqa: PLC0415

    if not load_keys(scope="threat_intel"):
        logger.error("Failed to load threat_intel keys -- exiting")
        sys.exit(1)

    from ai.mcp_bridge.server import _assert_localhost, create_app  # noqa: PLC0415

    _assert_localhost(args.bind)

    app = create_app()

    # SIGTERM handler for graceful shutdown
    def _sigterm_handler(signum, frame):
        logger.info("SIGTERM received -- shutting down")
        try:
            from ai.g4f_manager import get_manager  # noqa: PLC0415

            get_manager().stop()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _sigterm_handler)

    logger.info("MCP bridge starting on %s:%d", args.bind, args.port)
    app.run(transport="streamable-http", host=args.bind, port=args.port)


if __name__ == "__main__":
    main()
