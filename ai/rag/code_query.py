"""Code-aware RAG query engine.

Searches only the code_files LanceDB table (built by ai.rag.ingest_code).
Optionally synthesizes an LLM answer using the 'code' task type.

Usage:
    from ai.rag.code_query import code_rag_query
    result = code_rag_query("How does route_query work?")

    from ai.rag.code_query import code_fused_context
    result = code_fused_context("How does route_query connect to impact analysis?")
"""

import hashlib
import logging
from pathlib import Path

from ai.config import APP_NAME
from ai.rag.constants import CODE_TABLE

logger = logging.getLogger(APP_NAME)

_SYSTEM_PROMPT = (
    "You are a senior Python developer reviewing the Bazzite gaming laptop AI codebase. "
    "Answer based ONLY on the code context provided. "
    "Reference specific files and functions by name. "
    "If the context does not contain the answer, say so."
)

_INDEX_NOT_BUILT = "Code index not built yet. Run: python -m ai.rag.ingest_code --repo-root ."


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


def code_fused_context(question: str, limit: int = 5) -> dict:
    """Retrieve fused semantic + structural + learned code context.

    P74 fusion layer implementation that bridges:
    - semantic code chunks (`code_files`)
    - structural nodes/relationships (`code_nodes`, `relationships`)
    - task patterns (`task_patterns`)
    - phase/session artifacts (`HANDOFF.md`, docs phase artifacts)
    """
    semantic = code_rag_query(question, use_llm=False, limit=limit)
    from ai.code_intel.store import get_code_store  # noqa: PLC0415
    from ai.learning.handoff_parser import parse_handoff  # noqa: PLC0415
    from ai.learning.task_retriever import retrieve_similar_tasks  # noqa: PLC0415

    store = get_code_store()
    fused_results = []

    for chunk in semantic.get("results", []):
        rel_path = _normalize_path(str(chunk.get("relative_path", "") or ""))
        symbol_name = str(chunk.get("symbol_name", "") or "")
        line_start = int(chunk.get("line_start", 0) or 0)
        line_end = int(chunk.get("line_end", 0) or 0)

        stable_id = _stable_chunk_id(rel_path, symbol_name, line_start, line_end)
        mapped_nodes = store.map_code_chunk_to_nodes(
            relative_path=rel_path,
            symbol_name=symbol_name,
            line_start=line_start,
            line_end=line_end,
            limit=2,
        )

        structural = {
            "mapped_nodes": mapped_nodes,
            "relationships": [],
            "callers": [],
            "dependency_graph": {},
            "class_hierarchy": {},
        }

        if mapped_nodes:
            primary = mapped_nodes[0]
            node_id = primary.get("node_id", "")
            node_name = primary.get("qualified_name", "")
            structural["relationships"] = store.get_node_relationship_neighbors(node_id, limit=15)
            structural["callers"] = store.find_callers(node_name, include_indirect=False)[:10]

            module = _module_from_relative_path(rel_path)
            if module:
                structural["dependency_graph"] = store.query_dependency_graph(
                    module,
                    direction="both",
                    max_depth=2,
                )

            if primary.get("node_type") == "class":
                structural["class_hierarchy"] = store.get_class_hierarchy(node_name)

        fused_results.append(
            {
                "stable_id": stable_id,
                "semantic": chunk,
                "structural": structural,
            }
        )

    task_patterns = retrieve_similar_tasks(question, top_k=3)
    session_entries = _query_session_history(question, limit=3, parser=parse_handoff)
    phase_artifacts = _query_phase_artifacts(question, limit=5)

    return {
        "question": question,
        "results": semantic.get("results", []),
        "fused_results": fused_results,
        "task_patterns": task_patterns,
        "session_artifacts": session_entries,
        "phase_artifacts": phase_artifacts,
        "model_used": semantic.get("model_used", "context-only"),
        "answer": "",
    }


def _normalize_path(path: str) -> str:
    p = path.replace("\\", "/")
    marker = "/bazzite-laptop/"
    if marker in p:
        p = p.split(marker, 1)[1]
    return p.lstrip("./")


def _module_from_relative_path(path: str) -> str:
    p = _normalize_path(path)
    if not p.endswith(".py"):
        return ""
    if p.endswith("/__init__.py"):
        p = p[: -len("/__init__.py")]
    else:
        p = p[:-3]
    return p.replace("/", ".")


def _stable_chunk_id(path: str, symbol: str, line_start: int, line_end: int) -> str:
    payload = f"{_normalize_path(path)}|{symbol}|{line_start}|{line_end}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _query_session_history(question: str, limit: int, parser) -> list[dict]:
    handoff_path = Path(__file__).resolve().parent.parent.parent / "HANDOFF.md"
    if not handoff_path.exists():
        return []
    query = question.lower().strip()
    entries = parser(handoff_path)
    matches = []
    for entry in entries:
        summary = getattr(entry, "summary", "") or ""
        done = " ".join(getattr(entry, "done_tasks", []) or [])
        hay = f"{summary} {done}".lower()
        if not query or query in hay:
            matches.append(
                {
                    "timestamp": getattr(entry, "timestamp", ""),
                    "agent": getattr(entry, "agent", ""),
                    "summary": summary,
                    "done_tasks": list(getattr(entry, "done_tasks", []) or []),
                }
            )
    return matches[:limit]


def _query_phase_artifacts(question: str, limit: int) -> list[dict]:
    docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
    if not docs_dir.exists():
        return []
    terms = [t for t in question.lower().split() if len(t) >= 4]
    candidates = sorted(
        list(docs_dir.glob("P*_PLAN.md")) + list(docs_dir.glob("P*_COMPLETION_REPORT.md")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out = []
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug("Failed to read phase artifact %s: %s", path, e)
            continue
        content_lower = content.lower()
        score = sum(1 for t in terms if t in content_lower)
        if terms and score == 0:
            continue
        out.append(
            {
                "path": str(path.relative_to(Path(__file__).resolve().parent.parent.parent)),
                "match_score": score,
            }
        )
        if len(out) >= limit:
            break
    if not out and candidates:
        # Always provide a small artifact baseline for context continuity.
        for path in candidates[: min(3, limit)]:
            out.append(
                {
                    "path": str(path.relative_to(Path(__file__).resolve().parent.parent.parent)),
                    "match_score": 0,
                }
            )
    return out
