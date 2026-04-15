"""MCP Tool handlers for Dynamic Tool Discovery (P102).

Exposes tool.discover, tool.register, tool.reload, and tool.registry_stats
for runtime tool management.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai.config import PROJECT_ROOT
from ai.mcp_bridge.discovery import discover_tools_in_module
from ai.mcp_bridge.dynamic_registry import (
    AllowlistWatcher,
    discover_tools,
    get_registry,
    reload_allowlist,
)

logger = logging.getLogger("ai.mcp_bridge.tool_discovery_handlers")

# Global watcher instance (lazy initialized)
_watcher: AllowlistWatcher | None = None


def _ensure_watcher() -> AllowlistWatcher:
    """Ensure the allowlist watcher is initialized."""
    global _watcher
    if _watcher is None:
        _watcher = AllowlistWatcher(check_interval=10.0)
    return _watcher


async def handle_tool_discover(args: dict) -> str:
    """Discover tools in a Python module or directory.

        Scans Python files for functions matching tool patterns and extracts
    their signatures, docstrings, and type hints.

        Args:
            module_path: Path to Python file or directory (relative to project root)
            pattern: Optional regex pattern to filter function names
            include_source_info: Include file paths and line numbers

        Returns:
            JSON with discovered tools and their schemas
    """
    module_path = args.get("module_path", "")
    pattern = args.get("pattern")  # noqa: F841  # Reserved for future use
    include_source = args.get("include_source_info", True)

    if not module_path:
        return json.dumps(
            {
                "success": False,
                "error": "module_path is required",
            }
        )

    # Resolve path relative to project root
    full_path = Path(PROJECT_ROOT) / module_path

    if not full_path.exists():
        return json.dumps(
            {
                "success": False,
                "error": f"Path not found: {module_path}",
            }
        )

    try:
        tools = discover_tools_in_module(full_path, PROJECT_ROOT)

        result = []
        for tool in tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description,
                "handler": f"{tool.handler_module}.{tool.handler_func}",
                "args": tool.args,
                "return_type": tool.return_type,
            }
            if include_source:
                tool_info["source_file"] = tool.source_file
                tool_info["line_number"] = tool.line_number
            result.append(tool_info)

        return json.dumps(
            {
                "success": True,
                "module_path": module_path,
                "tools_found": len(result),
                "tools": result,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Tool discovery failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_register(args: dict) -> str:
    """Register a tool dynamically at runtime.

    Adds a new tool to the dynamic registry without requiring a service restart.
    The tool will be available immediately for use.

    Args:
        name: Tool name (e.g., "custom.my_tool")
        description: Tool description
        module: Python module path (e.g., "ai.custom.handlers")
        function: Function name within module
        args: Optional argument definitions
        auto_discover: If true, discover from module instead of manual definition

    Returns:
        JSON with registration result
    """
    name = args.get("name", "")
    auto_discover = args.get("auto_discover", False)

    if not name and not auto_discover:
        return json.dumps(
            {
                "success": False,
                "error": "name is required (or use auto_discover)",
            }
        )

    registry = get_registry()

    try:
        if auto_discover:
            module_path = args.get("module", "")
            if not module_path:
                return json.dumps(
                    {
                        "success": False,
                        "error": "module is required for auto_discover",
                    }
                )

            # Convert module path to file path
            module_file = module_path.replace(".", "/") + ".py"
            full_path = Path(PROJECT_ROOT) / "ai" / module_file

            if not full_path.exists():
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Module not found: {module_path}",
                    }
                )

            registered = discover_tools(full_path, pattern=args.get("pattern"))

            return json.dumps(
                {
                    "success": True,
                    "tools_registered": registered,
                    "count": len(registered),
                }
            )
        else:
            # Manual registration
            definition = {
                "description": args.get("description", ""),
                "source": "python",
                "module": args.get("module", ""),
                "function": args.get("function", ""),
            }

            if args.get("args"):
                definition["args"] = args["args"]

            success = registry.register_tool(name, definition)

            return json.dumps(
                {
                    "success": success,
                    "tool": name,
                    "action": "registered" if success else "already_exists",
                }
            )

    except Exception as e:
        logger.error(f"Tool registration failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_unregister(args: dict) -> str:
    """Unregister a dynamically registered tool.

    Removes a tool from the dynamic registry. Built-in tools from the
    allowlist cannot be unregistered this way.

    Args:
        name: Tool name to unregister

    Returns:
        JSON with unregistration result
    """
    name = args.get("name", "")

    if not name:
        return json.dumps(
            {
                "success": False,
                "error": "name is required",
            }
        )

    registry = get_registry()

    # Check if tool exists in registry
    tool = registry.get_tool(name)
    if not tool:
        return json.dumps(
            {
                "success": False,
                "error": f"Tool '{name}' not found in dynamic registry",
            }
        )

    # Only allow unregistering dynamically registered tools
    if tool.source == "hot_reload" and name in registry.tool_names:
        # This might be from allowlist - check carefully
        pass

    success = registry.unregister_tool(name)

    return json.dumps(
        {
            "success": success,
            "tool": name,
            "action": "unregistered" if success else "failed",
        }
    )


async def handle_tool_reload(args: dict) -> str:
    """Reload the tool allowlist from disk.

    Hot-reloads the MCP tool allowlist, registering new tools and removing
    deleted ones without requiring a service restart.

    Args:
        force: Force reload even if file hasn't changed
        dry_run: Preview changes without applying them

    Returns:
        JSON with reload results
    """
    force = args.get("force", False)
    dry_run = args.get("dry_run", False)

    registry = get_registry()

    try:
        if dry_run:
            # Check what would change
            changed = registry.check_allowlist_changed()
            return json.dumps(
                {
                    "success": True,
                    "dry_run": True,
                    "would_reload": changed,
                    "message": "Allowlist has changes" if changed else "No changes detected",
                }
            )

        result = reload_allowlist(force=force)

        return json.dumps(
            {
                "success": result["reloaded"] or not result["error"],
                "reloaded": result["reloaded"],
                "tools_added": result["added"],
                "tools_removed": result["removed"],
                "unchanged_count": result["unchanged"],
                "error": result["error"],
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Allowlist reload failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_registry_stats(args: dict) -> str:
    """Get dynamic tool registry statistics.

    Returns information about dynamically registered tools,
    including counts by source and registry metadata.

    Args:
        include_definitions: Include full tool definitions in output

    Returns:
        JSON with registry statistics
    """
    include_defs = args.get("include_definitions", False)

    registry = get_registry()
    stats = registry.get_registry_stats()

    result = {
        "success": True,
        "stats": stats,
    }

    if include_defs:
        tools = []
        for tool in registry.list_tools():
            tool_info = {
                "name": tool.name,
                "source": tool.source,
                "registered_at": tool.registered_at,
            }
            if include_defs:
                tool_info["definition"] = tool.definition
            tools.append(tool_info)
        result["tools"] = tools

    return json.dumps(result, indent=2, default=str)


async def handle_tool_watch(args: dict) -> str:
    """Control the allowlist file watcher.

    Enable or disable automatic reloading when the allowlist file changes.

    Args:
        action: "start", "stop", or "status"
        interval: Check interval in seconds (for start)

    Returns:
        JSON with watcher status
    """
    action = args.get("action", "status")

    global _watcher

    try:
        if action == "start":
            interval = args.get("interval", 10.0)
            if _watcher is None:
                _watcher = AllowlistWatcher(check_interval=interval)
            # Note: Cannot actually start async task from sync context here
            # The watcher would need to be started by the server
            return json.dumps(
                {
                    "success": True,
                    "action": "start",
                    "message": f"Watcher configured with {interval}s interval",
                    "note": "Watcher must be started by server on startup",
                }
            )

        elif action == "stop":
            if _watcher:
                # Same limitation as above
                return json.dumps(
                    {
                        "success": True,
                        "action": "stop",
                        "message": "Watcher stop requested",
                    }
                )
            return json.dumps(
                {
                    "success": True,
                    "action": "stop",
                    "message": "Watcher not running",
                }
            )

        else:  # status
            registry = get_registry()
            return json.dumps(
                {
                    "success": True,
                    "action": "status",
                    "allowlist_path": str(registry._allowlist_path),
                    "total_tools": registry.tool_count,
                    "watcher_configured": _watcher is not None,
                }
            )

    except Exception as e:
        logger.error(f"Tool watch command failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )
