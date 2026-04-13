"""Impact analysis tests."""

import json
from datetime import UTC, datetime, timedelta

from ai.code_intel.parser import CodeParser
from ai.code_intel.store import CodeIntelStore


def _seed_codebase(tmp_path):
    src_file = tmp_path / "ai" / "module.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text(
        """
def target():
    return 1

def caller():
    return target()
"""
    )

    test_file = tmp_path / "tests" / "test_module.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        """
from ai.module import target

def test_target():
    assert target() == 1
"""
    )

    parser = CodeParser(project_root=tmp_path)
    nodes_a, rels_a = parser.parse_file(str(src_file))
    nodes_b, rels_b = parser.parse_file(str(test_file))
    return src_file, test_file, nodes_a + nodes_b, rels_a + rels_b


def test_co_change_analysis_respects_window(tmp_path):
    store = CodeIntelStore(db_path=tmp_path / "impact_db")
    now = datetime.now(tz=UTC)
    old = now - timedelta(days=120)

    store._change_history.add(
        [
            {
                "commit_hash": "new-1",
                "file_path": "ai/module.py,tests/test_module.py",
                "functions_changed": "[]",
                "co_changed_files": json.dumps(["ai/module.py", "tests/test_module.py"]),
                "timestamp": now.isoformat(),
                "vector": [0.0] * 768,
            },
            {
                "commit_hash": "old-1",
                "file_path": "ai/module.py,docs/readme.md",
                "functions_changed": "[]",
                "co_changed_files": json.dumps(["ai/module.py", "docs/readme.md"]),
                "timestamp": old.isoformat(),
                "vector": [0.0] * 768,
            },
        ]
    )

    result = store._analyze_co_changes(["ai/module.py"], window_days=90)
    files = [item["file"] for item in result["files"]]
    assert "tests/test_module.py" in files
    assert "docs/readme.md" not in files


def test_query_impact_returns_weighted_score(tmp_path):
    store = CodeIntelStore(db_path=tmp_path / "impact_db_score")
    src_file, _test_file, nodes, rels = _seed_codebase(tmp_path)
    store.index_project(nodes, rels)
    store.store_import_graph(
        {
            "edges": [{"source": "ai.consumer", "target": "ai.module"}],
            "circular": [],
        }
    )

    impact = store.query_impact([str(src_file)], max_depth=2, include_tests=True)
    assert "impact_score" in impact
    assert impact["impact_score"]["score"] >= 0.0
    assert impact["impact_score"]["confidence"] >= 0.0
    assert "signals" in impact["impact_score"]


def test_query_impact_contains_blast_radius(tmp_path):
    store = CodeIntelStore(db_path=tmp_path / "impact_db_blast")
    src_file, _test_file, nodes, rels = _seed_codebase(tmp_path)
    store.index_project(nodes, rels)
    store.store_import_graph(
        {
            "edges": [{"source": "ai.consumer", "target": "ai.module"}],
            "circular": [],
        }
    )

    impact = store.query_impact([str(src_file)], max_depth=2, include_tests=False)
    assert "blast_radius" in impact
    assert "modules" in impact["blast_radius"]


def test_query_impact_suggested_tests_toggle(tmp_path):
    store = CodeIntelStore(db_path=tmp_path / "impact_db_tests")
    src_file, _test_file, nodes, rels = _seed_codebase(tmp_path)
    store.index_project(nodes, rels)

    with_tests = store.query_impact([str(src_file)], max_depth=2, include_tests=True)
    without_tests = store.query_impact([str(src_file)], max_depth=2, include_tests=False)

    assert isinstance(with_tests["suggested_tests"], list)
    assert without_tests["suggested_tests"] == []


def test_blast_radius_structural_symbols(tmp_path):
    store = CodeIntelStore(db_path=tmp_path / "impact_db_struct")
    src_file, _test_file, nodes, rels = _seed_codebase(tmp_path)
    store.index_project(nodes, rels)

    result = store.query_blast_radius([str(src_file)], max_depth=3)
    assert "symbols" in result
    assert isinstance(result["symbols"], list)
