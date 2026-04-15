"""Verify MCP allowlist YAML and tools.py implementation stay in sync."""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
ALLOWLIST_PATH = REPO_ROOT / "configs" / "mcp-bridge-allowlist.yaml"
TOOLS_PY = REPO_ROOT / "ai" / "mcp_bridge" / "tools.py"
SERVER_PY = REPO_ROOT / "ai" / "mcp_bridge" / "server.py"
SYSTEM_PROMPT = REPO_ROOT / "docs" / "newelle-system-prompt.md"


def _load_allowlist() -> dict:
    return yaml.safe_load(ALLOWLIST_PATH.read_text())["tools"]


def _python_tools(allowlist: dict) -> list[str]:
    """Tool names where source == python (require explicit elif branches)."""
    return [name for name, defn in allowlist.items() if defn.get("source") == "python"]


class TestAllowlistVsCode:
    def test_all_python_tools_have_handler(self):
        """Every source:python tool must have a handler in tools.py or server.py."""
        allowlist = _load_allowlist()
        tools_source = TOOLS_PY.read_text()
        server_source = SERVER_PY.read_text()
        combined = tools_source + server_source
        missing = [
            name
            for name in _python_tools(allowlist)
            if "tool_name == " + f'"{name}"' not in combined and "execute_tool(_tn" not in combined
        ]
        assert not missing, f"No handler found in tools.py or server.py for: {missing}"

    def test_all_handlers_in_yaml(self):
        """Every tool_name == branch in tools.py must be listed in the allowlist."""
        allowlist = _load_allowlist()
        source = TOOLS_PY.read_text()
        handled = re.findall(r'tool_name == "([^"]+)"', source)
        unknown = [name for name in handled if name not in allowlist]
        assert not unknown, f"tools.py has handler for tools not in allowlist: {unknown}"

    def test_tool_count_matches_server(self):
        """_TOOL_COUNT in server.py must equal the number of tools in the allowlist."""
        allowlist = _load_allowlist()
        source = SERVER_PY.read_text()
        assert "_count_tools()" in source, "_count_tools() function not found in server.py"
        from ai.mcp_bridge import server

        declared = server._TOOL_COUNT
        actual = len(allowlist)
        assert declared == actual, (
            f"server.py _TOOL_COUNT={declared} but allowlist has {actual} tools"
        )

    def test_system_prompt_has_all_tools(self):
        """Every tool in the allowlist must appear in the Newelle system prompt."""
        allowlist = _load_allowlist()
        prompt_text = SYSTEM_PROMPT.read_text()
        known_missing = {
            "intel.scrape_now",
            "system.dep_scan",
            "system.test_analysis",
            "system.perf_profile",
            "system.mcp_audit",
            "intel.ingest_pending",
            "workflow.history_steps",
            "workflow.cancel",
            "figma.list_teams",
            "figma.list_projects",
            "figma.list_project_files",
            "figma.get_file",
            "figma.find_project",
            "figma.reconcile",
        }
        missing = [
            name for name in allowlist if name not in prompt_text and name not in known_missing
        ]
        assert not missing, f"Tools missing from Newelle system prompt: {missing}"
