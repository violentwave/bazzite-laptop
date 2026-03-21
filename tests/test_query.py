"""Tests for ai.rag.query — RAG query engine.

All external calls (embedder, store, router) are mocked.
"""

import json
from unittest.mock import MagicMock, patch

# Lazy imports — query.py no longer imports store/embedder at module level,
# but we import here for convenience since the module is safe to load now.
from ai.rag.query import (
    QueryResult,
    _build_context,
    _build_prompt,
    format_result,
    rag_query,
)

# ── Fixtures ──


def _mock_embedding() -> list[float]:
    return [0.0] * 768


def _mock_log_results() -> list[dict]:
    return [
        {
            "source_file": "/var/log/clamav/scan-2025-03-14.log",
            "section": "findings",
            "text": "Found Eicar-Test-Signature in /tmp/test.exe",
            "_distance": 0.12,
        },
        {
            "source_file": "/var/log/system-health/health-latest.log",
            "section": "gpu",
            "text": "GPU temp: 72C, fan: 3200rpm",
            "_distance": 0.35,
        },
    ]


def _mock_threat_results() -> list[dict]:
    return [
        {
            "hash": "abc123def456" * 5 + "abcd",
            "source": "virustotal",
            "text": "VirusTotal: 15/72 detections, family: Eicar",
            "_distance": 0.20,
        },
    ]


# ── TestQueryResult ──


class TestQueryResult:
    """Test dataclass defaults and structure."""

    def test_defaults(self) -> None:
        qr = QueryResult(question="test?")
        assert qr.question == "test?"
        assert qr.context_chunks == []
        assert qr.answer == ""
        assert qr.sources == []
        assert qr.model_used == "context-only"

    def test_custom_values(self) -> None:
        qr = QueryResult(
            question="q",
            context_chunks=[{"a": 1}],
            answer="answer",
            sources=["src"],
            model_used="fast",
        )
        assert qr.model_used == "fast"
        assert len(qr.context_chunks) == 1


# ── TestBuildContext ──


class TestBuildContext:
    """Test context formatting from chunks."""

    def test_empty_chunks(self) -> None:
        assert _build_context([]) == ""

    def test_log_chunk_formatting(self) -> None:
        chunks = [
            {
                "source_file": "/var/log/test.log",
                "section": "findings",
                "text": "Found malware",
                "_distance": 0.15,
            }
        ]
        result = _build_context(chunks)
        assert "[/var/log/test.log | findings]" in result
        assert "Found malware" in result
        assert "0.1500" in result

    def test_threat_chunk_formatting(self) -> None:
        chunks = [
            {
                "hash": "abc123",
                "source": "virustotal",
                "text": "VT detection",
                "_distance": 0.20,
            }
        ]
        result = _build_context(chunks)
        assert "[virustotal]" in result
        assert "VT detection" in result

    def test_chunk_without_source_uses_hash(self) -> None:
        chunks = [
            {
                "hash": "deadbeef",
                "text": "unknown source",
                "_distance": 0.50,
            }
        ]
        result = _build_context(chunks)
        assert "[threat:deadbeef]" in result

    def test_multiple_chunks_separated(self) -> None:
        chunks = [
            {"source_file": "a.log", "text": "chunk1", "_distance": 0.1},
            {"source_file": "b.log", "text": "chunk2", "_distance": 0.2},
        ]
        result = _build_context(chunks)
        assert "chunk1" in result
        assert "chunk2" in result
        # Separated by double newline
        assert "\n\n" in result

    def test_chunk_without_distance(self) -> None:
        chunks = [{"source_file": "a.log", "text": "no dist"}]
        result = _build_context(chunks)
        assert "distance" not in result


# ── TestBuildPrompt ──


class TestBuildPrompt:
    """Test prompt structure."""

    def test_contains_system_context(self) -> None:
        prompt = _build_prompt("What threats?", "some context")
        assert "security analyst" in prompt
        assert "Bazzite 43" in prompt
        assert "GTX 1060" in prompt

    def test_contains_context_section(self) -> None:
        prompt = _build_prompt("question?", "ctx data here")
        assert "--- CONTEXT ---" in prompt
        assert "ctx data here" in prompt
        assert "--- END CONTEXT ---" in prompt

    def test_contains_question(self) -> None:
        prompt = _build_prompt("Is my GPU overheating?", "ctx")
        assert "Question: Is my GPU overheating?" in prompt

    def test_only_context_instruction(self) -> None:
        prompt = _build_prompt("q", "c")
        assert "ONLY on the provided context" in prompt


# ── TestFormatResult ──


