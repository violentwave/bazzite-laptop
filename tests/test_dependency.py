"""Dependency graph and blast radius tests."""

from ai.code_intel.store import CodeIntelStore


def _build_store(tmp_path):
    store = CodeIntelStore(db_path=tmp_path / "dep_db")
    store.store_import_graph(
        {
            "edges": [
                {"source": "ai.alpha", "target": "ai.beta"},
                {"source": "ai.beta", "target": "ai.gamma"},
                {"source": "ai.delta", "target": "ai.beta"},
                {"source": "ai.epsilon", "target": "ai.delta"},
            ],
            "circular": [],
        }
    )
    return store


def test_dependency_graph_downstream(tmp_path):
    store = _build_store(tmp_path)
    result = store.query_dependency_graph("ai.beta", direction="down", max_depth=2)
    modules = {item["module"] for item in result["dependencies"]}
    assert "ai.gamma" in modules


def test_dependency_graph_upstream(tmp_path):
    store = _build_store(tmp_path)
    result = store.query_dependency_graph("ai.beta", direction="up", max_depth=1)
    modules = {item["module"] for item in result["dependents"]}
    assert modules == {"ai.alpha", "ai.delta"}


def test_dependency_graph_depth_limit(tmp_path):
    store = _build_store(tmp_path)
    result = store.query_dependency_graph("ai.beta", direction="up", max_depth=2)
    by_depth = {item["module"]: item["depth"] for item in result["dependents"]}
    assert by_depth["ai.epsilon"] == 2


def test_dependency_graph_unknown_module(tmp_path):
    store = _build_store(tmp_path)
    result = store.query_dependency_graph("ai.unknown", direction="both", max_depth=2)
    assert result["dependencies"] == []
    assert result["dependents"] == []


def test_blast_radius_contains_module_impacts(tmp_path):
    store = _build_store(tmp_path)
    changed = [str(tmp_path / "ai" / "beta.py")]
    result = store.query_blast_radius(changed, max_depth=3)
    modules = {item["module"] for item in result["modules"]}
    assert "ai.alpha" in modules
    assert "ai.delta" in modules


def test_blast_radius_hop_depths(tmp_path):
    store = _build_store(tmp_path)
    changed = [str(tmp_path / "ai" / "beta.py")]
    result = store.query_blast_radius(changed, max_depth=3)
    depth_map = {item["module"]: item["depth"] for item in result["modules"]}
    assert depth_map["ai.epsilon"] == 2
