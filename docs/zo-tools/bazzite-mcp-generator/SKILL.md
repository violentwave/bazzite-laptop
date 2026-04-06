---
name: bazzite-mcp-generator
description: Generates new MCP tools for bazzite-laptop by analyzing existing tools, creating tool definitions, and validating against the allowlist schema
compatibility: Created for Zo Computer - Python 3.12+ with jinja2
metadata:
  author: topoman.zo.computer
  version: "1.0.0"
  created: 2026-04-06
---

# Bazzite MCP Tool Generator

Generates new MCP tool definitions for the bazzite-laptop AI layer. Analyzes existing tools, creates YAML allowlist entries, Python handlers, and validates against the MCP bridge schema.

## What It Does

1. **Tool Analysis** - Reads existing 79 tools from `ai/mcp_bridge/tools.py`
2. **Pattern Extraction** - Identifies common patterns (system calls, API wrappers, file operations)
3. **Template Generation** - Creates new tool from description using templates
4. **YAML Validation** - Validates against `configs/mcp-bridge-allowlist.yaml` schema
5. **Handler Generation** - Python handler function with proper error handling
6. **Test Generation** - pytest template for the new tool
7. **Integration Check** - Ensures no duplicate tool names

## Integration with Bazzite System

- Reads from `ai/mcp_bridge/tools.py` for patterns
- Updates `configs/mcp-bridge-allowlist.yaml`
- Generates handlers in `ai/mcp_bridge/generated_tools.py`
- Saves tests to `tests/test_generated_tools.py`
- Validates against existing tool registry

## Usage

### Generate Tool from Description
```bash
cd ~/workspace/Skills/bazzite-mcp-generator
./scripts/generate.sh "Get current CPU temperature and thermal throttling status"
```

### Generate with Custom Name
```bash
./scripts/generate.sh "List all systemd failed units" --name system_failed_units
```

### Validate Existing Tools
```bash
./scripts/generate.sh --validate-only
```

## Template Structure

Generated tools include:
```python
@mcp_tool("tool_name")  # Decorator from mcp_bridge
async def tool_name(param: str) -> dict:
    """
    Description from prompt.
    
    Args:
        param: Parameter description
    
    Returns:
        Structured result with status/error
    """
    try:
        # Implementation
        return {"success": True, "result": ...}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Files
- `scripts/generate.py` - Main generator
- `scripts/generate.sh` - Wrapper script
- `templates/tool_handler.py.j2` - Handler template
- `templates/allowlist_entry.yaml.j2` - YAML template
- `templates/tool_test.py.j2` - Test template