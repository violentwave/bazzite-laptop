#!/usr/bin/env python3
"""
mcp_tool_generator.py - Scaffold generator for MCP tools.

Generates YAML allowlist entries, Python handlers, and test stubs for FastMCP bridge.
"""

import argparse
import ast
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class ToolDefinition:
    name: str
    description: str
    handler_module: str
    handler_func: str
    args: list[dict]
    annotations: dict[str, Any]


class MCPToolGenerator:
    """Generator for MCP tool definitions, handlers, and tests."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.allowlist_path = self.project_root / "configs" / "mcp-bridge-allowlist.yaml"
        self.tools_py_path = self.project_root / "ai" / "mcp_bridge" / "tools.py"

    def parse_allowlist(self, yaml_path: str | None = None) -> dict[str, dict]:
        """Read the YAML, return dict of existing tool definitions."""
        path = Path(yaml_path) if yaml_path else self.allowlist_path

        if not path.exists():
            logging.warning(f"Allowlist not found: {path}")
            return {}

        if not HAS_YAML:
            raise RuntimeError("PyYAML required for parsing")

        content = path.read_text()
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        tools = data.get("tools", {})
        if not isinstance(tools, dict):
            raise ValueError("tools key must be a dict")

        for name, config in tools.items():
            if not isinstance(config, dict):
                logging.warning(f"Invalid tool config for {name}")
                continue
            if "description" not in config:
                logging.warning(f"Missing description for {name}")

        existing_handlers = self._extract_handlers_from_tools_py()
        missing = []
        for name, config in tools.items():
            handler = config.get("handler", "")
            if handler:
                func = handler.split(".")[-1] if "." in handler else handler
                if func not in existing_handlers:
                    missing.append(name)

        if missing:
            logging.warning(f"Tools missing handlers: {missing}")

        return tools

    def _extract_handlers_from_tools_py(self) -> set[str]:
        """Extract function names from tools.py."""
        if not self.tools_py_path.exists():
            return set()

        content = self.tools_py_path.read_text()
        handlers = set()

        for match in re.finditer(r"(?:async\s+)?def\s+(\w+)\s*\(", content):
            handlers.add(match.group(1))

        return handlers

    def scaffold_tool(
        self,
        name: str,
        description: str,
        handler_module: str,
        args_spec: list[dict],
        annotations: dict[str, Any],
        output_dir: str,
    ) -> dict[str, str]:
        """Generates YAML snippet, Python handler, and pytest test stub."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^\w]", "_", name).lower()
        func_name = f"handle_{safe_name}"

        yaml_entry = {
            name: {
                "description": description,
                "handler": f"{handler_module}.{func_name}",
                "args": {},
                "annotations": annotations
                or {"readOnly": True, "destructive": False, "openWorld": False},
            }
        }

        for arg in args_spec:
            yaml_entry[name]["args"][arg["name"]] = {k: v for k, v in arg.items() if k != "name"}

        handlers_dir = out / "handlers"
        handlers_dir.mkdir(exist_ok=True)
        handler_file = handlers_dir / f"{safe_name}.py"

        handler_code = f'''"""Handler for {name}.

Auto-generated MCP tool handler.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def {func_name}(args: dict) -> dict:
    """
    {description}
    Args:
'''
        for arg in args_spec:
            arg_name = arg.get("name", "arg")
            arg_desc = arg.get("description", "Parameter")
            handler_code += f"        {arg_name}: {arg_desc}\n"

        handler_code += '''
    Returns:
        dict with status and data/error
    """
    try:
        # TODO: Implement handler logic
        result = {}

        return {{"status": "ok", "data": result}}

    except Exception as e:
        logger.error(f"Error in {func_name}: {{e}}")
        return {{"status": "error", "error": str(e)}}
'''

        tmp_handler = handler_file.with_suffix(".tmp")
        with open(tmp_handler, "w") as f:
            f.write(handler_code)

        try:
            ast.parse(handler_code)
        except SyntaxError as e:
            raise ValueError(f"Generated handler has syntax error: {e}") from e

        os.replace(tmp_handler, handler_file)

        tests_dir = out / "tests"
        tests_dir.mkdir(exist_ok=True)
        test_file = tests_dir / f"test_{safe_name}.py"

        test_code = f'''"""Tests for {name}.

Auto-generated test stub.
"""
import pytest
from handlers.{safe_name} import {func_name}


@pytest.mark.asyncio
async def test_{func_name}_success():
    """Test successful invocation."""
    args = {{}}
    result = await {func_name}(args)
    assert result["status"] == "ok"
    assert "data" in result


@pytest.mark.asyncio
async def test_{func_name}_missing_required_args():
    """Test handling of missing required arguments."""
    args = {{}}  # Missing required args
    result = await {func_name}(args)
    # Should either succeed with defaults or fail gracefully
    assert result["status"] in ("ok", "error")


@pytest.mark.asyncio
async def test_{func_name}_error_handling():
    """Test error handling for edge cases."""
    args = {{"invalid": "data"}}
    result = await {func_name}(args)
    # Should not raise exception
    assert "status" in result
'''

        tmp_test = test_file.with_suffix(".tmp")
        with open(tmp_test, "w") as f:
            f.write(test_code)

        try:
            ast.parse(test_code)
        except SyntaxError as e:
            raise ValueError(f"Generated test has syntax error: {e}") from e

        os.replace(tmp_test, test_file)

        yaml_file = out / f"{safe_name}_allowlist_snippet.yaml"
        tmp_yaml = yaml_file.with_suffix(".tmp")
        with open(tmp_yaml, "w") as f:
            if HAS_YAML:
                yaml.dump({"tools": yaml_entry}, f, default_flow_style=False, sort_keys=False)
            else:
                if not HAS_YAML:
                    raise ImportError(
                        "PyYAML is required: uv pip install pyyaml --break-system-packages"
                    )

        if HAS_YAML:
            try:
                with open(tmp_yaml) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Generated YAML is invalid: {e}") from e

        os.replace(tmp_yaml, yaml_file)

        return {
            "yaml_snippet": str(yaml_file),
            "handler_file": str(handler_file),
            "test_file": str(test_file),
        }

    def validate_tool(
        self,
        name: str,
        allowlist_path: str | None = None,
        tools_py_path: str | None = None,
    ) -> dict[str, Any]:
        """Check that a tool defined in YAML has corresponding handler in tools.py."""
        al_path = Path(allowlist_path) if allowlist_path else self.allowlist_path
        tp_path = Path(tools_py_path) if tools_py_path else self.tools_py_path

        issues = []

        try:
            tools = self.parse_allowlist(str(al_path))
        except Exception as e:
            return {"valid": False, "issues": [str(e)]}

        if name not in tools:
            return {"valid": False, "issues": [f"Tool '{name}' not found in allowlist"]}

        config = tools[name]
        handler = config.get("handler", "")

        if not handler:
            issues.append("No handler specified")
            return {"valid": False, "issues": issues}

        func_name = handler.split(".")[-1] if "." in handler else handler

        if tp_path.exists():
            content = tp_path.read_text()
            if func_name not in content:
                issues.append(f"Handler function '{func_name}' not found in tools.py")
        else:
            issues.append(f"tools.py not found at {tp_path}")

        args = config.get("args", {})
        for arg_name, arg_config in args.items():
            if not isinstance(arg_config, dict):
                issues.append(f"Invalid arg config for '{arg_name}'")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def audit_all_tools(
        self,
        allowlist_path: str | None = None,
        tools_py_path: str | None = None,
    ) -> dict[str, Any]:
        """Run validate_tool for every entry in allowlist."""
        al_path = Path(allowlist_path) if allowlist_path else self.allowlist_path

        try:
            tools = self.parse_allowlist(str(al_path))
        except Exception as e:
            return {
                "total": 0,
                "valid": 0,
                "missing_handlers": 0,
                "issues": [{"tool": "_all", "issue": str(e)}],
            }

        summary = {
            "total": len(tools),
            "valid": 0,
            "missing_handlers": 0,
            "issues": [],
        }

        for name in tools:
            result = self.validate_tool(name, allowlist_path, tools_py_path)
            if result["valid"]:
                summary["valid"] += 1
            else:
                if any("not found in tools.py" in i for i in result["issues"]):
                    summary["missing_handlers"] += 1
                for issue in result["issues"]:
                    summary["issues"].append({"tool": name, "issue": issue})

        return summary

    def generate_annotation_block(self, tools_dict: dict[str, dict]) -> str:
        """Generate the _ANNOTATIONS dict Python code block from tool definitions."""
        lines = ["_ANNOTATIONS = {", "    # Auto-generated from allowlist", ""]

        for name, config in tools_dict.items():
            annotations = config.get("annotations", {})
            if not annotations:
                annotations = {"readOnly": True, "destructive": False, "openWorld": False}

            lines.append(f'    "{name}": {{')
            for key, value in annotations.items():
                if isinstance(value, bool):
                    lines.append(f'        "{key}": {value},')
                elif isinstance(value, str):
                    lines.append(f'        "{key}": "{value}",')
                else:
                    lines.append(f'        "{key}": {value},')
            lines.append("    },")

        lines.append("}")

        return "\n".join(lines)

    def run(self, command: str, **kwargs) -> Any:
        """CLI dispatcher. Commands: scaffold, validate, audit, gen-annotations."""
        if command == "scaffold":
            return self.scaffold_tool(
                name=kwargs["name"],
                description=kwargs["description"],
                handler_module=kwargs["handler_module"],
                args_spec=kwargs.get("args_spec", []),
                annotations=kwargs.get("annotations", {}),
                output_dir=kwargs["output_dir"],
            )
        elif command == "validate":
            return self.validate_tool(
                name=kwargs["name"],
                allowlist_path=kwargs.get("allowlist_path"),
                tools_py_path=kwargs.get("tools_py_path"),
            )
        elif command == "audit":
            return self.audit_all_tools(
                allowlist_path=kwargs.get("allowlist_path"),
                tools_py_path=kwargs.get("tools_py_path"),
            )
        elif command == "gen-annotations":
            tools = self.parse_allowlist(kwargs.get("allowlist_path"))
            code = self.generate_annotation_block(tools)
            out_file = Path(kwargs.get("output_dir", ".")) / "_annotations.py"
            tmp = out_file.with_suffix(".tmp")
            with open(tmp, "w") as f:
                f.write(code)
            os.replace(tmp, out_file)
            return {"file": str(out_file), "lines": len(code.split("\n"))}
        else:
            raise ValueError(f"Unknown command: {command}")


