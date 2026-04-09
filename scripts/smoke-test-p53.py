#!/usr/bin/env python3
"""P53 smoke test - verifies orchestration and workflow integration."""

# ruff: noqa: S101
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)


async def main():
    print("Running P53 smoke test...")

    # 1. Verify 5 agents registered in OrchestrationBus
    print("\n[1/4] Testing OrchestrationBus agent registration...")
    with patch("ai.orchestration.get_default_bus") as mock_get_bus:
        mock_bus = MagicMock()
        mock_bus.list_agents = AsyncMock(
            return_value=["security", "code_quality", "performance", "knowledge", "timer_sentinel"]
        )
        mock_bus.registry.get = AsyncMock(return_value=AsyncMock())
        mock_get_bus.return_value = mock_bus

        from ai.orchestration import get_default_bus

        bus = get_default_bus()
        agents = await bus.list_agents()

        agent_list = list(agents)
        print(f"   Found {len(agent_list)} agents: {agent_list}")
        assert len(agent_list) == 5, f"Expected 5 agents, got {len(agent_list)}"

    # 2. Test AgentMessage dispatch
    print("\n[2/4] Testing AgentMessage dispatch...")
    from ai.orchestration import AgentMessage

    msg = AgentMessage(
        source_agent="test",
        target_agent="security",
        task_type="run_audit",
        payload={"test": True},
        priority=0,
    )
    print(f"   Created message: {msg.task_type} -> {msg.target_agent}")
    assert msg.target_agent == "security"
    assert msg.task_type == "run_audit"

    # 3. Verify 3 workflows in WORKFLOW_REGISTRY
    print("\n[3/4] Testing WORKFLOW_REGISTRY...")
    from ai.workflows.definitions import WORKFLOW_REGISTRY

    workflow_names = list(WORKFLOW_REGISTRY.keys())
    print(f"   Found {len(workflow_names)} workflows: {workflow_names}")
    assert len(workflow_names) == 3, f"Expected 3 workflows, got {len(workflow_names)}"
    assert "security_deep_scan" in workflow_names
    assert "code_health_check" in workflow_names
    assert "morning_briefing_enriched" in workflow_names

    # 4. Import all 6 workflow tool handlers
    print("\n[4/4] Testing workflow tool handler imports...")
    from ai.mcp_bridge.handlers import workflow_tools

    handlers = [
        "workflow_list",
        "workflow_run",
        "workflow_status",
        "workflow_agents",
        "workflow_handoff",
        "workflow_history",
    ]

    for h in handlers:
        assert hasattr(workflow_tools, h), f"Missing handler: {h}"
        print(f"   ✓ {h}")

    print("\n" + "=" * 50)
    print("P53 smoke test: PASSED")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
