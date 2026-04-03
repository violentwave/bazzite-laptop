#!/usr/bin/env python3
"""
Phase 8 cleanup of .claude-flow/data/auto-memory-store.json

Fixes:
  1. Stale SSD paths: /run/media/lch/SteamLibrary -> /var/mnt/ext-ssd
  2. Outdated tool counts: any "N tools" (N != 43) -> "43 tools"
  3. Legacy AgentDB refs: remove entries that are purely about AgentDB,
     strip AgentDB sentences from mixed entries
"""

import json
import re
import shutil
from pathlib import Path

STORE = Path("/var/home/lch/projects/bazzite-laptop/.claude-flow/data/auto-memory-store.json")
BACKUP = STORE.with_suffix(".json.bak")

# Tool counts that should be replaced with "43"
STALE_COUNTS = {
    "22 tools", "23 tools", "24 tools", "25 tools", "26 tools",
    "27 tools", "28 tools", "29 tools", "30 tools", "31 tools",
    "32 tools", "33 tools", "34 tools", "35 tools", "36 tools",
    "37 tools", "38 tools", "39 tools", "40 tools", "41 tools",
    "42 tools",
}

# AgentDB-only keywords: entries whose content is purely about AgentDB
AGENTDB_ONLY_KEYS = re.compile(
    r"agentdb-(advanced|learning|memory-patterns|optimization|vector-search|unified|reflexion|consolidate|stats|skills)",
    re.IGNORECASE,
)

# Sentences/lines that are purely AgentDB operational (to strip from mixed entries)
AGENTDB_STRIP_PATTERNS = [
    re.compile(r"[^\n.]*\bAgentDB\b[^\n.]*[.!?]?\s*", re.IGNORECASE),
    re.compile(r"[^\n]*agentdb[^\n]*\n", re.IGNORECASE),
]


def fix_ssd_path(text: str) -> tuple[str, int]:
    new, n = re.subn(r"/run/media/lch/SteamLibrary", "/var/mnt/ext-ssd", text)
    return new, n


def fix_tool_counts(text: str) -> tuple[str, int]:
    total = 0
    for pattern in STALE_COUNTS:
        new, n = re.subn(re.escape(pattern), "43 tools", text, flags=re.IGNORECASE)
        text = new
        total += n
    return text, total


def is_pure_agentdb(entry: dict) -> bool:
    key = entry.get("key", "").lower()
    content = entry.get("content", "").lower()
    # Key contains agentdb-* prefix (from agentdb skills/features)
    if AGENTDB_ONLY_KEYS.search(key):
        return True
    # Content is almost entirely about AgentDB (>80% of non-whitespace lines contain "agentdb")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return False
    agentdb_lines = sum(1 for line in lines if "agentdb" in line.lower())
    return len(lines) > 0 and agentdb_lines / len(lines) >= 0.80


def strip_agentdb_refs(text: str) -> str:
    """Remove sentences/lines that mention AgentDB from mixed content."""
    # Remove full lines containing agentdb
    lines = text.splitlines(keepends=True)
    cleaned = []
    for line in lines:
        if re.search(r"\bAgentDB\b|\bagentdb\b", line, re.IGNORECASE):
            continue
        cleaned.append(line)
    return "".join(cleaned).strip()


def main():
    print(f"Loading {STORE}...")
    with open(STORE) as f:
        data = json.load(f)

    total_before = len(data)
    print(f"Entries before: {total_before}")

    # Backup
    shutil.copy2(STORE, BACKUP)
    print(f"Backup written to {BACKUP}")

    removed = 0
    ssd_fixed = 0
    count_fixed = 0
    agentdb_stripped = 0
    cleaned_entries = []

    for entry in data:
        content = entry.get("content", "")

        # Fix 1: stale SSD paths
        new_content, n = fix_ssd_path(content)
        ssd_fixed += n

        # Fix 2: outdated tool counts
        new_content, n = fix_tool_counts(new_content)
        count_fixed += n

        entry["content"] = new_content
        content = new_content

        # Fix 3: AgentDB cleanup
        if is_pure_agentdb(entry):
            removed += 1
            continue

        # Strip AgentDB mentions from mixed entries
        has_agentdb = bool(re.search(r"\bAgentDB\b|\bagentdb\b", content, re.IGNORECASE))
        if has_agentdb:
            stripped = strip_agentdb_refs(content)
            if stripped != content:
                entry["content"] = stripped
                agentdb_stripped += 1

        cleaned_entries.append(entry)

    total_after = len(cleaned_entries)

    print("\n--- Results ---")
    print(f"Entries before:       {total_before}")
    print(f"Entries after:        {total_after}")
    print(f"Entries removed:      {removed}  (pure AgentDB)")
    print(f"SSD paths fixed:      {ssd_fixed}")
    print(f"Tool counts fixed:    {count_fixed}")
    print(f"AgentDB refs stripped:{agentdb_stripped}")

    with open(STORE, "w") as f:
        json.dump(cleaned_entries, f, indent=2)
    print(f"\nWrote cleaned store to {STORE}")

    # Verify
    remaining_ssd = sum(
        1 for e in cleaned_entries if "/run/media/lch/SteamLibrary" in e.get("content", "")
    )
    remaining_counts = sum(
        1 for e in cleaned_entries
        if any(c in e.get("content", "") for c in STALE_COUNTS)
    )
    remaining_agentdb = sum(
        1 for e in cleaned_entries
        if re.search(r"\bAgentDB\b|\bagentdb\b", e.get("content", ""), re.IGNORECASE)
    )
    print("\n--- Verification ---")
    print(f"Remaining stale SSD paths:   {remaining_ssd}")
    print(f"Remaining wrong tool counts: {remaining_counts}")
    print(f"Remaining AgentDB refs:      {remaining_agentdb}")


if __name__ == "__main__":
    main()
