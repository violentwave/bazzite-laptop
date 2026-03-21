"""Code-aware RAG query engine.

Searches only the code_files LanceDB table (built by ai.rag.ingest_code).
Optionally synthesizes an LLM answer using the 'code' task type.

Usage:
    from ai.rag.code_query import code_rag_query
    result = code_rag_query("How does route_query work?")
"""

import logging

from ai.config import APP_NAME
from ai.rag.constants import CODE_TABLE

logger = logging.getLogger(APP_NAME)

_SYSTEM_PROMPT = (
    "You are a senior Python developer reviewing the Bazzite gaming laptop AI codebase. "
    "Answer based ONLY on the code context provided. "
    "Reference specific files and functions by name. "
    "If the context does not contain the answer, say so."
)

_INDEX_NOT_BUILT = (
    "Code index not built yet. Run: python -m ai.rag.ingest_code --repo-root ."
)


def code_rag_query(
    question: str,
    use_llm: bool = False,
    limit: int = 5,
) -> dict:
    """Search the code_files LanceDB table for relevant code chunks.

    Args:
        question: Natural language query about the codebase.
        use_llm: If True, synthesize an LLM answer using the 'code' task type.
        limit: Maximum number of results to return.

    Returns:
        Dict with keys: question, results, answer, model_used.
        results is a list of dicts with: relative_path, symbol_name,
        line_start, line_end, content, distance.
    """
    from ai.rag.embedder import embed_single  # noqa: PLC0415
    from ai.rag.store import get_store  # noqa: PLC0415

    store = get_store()

    # Check if the index has been built (count returns 0 for missing/empty table)
    if store.count(CODE_TABLE) == 0:
        return {
            "question": question,
            "results": [],
            "answer": _INDEX_NOT_BUILT,
            "model_used": "context-only",
        }

    # Embed the question
    logger.info("Embedding code query: %s", question[:80])
    query_vector = embed_single(question, input_type="search_query")

    # Search code_files table
    raw_results = store.search_code(query_vector, limit=limit)

    results = [
        {
            "relative_path": r.get("relative_path", ""),
            "symbol_name": r.get("symbol_name", ""),
            "line_start": r.get("line_start", 0),
            "line_end": r.get("line_end", 0),
            "content": r.get("content", ""),
            "distance": r.get("_distance"),
        }
        for r in raw_results
    ]

    if not use_llm:
        return {
            "question": question,
            "results": results,
            "answer": "",
            "model_used": "context-only",
        }

    # LLM synthesis over code context
    from ai.router import route_query  # noqa: PLC0415

    context = "\n\n".join(
        f"[{r['relative_path']} | {r['symbol_name']} "
        f"L{r['line_start']}-{r['line_end']}]\n{r['content']}"
        for r in results
    )
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"--- CODE CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
        f"Question: {question}"
    )

    try:
        answer = route_query("code", prompt)
        if "[SCAFFOLD]" in answer:
            logger.info("Router returned scaffold response, using context-only mode")
            answer = ""
            model_used = "context-only"
        else:
            model_used = "code"
    except (RuntimeError, ValueError) as e:
        logger.warning("LLM routing failed: %s — returning context-only", e)
        answer = ""
        model_used = "context-only"

    return {
        "question": question,
        "results": results,
        "answer": answer,
        "model_used": model_used,
    }
