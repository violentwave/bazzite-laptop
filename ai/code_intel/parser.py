"""Code intelligence parser using AST and import graph analysis."""

import ast
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("ai.code_intel")


@dataclass
class CodeNode:
    """Represents a code element (module, class, function, method)."""

    node_id: str
    node_type: str  # module, class, function, method
    name: str
    qualified_name: str
    file_path: str
    line_start: int
    line_end: int
    signature: str
    docstring: str
    complexity: int
    file_hash: str


@dataclass
class Relationship:
    """Represents a relationship between code elements."""

    source_id: str
    target_id: str
    rel_type: str  # calls, imports, inherits, overrides
    file_path: str
    line_number: int


@dataclass
class ScopeContext:
    """Tracks lexical scope during AST traversal."""

    module_name: str
    file_path: str
    current_class: str | None = None
    current_function: str | None = None

    def with_class(self, class_name: str) -> "ScopeContext":
        """Create a new context with class scope."""
        return ScopeContext(
            module_name=self.module_name,
            file_path=self.file_path,
            current_class=class_name,
            current_function=None,
        )

    def with_function(self, func_name: str) -> "ScopeContext":
        """Create a new context with function scope."""
        return ScopeContext(
            module_name=self.module_name,
            file_path=self.file_path,
            current_class=self.current_class,
            current_function=func_name,
        )


