#!/usr/bin/env python3
"""CLI script to ingest curated code patterns from markdown files into LanceDB.

Usage:
    python scripts/ingest-patterns.py [--dry-run] [--force] [--pattern GLOB]

Each markdown file in docs/patterns/ should have YAML frontmatter:
---
language: python
domain: security
type: pattern
title: Atomic file write with tempfile
tags: atomic-write, file-safety, crash-safe
---

The body of the file (after the second ---) becomes the `content` field.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
import re
from datetime import datetime

from ai.rag.embedder import embed_single
from ai.rag.pattern_store import (
    VALID_ARCHETYPES,
    VALID_DOMAINS,
    VALID_LANGUAGES,
    VALID_PATTERN_SCOPES,
    VALID_SEMANTIC_ROLES,
    VALID_TYPES,
    content_id,
    get_or_create_table,
    upsert_pattern,
)

logger = logging.getLogger("ingest-patterns")

DEFAULT_PATTERNS_DIR = Path("docs/patterns")
DEFAULT_PATTERN_GLOB = "*.md"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns tuple of (frontmatter_dict, body_without_frontmatter).
    """
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n",
        content,
        re.DOTALL,
    )
    if not frontmatter_match:
        raise ValueError("No YAML frontmatter found")

    frontmatter_text = frontmatter_match.group(1)
    body = content[frontmatter_match.end() :]

    fm = {}
    for line in frontmatter_text.split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()

    return fm, body.strip()


def build_record(frontmatter: dict, body: str, source: str = "curated") -> dict:
    """Build a pattern record from parsed frontmatter and body."""
    language = frontmatter.get("language", "").lower()
    domain = frontmatter.get("domain", "").lower()
    pattern_type = frontmatter.get("type", "").lower()
    title = frontmatter.get("title", "Untitled")
    tags = frontmatter.get("tags", "")

    # Frontend metadata (optional)
    archetype = frontmatter.get("archetype", "").lower() or None
    pattern_scope = frontmatter.get("pattern_scope", "").lower() or None
    semantic_role = frontmatter.get("semantic_role", "").lower() or None
    generation_priority = frontmatter.get("generation_priority")

    if language not in VALID_LANGUAGES:
        raise ValueError(f"Invalid language: {language!r}")
    if domain not in VALID_DOMAINS:
        raise ValueError(f"Invalid domain: {domain!r}")
    if pattern_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {pattern_type!r}")

    # Validate frontend metadata if present
    if archetype and archetype not in VALID_ARCHETYPES:
        raise ValueError(f"Invalid archetype: {archetype!r}")
    if pattern_scope and pattern_scope not in VALID_PATTERN_SCOPES:
        raise ValueError(f"Invalid pattern_scope: {pattern_scope!r}")
    if semantic_role and semantic_role not in VALID_SEMANTIC_ROLES:
        raise ValueError(f"Invalid semantic_role: {semantic_role!r}")
    if generation_priority is not None:
        try:
            priority = int(generation_priority)
            if priority < 1 or priority > 10:
                raise ValueError
            generation_priority = priority
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid generation_priority: {generation_priority!r}. Must be 1-10."
            ) from exc

    vector = embed_single(body)
    record = {
        "id": content_id(body),
        "content": body,
        "language": language,
        "domain": domain,
        "pattern_type": pattern_type,
        "title": title,
        "source": source,
        "tags": tags,
        "timestamp": datetime.now(tz=None).isoformat(),
        "vector": vector,
        "archetype": archetype,
        "pattern_scope": pattern_scope,
        "semantic_role": semantic_role,
        "generation_priority": generation_priority,
    }
    return record


def ingest_file(
    path: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """Ingest a single pattern file. Returns status dict."""
    try:
        content = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        record = build_record(frontmatter, body)

        if dry_run:
            logger.info(f"[DRY-RUN] Would ingest: {path.name}")
            return {"status": "dry-run", "path": path.name}

        if force:
            table = get_or_create_table()
            try:
                table.delete(f"id = '{record['id']}'")
            except Exception as e:
                logger.debug("Delete failed (id may not exist): %s", e)

        upsert_pattern(record)
        logger.info(f"Ingested: {path.name}")
        return {"status": "ingested", "path": path.name}

    except Exception as exc:
        logger.error(f"Error processing {path.name}: {exc}")
        return {"status": "error", "path": path.name, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest code patterns into LanceDB")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without actually adding to DB",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing records before re-embedding",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN_GLOB,
        help=f"Glob pattern for pattern files (default: {DEFAULT_PATTERN_GLOB})",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_PATTERNS_DIR,
        help=f"Directory containing pattern files (default: {DEFAULT_PATTERNS_DIR})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    pattern_dir = args.dir
    if not pattern_dir.is_dir():
        logger.error(f"Pattern directory not found: {pattern_dir}")
        return 1

    files = sorted(pattern_dir.glob(args.pattern))
    if not files:
        logger.warning(f"No files matching {args.pattern} in {pattern_dir}")
        return 0

    ingested = 0
    errors = 0

    for path in files:
        result = ingest_file(path, dry_run=args.dry_run, force=args.force)
        status = result["status"]
        if status == "ingested":
            ingested += 1
        elif status == "dry-run":
            pass
        elif status == "error":
            errors += 1

    if args.dry_run:
        logger.info(f"Would ingest {len(files)} pattern(s)")
    else:
        logger.info(f"Ingested {ingested}, errors {errors}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
