"""Tests for P102: Dynamic Tool Discovery.

Tests the tool discovery engine, dynamic registry, and MCP handlers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.mcp_bridge.discovery import (
    DiscoveredTool,
    ToolDiscoveryEngine,
    generate_tool_schema_from_function,
)
from ai.mcp_bridge.dynamic_registry import (
    DynamicToolRegistry,
    RegisteredTool,
    get_registry,
)
from ai.mcp_bridge.tool_discovery_handlers import (
    handle_tool_discover,
    handle_tool_register,
    handle_tool_registry_stats,
    handle_tool_reload,
    handle_tool_unregister,
    handle_tool_watch,
)

# =============================================================================
# Tool Discovery Engine Tests
# =============================================================================


class TestToolDiscoveryEngine:
    """Tests for the ToolDiscoveryEngine class."""

    def test_init_default_project_root(self):
        """Test engine initializes with default project root."""
        engine = ToolDiscoveryEngine()
        assert engine.project_root == Path.cwd()

    def test_init_with_project_root(self):
        """Test engine initializes with custom project root."""
        root = "/tmp/test"
        engine = ToolDiscoveryEngine(root)
        assert engine.project_root == Path(root)

    def test_discover_from_ast_simple_function(self):
        """Test discovering tools from simple function AST."""
        source = '''
def handle_test_func(arg1: str, arg2: int = 10) -> str:
    """Test function description."""
    return "test"
'''
        engine = ToolDiscoveryEngine()
        tools = engine.discover_from_ast(source, "test_module", "test.py")

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "test_module.handle_test_func"
        assert tool.description == "Test function description."
        assert tool.handler_module == "test_module"
        assert tool.handler_func == "handle_test_func"
        assert tool.return_type == "str"

    def test_discover_from_ast_with_decorator(self):
        """Test discovering tools with @mcp.tool() decorator."""
        source = '''
@mcp.tool()
def my_tool():
    """A tool with decorator."""
    pass
'''
        engine = ToolDiscoveryEngine()
        tools = engine.discover_from_ast(source, "test_module", "test.py")

        assert len(tools) == 1
        assert tools[0].handler_func == "my_tool"

    def test_discover_from_ast_no_tools(self):
        """Test discovering from source with no tool functions."""
        source = '''
def regular_function():
    """Not a tool."""
    pass
'''
        engine = ToolDiscoveryEngine()
        tools = engine.discover_from_ast(source, "test_module", "test.py")

        assert len(tools) == 0

    def test_extract_args_from_ast(self):
        """Test argument extraction from AST."""
        source = '''
def handle_test(required: str, optional: int = 5) -> bool:
    """Test."""
    pass
'''
        engine = ToolDiscoveryEngine()
        tools = engine.discover_from_ast(source, "test", "test.py")

        assert len(tools) == 1
        args = tools[0].args

        assert len(args) == 2
        assert args[0]["name"] == "required"
        assert args[0]["required"] is True
        assert args[1]["name"] == "optional"
        assert args[1]["required"] is False

    def test_map_python_type_to_json_schema(self):
        """Test Python to JSON schema type mapping."""
        engine = ToolDiscoveryEngine()

        assert engine._map_python_type_to_json_schema("str") == "string"
        assert engine._map_python_type_to_json_schema("int") == "integer"
        assert engine._map_python_type_to_json_schema("float") == "number"
        assert engine._map_python_type_to_json_schema("bool") == "boolean"
        assert engine._map_python_type_to_json_schema("list") == "array"
        assert engine._map_python_type_to_json_schema("dict") == "object"
        assert engine._map_python_type_to_json_schema("Unknown") == "string"

    def test_to_allowlist_entry(self):
        """Test conversion to allowlist entry format."""
        tool = DiscoveredTool(
            name="test.tool",
            description="Test tool",
            handler_module="ai.test",
            handler_func="handle_test",
            args=[
                {"name": "arg1", "type": "string", "required": True},
                {"name": "arg2", "type": "integer", "required": False, "default": 10},
            ],
            return_type="str",
        )

        entry = tool.to_allowlist_entry()

        assert "test.tool" in entry
        assert entry["test.tool"]["description"] == "Test tool"
        assert entry["test.tool"]["module"] == "ai.test"
        assert entry["test.tool"]["function"] == "handle_test"


class TestDiscoveredTool:
    """Tests for DiscoveredTool dataclass."""

    def test_default_values(self):
        """Test default values for optional fields."""
        tool = DiscoveredTool(
            name="test.tool",
            description="Test",
            handler_module="ai.test",
            handler_func="handle_test",
        )

        assert tool.args == []
        assert tool.return_type == "Any"
        assert tool.source_file == ""
        assert tool.line_number == 0


# =============================================================================
# Dynamic Registry Tests
# =============================================================================


class TestDynamicToolRegistry:
    """Tests for DynamicToolRegistry class."""

    def setup_method(self):
        """Set up fresh registry for each test."""
        # Reset singleton
        DynamicToolRegistry._instance = None
        self.registry = DynamicToolRegistry()
        self.registry.clear()

    def test_singleton_instance(self):
        """Test that registry is a singleton."""
        reg1 = DynamicToolRegistry.get_instance()
        reg2 = DynamicToolRegistry.get_instance()
        assert reg1 is reg2

    def test_register_tool_success(self):
        """Test successful tool registration."""
        definition = {"description": "Test tool", "source": "python"}
        result = self.registry.register_tool("test.tool", definition)

        assert result is True
        assert self.registry.tool_count == 1
        assert "test.tool" in self.registry.tool_names

    def test_register_tool_duplicate(self):
        """Test registration of duplicate tool."""
        definition = {"description": "Test tool"}
        self.registry.register_tool("test.tool", definition)
        result = self.registry.register_tool("test.tool", definition)

        assert result is False
        assert self.registry.tool_count == 1

    def test_unregister_tool_success(self):
        """Test successful tool unregistration."""
        definition = {"description": "Test tool"}
        self.registry.register_tool("test.tool", definition)

        result = self.registry.unregister_tool("test.tool")

        assert result is True
        assert self.registry.tool_count == 0

    def test_unregister_tool_not_found(self):
        """Test unregistration of non-existent tool."""
        result = self.registry.unregister_tool("nonexistent.tool")
        assert result is False

    def test_get_tool(self):
        """Test retrieving a registered tool."""
        definition = {"description": "Test tool"}
        self.registry.register_tool("test.tool", definition)

        tool = self.registry.get_tool("test.tool")

        assert tool is not None
        assert tool.name == "test.tool"
        assert tool.definition == definition

    def test_get_tool_not_found(self):
        """Test retrieving non-existent tool."""
        tool = self.registry.get_tool("nonexistent.tool")
        assert tool is None

    def test_get_tool_definition(self):
        """Test getting tool definition."""
        definition = {"description": "Test"}
        self.registry.register_tool("test.tool", definition)

        result = self.registry.get_tool_definition("test.tool")

        assert result == definition

    def test_list_tools(self):
        """Test listing all registered tools."""
        self.registry.register_tool("tool1", {"desc": "1"})
        self.registry.register_tool("tool2", {"desc": "2"})

        tools = self.registry.list_tools()

        assert len(tools) == 2

    def test_clear(self):
        """Test clearing all tools."""
        self.registry.register_tool("tool1", {})
        self.registry.register_tool("tool2", {})

        count = self.registry.clear()

        assert count == 2
        assert self.registry.tool_count == 0

    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        self.registry.register_tool("tool1", {}, source="manual")
        self.registry.register_tool("tool2", {}, source="discovery")

        stats = self.registry.get_registry_stats()

        assert stats["total_tools"] == 2
        assert stats["by_source"]["manual"] == 1
        assert stats["by_source"]["discovery"] == 1


class TestRegisteredTool:
    """Tests for RegisteredTool dataclass."""

    def test_default_source(self):
        """Test default source value."""
        tool = RegisteredTool(
            name="test",
            definition={},
        )
        assert tool.source == "manual"


# =============================================================================
# Tool Handler Tests
# =============================================================================


@pytest.mark.asyncio
class TestToolDiscoveryHandlers:
    """Tests for MCP tool discovery handlers."""

    async def test_handle_tool_discover_missing_path(self):
        """Test discover handler with missing module_path."""
        result = await handle_tool_discover({})
        data = json.loads(result)

        assert data["success"] is False
        assert "module_path is required" in data["error"]

    async def test_handle_tool_discover_invalid_path(self):
        """Test discover handler with invalid path."""
        result = await handle_tool_discover({"module_path": "/nonexistent"})
        data = json.loads(result)

        assert data["success"] is False
        assert "Path not found" in data["error"]

    async def test_handle_tool_register_auto_discover_no_module(self):
        """Test register handler with auto_discover but no module."""
        result = await handle_tool_register(
            {
                "auto_discover": True,
            }
        )
        data = json.loads(result)

        assert data["success"] is False
        assert "module is required" in data["error"]

    async def test_handle_tool_register_manual_no_name(self):
        """Test manual registration without name."""
        result = await handle_tool_register(
            {
                "auto_discover": False,
            }
        )
        data = json.loads(result)

        assert data["success"] is False
        assert "name is required" in data["error"]

    async def test_handle_tool_unregister_no_name(self):
        """Test unregister without name."""
        result = await handle_tool_unregister({})
        data = json.loads(result)

        assert data["success"] is False
        assert "name is required" in data["error"]

    async def test_handle_tool_unregister_not_found(self):
        """Test unregister non-existent tool."""
        result = await handle_tool_unregister({"name": "nonexistent.tool"})
        data = json.loads(result)

        assert data["success"] is False
        assert "not found" in data["error"]

    async def test_handle_tool_reload_dry_run(self):
        """Test reload handler in dry run mode."""
        result = await handle_tool_reload({"dry_run": True})
        data = json.loads(result)

        assert data["success"] is True
        assert data["dry_run"] is True

    async def test_handle_tool_registry_stats(self):
        """Test registry stats handler."""
        result = await handle_tool_registry_stats({})
        data = json.loads(result)

        assert data["success"] is True
        assert "stats" in data

    async def test_handle_tool_registry_stats_with_definitions(self):
        """Test registry stats with definitions included."""
        result = await handle_tool_registry_stats({"include_definitions": True})
        data = json.loads(result)

        assert data["success"] is True
        assert "tools" in data

    async def test_handle_tool_watch_status(self):
        """Test watch handler status action."""
        result = await handle_tool_watch({"action": "status"})
        data = json.loads(result)

        assert data["success"] is True
        assert data["action"] == "status"

    async def test_handle_tool_watch_start(self):
        """Test watch handler start action."""
        result = await handle_tool_watch({"action": "start", "interval": 5.0})
        data = json.loads(result)

        assert data["success"] is True
        assert data["action"] == "start"


# =============================================================================
# Integration Tests
# =============================================================================


class TestDiscoveryIntegration:
    """Integration tests for discovery and registry."""

    def setup_method(self):
        """Set up fresh registry."""
        DynamicToolRegistry._instance = None
        self.registry = DynamicToolRegistry()
        self.registry.clear()

    def test_discover_and_register_flow(self):
        """Test full discover and register flow."""
        # Create a temporary test file
        test_source = '''
def handle_test_tool(arg: str) -> str:
    """A test tool for integration testing."""
    return arg
'''
        engine = ToolDiscoveryEngine()
        tools = engine.discover_from_ast(test_source, "test_module", "test.py")

        assert len(tools) == 1

        # Register the discovered tool
        tool = tools[0]
        definition = tool.to_allowlist_entry()
        for name, defn in definition.items():
            self.registry.register_tool(name, defn, source="discovery")

        assert self.registry.tool_count == 1
        assert "test_module.handle_test_tool" in self.registry.tool_names


# =============================================================================
# Schema Generation Tests
# =============================================================================


class TestSchemaGeneration:
    """Tests for tool schema generation from functions."""

    def test_generate_from_function_simple(self):
        """Test schema generation from simple function."""

        def simple_func(arg1: str, arg2: int = 10) -> bool:
            """Simple test function."""
            return True

        schema = generate_tool_schema_from_function(simple_func)

        assert "simple_func" in schema
        assert schema["simple_func"]["description"] == "Simple test function."

    def test_generate_from_function_with_name_override(self):
        """Test schema generation with custom tool name."""

        def my_func():
            """Test."""
            pass

        schema = generate_tool_schema_from_function(my_func, "custom.name")

        assert "custom.name" in schema


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def setup_method(self):
        """Reset registry."""
        DynamicToolRegistry._instance = None
        get_registry().clear()

    def test_get_registry_singleton(self):
        """Test get_registry returns singleton."""
        from ai.mcp_bridge.dynamic_registry import get_registry as gr

        reg1 = gr()
        reg2 = gr()
        assert reg1 is reg2