class CodeParser:
    """Parse Python files to extract code elements and relationships."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path("/var/home/lch/projects/bazzite-laptop/ai")

    def get_file_hash(self, file_path: str) -> str:
        """Return SHA-256 hash of file contents."""
        path = Path(file_path)
        if not path.exists():
            return ""
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def parse_file(self, file_path: str) -> tuple[list[CodeNode], list[Relationship]]:
        """Parse a Python file and extract nodes and relationships."""
        path = Path(file_path)
        if not path.exists() or path.suffix != ".py":
            return [], []

        try:
            content = path.read_text()
            tree = ast.parse(content, filename=str(path))
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}")
            return [], []

        nodes: list[CodeNode] = []
        relationships: list[Relationship] = []
        file_hash = self.get_file_hash(str(path))

        module_name = path.stem
        if path.parent.name != "ai":
            module_name = f"{path.parent.name}.{module_name}"

        nodes.append(
            CodeNode(
                node_id=module_name,
                node_type="module",
                name=path.stem,
                qualified_name=module_name,
                file_path=str(path),
                line_start=1,
                line_end=len(content.splitlines()),
                signature="",
                docstring=ast.get_docstring(tree) or "",
                complexity=0,
                file_hash=file_hash,
            )
        )

        scope = ScopeContext(module_name=module_name, file_path=str(path))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._process_class(node, scope, nodes, relationships, file_hash)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(node, scope, nodes, relationships, file_hash)

        self._extract_imports(tree, module_name, str(path), relationships)

        return nodes, relationships

    def _process_class(
        self,
        node: ast.ClassDef,
        scope: ScopeContext,
        nodes: list[CodeNode],
        relationships: list[Relationship],
        file_hash: str,
    ) -> None:
        """Process a class definition and its members."""
        qualified_name = f"{scope.module_name}:{node.name}"
        docstring = ast.get_docstring(node) or ""
        complexity = self._get_complexity(node)

        nodes.append(
            CodeNode(
                node_id=qualified_name,
                node_type="class",
                name=node.name,
                qualified_name=qualified_name,
                file_path=scope.file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                signature=self._get_class_signature(node),
                docstring=docstring,
                complexity=complexity,
                file_hash=file_hash,
            )
        )

        # Extract inheritance relationships
        for base in node.bases:
            base_name = self._resolve_base_name(base)
            if base_name:
                relationships.append(
                    Relationship(
                        source_id=qualified_name,
                        target_id=base_name,
                        rel_type="inherits",
                        file_path=scope.file_path,
                        line_number=node.lineno,
                    )
                )

        class_scope = scope.with_class(node.name)

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(item, class_scope, nodes, relationships, file_hash)
            elif isinstance(item, ast.ClassDef):
                # Nested class
                self._process_class(item, class_scope, nodes, relationships, file_hash)

    def _process_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        scope: ScopeContext,
        nodes: list[CodeNode],
        relationships: list[Relationship],
        file_hash: str,
    ) -> None:
        """Process a function or method definition."""
        if scope.current_class:
            qualified_name = f"{scope.module_name}:{scope.current_class}.{node.name}"
            node_type = "method"
        else:
            qualified_name = f"{scope.module_name}:{node.name}"
            node_type = "function"

        docstring = ast.get_docstring(node) or ""
        complexity = self._get_complexity(node)

        nodes.append(
            CodeNode(
                node_id=qualified_name,
                node_type=node_type,
                name=node.name,
                qualified_name=qualified_name,
                file_path=scope.file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                signature=self._get_function_signature(node),
                docstring=docstring,
                complexity=complexity,
                file_hash=file_hash,
            )
        )

        self._extract_calls(node, qualified_name, scope, relationships)

    def _resolve_base_name(self, base: ast.expr) -> str | None:
        """Resolve a base class name from an AST expression."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            # Handle cases like `module.ClassName`
            parts = []
            current: ast.expr = base
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            parts.reverse()
            return ".".join(parts)
        elif isinstance(base, ast.Subscript):
            # Handle generic base classes like `Generic[T]`
            return self._resolve_base_name(base.value)
        return None

    def _get_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Extract function signature."""
        args = node.args
        arg_names = [arg.arg for arg in args.args]
        if args.vararg:
            arg_names.append(f"*{args.vararg.arg}")
        if args.kwarg:
            arg_names.append(f"**{args.kwarg.arg}")
        defaults = ["..."] * (len(args.args) - len(args.defaults))
        defaults.extend([ast.unparse(d) for d in args.defaults])
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{prefix}({', '.join(arg_names)})"

    def _get_class_signature(self, node: ast.ClassDef) -> str:
        """Extract class signature."""
        bases = [ast.unparse(b) for b in node.bases]
        return f"({', '.join(bases)})" if bases else "()"

    def _get_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity using radon if available."""
        try:
            from radon.visitors import ComplexityVisitor

            visitor = ComplexityVisitor()
            visitor.visit(node)
            return visitor.complexity
        except Exception:
            return 1

    def _extract_calls(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_id: str,
        scope: ScopeContext,
        relationships: list[Relationship],
    ) -> None:
        """Extract function call relationships with scope awareness.

        Handles:
        - Simple function calls: `func()`
        - Method calls: `obj.method()`
        - Self method calls: `self.method()`
        - Module function calls: `module.func()`
        - Chained calls: `obj.attr.method()`
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                target_id = self._resolve_call_target(child, scope)
                if target_id:
                    relationships.append(
                        Relationship(
                            source_id=source_id,
                            target_id=target_id,
                            rel_type="calls",
                            file_path=scope.file_path,
                            line_number=child.lineno or 0,
                        )
                    )

    def _resolve_call_target(self, call_node: ast.Call, scope: ScopeContext) -> str | None:
        """Resolve a call expression to a qualified target ID.

        Returns fully-qualified targets like:
        - `module:function` for top-level functions
        - `module:Class.method` for methods
        - `module.Class.method` for module-level function calls
        """
        func = call_node.func

        if isinstance(func, ast.Name):
            # Simple function call: `func()`
            # Target might be module-level or imported
            return f"{scope.module_name}:{func.id}"

        elif isinstance(func, ast.Attribute):
            # Method or attribute call: `obj.method()` or `module.func()`
            target_parts = self._extract_attribute_chain(func)

            if not target_parts:
                return None

            # Handle `self.method()` - resolve to current class
            if scope.current_class and target_parts[0] == "self":
                if len(target_parts) >= 2:
                    method_name = target_parts[1]
                    return f"{scope.module_name}:{scope.current_class}.{method_name}"
                return None

            # Handle `cls.method()` - resolve to current class (class method)
            if scope.current_class and target_parts[0] == "cls":
                if len(target_parts) >= 2:
                    method_name = target_parts[1]
                    return f"{scope.module_name}:{scope.current_class}.{method_name}"
                return None

            # Handle `obj.method()` where obj is a local variable or parameter
            # We can't resolve this statically, but we can still record the method name
            if len(target_parts) >= 2:
                # Record as `obj.method` - callers can resolve via semantic search
                # This preserves the method call relationship even if we don't know the class
                return ".".join(target_parts[-2:])  # Last two parts: obj.method

            # Single attribute access - not a call we can resolve
            return None

        return None

    def _extract_attribute_chain(self, node: ast.Attribute) -> list[str]:
        """Extract the full attribute chain from nested ast.Attribute nodes.

        Example: `self.foo.bar` -> ['self', 'foo', 'bar']
        Example: `module.func` -> ['module', 'func']
        """
        parts: list[str] = []

        def traverse(n: ast.expr) -> None:
            if isinstance(n, ast.Attribute):
                parts.append(n.attr)
                traverse(n.value)
            elif isinstance(n, ast.Name):
                parts.append(n.id)

        traverse(node)
        parts.reverse()
        return parts

    def _extract_imports(
        self, tree: ast.AST, module_name: str, file_path: str, relationships: list[Relationship]
    ) -> None:
        """Extract import relationships."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    relationships.append(
                        Relationship(
                            source_id=module_name,
                            target_id=alias.name,
                            rel_type="imports",
                            file_path=file_path,
                            line_number=node.lineno or 0,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    target = f"{module}.{alias.name}" if module else alias.name
                    relationships.append(
                        Relationship(
                            source_id=module_name,
                            target_id=target,
                            rel_type="imports",
                            file_path=file_path,
                            line_number=node.lineno or 0,
                        )
                    )

    def parse_project(self) -> tuple[list[CodeNode], list[Relationship]]:
        """Parse all Python files in the project."""
        all_nodes: list[CodeNode] = []
        all_relationships: list[Relationship] = []

        for py_file in self.project_root.rglob("*.py"):
            if any(
                skip in str(py_file) for skip in ["__pycache__", ".venv", "node_modules", ".git"]
            ):
                continue

            nodes, relationships = self.parse_file(str(py_file))
            all_nodes.extend(nodes)
            all_relationships.extend(relationships)

        return all_nodes, all_relationships


class ImportGraphBuilder:
    """Build import graph using grimp."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path("/var/home/lch/projects/bazzite-laptop/ai")

    def build(self) -> dict:
        """Build import graph for the project."""
        try:
            import grimp

            package_name = self.project_root.name
            graph = grimp.build_graph(package_name)
            edges = []
            for importer in graph.modules:
                for imported in graph.find_modules_directly_imported_by(importer):
                    edges.append(
                        {
                            "source": importer,
                            "target": imported,
                            "import_type": "grimp",
                        }
                    )

            circular_edges = self._detect_circular_edges(edges)
            circular = [
                {"source": source, "target": target} for source, target in sorted(circular_edges)
            ]

            return {
                "modules": list(graph.modules),
                "edges": edges,
                "circular": circular,
            }
        except Exception as e:
            logger.warning(f"grimp unavailable or failed ({e}), using AST-based fallback")
            return self._ast_build()

    def _ast_build(self) -> dict:
        """Fallback AST-based import extraction."""
        nodes = []
        edges = []

        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".venv"]):
                continue

            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                module_name = self._module_name_from_path(py_file)

                nodes.append(module_name)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            edges.append(
                                {
                                    "source": module_name,
                                    "target": alias.name,
                                    "import_type": "ast-import",
                                }
                            )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            edges.append(
                                {
                                    "source": module_name,
                                    "target": node.module,
                                    "import_type": "ast-from",
                                }
                            )
            except Exception:
                continue

        circular_edges = self._detect_circular_edges(edges)
        circular = [
            {"source": source, "target": target} for source, target in sorted(circular_edges)
        ]
        return {"modules": sorted(set(nodes)), "edges": edges, "circular": circular}

    def _module_name_from_path(self, py_file: Path) -> str:
        """Map a Python file path to a dotted module name."""
        rel = py_file.relative_to(self.project_root)
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")

        if not parts:
            return self.project_root.name

        return f"{self.project_root.name}." + ".".join(parts)

    def _detect_circular_edges(self, edges: list[dict]) -> set[tuple[str, str]]:
        """Return edges that participate in at least one cycle."""
        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if not source or not target:
                continue
            adjacency.setdefault(source, set()).add(target)

        def has_path(start: str, end: str) -> bool:
            if start == end:
                return True
            stack = [start]
            visited = set()
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                for nxt in adjacency.get(node, set()):
                    if nxt == end:
                        return True
                    if nxt not in visited:
                        stack.append(nxt)
            return False

        circular_edges: set[tuple[str, str]] = set()
        for source, targets in adjacency.items():
            for target in targets:
                if has_path(target, source):
                    circular_edges.add((source, target))

        return circular_edges

    def find_dependents(self, module: str, max_depth: int = 3) -> list[str]:
        """Find modules that depend on the given module."""
        graph = self.build()
        dependents = set()
        visited = set()

        def traverse(target: str, depth: int) -> None:
            if depth > max_depth or target in visited:
                return
            visited.add(target)

            for edge in graph.get("edges", []):
                if edge.get("target") == target:
                    source = edge.get("source")
                    if source:
                        dependents.add(source)
                        traverse(source, depth + 1)

        traverse(module, 0)
        return list(dependents)

    def find_dependencies(self, module: str, max_depth: int = 3) -> list[str]:
        """Find modules that the given module depends on."""
        graph = self.build()
        dependencies = set()
        visited = set()

        def traverse(target: str, depth: int) -> None:
            if depth > max_depth or target in visited:
                return
            visited.add(target)

            for edge in graph.get("edges", []):
                if edge.get("source") == target:
                    dep = edge.get("target")
                    if dep:
                        dependencies.add(dep)
                        traverse(dep, depth + 1)

        traverse(module, 0)
        return list(dependencies)
