"""Dynamic Tool Registry for MCP Bridge.

P102: Dynamic Tool Discovery - Runtime tool registration without restarts.

This module provides hot-reload capabilities for the MCP tool allowlist,
enabling dynamic tool registration and discovery at runtime.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml

from ai.config import CONFIGS_DIR
from ai.mcp_bridge.discovery import ToolDiscoveryEngine

logger = logging.getLogger("ai.mcp_bridge.dynamic_registry")


@dataclass
class RegisteredTool:
    """A dynamically registered tool.

    Attributes:
        name: Tool name
        definition: Tool definition dict
        handler: Optional callable handler
        registered_at: Registration timestamp
        source: Source of registration (manual, discovery, hot_reload)
    """

    name: str
    definition: dict[str, Any]
    handler: Callable[..., Any] | None = None
    registered_at: float = field(default_factory=time.time)
    source: str = "manual"  # manual, discovery, hot_reload


class DynamicToolRegistry:
    """Registry for dynamically managed MCP tools.

    Features:
    - Runtime tool registration without service restart
    - Hot-reload of allowlist YAML
    - Integration with tool discovery engine
    - Thread-safe operations

    This is a singleton class - use get_instance() to obtain the global registry.
    """

    _instance: ClassVar[DynamicToolRegistry | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __new__(cls) -> DynamicToolRegistry:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> DynamicToolRegistry:
        """Get or create the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry (only runs once due to singleton pattern)."""
        if self._initialized:
            return

        self._initialized = True
        self._tools: dict[str, RegisteredTool] = {}
        self._allowlist_path: Path = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"
        self._last_allowlist_mtime: float = 0
        self._last_allowlist_hash: str = ""
        self._discovery_engine = ToolDiscoveryEngine()
        self._reload_callbacks: list[Callable[[list[str]], None]] = []

    @property
    def tool_count(self) -> int:
        """Return number of dynamically registered tools."""
        return len(self._tools)

    @property
    def tool_names(self) -> list[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())

    def register_tool(
        self,
        name: str,
        definition: dict[str, Any],
        handler: Callable[..., Any] | None = None,
        source: str = "manual",
    ) -> bool:
        """Register a tool dynamically.

        Args:
            name: Tool name
            definition: Tool definition dict (allowlist format)
            handler: Optional callable handler
            source: Registration source

        Returns:
            True if registered, False if already exists
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, skipping")
            return False

        self._tools[name] = RegisteredTool(
            name=name,
            definition=definition,
            handler=handler,
            source=source,
        )

        logger.info(f"Registered tool '{name}' (source: {source})")
        return True

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if unregistered, False if not found
        """
        if name not in self._tools:
            return False

        del self._tools[name]
        logger.info(f"Unregistered tool '{name}'")
        return True

    def get_tool(self, name: str) -> RegisteredTool | None:
        """Get a registered tool by name.

        Args:
            name: Tool name

        Returns:
            RegisteredTool or None if not found
        """
        return self._tools.get(name)

    def get_tool_definition(self, name: str) -> dict[str, Any] | None:
        """Get tool definition by name.

        Args:
            name: Tool name

        Returns:
            Tool definition dict or None
        """
        tool = self._tools.get(name)
        return tool.definition if tool else None

    def list_tools(self) -> list[RegisteredTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def discover_and_register(
        self,
        module_path: str | Path,
        pattern: str | None = None,
    ) -> list[str]:
        """Discover tools in a module and register them.

        Args:
            module_path: Path to Python module or directory
            pattern: Optional regex pattern for function names

        Returns:
            List of registered tool names
        """
        discovered = self._discovery_engine.discover_module(module_path, pattern)

        registered = []
        for tool in discovered:
            definition = tool.to_allowlist_entry()
            # definition is a dict with tool name as key
            for tool_name, tool_def in definition.items():
                if self.register_tool(
                    name=tool_name,
                    definition=tool_def,
                    source="discovery",
                ):
                    registered.append(tool_name)

        logger.info(f"Discovered and registered {len(registered)} tools from {module_path}")
        return registered

    def check_allowlist_changed(self) -> bool:
        """Check if allowlist file has changed on disk.

        Returns:
            True if file has been modified since last load
        """
        if not self._allowlist_path.exists():
            return False

        try:
            mtime = self._allowlist_path.stat().st_mtime
            return mtime > self._last_allowlist_mtime
        except OSError:
            return False

    def reload_allowlist(self, force: bool = False) -> dict[str, Any]:
        """Reload allowlist from disk and register new tools.

        Args:
            force: Force reload even if file hasn't changed

        Returns:
            Reload result with statistics
        """
        result = {
            "reloaded": False,
            "added": [],
            "removed": [],
            "unchanged": 0,
            "error": None,
        }

        if not force and not self.check_allowlist_changed():
            result["unchanged"] = len(self._tools)
            return result

        try:
            with open(self._allowlist_path) as f:
                data = yaml.safe_load(f)

            if not data or "tools" not in data:
                result["error"] = "Invalid allowlist format"
                return result

            tools_data = data["tools"]
            current_names = set(self._tools.keys())
            new_names = set(tools_data.keys())

            # Find added tools
            added = new_names - current_names
            for name in added:
                self.register_tool(
                    name=name,
                    definition=tools_data[name],
                    source="hot_reload",
                )
                result["added"].append(name)

            # Find removed tools
            removed = current_names - new_names
            for name in removed:
                if self.unregister_tool(name):
                    result["removed"].append(name)

            # Update unchanged count
            result["unchanged"] = len(current_names & new_names)

            # Update metadata
            self._last_allowlist_mtime = self._allowlist_path.stat().st_mtime
            result["reloaded"] = True

            # Notify callbacks
            if added or removed:
                for callback in self._reload_callbacks:
                    try:
                        callback(result["added"] + result["removed"])
                    except Exception as e:
                        logger.warning(f"Reload callback failed: {e}")

            logger.info(f"Allowlist reloaded: +{len(added)} tools, -{len(removed)} tools")

        except yaml.YAMLError as e:
            result["error"] = f"YAML parse error: {e}"
            logger.error(f"Failed to reload allowlist: {e}")
        except OSError as e:
            result["error"] = f"File error: {e}"
            logger.error(f"Failed to read allowlist: {e}")

        return result

    def add_reload_callback(self, callback: Callable[[list[str]], None]) -> None:
        """Add a callback to be invoked when allowlist is reloaded.

        Args:
            callback: Function receiving list of changed tool names
        """
        self._reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable[[list[str]], None]) -> None:
        """Remove a reload callback."""
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    def export_to_allowlist(self, output_path: str | Path | None = None) -> Path:
        """Export dynamically registered tools to allowlist YAML.

        Args:
            output_path: Optional output path (defaults to allowlist path)

        Returns:
            Path to written file
        """
        output = Path(output_path) if output_path else self._allowlist_path

        # Build tools dict
        tools = {}
        for tool in self._tools.values():
            tools[tool.name] = tool.definition

        data = {"tools": tools}

        # Write with atomic rename
        temp_path = output.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=True)
        temp_path.replace(output)

        logger.info(f"Exported {len(tools)} tools to {output}")
        return output

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        sources = {}
        for tool in self._tools.values():
            sources[tool.source] = sources.get(tool.source, 0) + 1

        return {
            "total_tools": len(self._tools),
            "by_source": sources,
            "allowlist_path": str(self._allowlist_path),
            "last_reload": self._last_allowlist_mtime,
        }

    def clear(self) -> int:
        """Clear all dynamically registered tools.

        Returns:
            Number of tools cleared
        """
        count = len(self._tools)
        self._tools.clear()
        logger.info(f"Cleared {count} tools from registry")
        return count


# Convenience functions for module-level access


def get_registry() -> DynamicToolRegistry:
    """Get the global registry instance."""
    return DynamicToolRegistry.get_instance()


def register_tool(
    name: str,
    definition: dict[str, Any],
    handler: Callable[..., Any] | None = None,
) -> bool:
    """Register a tool in the global registry."""
    return get_registry().register_tool(name, definition, handler)


def unregister_tool(name: str) -> bool:
    """Unregister a tool from the global registry."""
    return get_registry().unregister_tool(name)


def get_tool(name: str) -> RegisteredTool | None:
    """Get a tool from the global registry."""
    return get_registry().get_tool(name)


def discover_tools(module_path: str | Path, pattern: str | None = None) -> list[str]:
    """Discover and register tools from a module."""
    return get_registry().discover_and_register(module_path, pattern)


def reload_allowlist(force: bool = False) -> dict[str, Any]:
    """Reload the allowlist from disk."""
    return get_registry().reload_allowlist(force)


class AllowlistWatcher:
    """Background watcher for allowlist file changes.

    Can be used to automatically reload tools when the allowlist changes.
    """

    def __init__(self, check_interval: float = 5.0):
        """Initialize watcher.

        Args:
            check_interval: Seconds between checks
        """
        self.check_interval = check_interval
        self._registry = get_registry()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background watcher."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"Allowlist watcher started (interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop the background watcher."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Allowlist watcher stopped")

    async def _watch_loop(self) -> None:
        """Main watch loop."""
        while self._running:
            try:
                if self._registry.check_allowlist_changed():
                    result = self._registry.reload_allowlist()
                    if result["added"] or result["removed"]:
                        logger.info(
                            f"Auto-reload: +{len(result['added'])} tools, "
                            f"-{len(result['removed'])} tools"
                        )
            except Exception as e:
                logger.error(f"Error in allowlist watch loop: {e}")

            await asyncio.sleep(self.check_interval)
