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

        nodes = []
        relationships = []
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

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                qualified_name = f"{module_name}:{node.name}"
                docstring = ast.get_docstring(node) or ""
                complexity = self._get_complexity(node)

                nodes.append(
                    CodeNode(
                        node_id=qualified_name,
                        node_type="class",
                        name=node.name,
                        qualified_name=qualified_name,
                        file_path=str(path),
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=self._get_class_signature(node),
                        docstring=docstring,
                        complexity=complexity,
                        file_hash=file_hash,
                    )
                )

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_qualified = f"{module_name}:{node.name}.{item.name}"
                        method_doc = ast.get_docstring(item) or ""
                        method_complexity = self._get_complexity(item)

                        nodes.append(
                            CodeNode(
                                node_id=method_qualified,
                                node_type="method",
                                name=item.name,
                                qualified_name=method_qualified,
                                file_path=str(path),
                                line_start=item.lineno,
                                line_end=item.end_lineno or item.lineno,
                                signature=self._get_function_signature(item),
                                docstring=method_doc,
                                complexity=method_complexity,
                                file_hash=file_hash,
                            )
                        )

                        self._extract_calls(
                            item, method_qualified, module_name, str(path), relationships
                        )

            elif isinstance(node, ast.FunctionDef):
                func_qualified = f"{module_name}:{node.name}"
                func_doc = ast.get_docstring(node) or ""
                func_complexity = self._get_complexity(node)

                nodes.append(
                    CodeNode(
                        node_id=func_qualified,
                        node_type="function",
                        name=node.name,
                        qualified_name=func_qualified,
                        file_path=str(path),
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=self._get_function_signature(node),
                        docstring=func_doc,
                        complexity=func_complexity,
                        file_hash=file_hash,
                    )
                )

                self._extract_calls(node, func_qualified, module_name, str(path), relationships)

        self._extract_imports(tree, module_name, str(path), relationships)

        return nodes, relationships

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature."""
        args = node.args
        arg_names = [arg.arg for arg in args.args]
        if args.vararg:
            arg_names.append(f"*{args.vararg.arg}")
        if args.kwarg:
            arg_names.append(f"**{args.kwarg.arg}")
        defaults = ["..."] * (len(args.args) - len(args.defaults))
        defaults.extend([ast.unparse(d) for d in args.defaults])
        return f"({', '.join(arg_names)})"

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
        node: ast.FunctionDef,
        source_id: str,
        module_name: str,
        file_path: str,
        relationships: list[Relationship],
    ) -> None:
        """Extract function call relationships."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    target = f"{module_name}:{child.func.id}"
                    relationships.append(
                        Relationship(
                            source_id=source_id,
                            target_id=target,
                            rel_type="calls",
                            file_path=file_path,
                            line_number=child.lineno or 0,
                        )
                    )

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
        all_nodes = []
        all_relationships = []

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

            graph = grimp.build_graph(str(self.project_root))
            edges = []
            for module, importers in graph.imports.items():
                for importer in importers:
                    edges.append(
                        {
                            "source": importer,
                            "target": module,
                        }
                    )

            return {
                "modules": list(graph.modules),
                "edges": edges,
                "circular": [],  # grimp doesn't expose circular directly
            }
        except ImportError:
            logger.warning("grimp not available, using AST-based fallback")
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

                module_name = py_file.stem
                if py_file.parent.name != "ai":
                    module_name = f"{py_file.parent.name}.{module_name}"

                nodes.append(module_name)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            edges.append(
                                {
                                    "source": module_name,
                                    "target": alias.name.split(".")[0],
                                }
                            )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            edges.append(
                                {
                                    "source": module_name,
                                    "target": node.module.split(".")[0],
                                }
                            )
            except Exception:
                continue

        return {"modules": nodes, "edges": edges, "circular": []}

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