def main():
    parser = argparse.ArgumentParser(description="MCP Tool Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold", help="Generate new tool stubs")
    scaffold_parser.add_argument("name", help="Tool name")
    scaffold_parser.add_argument("--description", "-d", required=True, help="Tool description")
    scaffold_parser.add_argument(
        "--handler-module", "-m", default="ai.mcp_bridge.generated", help="Handler module path"
    )
    scaffold_parser.add_argument(
        "--args", "-a", help='Args spec as JSON \'[{"name":"x","type":"str"}]\''
    )
    scaffold_parser.add_argument("--annotations", help="Annotations as JSON '{\"readOnly\":true}'")
    scaffold_parser.add_argument(
        "--output-dir", "-o", default="./generated_tools", help="Output directory"
    )

    validate_parser = subparsers.add_parser("validate", help="Validate existing tool")
    validate_parser.add_argument("name", help="Tool name to validate")
    validate_parser.add_argument("--project-root", "-r", help="Project root path")

    audit_parser = subparsers.add_parser("audit", help="Audit all tools")
    audit_parser.add_argument("--project-root", "-r", help="Project root path")

    gen_parser = subparsers.add_parser("gen-annotations", help="Generate _ANNOTATIONS block")
    gen_parser.add_argument("--project-root", "-r", help="Project root path")
    gen_parser.add_argument("--output-dir", "-o", default=".", help="Output directory")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    project_root = getattr(args, "project_root", None)
    if not project_root:
        possible = Path.home() / "workspace" / "bazzite-laptop"
        if possible.exists():
            project_root = str(possible)
        else:
            project_root = "."

    gen = MCPToolGenerator(project_root)

    if args.command == "scaffold":
        args_spec = json.loads(args.args) if args.args else []
        annotations = json.loads(args.annotations) if args.annotations else {}

        result = gen.run(
            "scaffold",
            name=args.name,
            description=args.description,
            handler_module=args.handler_module,
            args_spec=args_spec,
            annotations=annotations,
            output_dir=args.output_dir,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "validate":
        result = gen.run("validate", name=args.name)
        print(json.dumps(result, indent=2))

    elif args.command == "audit":
        result = gen.run("audit")
        print(json.dumps(result, indent=2))

    elif args.command == "gen-annotations":
        result = gen.run("gen-annotations", output_dir=args.output_dir)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
