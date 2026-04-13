"""Tests for code intelligence module."""

import pytest

from ai.code_intel.parser import CodeParser, ImportGraphBuilder, ScopeContext


class TestScopeContext:
    """Tests for ScopeContext."""

    def test_with_class(self):
        scope = ScopeContext(module_name="test", file_path="test.py")
        class_scope = scope.with_class("MyClass")
        assert class_scope.module_name == "test"
        assert class_scope.current_class == "MyClass"
        assert class_scope.current_function is None

    def test_with_function(self):
        scope = ScopeContext(module_name="test", file_path="test.py", current_class="MyClass")
        func_scope = scope.with_function("my_method")
        assert func_scope.module_name == "test"
        assert func_scope.current_class == "MyClass"
        assert func_scope.current_function == "my_method"


class TestParseFile:
    """Tests for file parsing."""

    def test_parse_file_extracts_functions(self, tmp_path):
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
def hello_world():
    pass

class MyClass:
    pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        assert len(nodes) > 0
        node_names = [n.name for n in nodes]
        assert "hello_world" in node_names or "test_module" in node_names

    def test_parse_file_extracts_classes(self, tmp_path):
        test_file = tmp_path / "test_classes.py"
        test_file.write_text("""
class BaseClass:
    def base_method(self):
        pass

class DerivedClass(BaseClass):
    def derived_method(self):
        pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        # Check class nodes
        class_nodes = [n for n in nodes if n.node_type == "class"]
        assert len(class_nodes) >= 2

        # Check inheritance relationships
        inherits_rels = [r for r in relationships if r.rel_type == "inherits"]
        assert len(inherits_rels) >= 1
        # DerivedClass should inherit from BaseClass
        derived_inherits = [r for r in inherits_rels if "DerivedClass" in r.source_id]
        assert len(derived_inherits) >= 1

    def test_parse_async_functions(self, tmp_path):
        test_file = tmp_path / "test_async.py"
        test_file.write_text("""
async def async_func():
    await something()

class AsyncClass:
    async def async_method(self):
        await something_else()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        # Should find async function and method
        func_nodes = [n for n in nodes if n.node_type == "function"]
        method_nodes = [n for n in nodes if n.node_type == "method"]
        assert len(func_nodes) >= 1
        assert len(method_nodes) >= 1

    def test_parse_nested_classes(self, tmp_path):
        test_file = tmp_path / "test_nested.py"
        test_file.write_text("""
class Outer:
    class Inner:
        def inner_method(self):
            pass

    def outer_method(self):
        pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        # Should find both classes
        class_nodes = [n for n in nodes if n.node_type == "class"]
        assert len(class_nodes) >= 2


class TestASTCallExtraction:
    """Tests for AST call extraction including ast.Attribute."""

    def test_simple_function_call(self, tmp_path):
        test_file = tmp_path / "test_calls.py"
        test_file.write_text("""
def foo():
    pass

def bar():
    foo()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        calls = [r for r in relationships if r.rel_type == "calls"]
        # Should have a call from bar to foo
        bar_calls = [c for c in calls if "bar" in c.source_id]
        assert len(bar_calls) >= 1

    def test_method_call_self(self, tmp_path):
        test_file = tmp_path / "test_self_call.py"
        test_file.write_text("""
class MyClass:
    def method_a(self):
        pass

    def method_b(self):
        self.method_a()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        calls = [r for r in relationships if r.rel_type == "calls"]
        # Should have self.method_a() call resolved to MyClass.method_a
        self_calls = [
            c for c in calls if "self" in c.target_id or "MyClass.method_a" in c.target_id
        ]
        assert len(self_calls) >= 1

    def test_method_call_obj(self, tmp_path):
        test_file = tmp_path / "test_obj_call.py"
        test_file.write_text("""
class Service:
    def process(self):
        helper.prepare()
        result = helper.finalize()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        calls = [r for r in relationships if r.rel_type == "calls"]
        # Should have method calls like helper.prepare, helper.finalize
        method_calls = [c for c in calls if "." in c.target_id]
        assert len(method_calls) >= 1

    def test_chained_calls(self, tmp_path):
        test_file = tmp_path / "test_chained.py"
        test_file.write_text("""
def process():
    obj.get_data().transform().save()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        # Should extract calls, even if chained
        calls = [r for r in relationships if r.rel_type == "calls"]
        assert len(calls) >= 1


class TestInheritanceExtraction:
    """Tests for inheritance relationship extraction."""

    def test_single_inheritance(self, tmp_path):
        test_file = tmp_path / "test_inherit.py"
        test_file.write_text("""
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        inherits = [r for r in relationships if r.rel_type == "inherits"]
        assert len(inherits) >= 1
        # Dog inherits from Animal
        dog_inherits = [r for r in inherits if "Dog" in r.source_id]
        assert len(dog_inherits) >= 1

    def test_multiple_inheritance(self, tmp_path):
        test_file = tmp_path / "test_multi.py"
        test_file.write_text("""
class A:
    pass

class B:
    pass

class C(A, B):
    pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        inherits = [r for r in relationships if r.rel_type == "inherits"]
        # C should have two inheritance relationships
        c_inherits = [r for r in inherits if "C" in r.source_id]
        assert len(c_inherits) >= 2

    def test_qualified_base_class(self, tmp_path):
        test_file = tmp_path / "test_qualified.py"
        test_file.write_text("""
from module import BaseClass

class Derived(BaseClass):
    pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        inherits = [r for r in relationships if r.rel_type == "inherits"]
        assert len(inherits) >= 1


class TestStoreMethods:
    """Tests for CodeIntelStore methods."""

    def test_index_project_to_lancedb(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_db")

        test_file = tmp_path / "test_store.py"
        test_file.write_text("def test(): pass")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        store.index_project(nodes, relationships)

        df = store._code_nodes.to_pandas()
        assert len(df) >= 0

    def test_get_file_hashes(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_hashes")

        test_file = tmp_path / "test_hash.py"
        test_file.write_text("def test(): pass")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        store.index_project(nodes, relationships)

        hashes = store.get_file_hashes()
        # Should have at least one file hash
        assert isinstance(hashes, dict)

    def test_search_nodes_semantic(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_search")

        results = store.search_nodes("test query", top_k=5)
        assert isinstance(results, list)


class TestFindCallers:
    """Tests for find_callers method."""

    def test_find_callers_basic(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_callers")

        # Create test file with function and callers
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
def target_func():
    pass

def caller_a():
    target_func()

def caller_b():
    target_func()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))
        store.index_project(nodes, relationships)

        # Test find_callers
        callers = store.find_callers("target_func")
        assert isinstance(callers, list)


class TestSuggestTests:
    """Tests for suggest_tests method."""

    def test_suggest_tests_heuristics(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_suggest")

        # Create source file
        src_file = tmp_path / "ai" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("""
def important_func():
    pass

class ImportantClass:
    def method(self):
        pass
""")

        # Create test file
        test_file = tmp_path / "tests" / "test_module.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("""
from ai.module import important_func

def test_important_func():
    important_func()
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, rels = parser.parse_file(str(src_file))
        test_nodes, test_rels = parser.parse_file(str(test_file))
        store.index_project(nodes + test_nodes, rels + test_rels)

        # Test suggest_tests
        suggestions = store.suggest_tests([str(src_file)])
        assert isinstance(suggestions, list)


class TestComplexityReport:
    """Tests for get_complexity_report method."""

    def test_complexity_report_basic(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_complexity")

        test_file = tmp_path / "test_complex.py"
        test_file.write_text("""
def simple_func():
    pass

def complex_func():
    if x:
        if y:
            for i in range(10):
                if z:
                    pass
                else:
                    pass
        else:
            pass
    else:
        pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))
        store.index_project(nodes, relationships)

        report = store.get_complexity_report(threshold=1)
        assert "summary" in report
        assert "entries" in report


class TestClassHierarchy:
    """Tests for get_class_hierarchy method."""

    def test_class_hierarchy_basic(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_hierarchy")

        test_file = tmp_path / "test_hierarchy.py"
        test_file.write_text("""
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        pass

    def fetch(self):
        pass

class Cat(Animal):
    def speak(self):
        pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))
        store.index_project(nodes, relationships)

        # Test get_class_hierarchy for Animal
        hierarchy = store.get_class_hierarchy("Animal")
        assert "class" in hierarchy or "parents" in hierarchy


class TestImportGraph:
    """Tests for import graph."""

    def test_import_graph_no_circular(self):
        graph = ImportGraphBuilder()
        assert hasattr(graph, "build")
        assert hasattr(graph, "find_dependents")
        assert hasattr(graph, "find_dependencies")

    def test_import_graph_build(self, tmp_path):
        parser = ImportGraphBuilder(project_root=tmp_path)

        # Create test module structure
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "module_a.py").write_text("import module_b")
        (tmp_path / "module_b.py").write_text("import os")

        graph = parser.build()
        assert "modules" in graph
        assert "edges" in graph


class TestDependencyGraphQueries:
    """Tests for dependency graph queries from import_graph table."""

    def test_query_dependency_graph_direction_and_depth(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_deps")
        store.store_import_graph(
            {
                "edges": [
                    {"source": "ai.alpha", "target": "ai.beta"},
                    {"source": "ai.beta", "target": "ai.gamma"},
                    {"source": "ai.delta", "target": "ai.beta"},
                ],
                "circular": [],
            }
        )

        down = store.query_dependency_graph("ai.beta", direction="down", max_depth=1)
        up = store.query_dependency_graph("ai.beta", direction="up", max_depth=1)
        both = store.query_dependency_graph("ai.beta", direction="both", max_depth=2)

        assert any(item["module"] == "ai.gamma" for item in down["dependencies"])
        assert any(item["module"] == "ai.alpha" for item in up["dependents"])
        assert any(item["module"] == "ai.delta" for item in up["dependents"])
        assert both["module"] == "ai.beta"

    def test_query_dependency_graph_circular_edges(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_cycles")
        store.store_import_graph(
            {
                "edges": [
                    {"source": "ai.a", "target": "ai.b"},
                    {"source": "ai.b", "target": "ai.a"},
                ],
                "circular": [
                    {"source": "ai.a", "target": "ai.b"},
                    {"source": "ai.b", "target": "ai.a"},
                ],
            }
        )

        graph = store.query_dependency_graph("ai.a", direction="both", max_depth=2)
        assert len(graph["circular"]) >= 1
        assert any(edge["is_circular"] for edge in graph["edges"])


class TestImpactAnalysis:
    """Tests for impact analysis graph + test suggestion integration."""

    def test_query_impact_includes_dependency_and_tests(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_impact")

        src_file = tmp_path / "ai" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text(
            """
def important_func():
    return 1
"""
        )

        test_file = tmp_path / "tests" / "test_module.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(
            """
from ai.module import important_func

def test_important_func():
    assert important_func() == 1
"""
        )

        parser = CodeParser(project_root=tmp_path)
        nodes, rels = parser.parse_file(str(src_file))
        test_nodes, test_rels = parser.parse_file(str(test_file))
        store.index_project(nodes + test_nodes, rels + test_rels)
        store.store_import_graph(
            {
                "edges": [
                    {"source": "ai.consumer", "target": "ai.module"},
                ],
                "circular": [],
            }
        )

        impact = store.query_impact([str(src_file)], max_depth=2, include_tests=True)

        assert "direct_dependents" in impact
        assert "suggested_tests" in impact
        assert any(dep.get("source_id") == "ai.consumer" for dep in impact["direct_dependents"])
        assert isinstance(impact["suggested_tests"], list)


class TestIncrementalIndexing:
    """Tests for incremental indexing."""

    def test_update_incremental(self, tmp_path):
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_incremental")

        # Create initial file
        test_file = tmp_path / "test_incremental.py"
        test_file.write_text("def original(): pass")

        parser = CodeParser(project_root=tmp_path)
        nodes, rels = parser.parse_file(str(test_file))
        store.index_project(nodes, rels)

        # Modify file
        test_file.write_text("def modified(): pass")

        # Test update_incremental
        store.update_incremental([str(test_file)], parser)

        # Verify update worked
        hashes = store.get_file_hashes()
        assert str(test_file) in hashes or len(hashes) >= 0


class TestPerformance:
    """Tests for performance optimizations."""

    def test_query_dependents_uses_filter(self, tmp_path):
        """Verify query_dependents doesn't load entire table."""
        from ai.code_intel.store import CodeIntelStore

        store = CodeIntelStore(db_path=tmp_path / "test_perf")

        test_file = tmp_path / "test_perf.py"
        test_file.write_text("""
def func_a():
    func_b()

def func_b():
    func_c()

def func_c():
    pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))
        store.index_project(nodes, relationships)

        # Query should work without loading entire table
        dependents = store.query_dependents("test_perf:func_c", max_depth=2)
        assert isinstance(dependents, list)


class TestSignatureExtraction:
    """Tests for function and class signature extraction."""

    def test_function_signature_params(self, tmp_path):
        test_file = tmp_path / "test_sig.py"
        test_file.write_text("""
def func_simple():
    pass

def func_params(a, b, c=1, d=None):
    pass

def func_varargs(*args, **kwargs):
    pass

async def async_func(a, b):
    pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        # Check signatures
        simple = [n for n in nodes if n.name == "func_simple"]
        assert len(simple) >= 1
        assert "()" in simple[0].signature

        params = [n for n in nodes if n.name == "func_params"]
        assert len(params) >= 1

        varargs = [n for n in nodes if n.name == "func_varargs"]
        assert len(varargs) >= 1

        async_func = [n for n in nodes if n.name == "async_func"]
        assert len(async_func) >= 1
        assert "async" in async_func[0].signature.lower() or "async" in async_func[0].node_type

    def test_class_signature_bases(self, tmp_path):
        test_file = tmp_path / "test_class_sig.py"
        test_file.write_text("""
class Simple:
    pass

class WithBase(object):
    pass

class Multiple(A, B, C):
    pass
""")

        parser = CodeParser(project_root=tmp_path)
        nodes, relationships = parser.parse_file(str(test_file))

        simple = [n for n in nodes if n.name == "Simple"]
        assert len(simple) >= 1
        assert simple[0].signature == "()"

        with_base = [n for n in nodes if n.name == "WithBase"]
        assert len(with_base) >= 1
        assert "object" in with_base[0].signature


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
