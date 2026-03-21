"""Ingest markdown documentation into LanceDB for RAG queries.

Reads .md files, splits by ## headers into sections, embeds each section,
and stores in a 'docs' table in LanceDB. Uses a state file to skip
files that haven't changed since last ingest.

Usage:
    python -m ai.rag.ingest_docs docs/*.md docs/reference/*.md
    python -m ai.rag.ingest_docs --dir docs/
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

from ai.config import APP_NAME, VECTOR_DB_DIR, setup_logging

logger = logging.getLogger(APP_NAME)

_STATE_FILE = VECTOR_DB_DIR / ".doc-ingest-state.json"

# nomic-embed-text context window is 8192 tokens (~2000 words/token ratio varies,
# but 1500 words ≈ 6000 tokens gives safe headroom)
MAX_CHUNK_WORDS = 1000

# Infer doc_type from filename patterns
_DOC_TYPE_PATTERNS = [
    (re.compile(r"troubleshoot", re.I), "troubleshooting"),
    (re.compile(r"config|snapshot", re.I), "config"),
    (re.compile(r"guide|optimization|speed", re.I), "guide"),
    (re.compile(r"audit|security", re.I), "audit"),
    (re.compile(r"readme|implementation|health", re.I), "reference"),
    (re.compile(r"onboarding|instruction", re.I), "reference"),
]


def _infer_doc_type(filename: str) -> str:
    """Infer document type from filename."""
    for pattern, doc_type in _DOC_TYPE_PATTERNS:
        if pattern.search(filename):
            return doc_type
    return "reference"


def _file_hash(path: Path) -> str:
    """SHA256 of file contents for dedup."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_state() -> dict:
    """Load the ingest state (file hashes from last run)."""
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict) -> None:
    """Atomically save the ingest state."""
    import tempfile  # noqa: PLC0415

    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(_STATE_FILE.parent),
        prefix=".doc-ingest-state-",
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


def _split_oversized(content: str, section_title: str, base: dict) -> list[dict]:
    """Split a single oversized chunk into sub-chunks by paragraph.

    Accumulates paragraphs until adding the next one would exceed
    MAX_CHUNK_WORDS, then starts a new sub-chunk. Sub-chunks are titled
    "Original Title (part N)".
    """
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    sub_chunks: list[dict] = []
    current_parts: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if (current_words + para_words > MAX_CHUNK_WORDS or len("\n\n".join(current_parts)) > 4000) and current_parts:
            part_num = len(sub_chunks) + 1
            sub_chunks.append({
                **base,
                "id": str(uuid4()),
                "section_title": f"{section_title} (part {part_num})",
                "content": "\n\n".join(current_parts),
            })
            current_parts = []
            current_words = 0
        current_parts.append(para)
        current_words += para_words

    if current_parts:
        # If only one part was produced, keep the original title
        part_num = len(sub_chunks) + 1
        title = f"{section_title} (part {part_num})" if sub_chunks else section_title
        sub_chunks.append({
            **base,
            "id": str(uuid4()),
            "section_title": title,
            "content": "\n\n".join(current_parts),
        })

    return sub_chunks


def chunk_markdown(text: str, source_file: str) -> list[dict]:
    """Split markdown text into sections by ## headers.

    Any section exceeding MAX_CHUNK_WORDS is further split by paragraph
    into sub-chunks so embeddings stay within the model's context window.

    Returns a list of dicts with keys: source_file, section_title,
    doc_type, content.
    """
    doc_type = _infer_doc_type(source_file)
    chunks: list[dict] = []

    # Split on ## headers (keep the header with its section)
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract section title from ## header if present
        header_match = re.match(r"^##\s+(.+?)$", section, re.MULTILINE)
        section_title = header_match.group(1).strip() if header_match else "Introduction"

        # Skip very short sections (just a header with no content)
        if len(section) < 20:
            continue

        base = {
            "source_file": source_file,
            "section_title": section_title,
            "doc_type": doc_type,
        }

        if len(section.split()) > MAX_CHUNK_WORDS or len(section) > 5000:
            chunks.extend(_split_oversized(section, section_title, base))
        else:
            chunks.append({"id": str(uuid4()), **base, "content": section})

    return chunks


def ingest_files(paths: list[Path], force: bool = False) -> dict:
    """Ingest markdown files into LanceDB docs table.

    Args:
        paths: List of markdown file paths to ingest.
        force: If True, re-ingest even if file hash hasn't changed.

    Returns:
        Dict with keys: files_processed, files_skipped, chunks_created.
    """
    from ai.rag.embedder import embed_texts, select_provider  # noqa: PLC0415
    from ai.rag.store import get_store  # noqa: PLC0415

    state = {} if force else _load_state()
    store = get_store()

    # Lock to a single provider for the entire run to avoid dimension mismatch
    provider = select_provider()

    files_processed = 0
    files_skipped = 0
    chunks_created = 0
    all_chunks: list[dict] = []

    for path in paths:
        path = Path(path).resolve()
        if not path.exists() or not path.suffix == ".md":
            logger.warning("Skipping %s (not found or not .md)", path)
            continue

        file_hash = _file_hash(path)
        state_key = str(path)

        if not force and state.get(state_key) == file_hash:
            files_skipped += 1
            continue

        logger.info("Processing: %s", path.name)
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, path.name)

        if not chunks:
            logger.warning("No sections found in %s", path.name)
            continue

        all_chunks.extend(chunks)
        state[state_key] = file_hash
        files_processed += 1

    # Embed all chunks in batches
    if all_chunks:
        texts = [c["content"] for c in all_chunks]
        # Embed in batches of 20 to avoid overwhelming Ollama
        batch_size = 1
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = embed_texts(batch, provider=provider)
            all_vectors.extend(vectors)

        for chunk, vector in zip(all_chunks, all_vectors, strict=True):
            chunk["vector"] = vector

        added = store.add_doc_chunks(all_chunks)
        chunks_created = added

    if chunks_created > 0:
        _save_state(state)

    return {
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "chunks_created": chunks_created,
    }


def ingest_directory(directory: Path, force: bool = False) -> dict:
    """Find all .md files in a directory (non-recursive) and ingest them."""
    md_files = sorted(directory.glob("*.md"))
    return ingest_files(md_files, force=force)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest markdown docs into RAG vector database",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Markdown files to ingest",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory to scan for .md files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if files haven't changed",
    )
    args = parser.parse_args()

    setup_logging()

    paths: list[Path] = []
    if args.dir:
        paths.extend(sorted(args.dir.glob("*.md")))
        # Also check reference/ subdirectory
        ref_dir = args.dir / "reference"
        if ref_dir.is_dir():
            paths.extend(sorted(ref_dir.glob("*.md")))
    if args.files:
        paths.extend(Path(f) for f in args.files)

    if not paths:
        print("No files specified. Use --dir docs/ or pass file paths.")  # noqa: T201
        sys.exit(1)

    print(f"Found {len(paths)} markdown file(s) to process...")  # noqa: T201

    result = ingest_files(paths, force=args.force)

    print(  # noqa: T201
        f"Done: {result['files_processed']} processed, "
        f"{result['files_skipped']} skipped (unchanged), "
        f"{result['chunks_created']} chunks embedded"
    )


if __name__ == "__main__":
    main()
