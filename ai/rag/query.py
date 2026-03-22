"""RAG query engine for security intelligence.

Embeds a user question, searches LanceDB for relevant context from scan
logs, health snapshots, and threat intel, then optionally augments the
answer via LLM routing.

Usage:
    from ai.rag.query import rag_query
    result = rag_query("What threats were detected last week?")

CLI:
    python -m ai.rag "What GPU temps were recorded?"
"""

import json
import logging
from dataclasses import dataclass, field

from ai.config import APP_NAME
from ai.rate_limiter import RateLimiter
from ai.router import route_query

logger = logging.getLogger(APP_NAME)

_SYSTEM_PROMPT = (
    "You are a security analyst for a Bazzite 43 gaming laptop "
    "(Acer Predator G3-571, GTX 1060, Intel HD 630). "
    "Answer based ONLY on the provided context. "
    "If the context does not contain enough information, say so. "
    "Be concise and cite sources when possible."
)


@dataclass
class QueryResult:
    """Result container for a RAG query."""

    question: str
    context_chunks: list[dict] = field(default_factory=list)
    answer: str = ""
    sources: list[str] = field(default_factory=list)
    model_used: str = "context-only"


def rag_query(
    question: str,
    limit: int = 5,
    use_llm: bool = True,
    rate_limiter: RateLimiter | None = None,
) -> QueryResult:
    """Execute a RAG query against the security knowledge base.

    Steps:
    1. Embed the question using embed_single(text, input_type="search_query")
    2. Search both security_logs and threat_intel tables
    3. Merge and rank results by distance
    4. If use_llm=True, build a prompt with context and route to LLM
    5. If use_llm=False, return raw context as the answer

    Args:
        question: Natural language query.
        limit: Max results per table.
        use_llm: Whether to generate an LLM answer.
        rate_limiter: Optional rate limiter for embedding + LLM calls.

    Returns:
        QueryResult with answer and source references.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    # Lazy imports to avoid pyarrow/lancedb segfault at collection time
    from ai.rag.embedder import embed_single  # noqa: PLC0415
    from ai.rag.store import get_store  # noqa: PLC0415

    # Step 1: embed the question
    logger.info("Embedding query: %s", question[:80])
    query_vector = embed_single(question, input_type="search_query")

    # Step 2: search all tables
    store = get_store()
    log_results = _safe_search(store, "search_logs", query_vector, limit)
    threat_results = _safe_search(store, "search_threats", query_vector, limit)
    doc_results = _safe_search(store, "search_docs", query_vector, limit)

    # Step 3: merge and rank by _distance (ascending = most similar)
    all_chunks = log_results + threat_results + doc_results
    all_chunks.sort(key=lambda c: c.get("_distance", float("inf")))

    # Step 3.5: Cohere rerank (only when LLM synthesis is requested)
    if use_llm and all_chunks:
        all_chunks = _cohere_rerank(question, all_chunks, rate_limiter)

    # Collect unique sources
    sources = _extract_sources(all_chunks)

    # Step 4/5: build answer
    context_str = _build_context(all_chunks)

    if not all_chunks:
        return QueryResult(
            question=question,
            context_chunks=all_chunks,
            answer="No relevant context found in the knowledge base.",
            sources=sources,
            model_used="context-only",
        )

    if not use_llm:
        return QueryResult(
            question=question,
            context_chunks=all_chunks,
            answer=context_str,
            sources=sources,
            model_used="context-only",
        )

    # Route to LLM
    prompt = _build_prompt(question, context_str)
    try:
        llm_answer = route_query("fast", prompt)

        # Detect scaffold response and fall back to context-only
        if "[SCAFFOLD]" in llm_answer:
            logger.info("Router returned scaffold response, using context-only mode")
            return QueryResult(
                question=question,
                context_chunks=all_chunks,
                answer=context_str,
                sources=sources,
                model_used="context-only",
            )

        return QueryResult(
            question=question,
            context_chunks=all_chunks,
            answer=llm_answer,
            sources=sources,
            model_used="fast",
        )
    except (RuntimeError, ValueError) as e:
        logger.warning("LLM routing failed: %s — falling back to context-only", e)
        return QueryResult(
            question=question,
            context_chunks=all_chunks,
            answer=context_str,
            sources=sources,
            model_used="context-only",
        )


def _cohere_rerank(
    question: str,
    chunks: list[dict],
    rate_limiter: RateLimiter,
    top_n: int = 5,
) -> list[dict]:
    """Reorder chunks by Cohere rerank relevance score.

    Only runs when COHERE_API_KEY is set and rate limits allow.
    Falls back to original order on any error.
    """
    import os  # noqa: PLC0415

    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        return chunks

    if not rate_limiter.can_call("cohere_rerank"):
        logger.warning("Cohere rerank rate limit reached, using original order")
        return chunks

    try:
        import cohere  # noqa: PLC0415

        co = cohere.ClientV2(api_key)
        documents = [c.get("text", c.get("content", "")) for c in chunks]
        response = co.rerank(
            model="rerank-english-v3.0",
            query=question,
            documents=documents,
            top_n=min(top_n, len(chunks)),
        )
        rate_limiter.record_call("cohere_rerank")
        return [chunks[r.index] for r in response.results]
    except Exception as e:
        logger.warning("Cohere rerank failed: %s — using original order", e)
        return chunks


def _safe_search(
    store: object, method_name: str, vector: list[float], limit: int
) -> list[dict]:
    """Call a store search method, returning empty list on failure."""
    try:
        fn = getattr(store, method_name)
        return fn(vector, limit=limit)
    except Exception:
        logger.exception("Search failed for %s", method_name)
        return []


def _extract_sources(chunks: list[dict]) -> list[str]:
    """Extract unique source identifiers from result chunks."""
    seen: set[str] = set()
    sources: list[str] = []
    for chunk in chunks:
        source = chunk.get("source_file") or chunk.get("source")
        if not source:
            # For threat_intel results, use hash as source identifier
            hash_val = chunk.get("hash", "")
            source = f"threat:{hash_val}" if hash_val else ""
        if source and source not in seen:
            seen.add(source)
            sources.append(source)
    return sources


def _build_context(chunks: list[dict]) -> str:
    """Format search result chunks into a context string for LLM prompting.

    Each chunk is formatted as:
        [source | section] content
    """
    if not chunks:
        return ""

    lines: list[str] = []
    for chunk in chunks:
        source = chunk.get("source_file") or chunk.get("source") or ""
        if not source:
            hash_val = chunk.get("hash", "")
            source = f"threat:{hash_val}" if hash_val else "unknown"
        section = chunk.get("section", "")
        content = chunk.get("text", chunk.get("content", ""))
        distance = chunk.get("_distance")

        header = f"[{source}"
        if section:
            header += f" | {section}"
        header += "]"

        line = f"{header} {content}"
        if distance is not None:
            line += f"  (distance: {distance:.4f})"
        lines.append(line)

    return "\n\n".join(lines)


def _build_prompt(question: str, context: str) -> str:
    """Build the system+user prompt for the LLM.

    System prompt establishes the AI as a security analyst for a Bazzite
    gaming laptop. Context is injected. Question is the user query.
    """
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
        f"Question: {question}"
    )


def format_result(result: QueryResult, fmt: str = "text") -> str:
    """Format a QueryResult for display.

    Args:
        result: The QueryResult to format.
        fmt: Output format — "text" for plain text, "json" for JSON.

    Returns:
        Formatted string.
    """
    if fmt == "json":
        return json.dumps(
            {
                "question": result.question,
                "answer": result.answer,
                "sources": result.sources,
                "model_used": result.model_used,
                "context_chunks": result.context_chunks,
            },
            indent=2,
        )

    # Plain text format
    lines = [
        f"Question: {result.question}",
        f"Model: {result.model_used}",
        "",
        "Answer:",
        result.answer,
        "",
        f"Sources ({len(result.sources)}):",
    ]
    for src in result.sources:
        lines.append(f"  - {src}")
    if not result.sources:
        lines.append("  (none)")

    return "\n".join(lines)
