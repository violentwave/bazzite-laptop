"""Tests for ai/system/mcp_generator.py"""

from unittest.mock import MagicMock, patch


class TestMCPToolGenerator:
    """Test MCPToolGenerator class."""

    def test_tool_definition_dataclass(self):
        """Test ToolDefinition dataclass."""
        from ai.system.mcp_generator import ToolDefinition

        tool = ToolDefinition(
            name="test.tool",
            description="Test tool",
            handler_module="ai.mcp_bridge.tools",
            handler_func="handle_test",
            args=[{"name": "input", "type": "str", "required": True}],
            annotations={"readOnly": True, "destructive": False},
        )
        assert tool.name == "test.tool"
        assert tool.handler_func == "handle_test"

    @patch("ai.system.mcp_generator.Path")
    def test_parse_allowlist_missing_yaml(self, mock_path_cls):
        """Test parse_allowlist returns empty dict when file missing."""
        from ai.system.mcp_generator import MCPToolGenerator

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_cls.return_value = mock_path

        gen = MCPToolGenerator("/fake/project")
        result = gen.parse_allowlist("/fake/path.yaml")

        assert result == {}

    def test_generate_annotation_block_uses_real_newlines(self):
        """Test generate_annotation_block returns string with real newlines."""
        from ai.system.mcp_generator import MCPToolGenerator

        gen = MCPToolGenerator("/fake")
        tools_dict = {"test.tool": {"annotations": {"readOnly": True}}}
        result = gen.generate_annotation_block(tools_dict)

        assert "\\n" not in result
        assert "\n" in result
        assert "_ANNOTATIONS" in result

    def test_validate_tool_missing_handler(self):
        """Test validate_tool detects tool not in allowlist."""
        from ai.system.mcp_generator import MCPToolGenerator

        with patch.object(MCPToolGenerator, "parse_allowlist", return_value={}):
            gen = MCPToolGenerator("/var/home/lch/projects/bazzite-laptop")
            result = gen.validate_tool("nonexistent.tool")

        assert result["valid"] is False
        assert "not found in allowlist" in result["issues"][0]

    def test_generate_annotation_block_multiple_tools(self):
        """Test generate_annotation_block with multiple tools."""
        from ai.system.mcp_generator import MCPToolGenerator

        gen = MCPToolGenerator("/fake")
        tools_dict = {
            "tool.one": {"annotations": {"readOnly": True}},
            "tool.two": {"annotations": {"readOnly": False, "destructive": True}},
        }
        result = gen.generate_annotation_block(tools_dict)

        assert "tool.one" in result
        assert "tool.two" in result
        lines = result.split("\n")
        assert len(lines) > 5

    @patch("ai.system.mcp_generator.MCPToolGenerator.parse_allowlist")
    def test_audit_all_tools_summary(self, mock_parse):
        """Test audit_all_tools returns correct summary."""
        from ai.system.mcp_generator import MCPToolGenerator

        mock_parse.return_value = {
            "tool1": {"handler": "handle_tool1"},
            "tool2": {},
        }

        gen = MCPToolGenerator("/fake")
        result = gen.audit_all_tools()

        assert result["total"] == 2
        assert result["missing_handlers"] >= 0
