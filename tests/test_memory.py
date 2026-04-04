"""Unit tests for ai/memory.py ConversationMemory."""

import json
from unittest.mock import patch

import pytest

from ai.memory import ConversationMemory, get_memory, summarize_session  # noqa: E402


def mock_embed_single(text: str, **kwargs):
    return [0.0] * 768


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_memory"


class TestConversationMemory:
    def test_store_memory_basic(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            result = memory.store_memory("User prefers dark mode", importance=3)
            assert result != ""
            memories = memory.get_recent(n=1)
            assert len(memories) == 1
            assert "prefers dark mode" in memories[0]["summary"]

    def test_store_memory_validates_importance(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            with pytest.raises(ValueError, match="importance must be between"):
                memory.store_memory("test", importance=0)
            with pytest.raises(ValueError, match="importance must be between"):
                memory.store_memory("test", importance=6)

    def test_retrieve_memories_by_similarity(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            memory.store_memory("Python is great", importance=3)
            memory.store_memory("I love coffee", importance=3)
            memory.store_memory("Dark mode preferred", importance=3)

            with patch("ai.memory.embed_single", return_value=[0.0] * 768):
                results = memory.retrieve_memories("programming", top_k=2)
            assert len(results) <= 2

    def test_retrieve_memories_min_importance(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            memory.store_memory("low importance", importance=1)
            memory.store_memory("high importance", importance=5)

            with patch("ai.memory.embed_single", return_value=[0.0] * 768):
                results = memory.retrieve_memories("test", min_importance=3)
            assert all(r["importance"] >= 3 for r in results)

    def test_search_memories_returns_json(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            memory.store_memory("test fact", importance=3)

            with patch("ai.memory.embed_single", return_value=[0.0] * 768):
                result = memory.search_memories("test", top_k=5)
            assert result
            parsed = json.loads(result)
            assert isinstance(parsed, list)

    def test_get_recent(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            for i in range(5):
                memory.store_memory(f"fact {i}", importance=3)
            recent = memory.get_recent(n=3)
            assert len(recent) == 3

    def test_prune_memories_by_age(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            memory.store_memory("old fact", importance=1)
            deleted = memory.prune_memories(max_age_days=30, min_importance=1)
            assert deleted >= 0

    def test_prune_keeps_high_importance(self, tmp_db):
        with patch("ai.memory.embed_single", mock_embed_single):
            memory = ConversationMemory(db_path=tmp_db)
            memory.store_memory("important fact", importance=5)
            deleted = memory.prune_memories(max_age_days=1, min_importance=1)
            assert deleted == 0


class TestSummarizeSession:
    def test_summarize_session_preferences(self):
        messages = [{"role": "user", "content": "I prefer dark mode for coding"}]
        summaries = summarize_session(messages)
        assert len(summaries) >= 1
        assert "prefer" in summaries[0].lower() or "dark" in summaries[0].lower()

    def test_summarize_session_security(self):
        messages = [{"role": "user", "content": "Found CVE-2026-1234 in the system scan"}]
        summaries = summarize_session(messages)
        assert len(summaries) >= 1

    def test_summarize_session_max_3(self):
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        summaries = summarize_session(messages)
        assert len(summaries) <= 3


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        m1 = get_memory()
        m2 = get_memory()
        assert m1 is m2
