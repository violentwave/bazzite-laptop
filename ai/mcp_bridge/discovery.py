"""Dynamic Tool Discovery for MCP Bridge.

P102: Dynamic Tool Discovery - Auto-discover tools from code inspection,
register dynamically without restarts, and self-document tool capabilities.
"""

from __future__ import annotations

import ast
import inspect
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_type_hints

logger = logging.getLogger("ai.mcp_bridge.discovery")


@dataclass
class DiscoveredTool:
    """A tool discovered through code inspection.

    Attributes:
        name: Tool name (e.g., "module.function")
        description: Docstring description
        handler_module: Python module path
        handler_func: Function name
        args: List of argument specifications
        return_type: Return type annotation
        source_file: Path to source file
        line_number: Line number in source
    """

    name: str
    description: str
    handler_module: str
    handler_func: str
    args: list[dict[str, Any]] = field(default_factory=list)
    return_type: str = "Any"
    source_file: str = ""
    line_number: int = 0

    def to_allowlist_entry(self) -> dict[str, Any]:
        """Convert to allowlist YAML entry format."""
        args_def = {}
        for arg in self.args:
            arg_name = arg["name"]
            arg_def = {
                "type": arg.get("type", "string"),
                "required": arg.get("required", True),
            }
            if "description" in arg:
                arg_def["description"] = arg["description"]
            if "pattern" in arg:
                arg_def["pattern"] = arg["pattern"]
            if "max_length" in arg:
                arg_def["max_length"] = arg["max_length"]
            args_def[arg_name] = arg_def

        return {
            self.name: {
                "description": self.description,
                "source": "python",
                "module": self.handler_module,
                "function": self.handler_func,
                "args": args_def if args_def else None,
            }
        }


