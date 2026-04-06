#!/usr/bin/env python3
"""Validate Newelle skill documentation against MCP bridge allowlist.

Checks that all tool references in docs/newelle-skills/*.md exist in
configs/mcp-bridge-allowlist.yaml.
"""

import re
import sys
from pathlib import Path

import yaml

SKILLS_DIR = Path("docs/newelle-skills")
ALLOWLIST = Path("configs/mcp-bridge-allowlist.yaml")

TOOL_REFERENCE_RE = r"`([\w]+\.[\w]+)`"


def load_allowlist_tools(allowlist_path: Path) -> set[str]:
    """Load all tool names from the allowlist YAML."""
    if not allowlist_path.exists():
        print(f"ERROR: Allowlist not found: {allowlist_path}")
        sys.exit(1)

    content = allowlist_path.read_text()
    data = yaml.safe_load(content)
    tools = data.get("tools", {})
    return set(tools.keys())


def extract_tool_references(skill_file: Path) -> list[str]:
    """Extract backtick-quoted dotted tool names from a markdown file."""
    if not skill_file.exists():
        return []

    content = skill_file.read_text()
    matches = re.findall(TOOL_REFERENCE_RE, content)
    return matches


def main():
    """Run validation and report results."""
    allowlist_tools = load_allowlist_tools(ALLOWLIST)

    if not SKILLS_DIR.exists():
        print(f"ERROR: Skills directory not found: {SKILLS_DIR}")
        sys.exit(1)

    skill_files = sorted(SKILLS_DIR.glob("*.md"))
    if not skill_files:
        print(f"WARNING: No .md files found in {SKILLS_DIR}")
        sys.exit(0)

    all_missing = []
    total_referenced = 0

    print(f"\n{'=' * 70}")
    print("NEWELLE SKILLS VALIDATION REPORT")
    print(f"{'=' * 70}")
    print(f"Allowlist: {ALLOWLIST}")
    print(f"Skills dir: {SKILLS_DIR}")
    print(f"Tools in allowlist: {len(allowlist_tools)}")
    print(f"{'=' * 70}\n")

    for skill_file in skill_files:
        references = extract_tool_references(skill_file)
        unique_refs = set(references)
        total_referenced += len(unique_refs)

        existing = []
        missing = []
        for tool in sorted(unique_refs):
            if tool in allowlist_tools:
                existing.append(tool)
            else:
                missing.append(tool)

        all_missing.extend(missing)

        print(f"📄 {skill_file.name}")
        print(f"   Referenced tools: {len(unique_refs)}")
        if existing:
            print(
                f"   ✓ Found: {', '.join(sorted(existing)[:5])}{'...' if len(existing) > 5 else ''}"
            )
        if missing:
            print(f"   ✗ Missing: {', '.join(missing)}")
        else:
            print("   ✓ All tools found")
        print()

    print(f"{'=' * 70}")
    print(f"SUMMARY: {total_referenced} tools referenced across {len(skill_files)} files")
    print(f"{'=' * 70}")

    if all_missing:
        unique_missing = sorted(set(all_missing))
        print(f"\n❌ FAILED: {len(unique_missing)} unique tool(s) not in allowlist:")
        for tool in unique_missing:
            print(f"   - {tool}")
        sys.exit(1)
    else:
        print(f"\n✅ PASSED: All {total_referenced} referenced tools exist in allowlist")
        sys.exit(0)


if __name__ == "__main__":
    main()
