"""Ingest Python source files into LanceDB for code-aware RAG queries.

Walks a repo root, splits each .py file on function/class boundaries,
embeds each symbol chunk, and stores them in the 'code_files' LanceDB table.
Uses file mtime to skip unchanged files on subsequent runs.

Usage:
    python -m ai.rag.ingest_code --repo-root .
    python -m ai.rag.ingest_code --repo-root . --force
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

from ai.config import APP_NAME, VECTOR_DB_DIR, setup_logging
from ai.rag.constants import (
    MAX_BYTES_PER_DOC,
    MAX_DOCS_PER_RUN,
    MAX_TOTAL_BYTES,
)

logger = logging.getLogger(APP_NAME)

_STATE_FILE = VECTOR_DB_DIR / ".code-ingest-state.json"

# Directories to exclude when walking the repo
_EXCLUDE_DIRS = frozenset({
    ".venv", "__pycache__", ".git", "node_modules",
    ".pytest_cache", "dist", "build", ".mypy_cache", ".ruff_cache",
})

# Max words per chunk before truncation
_MAX_CHUNK_WORDS = 1000

# Regex to find top-level def/class (column 0 only)
_TOP_LEVEL_DEF = re.compile(r"^(def |class )(\w+)", re.MULTILINE)


# ── State file ──

def _load_state() -> dict:
    """Load mtime state from disk. Returns empty dict on missing/corrupt file."""
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict) -> None:
    """Atomically save mtime state to disk."""
    import tempfile  # noqa: PLC0415

    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(_STATE_FILE.parent),
        prefix=".code-ingest-state-",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.rename(tmp, str(_STATE_FILE))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── File discovery ──

def discover_python_files(repo_root: Path) -> list[Path]:
    """Walk repo_root and return all .py files, respecting _EXCLUDE_DIRS.

    Returns paths sorted for deterministic ordering.
    """
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # Prune excluded directories in-place so os.walk won't descend into them
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for filename in filenames:
            if filename.endswith(".py"):
                results.append(Path(dirpath) / filename)
    return sorted(results)


# ── Code-aware chunking ──

def chunk_python_file(text: str, relative_path: str, repo_root: str) -> list[dict]:
    """Split a Python file into per-symbol chunks on function/class boundaries.

    Each top-level def/class becomes one chunk, with the file header
    (imports, module docstring, top-level constants) prepended as context.
    Files with no top-level definitions produce a single '__module__' chunk.

    Chunks exceeding _MAX_CHUNK_WORDS are word-truncated with a marker.

    Args:
        text: Full file source text.
        relative_path: Path relative to repo root (used as metadata).
        repo_root: Absolute path of the repo root (stored as metadata).

    Returns:
        List of chunk dicts ready for embedding (no 'vector' key yet).
    """
    lines = text.splitlines()

    # Collect top-level def/class positions
    boundaries: list[tuple[int, str]] = []  # (0-indexed line, symbol_name)
    for i, line in enumerate(lines):
        m = _TOP_LEVEL_DEF.match(line)
        if m:
            boundaries.append((i, m.group(2)))

    base = {
        "relative_path": relative_path,
        "repo_root": repo_root,
        "language": "python",
    }

    if not boundaries:
        return [_make_chunk(base, "__module__", 1, len(lines), text.strip())]

    # File header: everything before the first top-level symbol
    header_lines = lines[: boundaries[0][0]]
    header = "\n".join(header_lines).strip()

    chunks: list[dict] = []
    for idx, (line_start, symbol_name) in enumerate(boundaries):
        line_end = boundaries[idx + 1][0] - 1 if idx + 1 < len(boundaries) else len(lines) - 1
        body = "\n".join(lines[line_start : line_end + 1])
        content = f"{header}\n\n{body}".strip() if header else body
        chunks.append(_make_chunk(base, symbol_name, line_start + 1, line_end + 1, content))

    return chunks


def _make_chunk(
    base: dict,
    symbol_name: str,
    line_start: int,
    line_end: int,
    content: str,
) -> dict:
    """Build a chunk dict, truncating content if it exceeds _MAX_CHUNK_WORDS."""
    words = content.split()
    if len(words) > _MAX_CHUNK_WORDS:
        content = " ".join(words[:_MAX_CHUNK_WORDS]) + " ...[truncated]"
    return {
        **base,
        "id": str(uuid4()),
        "symbol_name": symbol_name,
        "line_start": line_start,
        "line_end": line_end,
        "content": content,
    }


# ── Ingestion ──

def ingest_files(
    paths: list[Path],
    repo_root: Path,
    force: bool = False,
) -> dict:
    """Ingest Python files into the code_files LanceDB table.

    Args:
        paths: List of .py file paths to process.
        repo_root: Repo root used to compute relative paths and as metadata.
        force: If True, re-ingest even if mtime hasn't changed.

    Returns:
        Dict with keys: processed, skipped_unchanged, skipped_size,
        skipped_deferred, total_chunks.
    """
    from ai.rag.embedder import embed_texts, select_provider  # noqa: PLC0415
    from ai.rag.store import get_store  # noqa: PLC0415

    state = {} if force else _load_state()
    store = get_store()
    provider = select_provider()

    repo_root_str = str(repo_root.resolve())
    processed = 0
    skipped_unchanged = 0
    skipped_size = 0
    skipped_deferred = 0
    total_bytes = 0
    all_chunks: list[dict] = []
    new_state: dict = {}

    for path in paths:
        path = Path(path).resolve()
        if not path.exists() or path.suffix != ".py":
            logger.warning("Skipping %s (not found or not .py)", path)
            continue

        # Size cap — checked before reading
        file_size = path.stat().st_size
        if file_size > MAX_BYTES_PER_DOC:
            logger.warning(
                "Skipping %s (%.1f KB > %d KB limit)",
                path.name, file_size / 1024, MAX_BYTES_PER_DOC // 1024,
            )
            skipped_size += 1
            continue

        # Mtime dedup
        try:
            rel_path = str(path.relative_to(repo_root.resolve()))
        except ValueError:
            rel_path = str(path)
        mtime = path.stat().st_mtime

        if not force and state.get(rel_path) == mtime:
            skipped_unchanged += 1
            continue

        # Doc count cap
        if processed >= MAX_DOCS_PER_RUN:
            if skipped_deferred == 0:
                logger.info(
                    "Reached max docs per run (%d), deferring remaining files",
                    MAX_DOCS_PER_RUN,
                )
            skipped_deferred += 1
            continue

        # Total bytes cap
        if total_bytes + file_size > MAX_TOTAL_BYTES:
            if skipped_deferred == 0:
                logger.info(
                    "Reached max total bytes (%d MB), deferring remaining files",
                    MAX_TOTAL_BYTES // 1_000_000,
                )
            skipped_deferred += 1
            continue

        logger.info("Processing: %s", rel_path)
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_python_file(text, rel_path, repo_root_str)

        if not chunks:
            logger.warning("No chunks produced for %s", rel_path)
            continue

        all_chunks.extend(chunks)
        new_state[rel_path] = mtime
        processed += 1
        total_bytes += file_size

    if skipped_deferred:
        logger.info(
            "Reached cap, %d files deferred (processed %d / max %d)",
            skipped_deferred, processed, MAX_DOCS_PER_RUN,
        )

    # Embed and store
    chunks_created = 0
    if all_chunks:
        texts = [c["content"] for c in all_chunks]
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), 1):
            batch = texts[i : i + 1]
            vectors = embed_texts(batch, provider=provider)
            all_vectors.extend(vectors)

        for chunk, vector in zip(all_chunks, all_vectors, strict=True):
            chunk["vector"] = vector

        chunks_created = store.add_code_chunks(all_chunks)

    if new_state and chunks_created > 0:
        merged = {} if force else _load_state()
        merged.update(new_state)
        _save_state(merged)

    return {
        "processed": processed,
        "skipped_unchanged": skipped_unchanged,
        "skipped_size": skipped_size,
        "skipped_deferred": skipped_deferred,
        "total_chunks": chunks_created,
    }


def ingest_repo(repo_root: Path, force: bool = False) -> dict:
    """Discover all .py files under repo_root and ingest them."""
    paths = discover_python_files(repo_root)
    return ingest_files(paths, repo_root, force=force)


# ── CLI ──

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest Python source files into RAG code_files table",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Root of the repository to index (default: current dir)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest all files, ignoring mtime state",
    )
    args = parser.parse_args()

    setup_logging()

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print(f"Error: {repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    t0 = time.monotonic()
    paths = discover_python_files(repo_root)
    print(f"Found {len(paths)} Python file(s) under {repo_root}")  # noqa: T201

    result = ingest_files(paths, repo_root, force=args.force)
    elapsed = time.monotonic() - t0

    parts = [
        f"{result['processed']} processed",
        f"{result['skipped_unchanged']} skipped (unchanged)",
        f"{result['total_chunks']} chunks embedded",
        f"{elapsed:.1f}s",
    ]
    if result["skipped_size"]:
        parts.append(f"{result['skipped_size']} skipped (too large)")
    if result["skipped_deferred"]:
        parts.append(f"{result['skipped_deferred']} deferred (cap hit)")
    print(f"Done: {', '.join(parts)}")  # noqa: T201


if __name__ == "__main__":
    main()
