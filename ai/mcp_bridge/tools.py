"""MCP Bridge tool implementations.

All tools are read-only. Subprocess commands are static lists (no shell=True,
no user argument interpolation). Output is truncated to 4KB max.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

import yaml

from ai.config import CONFIGS_DIR, STATUS_FILE

logger = logging.getLogger("ai.mcp_bridge")

_MAX_OUTPUT_BYTES = 4096
_SUBPROCESS_TIMEOUT_S = 30

# Concurrency limit for subprocess tool calls
_subprocess_semaphore = asyncio.Semaphore(4)

# Path redaction pattern
_HOME_PATTERN = re.compile(r"/home/lch")

# Allowlist loaded once at module import
_ALLOWLIST_PATH = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"
_allowlist: dict | None = None


def _load_allowlist() -> dict:
    """Load the tool allowlist from YAML."""
    global _allowlist  # noqa: PLW0603
    if _allowlist is not None:
        return _allowlist
    with open(_ALLOWLIST_PATH) as f:
        data = yaml.safe_load(f) or {}
    _allowlist = data.get("tools", {})
    return _allowlist


def _truncate(text: str) -> str:
    """Truncate output to 4KB max, appending truncation marker if cut."""
    if len(text) <= _MAX_OUTPUT_BYTES:
        return text
    return text[:_MAX_OUTPUT_BYTES] + "...[truncated]"


def _redact_paths(text: str) -> str:
    """Replace /home/lch with [HOME] to prevent path leakage."""
    return _HOME_PATTERN.sub("[HOME]", text)


def _read_file_tail(path: str, lines: int) -> str:
    """Read last N lines from a file."""
    p = Path(path)
    all_lines = p.read_text().splitlines()
    return "\n".join(all_lines[-lines:])


def _read_status_file() -> dict:
    """Read and parse the status JSON file."""
    return json.loads(STATUS_FILE.read_text())


# Status key whitelist
_STATUS_ALLOWED_KEYS = {"state", "scan_type", "last_scan_time", "result", "health_status", "health_issues"}


async def _run_subprocess(command: list[str]) -> str:
    """Run a subprocess with timeout and concurrency limiting."""
    async with _subprocess_semaphore:
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=_SUBPROCESS_TIMEOUT_S,
            )
            return _truncate(stdout.decode("utf-8", errors="replace"))
        except FileNotFoundError:
            return "[Command not found]"
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return "[Tool timed out]"


async def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool by name with validated arguments.

    Args:
        tool_name: The tool identifier (e.g. "system.disk_usage").
        args: Validated arguments dict.

    Returns:
        Tool output as a string.

    Raises:
        ValueError: If tool_name is not in the allowlist.
    """
    allowlist = _load_allowlist()
    if tool_name not in allowlist:
        raise ValueError(f"Unknown tool: '{tool_name}'")

    tool_def = allowlist[tool_name]

    # Subprocess-based tools
    if "command" in tool_def:
        return await _run_subprocess(tool_def["command"])

    # File tail tools
    if tool_def.get("source") == "file_tail":
        try:
            text = _read_file_tail(tool_def["path"], tool_def.get("lines", 20))
            return _truncate(_redact_paths(text))
        except FileNotFoundError:
            return "No data yet -- run a snapshot first"

    # Status file tool
    if tool_def.get("source") == "json_file":
        try:
            data = _read_status_file()
            filtered = {k: v for k, v in data.items() if k in _STATUS_ALLOWED_KEYS}
            return json.dumps(filtered, indent=2)
        except FileNotFoundError:
            return "No data yet -- run a scan first"

    # Python module tools (threat_lookup, rag_query, gaming)
    if tool_def.get("source") == "python":
        return await _execute_python_tool(tool_name, tool_def, args)

    return f"[Tool '{tool_name}' has unsupported source type]"


async def _execute_python_tool(tool_name: str, tool_def: dict, args: dict) -> str:
    """Execute a Python-module-backed tool."""
    module_name = tool_def["module"]
    function_name = tool_def.get("function")

    try:
        if tool_name == "security.threat_lookup":
            from ai.threat_intel.lookup import lookup_hash  # noqa: PLC0415

            result = lookup_hash(args["hash"])
            # Sanitize: strip raw_data, return only safe fields
            safe_fields = {"hash", "source", "family", "risk_level", "detection_ratio", "description", "tags"}
            if isinstance(result, dict):
                filtered = {k: v for k, v in result.items() if k in safe_fields}
                return json.dumps(filtered, indent=2)
            return _truncate(str(result))

        elif tool_name == "knowledge.rag_query":
            from ai.rag.query import query as rag_query  # noqa: PLC0415

            result = rag_query(args["question"], use_llm=False)
            # Sanitize: return only answer, strip context_chunks and sources
            if isinstance(result, dict):
                return result.get("answer", str(result))
            return _truncate(str(result))

        elif tool_name == "gaming.profiles":
            from ai.gaming.scopebuddy import list_profiles  # noqa: PLC0415

            return json.dumps(list_profiles(), indent=2)

        elif tool_name == "gaming.mangohud_preset":
            from ai.gaming.scopebuddy import get_preset  # noqa: PLC0415

            return json.dumps(get_preset(args["game"]), indent=2)

        else:
            return f"[Tool '{tool_name}' not implemented]"

    except ImportError as e:
        return f"[Module not available: {e}]"
    except Exception as e:
        logger.error("Tool '%s' failed: %s", tool_name, e)
        return f"[Tool error: {e}]"
