from __future__ import annotations

from ai.rag.embedder import embed_single
from ai.rag.pattern_store import (
    VALID_ARCHETYPES,
    VALID_DOMAINS,
    VALID_LANGUAGES,
    VALID_PATTERN_SCOPES,
    VALID_SEMANTIC_ROLES,
    get_or_create_table,
)


def search_patterns(
    query: str,
    language: str | None = None,
    domain: str | None = None,
    archetype: str | None = None,
    pattern_scope: str | None = None,
    semantic_role: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Semantic search over code_patterns with optional filters.

    Supports standard filters (language, domain) and frontend-specific
    filters (archetype, pattern_scope, semantic_role) for targeted
    pattern retrieval.
    """
    if not query or not query.strip():
        return []

    # Validate filters
    if language:
        language = language.lower().strip()
        if language not in VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {language!r}. Valid: {sorted(VALID_LANGUAGES)}")
    if domain:
        domain = domain.lower().strip()
        if domain not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain!r}. Valid: {sorted(VALID_DOMAINS)}")
    if archetype:
        archetype = archetype.lower().strip()
        if archetype not in VALID_ARCHETYPES:
            raise ValueError(f"Invalid archetype: {archetype!r}. Valid: {sorted(VALID_ARCHETYPES)}")
    if pattern_scope:
        pattern_scope = pattern_scope.lower().strip()
        if pattern_scope not in VALID_PATTERN_SCOPES:
            scopes = sorted(VALID_PATTERN_SCOPES)
            raise ValueError(f"Invalid pattern_scope: {pattern_scope!r}. Valid: {scopes}")
    if semantic_role:
        semantic_role = semantic_role.lower().strip()
        if semantic_role not in VALID_SEMANTIC_ROLES:
            roles = sorted(VALID_SEMANTIC_ROLES)
            raise ValueError(f"Invalid semantic_role: {semantic_role!r}. Valid: {roles}")

    table = get_or_create_table()
    vector = embed_single(query.strip())

    search = table.search(vector).limit(limit)

    filters = []
    if language:
        filters.append(f"language = '{language}'")
    if domain:
        filters.append(f"domain = '{domain}'")
    if archetype:
        filters.append(f"archetype = '{archetype}'")
    if pattern_scope:
        filters.append(f"pattern_scope = '{pattern_scope}'")
    if semantic_role:
        filters.append(f"semantic_role = '{semantic_role}'")
    if filters:
        search = search.where(" AND ".join(filters))

    results = search.to_list()

    return [{k: v for k, v in r.items() if k != "vector"} for r in results]
