# P102 — Dynamic Tool Discovery

**Status:** Complete  
**Date:** 2026-04-15  
**Dependencies:** P101 (Tool Governance + Analytics Platform)  

---

## Objective

Implement runtime tool registration without service restarts, enabling:
1. Auto-discovery of tools from Python code inspection
2. Self-documenting tool capabilities via function signatures and docstrings
3. Hot-reload of the tool allowlist
4. Dynamic tool management via MCP tools

---

## Deliverables

### 1. Tool Discovery Engine (`ai/mcp_bridge/discovery.py`)

AST-based code inspection that extracts tool definitions from Python modules:

- **DiscoveredTool dataclass**: Structured representation of discovered tools
- **ToolDiscoveryEngine class**: Main discovery engine with configurable patterns
  - AST parsing for function extraction
  - Decorator detection (`@mcp.tool()`, `@tool()`)
  - Type hint extraction
  - Docstring parsing for descriptions
  - Pattern-based function filtering

**Key Features:**
- Discovers functions matching patterns: `handle_*`, `tool_*`, `*_tool`
- Extracts function signatures with type hints
- Parses docstrings for descriptions
- Generates allowlist-compatible tool definitions

**Usage:**
```python
from ai.mcp_bridge.discovery import discover_tools_in_module

tools = discover_tools_in_module("ai/custom/handlers.py")
for tool in tools:
    print(f"Found: {tool.name} - {tool.description}")
```

### 2. Dynamic Tool Registry (`ai/mcp_bridge/dynamic_registry.py`)

Runtime registry for managing tools without restarts:

- **DynamicToolRegistry class**: Singleton registry
  - Register/unregister tools at runtime
  - Hot-reload allowlist from disk
  - Track tool sources (manual, discovery, hot_reload)
  - Export tools to allowlist YAML

- **AllowlistWatcher class**: Background file watcher
  - Automatic reload on allowlist changes
  - Configurable check interval

**Key Features:**
- Thread-safe singleton pattern
- Callback support for reload events
- Tool source tracking for audit
- Atomic file writes for exports

**Usage:**
```python
from ai.mcp_bridge.dynamic_registry import get_registry

registry = get_registry()
registry.register_tool(
    name="custom.my_tool",
    definition={"description": "My tool", "source": "python", ...},
    source="manual"
)

# Hot-reload allowlist
result = registry.reload_allowlist()
print(f"Added: {result['added']}, Removed: {result['removed']}")
```

### 3. MCP Tool Handlers (`ai/mcp_bridge/tool_discovery_handlers.py`)

Six new MCP tools for dynamic tool management:

| Tool | Description | Read-Only |
|------|-------------|-----------|
| `tool.discover` | Discover tools in a Python module | Yes |
| `tool.register` | Register a tool dynamically | No |
| `tool.unregister` | Unregister a dynamic tool | No |
| `tool.reload` | Hot-reload the allowlist | No |
| `tool.registry_stats` | Get registry statistics | Yes |
| `tool.watch` | Control allowlist file watcher | No |

**Example Usage:**

```bash
# Discover tools in a module
tool.discover module_path="ai/custom/handlers.py"

# Register discovered tools
tool.register auto_discover=true module="ai.custom.handlers"

# Check registry stats
tool.registry_stats include_definitions=true

# Hot-reload allowlist
tool.reload force=false dry_run=false
```

### 4. Updated Allowlist (`configs/mcp-bridge-allowlist.yaml`)

Added 6 new tools (total now 151):

- `tool.discover`
- `tool.register`
- `tool.unregister`
- `tool.reload`
- `tool.registry_stats`
- `tool.watch`

### 5. Tool Handler Wiring (`ai/mcp_bridge/tools.py`)

Updated `_execute_python_tool()` to handle the 6 new P102 tools.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Bridge Server                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐      ┌──────────────────┐                 │
│  │  Tool Discovery │      │ Dynamic Registry │                 │
│  │     Engine      │──────│    (Singleton)   │                 │
│  └─────────────────┘      └────────┬─────────┘                 │
│           │                        │                            │
│           │                        │                            │
│           ▼                        ▼                            │
│  ┌─────────────────┐      ┌──────────────────┐                 │
│  │  AST Parsing    │      │  Allowlist YAML  │                 │
│  │  Introspection  │      │  Hot-reload      │                 │
│  └─────────────────┘      └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MCP Tool Handlers (6 tools)                  │  │
│  │  tool.discover | tool.register | tool.unregister         │  │
│  │  tool.reload   | tool.registry_stats | tool.watch        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Testing

Comprehensive test suite in `tests/test_p102_dynamic_tool_discovery.py`:

- **ToolDiscoveryEngine tests**: AST parsing, argument extraction, type mapping
- **DynamicRegistry tests**: Registration, unregistration, hot-reload
- **Handler tests**: All 6 MCP tool handlers
- **Integration tests**: End-to-end discover → register flow
- **Schema generation tests**: Function introspection

Run tests:
```bash
python -m pytest tests/test_p102_dynamic_tool_discovery.py -v
```

---

## Validation

### Ruff Linting
```bash
ruff check ai/mcp_bridge/discovery.py ai/mcp_bridge/dynamic_registry.py \
    ai/mcp_bridge/tool_discovery_handlers.py
# Result: All checks passed!
```

### Files Created/Modified

**New Files:**
- `ai/mcp_bridge/discovery.py` (436 lines)
- `ai/mcp_bridge/dynamic_registry.py` (424 lines)
- `ai/mcp_bridge/tool_discovery_handlers.py` (416 lines)
- `tests/test_p102_dynamic_tool_discovery.py` (416 lines)
- `docs/P102_PLAN.md` (this document)

**Modified Files:**
- `configs/mcp-bridge-allowlist.yaml` (+77 lines for 6 new tools)
- `ai/mcp_bridge/tools.py` (+45 lines for handler wiring)

**Total:** 4 new files, 2 modified files, ~1800 lines

---

## Future Enhancements

### P102.1: Advanced Discovery Patterns
- Support for class-based tool definitions
- Decorator argument extraction
- Generic type handling

### P102.2: Tool Validation Pipeline
- Runtime schema validation
- Handler existence verification
- Argument type checking

### P102.3: Tool Marketplace Integration
- Import tools from external repositories
- Version management for dynamic tools
- Tool dependency resolution

---

## Success Criteria

- [x] Tool Discovery Engine implemented with AST parsing
- [x] Dynamic Tool Registry with hot-reload capability
- [x] 6 new MCP tools for tool management
- [x] Self-documenting tool schema generation
- [x] Code inspection for auto-discovery
- [x] Comprehensive test coverage (416 lines of tests)
- [x] Ruff clean on all new code
- [x] Documentation complete

---

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [P101 Tool Governance](./P101_COMPLETION_REPORT.md)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)