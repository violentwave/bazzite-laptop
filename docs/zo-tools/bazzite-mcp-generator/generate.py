#!/usr/bin/env python3
"""
Bazzite MCP Tool Generator

Generates new MCP tool definitions, handlers, and tests for the bazzite-laptop
AI system based on existing tool patterns.
"""

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class ExistingTool:
    name: str
    category: str
    args: list[dict]
    description: str
    source: str


@dataclass
class GeneratedTool:
    name: str
    category: str
    description: str
    args: list[dict]
    handler_code: str
    yaml_entry: str
    test_code: str


class MCPGenerator:
    # Category detection patterns
    CATEGORY_PATTERNS = {
        "system": ["systemd", "service", "timer", "journal", "unit", "process", "cpu", "memory", "disk"],
        "security": ["threat", "intel", "hash", "scan", "vulnerability", "cve", "malware"],
        "code": ["git", "commit", "pr", "branch", "file", "code", "ast", "parse"],
        "llm": ["model", "prompt", "token", "cost", "provider", "router"],
        "knowledge": ["rag", "vector", "search", "embed", "document", "memory"],
        "monitoring": ["metric", "health", "status", "alert", "perf", "profile"],
    }

    # Common parameter patterns
    PARAM_PATTERNS = {
        "path": {"type": "string", "description": "Path to file or directory", "required": True},
        "name": {"type": "string", "description": "Resource name", "required": True},
        "id": {"type": "string", "description": "Unique identifier", "required": True},
        "limit": {"type": "integer", "description": "Maximum results to return", "default": 10, "required": False},
        "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30, "required": False},
        "format": {"type": "string", "description": "Output format", "enum": ["json", "yaml", "text"], "default": "json", "required": False},
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.existing_tools: list[ExistingTool] = []
        self.generated_dir = project_root / "ai" / "mcp_bridge" / "generated"

    def load_existing_tools(self) -> list[ExistingTool]:
        """Analyze existing tools from allowlist and source."""
        tools = []

        # Load from allowlist YAML
        allowlist_path = self.project_root / "configs" / "mcp-bridge-allowlist.yaml"
        if allowlist_path.exists() and HAS_YAML:
            try:
                data = yaml.safe_load(allowlist_path.read_text())
                for name, config in data.get("tools", {}).items():
                    tools.append(ExistingTool(
                        name=name,
                        category=config.get("category", "unknown"),
                        args=config.get("args", []),
                        description=config.get("description", ""),
                        source="allowlist",
                    ))
            except Exception as e:
                logger.warning(f"Failed to parse allowlist: {e}")

        # Load from tools.py source
        tools_py = self.project_root / "ai" / "mcp_bridge" / "tools.py"
        if tools_py.exists():
            content = tools_py.read_text()
            # Extract @mcp_tool decorated functions
            pattern = r'@mcp_tool\(["\'](\w+)["\'][^)]*\)\s*(?:async\s+)?def\s+(\w+)\([^)]*\)[^:]*:\s*"""([^"]*)"""'
            for match in re.finditer(pattern, content, re.DOTALL):
                name = match.group(1)
                func = match.group(2)
                desc = match.group(3).strip()[:100]

                # Check if already in list
                if not any(t.name == name for t in tools):
                    tools.append(ExistingTool(
                        name=name,
                        category="unknown",
                        args=[],
                        description=desc,
                        source="tools.py",
                    ))

        self.existing_tools = tools
        logger.info(f"Loaded {len(tools)} existing tools")
        return tools

    def detect_category(self, description: str) -> str:
        """Detect tool category from description."""
        desc_lower = description.lower()
        scores: dict[str, int] = {}

        for category, patterns in self.CATEGORY_PATTERNS.items():
            score = sum(1 for p in patterns if p in desc_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "general"

    def suggest_tool_name(self, description: str) -> str:
        """Suggest a tool name from description."""
        # Extract key verbs and nouns
        words = re.findall(r'\b\w+\b', description.lower())

        # Filter out common words
        stop_words = {"the", "and", "get", "set", "to", "from", "a", "an", "of", "in", "on", "with", "current", "all", "list", "check", "update", "create", "delete", "remove", "add", "new"}
        keywords = [w for w in words if w not in stop_words and len(w) > 3][:3]

        if keywords:
            # Common prefix based on action
            if any(w in words for w in ["get", "read", "fetch", "retrieve"]):
                prefix = "get_"
            elif any(w in words for w in ["list", "show", "display"]):
                prefix = "list_"
            elif any(w in words for w in ["check", "verify", "validate", "test"]):
                prefix = "check_"
            elif any(w in words for w in ["update", "set", "modify", "change"]):
                prefix = "update_"
            elif any(w in words for w in ["create", "generate", "build", "make"]):
                prefix = "create_"
            elif any(w in words for w in ["delete", "remove", "clear"]):
                prefix = "delete_"
            else:
                prefix = ""

            name = prefix + "_".join(keywords)
        else:
            name = "tool_" + datetime.now(UTC).strftime("%H%M%S")

        # Sanitize
        name = re.sub(r'[^\w_]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name[:50].strip('_')

    def infer_parameters(self, description: str) -> list[dict]:
        """Infer parameters from description."""
        params = []
        desc_lower = description.lower()

        # Check for path references
        if any(w in desc_lower for w in ["path", "file", "directory", "folder", "location"]):
            params.append({
                "name": "path",
                **self.PARAM_PATTERNS["path"]
            })

        # Check for name/id references
        if any(w in desc_lower for w in ["name", "id", "identifier", "unit", "service"]):
            if "service" in desc_lower or "unit" in desc_lower or "systemd" in desc_lower:
                params.append({
                    "name": "name",
                    "type": "string",
                    "description": "Service or unit name",
                    "required": False,
                })
            else:
                params.append({
                    **self.PARAM_PATTERNS["name"],
                    "required": False,
                })

        # Check for limit
        if any(w in desc_lower for w in ["all", "list", "top", "recent"]):
            params.append({**self.PARAM_PATTERNS["limit"]})

        # Check for format
        if any(w in desc_lower for w in ["output", "format", "json", "yaml"]):
            params.append({**self.PARAM_PATTERNS["format"]})

        return params

    def generate_handler(self, tool: GeneratedTool) -> str:
        """Generate Python handler code."""
        # Detect implementation pattern based on category
        if tool.category == "system":
            impl = self._system_implementation(tool)
        elif tool.category == "security":
            impl = self._security_implementation(tool)
        elif tool.category == "code":
            impl = self._code_implementation(tool)
        else:
            impl = self._general_implementation(tool)

        code = f'''"""{tool.description}"""

@mcp_tool("{tool.name}")
async def {tool.name.replace("-", "_")}({self._param_signature(tool.args)}) -> dict:
    """
    {tool.description}
    
    Returns:
        dict: Operation result with success status
    """
    try:
{impl}
    except Exception as e:
        logger.error(f"{tool.name} failed: {{e}}")
        return {{"success": False, "error": str(e)}}
'''
        return code

    def _param_signature(self, args: list[dict]) -> str:
        """Generate function parameter signature."""
        if not args:
            return ""

        params = []
        for arg in args:
            name = arg["name"]
            default = arg.get("default")

            if arg.get("required", True):
                params.append(f"{name}: {arg['type']}")
            else:
                if default is not None:
                    if isinstance(default, str):
                        params.append(f"{name}: {arg['type']} = '{default}'")
                    else:
                        params.append(f"{name}: {arg['type']} = {default}")
                else:
                    params.append(f"{name}: {arg['type']} = None")

        return ", ".join(params)

    def _system_implementation(self, tool: GeneratedTool) -> str:
        """Generate system call implementation."""
        return '''        # System implementation
        result = subprocess.run(
            ["systemctl", "status", name] if name else ["systemctl", "list-units", "--failed"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }'''

    def _security_implementation(self, tool: GeneratedTool) -> str:
        """Generate security API implementation."""
        return '''        # Security implementation
        # TODO: Implement security check logic
        return {
            "success": True,
            "result": "Security check completed",
        }'''

    def _code_implementation(self, tool: GeneratedTool) -> str:
        """Generate file/code implementation."""
        return '''        # File implementation
        if not Path(path).exists():
            return {"success": False, "error": f"Path not found: {path}"}
        
        # TODO: Implement file operation
        return {
            "success": True,
            "result": "Operation completed",
        }'''

    def _general_implementation(self, tool: GeneratedTool) -> str:
        """Generate general implementation stub."""
        return f'''        # Implementation
        # TODO: Implement tool logic based on: {tool.description[:50]}
        return {{
            "success": True,
            "result": "Stub implementation - replace with actual logic",
        }}'''

    def generate_yaml(self, tool: GeneratedTool) -> str:
        """Generate allowlist YAML entry."""
        yaml_entry = f'''  {tool.name}:
    description: "{tool.description[:200]}"
    category: {tool.category}
    args:
'''
        for arg in tool.args:
            yaml_entry += f'''      - name: {arg["name"]}
        type: {arg["type"]}
        description: "{arg.get("description", "")}"
        required: {str(arg.get("required", False)).lower()}
'''
            if "default" in arg:
                yaml_entry += f'''        default: {arg["default"]}
'''
            if "enum" in arg:
                yaml_entry += f'''        enum: {arg["enum"]}
'''

        yaml_entry += '''    source: python
    module: "ai.mcp_bridge.generated_tools"
    enabled: true
'''
        return yaml_entry

    def generate_test(self, tool: GeneratedTool) -> str:
        """Generate pytest test."""
        test_code = f'''
def test_{tool.name.replace("-", "_")}():
    """Test {tool.name} tool."""
    # Import the tool
    from ai.mcp_bridge.generated_tools import {tool.name.replace("-", "_")}
    
    # Run basic invocation
    result = await {tool.name.replace("-", "_")}()
    
    # Assertions
    assert "success" in result
    assert isinstance(result["success"], bool)
    
    # Test with parameters if applicable
'''
        for arg in tool.args:
            if arg.get("required", False):
                test_code += f'''    with pytest.raises(TypeError):
        await {tool.name.replace("-", "_")}()  # Missing required {arg["name"]}
'''
                break

        return test_code

    def validate_name(self, name: str) -> tuple[bool, str]:
        """Validate tool name is unique and valid."""
        # Check format
        if not re.match(r'^[a-z][a-z0-9_-]*$', name):
            return False, "Name must start with lowercase letter, contain only letters/numbers/_/-"

        # Check length
        if len(name) > 50:
            return False, "Name must be 50 characters or less"

        # Check uniqueness
        existing_names = {t.name for t in self.existing_tools}
        if name in existing_names:
            return False, f"Tool '{name}' already exists"

        return True, "Valid"

    def generate(self, description: str, name: str | None = None) -> GeneratedTool:
        """Generate complete tool from description."""
        self.load_existing_tools()

        # Suggest or validate name
        if name is None:
            name = self.suggest_tool_name(description)

        is_valid, msg = self.validate_name(name)
        if not is_valid:
            logger.error(f"Name validation failed: {msg}")
            sys.exit(1)

        # Detect category
        category = self.detect_category(description)

        # Infer parameters
        args = self.infer_parameters(description)

        tool = GeneratedTool(
            name=name,
            category=category,
            description=description,
            args=args,
            handler_code="",
            yaml_entry="",
            test_code="",
        )

        # Generate all components
        tool.handler_code = self.generate_handler(tool)
        tool.yaml_entry = self.generate_yaml(tool)
        tool.test_code = self.generate_test(tool)

        return tool

    def save_tool(self, tool: GeneratedTool, dry_run: bool = False) -> list[Path]:
        """Save generated tool to project."""
        if dry_run:
            logger.info("DRY RUN - would save to:")
            logger.info("  - Handler: ai/mcp_bridge/generated_tools.py")
            logger.info("  - Allowlist: configs/mcp-bridge-allowlist.yaml")
            logger.info("  - Test: tests/test_generated_tools.py")
            return []

        self.generated_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []

        # Save handler
        handler_file = self.generated_dir / "generated_tools.py"
        if handler_file.exists():
            content = handler_file.read_text()
            content += "\n\n" + tool.handler_code
        else:
            content = f'''"""Auto-generated MCP tools for bazzite-laptop.
Generated: {datetime.now(UTC).isoformat()}
"""

import logging
import subprocess
from pathlib import Path

from ai.mcp_bridge.tools import mcp_tool

logger = logging.getLogger(__name__)


''' + tool.handler_code

        handler_file.write_text(content)
        saved.append(handler_file)
        logger.info(f"Saved handler: {handler_file}")

        # Append to allowlist
        allowlist_path = self.project_root / "configs" / "mcp-bridge-allowlist.yaml"
        if allowlist_path.exists():
            content = allowlist_path.read_text()
            # Insert before the last line or at end
            content = content.rstrip() + "\n\n" + tool.yaml_entry
            allowlist_path.write_text(content)
            saved.append(allowlist_path)
            logger.info(f"Updated allowlist: {allowlist_path}")

        # Append test
        test_file = self.project_root / "tests" / "test_generated_tools.py"
        if test_file.exists():
            content = test_file.read_text()
            content = content.rstrip() + "\n\n" + tool.test_code
        else:
            content = '''"""Tests for auto-generated MCP tools."""

import pytest

''' + tool.test_code

        test_file.write_text(content)
        saved.append(test_file)
        logger.info(f"Saved test: {test_file}")

        return saved


def main():
    parser = argparse.ArgumentParser(
        description="Generate MCP tools for bazzite-laptop"
    )
    parser.add_argument("description", nargs="?", help="Tool description")
    parser.add_argument("--name", help="Force tool name (auto-generated if omitted)")
    parser.add_argument("--project-root", default=".", help="Bazzite project root")
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't save")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing tools")
    parser.add_argument("--category", help="Force category (auto-detected if omitted)")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    generator = MCPGenerator(project_root)

    if args.validate_only:
        tools = generator.load_existing_tools()
        print(f"\n{'='*60}")
        print(f"VALIDATED {len(tools)} EXISTING TOOLS")
        print(f"{'='*60}")
        by_category: dict[str, int] = {}
        for t in tools:
            by_category[t.category] = by_category.get(t.category, 0) + 1

        for cat, count in sorted(by_category.items()):
            print(f"  {cat}: {count}")
        return

    if not args.description:
        parser.error("Description required (or use --validate-only)")

    # Generate tool
    tool = generator.generate(args.description, args.name)

    print(f"\n{'='*60}")
    print(f"GENERATED MCP TOOL: {tool.name}")
    print(f"{'='*60}")
    print(f"Category: {tool.category}")
    print(f"Args: {len(tool.args)} parameters")
    for arg in tool.args:
        req = "required" if arg.get("required") else "optional"
        print(f"  - {arg['name']} ({arg['type']}) - {req}")

    print("\n--- YAML ALLOWLIST ENTRY ---")
    print(tool.yaml_entry)

    print("\n--- PYTHON HANDLER ---")
    print(tool.handler_code)

    print("\n--- PYTEST TEST ---")
    print(tool.test_code)

    # Save
    saved = generator.save_tool(tool, args.dry_run)

    if saved:
        print(f"\n✅ Saved to {len(saved)} files")
        for p in saved:
            print(f"  - {p}")
    elif not args.dry_run:
        print("\n⚠️  Failed to save")
        sys.exit(1)

    print("\nNext steps:")
    print("  1. Review the generated handler implementation")
    print("  2. Add actual logic where TODO comments appear")
    print(f"  3. Run: pytest tests/test_generated_tools.py::test_{tool.name} -v")
    print("  4. Restart MCP bridge: systemctl restart bazzite-mcp-bridge")


if __name__ == "__main__":
    main()
