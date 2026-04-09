"""CLI for triggering workflows from systemd or manual invocation."""

import argparse
import asyncio
import logging
import sys

from ai.workflows.definitions import WORKFLOW_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ai.workflows.cli")


async def run_workflow(workflow_name: str) -> dict:
    """Run a workflow by name, using the MCP handler logic."""
    from ai.mcp_bridge.handlers.workflow_tools import workflow_run

    result = await workflow_run({"name": workflow_name, "triggered_by": "timer"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Bazzite AI Workflow CLI")
    parser.add_argument("--run", dest="workflow_name", help="Workflow name to run")
    args = parser.parse_args()

    if not args.workflow_name:
        parser.print_help()
        return 1

    if args.workflow_name not in WORKFLOW_REGISTRY:
        logger.error("Unknown workflow: %s", args.workflow_name)
        logger.info("Available workflows: %s", ", ".join(WORKFLOW_REGISTRY.keys()))
        return 1

    logger.info("Running workflow: %s", args.workflow_name)
    result = asyncio.run(run_workflow(args.workflow_name))

    if "error" in result:
        logger.error("Workflow failed: %s", result["error"])
        return 1

    logger.info("Workflow %s completed with status: %s", args.workflow_name, result.get("status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
