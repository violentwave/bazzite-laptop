#!/usr/bin/env python3
"""Smoke test for P42-wired tools.

Verifies dispatch wiring — that each of the 30 tools wired in P42 is reachable
through execute_tool() and does not return an 'unknown tool' error.

Business logic failures (missing modules, empty DB, etc.) are noted but do NOT
fail the test — only dispatch failures count.

Run:
    source .venv/bin/activate
    python scripts/smoke-test-tools.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on the path when run as a script
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Tools wired in P42 with minimal valid arguments.
# Ordered to match the _execute_python_tool dispatch.
NEW_TOOLS: list[tuple[str, dict]] = [
    # Intel pipeline
    ("intel.scrape_now", {}),
    ("intel.ingest_pending", {}),
    # System modules
    ("system.dep_scan", {}),
    ("system.test_analysis", {}),
    ("system.perf_profile", {}),
    ("system.mcp_audit", {}),
    ("system.alert_history", {"limit": 5}),
    ("system.alert_rules", {}),
    ("system.dep_audit", {}),
    ("system.dep_audit_history", {"limit": 5}),
    ("system.budget_status", {}),
    ("system.metrics_summary", {}),
    ("system.provider_status", {}),
    ("system.weekly_insights", {"limit": 2}),
    (
        "system.create_tool",
        {
            "name": "_smoke_test_probe",
            "description": "smoke test probe",
            "handler_code": "def _smoke_test_probe(**kwargs):\n    return {'ok': True}\n",
            "parameters": [],
            "created_by": "smoke-test",
        },
    ),
    ("system.list_dynamic_tools", {}),
    # Knowledge / learning
    ("knowledge.task_patterns", {"query": "smoke test"}),
    ("knowledge.session_history", {"limit": 3}),
    # Memory
    ("memory.search", {"query": "smoke test", "top_k": 3}),
    # Collaboration
    ("collab.queue_status", {}),
    ("collab.add_task", {"title": "smoke-test-sentinel", "description": "auto by smoke test"}),
    ("collab.search_knowledge", {"query": "smoke test"}),
    # Workflows
    ("workflow.list", {}),
    ("workflow.run", {"workflow_id": "nonexistent-smoke-test"}),
    # Code intelligence
    ("code.impact_analysis", {"changed_files": "ai/config.py"}),
    ("code.dependency_graph", {"module": "ai.config", "max_depth": 1}),
    ("code.fused_context", {"question": "How does route_query relate to impact analysis?"}),
    ("code.blast_radius", {"changed_files": "ai/config.py", "max_depth": 2}),
    ("code.find_callers", {"function_name": "route_query"}),
    ("code.suggest_tests", {"changed_files": "ai/config.py"}),
    ("code.complexity_report", {"target": "ai/", "threshold": 10}),
    ("code.class_hierarchy", {"class_name": "Router"}),
]

_DISPATCH_FAILURES = {
    "unknown_tool",
    "AttributeError",
    "KeyError: 'tool_name'",
    "not found in dispatch",
}


def _is_dispatch_failure(raw: str | dict) -> bool:
    """Return True if the response signals a wiring/dispatch bug."""
    text = raw if isinstance(raw, str) else json.dumps(raw)
    lower = text.lower()
    # "unknown tool" means the elif chain fell through without matching
    if "unknown tool" in lower:
        return True
    # A bare unhandled exception traceback is a dispatch bug
    if "traceback (most recent call last)" in lower and "unknown" in lower:
        return True
    return False


async def smoke_test() -> int:
    """Run all smoke tests. Returns exit code (0 = all dispatch ok)."""
    from ai.mcp_bridge.tools import execute_tool  # noqa: PLC0415

    passed = 0
    dispatch_failed = 0
    logic_errors: list[str] = []
    dispatch_errors: list[str] = []

    print(f"Smoke-testing {len(NEW_TOOLS)} P42-wired tools...")
    print()

    for tool_name, args in NEW_TOOLS:
        try:
            raw = await execute_tool(tool_name, args)
            if _is_dispatch_failure(raw):
                dispatch_errors.append(f"  DISPATCH FAIL: {tool_name} → {str(raw)[:120]}")
                dispatch_failed += 1
            else:
                print(f"  OK: {tool_name}")
                passed += 1
        except Exception as exc:
            exc_type = type(exc).__name__
            exc_msg = str(exc)[:100]
            # An exception from inside the handler is a logic error, not a dispatch error,
            # UNLESS the exception says the tool name was unknown.
            if "unknown" in exc_msg.lower() or "not found" in exc_msg.lower():
                dispatch_errors.append(f"  DISPATCH FAIL: {tool_name} → {exc_type}: {exc_msg}")
                dispatch_failed += 1
            else:
                logic_errors.append(f"  LOGIC ERR: {tool_name} → {exc_type}: {exc_msg}")
                print(f"  LOGIC ERR: {tool_name} → {exc_type}: {exc_msg}")
                # Logic errors mean the tool IS wired but the implementation hit an issue.
                # Count as passed from a wiring perspective.
                passed += 1

    print()
    print("=" * 60)
    print(f"Dispatch OK   : {passed}/{len(NEW_TOOLS)}")
    print(f"Dispatch FAIL : {dispatch_failed}/{len(NEW_TOOLS)}")
    print(f"Logic errors  : {len(logic_errors)} (wired but implementation issue)")
    print()

    if dispatch_errors:
        print("DISPATCH FAILURES (wiring bugs — must fix):")
        for err in dispatch_errors:
            print(err)
        print()

    if logic_errors:
        print("LOGIC ERRORS (wired ok, but runtime issue — may need data/config):")
        for err in logic_errors:
            print(err)
        print()

    if dispatch_failed == 0:
        print("All 30 tools are correctly wired into the dispatch chain.")
    else:
        print(f"{dispatch_failed} tool(s) have wiring bugs that must be fixed.")

    return 1 if dispatch_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(smoke_test()))
