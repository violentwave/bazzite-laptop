"""Tests for scripts/validate_newelle_skills.py"""

from unittest.mock import patch


class TestValidateSkills:
    """Test skill validation functionality."""

    def test_finds_tool_references(self):
        """Regex extracts backtick tool names correctly."""
        import re

        from scripts.validate_newelle_skills import TOOL_REFERENCE_RE

        content = """
        Use `system.disk_usage` to check space.
        Also need `security.threat_lookup` and `system.memory_usage`.
        """

        matches = re.findall(TOOL_REFERENCE_RE, content)
        assert "system.disk_usage" in matches
        assert "security.threat_lookup" in matches
        assert "system.memory_usage" in matches
        assert len(matches) == 3

    def test_detects_missing_tools(self, tmp_path):
        """Tool not in allowlist flagged as missing."""
        import yaml

        from scripts.validate_newelle_skills import (
            extract_tool_references,
            load_allowlist_tools,
        )

        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text(
            yaml.dump({"tools": {"system.disk_usage": {"description": "test"}}})
        )

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "test.md"
        skill_file.write_text("Use `system.disk_usage` and `missing.tool` here.")

        allowlist = load_allowlist_tools(allowlist_file)
        refs = extract_tool_references(skill_file)

        missing = [r for r in refs if r not in allowlist]
        assert "missing.tool" in missing
        assert "system.disk_usage" not in missing

    def test_exits_zero_when_all_valid(self, tmp_path):
        """Exits 0 when all referenced tools exist."""

        import yaml

        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text(
            yaml.dump(
                {
                    "tools": {
                        "system.disk_usage": {"description": "test"},
                        "system.memory_usage": {"description": "test"},
                    }
                }
            )
        )

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "test.md"
        skill_file.write_text("Use `system.disk_usage` and `system.memory_usage`.")

        with patch("scripts.validate_newelle_skills.ALLOWLIST", allowlist_file):
            with patch("scripts.validate_newelle_skills.SKILLS_DIR", skills_dir):
                from scripts.validate_newelle_skills import (
                    extract_tool_references,
                    load_allowlist_tools,
                )

                allowlist = load_allowlist_tools(allowlist_file)
                refs = extract_tool_references(skill_file)
                missing = [r for r in refs if r not in allowlist]

                assert len(missing) == 0
