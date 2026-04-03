"""Tests for ai/learning task logger and retriever."""

import subprocess
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.learning.task_logger import TaskLogger
from ai.learning.task_retriever import retrieve_similar_tasks


class TestTaskLogger:
    def test_log_success_returns_uuid(self, tmp_path):
        logger = TaskLogger(db_path=str(tmp_path))
        result = logger.log_success(
            description="Test task",
            approach="Test approach",
            outcome="Test outcome",
        )
        UUID(result)

    def test_log_success_creates_table_entry(self, tmp_path):
        logger = TaskLogger(db_path=str(tmp_path))
        logger.log_success(
            description="Added HTTP session reuse",
            approach="Module-level requests.Session",
            outcome="30-50% latency reduction",
            phase="P22",
        )
        results = retrieve_similar_tasks(
            query="Added HTTP session reuse",
            top_k=3,
            db_path=str(tmp_path),
        )
        assert len(results) >= 1
        assert results[0]["description"] == "Added HTTP session reuse"


class TestTaskRetriever:
    def test_retrieve_returns_empty_when_no_table(self, tmp_path):
        results = retrieve_similar_tasks(
            query="test query",
            top_k=3,
            db_path=str(tmp_path),
        )
        assert results == []

    def test_retrieve_filters_by_similarity(self, tmp_path):
        logger = TaskLogger(db_path=str(tmp_path))
        logger.log_success(
            description="Add HTTP session reuse to threat intel",
            approach="Module-level requests.Session with connection pooling",
            outcome="30-50% latency reduction",
            phase="P22",
        )
        logger.log_success(
            description="Fix typo in documentation",
            approach="Simple find and replace",
            outcome="Documentation corrected",
            phase="P20",
        )
        results = retrieve_similar_tasks(
            query="HTTP connection pooling for API calls",
            top_k=3,
            min_similarity=0.75,
            db_path=str(tmp_path),
        )
        assert len(results) >= 1
        assert "HTTP" in results[0]["description"]


class TestCLI:
    def test_cli_script_invocation(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable,
                "scripts/log-task-success.py",
                "--description",
                "test",
                "--approach",
                "test",
                "--outcome",
                "test",
                "--phase",
                "P22",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "Logged task" in result.stdout


class TestAllowlist:
    def test_mcp_tool_in_allowlist(self):
        import yaml

        allowlist_path = Path(__file__).parent.parent / "configs" / "mcp-bridge-allowlist.yaml"
        with open(allowlist_path) as f:
            data = yaml.safe_load(f)
        assert "knowledge.task_patterns" in data.get("tools", {})


class TestMCPHandlerRobustness:
    def test_knowledge_task_patterns_docstring_tool_count(self):
        """Server module docstring must not claim stale tool count."""
        import ai.mcp_bridge.server as server_mod
        assert "46 tools" not in (server_mod.__doc__ or ""), (
            "Stale docstring: update tool count in server.py module docstring"
        )
