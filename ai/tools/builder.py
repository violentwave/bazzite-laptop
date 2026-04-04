"""Dynamic tool builder with safety validation."""

import ast
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed

logger = logging.getLogger("ai.tools")

FORBIDDEN_PATTERNS = {
    "modules": ["os", "subprocess", "sys", "shutil", "socket", "http", "urllib", " pathlib"],
    "functions": ["exec", "eval", "compile", "__import__", "open"],
    "attributes": ["__builtins__", "__class__", "__subclasses__"],
}

SAFE_BUILTINS = {
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "tuple",
    "set",
    "len",
    "range",
    "enumerate",
    "zip",
    "map",
    "filter",
    "sorted",
    "reversed",
    "min",
    "max",
    "sum",
    "abs",
    "round",
    "isinstance",
    "issubclass",
    "hasattr",
    "getattr",
    "json",
    "print",
    "type",
    "any",
    "all",
    "ord",
    "chr",
    "bin",
    "hex",
}


class SafetyValidator(ast.NodeVisitor):
    """AST-based safety validator for dynamic code."""

    def __init__(self):
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if any(forbidden in alias.name for forbidden in FORBIDDEN_PATTERNS["modules"]):
                self.violations.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and any(
            forbidden in node.module for forbidden in FORBIDDEN_PATTERNS["modules"]
        ):
            self.violations.append(f"Forbidden import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_PATTERNS["functions"]:
                self.violations.append(f"Forbidden call: {node.func.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__") and node.attr.endswith("__"):
            self.violations.append(f"Dunder access: {node.attr}")
        self.generic_visit(node)

    def validate(self, code: str) -> tuple[bool, list[str]]:
        """Validate code for safety."""
        try:
            tree = ast.parse(code)
            self.violations = []
            self.visit(tree)
            return len(self.violations) == 0, self.violations
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]


class ToolBuilder:
    """Build and persist dynamic tools with safety checks."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize persisted_tools table."""
        schema = pa.schema(
            [
                pa.field("tool_id", pa.string()),
                pa.field("name", pa.string()),
                pa.field("description", pa.string()),
                pa.field("parameters", pa.string()),  # JSON Schema
                pa.field("code", pa.string()),
                pa.field("version", pa.int32()),
                pa.field("created_at", pa.string()),
                pa.field("created_by", pa.string()),
                pa.field("is_active", pa.bool_()),
                pa.field("code_hash", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ]
        )

        table_names = self._db.list_tables()
        if "persisted_tools" in table_names:
            self._table = self._db.open_table("persisted_tools")
        else:
            self._table = self._db.create_table("persisted_tools", schema=schema)

    def create_tool(
        self,
        name: str,
        description: str,
        handler_code: str,
        parameters: dict | None = None,
        created_by: str = "system",
    ) -> dict:
        """Create and persist a dynamic tool."""
        validator = SafetyValidator()
        is_safe, violations = validator.validate(handler_code)

        if not is_safe:
            raise ValueError(f"Unsafe code: {violations}")

        code_hash = hashlib.sha256(handler_code.encode()).hexdigest()

        try:
            exec_globals = {"__builtins__": SAFE_BUILTINS}
            exec(handler_code, exec_globals)

            func = None
            for obj in exec_globals.values():
                if callable(obj) and not isinstance(obj, type):
                    func = obj
                    break

            if func is None:
                raise ValueError("No callable function found in code")
        except Exception as e:
            raise ValueError(f"Code execution failed: {e}")

        tool_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()

        try:
            vector = embed(f"{name} {description}")
        except Exception:
            vector = [0.0] * 768

        self._table.add(
            [
                {
                    "tool_id": tool_id,
                    "name": name,
                    "description": description,
                    "parameters": json.dumps(parameters) if parameters else "{}",
                    "code": handler_code,
                    "version": 1,
                    "created_at": timestamp,
                    "created_by": created_by,
                    "is_active": True,
                    "code_hash": code_hash,
                    "vector": vector,
                }
            ]
        )

        return {"status": "created", "tool_name": name, "version": 1}

    def register_tool(self, name: str, mcp_server) -> None:
        """Register tool with MCP server."""
        df = self._table.to_pandas()
        row = df[df["name"] == name]
        if row.empty:
            raise ValueError(f"Tool {name} not found")

        row = row.iloc[0]
        handler_code = row["code"]

        exec_globals = {"__builtins__": SAFE_BUILTINS}
        exec(handler_code, exec_globals)

        func = None
        for obj in exec_globals.values():
            if callable(obj) and not isinstance(obj, type):
                func = obj
                break

        if func and hasattr(mcp_server, "add_tool"):
            mcp_server.add_tool(name=name, function=func, description=row["description"])

    def load_all_persisted(self, mcp_server) -> None:
        """Load all active persisted tools."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return

            for _, row in df.iterrows():
                if row["is_active"]:
                    try:
                        self.register_tool(row["name"], mcp_server)
                    except Exception as e:
                        logger.warning(f"Failed to register {row['name']}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load persisted tools: {e}")

    def update_tool(self, name: str, handler_code: str, description: str | None = None) -> dict:
        """Update an existing tool."""
        validator = SafetyValidator()
        is_safe, violations = validator.validate(handler_code)

        if not is_safe:
            raise ValueError(f"Unsafe code: {violations}")

        df = self._table.to_pandas()
        row = df[df["name"] == name]
        if row.empty:
            raise ValueError(f"Tool {name} not found")

        old_row = row.iloc[0]
        new_version = old_row["version"] + 1
        code_hash = hashlib.sha256(handler_code.encode()).hexdigest()

        self._table.update(
            f"name = '{name}'",
            {
                "code": handler_code,
                "version": new_version,
                "code_hash": code_hash,
                "description": description or old_row["description"],
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

        return {"status": "updated", "tool_name": name, "version": new_version}

    def deactivate_tool(self, name: str) -> None:
        """Deactivate a tool."""
        try:
            self._table.update(f"name = '{name}'", {"is_active": False})
        except Exception as e:
            logger.warning(f"Failed to deactivate tool: {e}")

    def list_dynamic_tools(self) -> list[dict]:
        """List all persisted tools."""
        try:
            df = self._table.to_pandas()
            if df.empty:
                return []

            results = []
            for _, row in df.iterrows():
                results.append(
                    {
                        "tool_id": row["tool_id"],
                        "name": row["name"],
                        "description": row["description"],
                        "version": row["version"],
                        "created_at": row["created_at"],
                        "created_by": row["created_by"],
                        "is_active": row["is_active"],
                    }
                )

            return results
        except Exception as e:
            logger.warning(f"Failed to list tools: {e}")
            return []


_builder_instance: ToolBuilder | None = None


def get_builder() -> ToolBuilder:
    """Get singleton ToolBuilder."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = ToolBuilder()
    return _builder_instance
