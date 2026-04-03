"""Tests for generated_at freshness timestamps and system.token_report MCP tool."""

import json
import re
from unittest.mock import patch

import pytest


class TestFreshnessTimestamps:
    def test_release_watch_has_generated_at(self, tmp_path):
        """_write_report in release_watch.py adds generated_at."""
        from ai.system import release_watch

        watch_file = tmp_path / "release-watch.json"
        with patch.object(release_watch, "RELEASE_WATCH_PATH", watch_file):
            release_watch._write_report({"repo1": {"tag_name": "v1.0"}})
            data = json.loads(watch_file.read_text())

        assert "generated_at" in data
        # Accept either Z suffix or +00:00 offset format
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$", data["generated_at"]
        )

    def test_fedora_updates_has_generated_at(self, tmp_path):
        """_write_report in fedora_updates.py adds generated_at."""
        from ai.system import fedora_updates

        updates_file = tmp_path / "fedora-updates.json"
        with patch.object(fedora_updates, "FEDORA_UPDATES_PATH", updates_file):
            fedora_updates._write_report(
                {
                    "checked_at": "2026-01-01T00:00:00+00:00",
                    "summary": {"security_count": 0},
                }
            )
            data = json.loads(updates_file.read_text())

        assert "generated_at" in data
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$", data["generated_at"]
        )

    def test_key_manager_has_generated_at(self, tmp_path):
        """write_status_file in key_manager.py adds generated_at."""
        from ai import key_manager

        with patch.object(key_manager, "SECURITY_DIR", tmp_path):
            with patch.object(key_manager, "_KEY_STATUS_FILE", tmp_path / "key-status.json"):
                key_manager.write_status_file({"GROQ_API_KEY": "set"})
                data = json.loads((tmp_path / "key-status.json").read_text())

        assert "generated_at" in data
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$", data["generated_at"]
        )

    def test_llm_proxy_status_has_generated_at(self, tmp_path):
        """llm_proxy._write_llm_status adds generated_at."""
        from ai import llm_proxy

        status_file = tmp_path / "llm-status.json"
        # Patch both the file path and the dependencies
        with patch.object(llm_proxy, "_LLM_STATUS_FILE", status_file):
            with patch.object(llm_proxy, "get_health_snapshot", return_value={}):
                with patch.object(llm_proxy, "get_cost_stats", return_value={}):
                    llm_proxy._write_llm_status()
                    data = json.loads(status_file.read_text())

        assert "generated_at" in data
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$", data["generated_at"]
        )


class TestTokenReportTool:
    @pytest.mark.asyncio
    async def test_token_report_returns_usage_section(self, tmp_path):
        """system.token_report reads llm-status.json and returns usage dict."""
        from ai.mcp_bridge import tools

        # Usage dict uses task_type keys with nested dicts containing
        # prompt_tokens, completion_tokens, requests
        status = {
            "updated_at": "2026-01-01T00:00:00+00:00",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "usage": {
                "fast": {
                    "prompt_tokens": 500,
                    "completion_tokens": 500,
                    "requests": 10,
                },
                "reason": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 2000,
                    "requests": 5,
                },
            },
            "providers": {},
        }
        status_file = tmp_path / "llm-status.json"
        status_file.write_text(json.dumps(status))

        with patch.object(tools, "_LLM_STATUS_PATH", status_file):
            result = await tools.execute_tool("system.token_report", {})

        data = json.loads(result)
        assert "usage" in data
        assert data["usage"]["total_tokens"] == 4000
        assert data["usage"]["requests"] == 15
        assert "by_task" in data["usage"]

    @pytest.mark.asyncio
    async def test_token_report_missing_file_returns_error(self, tmp_path):
        """system.token_report returns helpful error when file missing."""
        from ai.mcp_bridge import tools

        missing = tmp_path / "nonexistent-llm-status.json"
        with patch.object(tools, "_LLM_STATUS_PATH", missing):
            result = await tools.execute_tool("system.token_report", {})

        assert "error" in result.lower() or "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_token_report_malformed_file_returns_error(self, tmp_path):
        """system.token_report returns error for malformed JSON."""
        import time

        from ai.mcp_bridge import tools

        # Wait to avoid rate limiting
        time.sleep(1.1)

        malformed = tmp_path / "malformed-llm-status.json"
        malformed.write_text("{ invalid json }")

        with patch.object(tools, "_LLM_STATUS_PATH", malformed):
            result = await tools.execute_tool("system.token_report", {})

        assert "error" in result.lower() or "malformed" in result.lower()

    @pytest.mark.asyncio
    async def test_token_report_stale_data_includes_freshness_warning(self, tmp_path):
        """system.token_report includes freshness warning when data is old."""
        import time
        from datetime import UTC, datetime, timedelta

        from ai.mcp_bridge import tools

        time.sleep(1.1)

        # Create data that's 3 hours old
        old_time = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
        status = {
            "generated_at": old_time,
            "usage": {
                "fast": {"prompt_tokens": 50, "completion_tokens": 50, "requests": 5},
            },
            "providers": {},
        }
        status_file = tmp_path / "llm-status.json"
        status_file.write_text(json.dumps(status))

        with patch.object(tools, "_LLM_STATUS_PATH", status_file):
            result = await tools.execute_tool("system.token_report", {})

        data = json.loads(result)
        assert "freshness_warning" in data or "hours old" in result.lower()


class TestFreshnessHelperUnit:
    def test_format_freshness_age_returns_none_for_fresh_data(self):
        """format_freshness_age returns None for data < 1 hour old."""
        from datetime import UTC, datetime, timedelta

        from ai.utils.freshness import format_freshness_age

        # Use timezone-aware UTC datetime
        recent = datetime.now(UTC) - timedelta(minutes=30)
        result = format_freshness_age(recent)
        # Should be None since less than 1 hour old
        assert result is None

    def test_format_freshness_age_returns_message_for_stale_data(self):
        """format_freshness_age returns message for data >= 1 hour old."""
        from ai.utils.freshness import format_freshness_age

        # Use ISO string with UTC timezone to ensure consistent calculation
        old_time = "2026-01-01T00:00:00+00:00"
        result = format_freshness_age(old_time)
        assert result is not None
        assert "hours old" in result or "days old" in result

    def test_format_freshness_age_handles_iso_string(self):
        """format_freshness_age works with ISO string timestamps."""
        from ai.utils.freshness import format_freshness_age

        # Use an ISO string that represents time 2 hours ago (in UTC)
        old_time = "2026-01-01T00:00:00+00:00"
        result = format_freshness_age(old_time)
        assert result is not None

    def test_format_freshness_age_returns_none_for_invalid(self):
        """format_freshness_age returns None for invalid/None input."""
        from ai.utils.freshness import format_freshness_age

        assert format_freshness_age(None) is None
        assert format_freshness_age("invalid-timestamp") is None
        assert format_freshness_age(12345) is None

    def test_backward_compat_tolerates_missing_generated_at(self, tmp_path):
        """Readers should tolerate JSON files without generated_at field."""
        from ai.utils.freshness import read_json_with_freshness

        old_file = tmp_path / "old-status.json"
        old_file.write_text(json.dumps({"some_data": "value"}))

        data, freshness = read_json_with_freshness(old_file)
        assert data == {"some_data": "value"}
        assert freshness is None