class TestFormatResult:
    """Test output formatting."""

    def test_text_format(self) -> None:
        qr = QueryResult(
            question="What threats?",
            answer="Found Eicar test signature.",
            sources=["/var/log/clamav/scan.log"],
            model_used="fast",
        )
        text = format_result(qr, fmt="text")
        assert "Question: What threats?" in text
        assert "Model: fast" in text
        assert "Found Eicar test signature." in text
        assert "/var/log/clamav/scan.log" in text

    def test_text_no_sources(self) -> None:
        qr = QueryResult(question="q", answer="a")
        text = format_result(qr, fmt="text")
        assert "(none)" in text

    def test_json_format(self) -> None:
        qr = QueryResult(
            question="q",
            answer="a",
            sources=["src1"],
            model_used="fast",
            context_chunks=[{"text": "chunk"}],
        )
        output = format_result(qr, fmt="json")
        parsed = json.loads(output)
        assert parsed["question"] == "q"
        assert parsed["answer"] == "a"
        assert parsed["sources"] == ["src1"]
        assert parsed["model_used"] == "fast"
        assert len(parsed["context_chunks"]) == 1

    def test_json_is_valid(self) -> None:
        qr = QueryResult(question="test")
        output = format_result(qr, fmt="json")
        # Should not raise
        json.loads(output)


# ── TestRagQuery ──


class TestRagQuery:
    """Test full RAG pipeline with mocked dependencies."""

    @patch("ai.rag.query.route_query")
    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_full_pipeline_with_llm(
        self, mock_embed: MagicMock, mock_store: MagicMock, mock_route: MagicMock
    ) -> None:
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = _mock_log_results()
        store_instance.search_threats.return_value = _mock_threat_results()
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance
        mock_route.return_value = "The scan found an Eicar test signature."

        result = rag_query("What threats were detected?", use_llm=True)

        assert result.answer == "The scan found an Eicar test signature."
        assert result.model_used == "fast"
        assert len(result.context_chunks) == 3
        assert len(result.sources) > 0
        mock_embed.assert_called_once_with(
            "What threats were detected?", input_type="search_query"
        )

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_context_only_mode(
        self, mock_embed: MagicMock, mock_store: MagicMock
    ) -> None:
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = _mock_log_results()
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        result = rag_query("GPU temps?", use_llm=False)

        assert result.model_used == "context-only"
        assert "GPU temp" in result.answer
        assert len(result.context_chunks) == 2

    @patch("ai.rag.query.route_query")
    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_scaffold_fallback(
        self, mock_embed: MagicMock, mock_store: MagicMock, mock_route: MagicMock
    ) -> None:
        """When router returns [SCAFFOLD], fall back to context-only."""
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = _mock_log_results()
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance
        mock_route.return_value = "[SCAFFOLD] Would route 'fast' query to LiteLLM."

        result = rag_query("test question", use_llm=True)

        assert result.model_used == "context-only"
        assert "[SCAFFOLD]" not in result.answer

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_empty_results(
        self, mock_embed: MagicMock, mock_store: MagicMock
    ) -> None:
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = []
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        result = rag_query("nonexistent topic", use_llm=True)

        assert "No relevant context" in result.answer
        assert result.model_used == "context-only"
        assert result.sources == []

    @patch("ai.rag.query.route_query")
    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_llm_error_fallback(
        self, mock_embed: MagicMock, mock_store: MagicMock, mock_route: MagicMock
    ) -> None:
        """When LLM routing raises, fall back to context-only."""
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = _mock_log_results()
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance
        mock_route.side_effect = RuntimeError("All providers exhausted")

        result = rag_query("test question", use_llm=True)

        assert result.model_used == "context-only"
        assert len(result.context_chunks) == 2

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_results_sorted_by_distance(
        self, mock_embed: MagicMock, mock_store: MagicMock
    ) -> None:
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = [
            {"source_file": "b.log", "text": "far", "_distance": 0.9},
        ]
        store_instance.search_threats.return_value = [
            {"source": "vt", "text": "close", "_distance": 0.1},
        ]
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        result = rag_query("test", use_llm=False)

        assert result.context_chunks[0]["_distance"] == 0.1
        assert result.context_chunks[1]["_distance"] == 0.9

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_sources_deduplicated(
        self, mock_embed: MagicMock, mock_store: MagicMock
    ) -> None:
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = [
            {"source_file": "same.log", "text": "a", "_distance": 0.1},
            {"source_file": "same.log", "text": "b", "_distance": 0.2},
        ]
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        result = rag_query("test", use_llm=False)

        assert result.sources == ["same.log"]

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_threat_source_uses_hash(
        self, mock_embed: MagicMock, mock_store: MagicMock
    ) -> None:
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.return_value = []
        store_instance.search_threats.return_value = [
            {"hash": "deadbeef1234", "text": "threat", "_distance": 0.3},
        ]
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        result = rag_query("test", use_llm=False)

        assert "threat:deadbeef1234" in result.sources

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_search_failure_graceful(
        self, mock_embed: MagicMock, mock_store: MagicMock
    ) -> None:
        """If one table search fails, the other still works."""
        mock_embed.return_value = _mock_embedding()
        store_instance = MagicMock()
        store_instance.search_logs.side_effect = Exception("DB error")
        store_instance.search_threats.return_value = _mock_threat_results()
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        result = rag_query("test", use_llm=False)

        assert len(result.context_chunks) == 1
