from __future__ import annotations

from ai.rag.embedder import embed_single
from ai.rag.pattern_store import get_or_create_table

VALID_LANGUAGES = {"python", "rust", "javascript", "bash", "c", "yaml"}
VALID_DOMAINS = {"security", "networking", "systems", "data", "web", "testing"}


def search_patterns(
    query: str,
    language: str | None = None,
    domain: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Semantic search over code_patterns with optional language/domain filters."""
    if not query or not query.strip():
        return []

    if language:
        language = language.lower().strip()
        if language not in VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {language!r}. Valid: {sorted(VALID_LANGUAGES)}")
    if domain:
        domain = domain.lower().strip()
        if domain not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain!r}. Valid: {sorted(VALID_DOMAINS)}")

    table = get_or_create_table()
    vector = embed_single(query.strip())

    search = table.search(vector).limit(limit)

    filters = []
    if language:
        filters.append(f"language = '{language}'")
    if domain:
        filters.append(f"domain = '{domain}'")
    if filters:
        search = search.where(" AND ".join(filters))

    results = search.to_list()

    return [{k: v for k, v in r.items() if k != "vector"} for r in results]