class ToolDiscoveryEngine:
    """Engine for discovering tools from Python code.

    Uses AST parsing and introspection to extract tool definitions
    from Python modules without executing them.
    """

    # Patterns that indicate a function is a tool handler
    TOOL_NAME_PATTERNS = [
        r"^handle_",  # handle_* functions
        r"^_?tool_",  # tool_* functions
        r".*_tool$",  # *_tool functions
    ]

    # Modules to skip during discovery
    SKIP_MODULES = {
        "test",
        "tests",
        "conftest",
        "__pycache__",
        "venv",
        ".venv",
        "env",
        ".env",
    }

    def __init__(self, project_root: str | Path | None = None):
        """Initialize discovery engine.

        Args:
            project_root: Root directory for discovery
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.discovered_tools: dict[str, DiscoveredTool] = {}

    def discover_module(
        self,
        module_path: str | Path,
        pattern: str | None = None,
    ) -> list[DiscoveredTool]:
        """Discover tools in a Python module.

        Args:
            module_path: Path to Python file or package directory
            pattern: Optional regex pattern to filter function names

        Returns:
            List of discovered tools
        """
        path = Path(module_path)
        discovered = []

        if path.is_file() and path.suffix == ".py":
            discovered.extend(self._scan_file(path, pattern))
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                # Skip test files and hidden directories
                if any(skip in str(py_file) for skip in self.SKIP_MODULES):
                    continue
                if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
                    continue
                discovered.extend(self._scan_file(py_file, pattern))

        # Store discovered tools
        for tool in discovered:
            self.discovered_tools[tool.name] = tool

        return discovered

    def discover_from_ast(
        self,
        source_code: str,
        module_name: str,
        source_file: str = "<string>",
    ) -> list[DiscoveredTool]:
        """Discover tools from source code using AST parsing.

        Args:
            source_code: Python source code
            module_name: Module name for discovered tools
            source_file: Source file path for metadata

        Returns:
            List of discovered tools
        """
        discovered = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.warning(f"Failed to parse {source_file}: {e}")
            return discovered

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            func_name = node.name

            # Check if function matches tool patterns
            is_tool = any(re.match(pattern, func_name) for pattern in self.TOOL_NAME_PATTERNS)

            # Also check for @mcp.tool() decorator
            has_tool_decorator = self._has_tool_decorator(node)

            if not is_tool and not has_tool_decorator:
                continue

            # Extract docstring
            docstring = ast.get_docstring(node) or ""
            description = self._extract_description(docstring)

            # Extract arguments
            args = self._extract_args_from_ast(node)

            # Determine return type
            return_type = "Any"
            if node.returns:
                return_type = self._ast_type_to_str(node.returns)

            # Build tool name
            tool_name = f"{module_name}.{func_name}"

            tool = DiscoveredTool(
                name=tool_name,
                description=description,
                handler_module=module_name,
                handler_func=func_name,
                args=args,
                return_type=return_type,
                source_file=source_file,
                line_number=node.lineno,
            )

            discovered.append(tool)

        return discovered

    def _scan_file(
        self,
        file_path: Path,
        pattern: str | None = None,
    ) -> list[DiscoveredTool]:
        """Scan a single Python file for tool functions."""
        discovered = []

        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return discovered

        # Derive module name from file path
        try:
            relative_path = file_path.relative_to(self.project_root)
            module_parts = list(relative_path.with_suffix("").parts)
            # Remove ai/ prefix if present (it's a package)
            if module_parts[0] == "ai":
                module_parts = module_parts[1:]
            module_name = ".".join(module_parts)
        except ValueError:
            module_name = file_path.stem

        tools = self.discover_from_ast(source, module_name, str(file_path))

        # Apply pattern filter
        if pattern:
            regex = re.compile(pattern)
            tools = [t for t in tools if regex.search(t.handler_func)]

        return tools

    def _has_tool_decorator(self, func_node: ast.FunctionDef) -> bool:
        """Check if function has @mcp.tool() or similar decorator."""
        for decorator in func_node.decorator_list:
            # Check for @mcp.tool() or @tool()
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == "tool":
                    return True
            elif isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "tool":
                    return True
                elif isinstance(func, ast.Name) and func.id == "tool":
                    return True
            elif isinstance(decorator, ast.Name) and decorator.id == "tool":
                return True
        return False

    def _extract_description(self, docstring: str) -> str:
        """Extract short description from docstring."""
        if not docstring:
            return ""
        # Take first line or first sentence
        lines = docstring.strip().split("\n")
        first_line = lines[0].strip()
        # Truncate if too long
        if len(first_line) > 200:
            first_line = first_line[:197] + "..."
        return first_line

    def _extract_args_from_ast(self, func_node: ast.FunctionDef) -> list[dict[str, Any]]:
        """Extract argument specifications from AST function node."""
        args = []

        # Get function arguments
        func_args = func_node.args

        # Map defaults to arguments
        defaults = [None] * (len(func_args.args) - len(func_args.defaults)) + list(
            func_args.defaults
        )

        for _i, (arg, default) in enumerate(zip(func_args.args, defaults, strict=False)):
            arg_name = arg.arg
            arg_info: dict[str, Any] = {"name": arg_name}

            # Get type annotation
            if arg.annotation:
                arg_type = self._ast_type_to_str(arg.annotation)
                arg_info["type"] = self._map_python_type_to_json_schema(arg_type)
            else:
                arg_info["type"] = "string"

            # Check if has default (optional)
            if default is not None:
                arg_info["required"] = False
                # Try to extract default value
                if isinstance(default, ast.Constant):
                    arg_info["default"] = default.value
            else:
                arg_info["required"] = True

            args.append(arg_info)

        return args

    def _ast_type_to_str(self, node: ast.AST) -> str:
        """Convert AST type node to string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Subscript):
            value = self._ast_type_to_str(node.value)
            slice_node = self._ast_type_to_str(node.slice) if hasattr(node, "slice") else ""
            return f"{value}[{slice_node}]"
        elif isinstance(node, ast.Attribute):
            value = self._ast_type_to_str(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Handle Union types (X | Y)
            left = self._ast_type_to_str(node.left)
            right = self._ast_type_to_str(node.right)
            return f"Union[{left}, {right}]"
        elif isinstance(node, ast.List):
            elements = [self._ast_type_to_str(e) for e in node.elts]
            return f"[{', '.join(elements)}]"
        return "Any"

    def _map_python_type_to_json_schema(self, python_type: str) -> str:
        """Map Python type to JSON schema type."""
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "Any": "string",
            "Optional": "string",
        }

        # Handle Optional[T] and Union types
        if "Optional[" in python_type or "Union[" in python_type:
            return "string"  # Simplified

        # Handle List[T]
        if python_type.startswith("List[") or python_type.startswith("list["):
            return "array"

        # Handle Dict[K, V]
        if python_type.startswith("Dict[") or python_type.startswith("dict["):
            return "object"

        return type_mapping.get(python_type, "string")

    def generate_allowlist_patch(self) -> dict[str, Any]:
        """Generate allowlist patch from discovered tools."""
        tools = {}
        for tool in self.discovered_tools.values():
            tools.update(tool.to_allowlist_entry())
        return {"tools": tools}


def discover_tools_in_module(
    module_path: str | Path,
    project_root: str | Path | None = None,
) -> list[DiscoveredTool]:
    """Convenience function to discover tools in a module.

    Args:
        module_path: Path to Python module or package
        project_root: Project root for module name resolution

    Returns:
        List of discovered tools
    """
    engine = ToolDiscoveryEngine(project_root)
    return engine.discover_module(module_path)


def generate_tool_schema_from_function(
    func: Callable[..., Any],
    tool_name: str | None = None,
) -> dict[str, Any]:
    """Generate tool schema from a function using introspection.

    Args:
        func: Function to introspect
        tool_name: Optional override for tool name

    Returns:
        Tool schema dictionary
    """
    name = tool_name or func.__name__

    # Get docstring
    docstring = inspect.getdoc(func) or ""
    description = docstring.split("\n")[0] if docstring else ""

    # Get signature
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    args = {}
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        arg_def: dict[str, Any] = {}

        # Get type
        param_type = type_hints.get(param_name, str)
        if hasattr(param_type, "__name__"):
            arg_def["type"] = param_type.__name__
        else:
            arg_def["type"] = "string"

        # Check if required
        if param.default is inspect.Parameter.empty:
            arg_def["required"] = True
        else:
            arg_def["required"] = False
            arg_def["default"] = param.default

        args[param_name] = arg_def

    return {
        name: {
            "description": description,
            "args": args if args else None,
        }
    }
