"""Tests for P74 code intelligence fusion layer."""

from unittest.mock import MagicMock, patch


def test_module_from_relative_path_handles_init():
    from ai.rag.code_query import _module_from_relative_path

    assert _module_from_relative_path("ai/mcp_bridge/__init__.py") == "ai.mcp_bridge"
    assert _module_from_relative_path("ai/router.py") == "ai.router"


def test_stable_chunk_id_is_deterministic():
    from ai.rag.code_query import _stable_chunk_id

    a = _stable_chunk_id("ai/router.py", "route_query", 10, 20)
    b = _stable_chunk_id("ai/router.py", "route_query", 10, 20)
    c = _stable_chunk_id("ai/router.py", "other", 10, 20)

    assert a == b
    assert a != c


def test_code_fused_context_enriches_semantic_hits():
    fake_semantic = {
        "question": "How does routing work?",
        "results": [
            {
                "relative_path": "ai/router.py",
                "symbol_name": "route_query",
                "line_start": 10,
                "line_end": 40,
                "content": "def route_query(...):",
                "distance": 0.12,
            }
        ],
        "answer": "",
        "model_used": "context-only",
    }

    mock_store = MagicMock()
    mock_store.map_code_chunk_to_nodes.return_value = [
        {
            "stable_id": "abc123",
            "node_id": "n1",
            "qualified_name": "ai.router:route_query",
            "node_type": "function",
            "file_path": "ai/router.py",
            "line_start": 10,
            "line_end": 40,
            "score": 0.9,
        }
    ]
    mock_store.get_node_relationship_neighbors.return_value = [
        {"source_id": "n2", "target_id": "n1", "rel_type": "calls"}
    ]
    mock_store.find_callers.return_value = [{"caller_id": "n2", "caller_name": "foo"}]
    mock_store.query_dependency_graph.return_value = {
        "module": "ai.router",
        "dependencies": [],
        "dependents": [],
        "edges": [],
        "circular": [],
    }

    with (
        patch("ai.rag.code_query.code_rag_query", return_value=fake_semantic),
        patch("ai.code_intel.store.get_code_store", return_value=mock_store),
        patch("ai.learning.task_retriever.retrieve_similar_tasks", return_value=[]),
        patch("ai.rag.code_query._query_session_history", return_value=[]),
        patch("ai.rag.code_query._query_phase_artifacts", return_value=[]),
    ):
        from ai.rag.code_query import code_fused_context

        result = code_fused_context("How does routing work?")

    assert result["question"] == "How does routing work?"
    assert len(result["fused_results"]) == 1
    fused = result["fused_results"][0]
    assert "semantic" in fused
    assert "structural" in fused
    assert fused["structural"]["mapped_nodes"][0]["qualified_name"] == "ai.router:route_query"
