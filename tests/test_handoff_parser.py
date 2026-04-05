"""Unit tests for ai/learning/handoff_parser.py."""

import tempfile


class TestParseHandoff:
    """Tests for parse_handoff function."""

    def test_parse_summary_extracted(self):
        """Summary text should be captured."""
        from ai.learning.handoff_parser import parse_handoff

        content = """# Handoff

### 2026-04-04T10:00:00Z — claude-code
[P34 complete]

- [x] Performance hardening
- [ ] P35 tasks
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            entries = parse_handoff(f.name)

        assert len(entries) == 1
        assert "P34 complete" in entries[0].summary

    def test_parse_done_tasks(self):
        """Done tasks should be extracted as list."""
        from ai.learning.handoff_parser import parse_handoff

        content = """### 2026-04-04T10:00:00Z — claude-code

- [x] Task 1
- [x] Task 2
- [ ] Open task
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            entries = parse_handoff(f.name)

        assert len(entries[0].done_tasks) == 2
        assert "Task 1" in entries[0].done_tasks

    def test_parse_open_tasks(self):
        """Open tasks should be captured."""
        from ai.learning.handoff_parser import parse_handoff

        content = """### 2026-04-04T10:00:00Z — claude-code

- [ ] Pending task
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            entries = parse_handoff(f.name)

        assert "Pending task" in entries[0].open_tasks

    def test_parse_agent_name(self):
        """Agent name should be preserved."""
        from ai.learning.handoff_parser import parse_handoff

        content = """### 2026-04-04T10:00:00Z — opencode

[Summary]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            entries = parse_handoff(f.name)

        assert entries[0].agent == "opencode"

    def test_parse_empty_handoff(self):
        """Empty file should return empty list, no crash."""
        from ai.learning.handoff_parser import parse_handoff

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            f.flush()
            entries = parse_handoff(f.name)

        assert entries == []

    def test_parse_multiple_sessions(self):
        """Multi-session HANDOFF should return multiple entries."""
        from ai.learning.handoff_parser import parse_handoff

        content = """### 2026-04-04T10:00:00Z — agent1

[Session 1]

### 2026-04-04T09:00:00Z — agent2

[Session 2]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            entries = parse_handoff(f.name)

        assert len(entries) == 2

    def test_correlate_commits_fallback(self):
        """No repo should return empty changed files list."""

        from ai.learning.handoff_parser import HandoffEntry, correlate_with_commits

        entry = HandoffEntry(
            timestamp="2026-04-04T10:00:00Z",
            agent="test",
            summary="test",
            done_tasks=[],
            open_tasks=[],
        )

        result = correlate_with_commits(entry, None)
        assert result == []

    def test_entry_to_task_pattern_keys(self):
        """Output should have required keys for TaskLogger."""
        from ai.learning.handoff_parser import HandoffEntry, entry_to_task_pattern

        entry = HandoffEntry(
            timestamp="2026-04-04T10:00:00Z",
            agent="test",
            summary="test summary",
            done_tasks=["task1", "task2"],
            open_tasks=[],
        )

        result = entry_to_task_pattern(entry)

        assert "task_type" in result
        assert "prompt" in result
        assert "result" in result
        assert "success" in result

    def test_since_date_filter(self):
        """Entries before cutoff should be excluded."""
        from ai.learning.handoff_parser import HandoffEntry, filter_by_date

        entries = [
            HandoffEntry("2026-04-01T10:00:00Z", "a", "s", [], []),
            HandoffEntry("2026-04-05T10:00:00Z", "b", "s", [], []),
            HandoffEntry("2026-04-10T10:00:00Z", "c", "s", [], []),
        ]

        filtered = filter_by_date(entries, "2026-04-06")

        assert len(filtered) == 1
        assert filtered[0].agent == "c"
