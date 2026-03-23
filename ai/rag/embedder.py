"""Embedding generation for the RAG pipeline.

Primary:   Gemini Embedding 001 (cloud, free tier, 768-dim via Matryoshka)
Fallback:  Cohere embed-english-v3.0 (cloud, rate-limited)
Emergency: Ollama nomic-embed-text (local, no VRAM budget for routine use)

Usage:
    from ai.rag.embedder import embed_texts
    vectors = embed_texts(["text1", "text2"])
"""

import logging
import time

import cohere
import httpx
import litellm
import ollama

from ai.config import APP_NAME, get_key, load_keys
from ai.rag.constants import EMBEDDING_DIM
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

GEMINI_EMBED_MODEL = "gemini/gemini-embedding-001"
COHERE_MODEL = "embed-english-v3.0"
OLLAMA_MODEL = "nomic-embed-text"

# Gemini Embedding 001: single input per call limitation
_GEMINI_BATCH_DELAY_S = 0.1  # 100 ms between calls during bulk ingestion
_GEMINI_RETRY_WAIT_S = 2.0   # 2 s wait on 429 before retry
_GEMINI_MAX_RETRIES = 3

_INPUT_TYPE_TO_GEMINI_TASK = {
    "search_document": "RETRIEVAL_DOCUMENT",
    "search_query": "RETRIEVAL_QUERY",
}


def _embed_gemini(
    texts: list[str],
    rate_limiter: RateLimiter | None = None,
    input_type: str = "search_document",
) -> list[list[float]] | None:
    """Generate embeddings via Gemini Embedding 001 (LiteLLM).

    Gemini accepts only ONE input text per call, so we loop with a small
    inter-call delay to stay within the free-tier burst limit.
    Returns None if GEMINI_API_KEY is missing or all calls fail.
    """
    load_keys()
    api_key = get_key("GEMINI_API_KEY")
    if api_key is None:
        logger.debug("GEMINI_API_KEY not set, skipping Gemini embed")
        return None

    if rate_limiter is not None and not rate_limiter.can_call("gemini_embed"):
        logger.warning("Gemini embed rate limit reached, skipping primary")
        return None

    task_type = _INPUT_TYPE_TO_GEMINI_TASK.get(input_type, "RETRIEVAL_DOCUMENT")
    vectors: list[list[float]] = []

    for i, text in enumerate(texts):
        if i > 0:
            time.sleep(_GEMINI_BATCH_DELAY_S)

        last_exc: Exception | None = None
        for attempt in range(_GEMINI_MAX_RETRIES):
            try:
                response = litellm.embedding(
                    model=GEMINI_EMBED_MODEL,
                    input=[text],
                    dimensions=768,
                    task_type=task_type,
                )
                vectors.append(response.data[0]["embedding"])
                if rate_limiter is not None:
                    rate_limiter.record_call("gemini_embed")
                break
            except litellm.RateLimitError:
                wait = _GEMINI_RETRY_WAIT_S * (attempt + 1)
                logger.warning("Gemini embed 429, waiting %.1fs (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                last_exc = None  # will retry
            except Exception as exc:  # noqa: BLE001
                logger.error("Gemini embed failed for text %d: %s", i, exc)
                last_exc = exc
                break

        if len(vectors) != i + 1:
            logger.error("Gemini embed gave up on text %d after retries: %s", i, last_exc)
            return None

    return vectors


def _embed_cohere(
    texts: list[str],
    rate_limiter: RateLimiter | None = None,
    input_type: str = "search_document",
) -> list[list[float]] | None:
    """Generate embeddings via Cohere API (cloud fallback)."""
    load_keys()
    api_key = get_key("COHERE_API_KEY")
    if api_key is None:
        logger.debug("COHERE_API_KEY not set, skipping Cohere fallback")
        return None

    if rate_limiter is not None and not rate_limiter.can_call("cohere"):
        logger.warning("Cohere rate limit reached, skipping fallback")
        return None

    cohere_input_type = "search_document" if input_type == "search_document" else "search_query"

    try:
        client = cohere.ClientV2(api_key=api_key)
        response = client.embed(
            texts=texts,
            model=COHERE_MODEL,
            input_type=cohere_input_type,
            embedding_types=["float"],
        )
        vectors: list[list[float]] = list(response.embeddings.float_)

        if rate_limiter is not None:
            rate_limiter.record_call("cohere")

        return vectors
    except Exception:  # noqa: BLE001
        logger.exception("Cohere embedding call failed")
        return None


def is_ollama_available() -> bool:
    """Check if Ollama server is running and the model is available."""
    try:
        models_response = ollama.list()
        available = [m.model for m in models_response.models]
        return any(
            name == OLLAMA_MODEL or name.startswith(f"{OLLAMA_MODEL}:")
            for name in available
        )
    except (ConnectionError, httpx.ConnectError, Exception):  # noqa: BLE001
        return False


def _embed_ollama(texts: list[str]) -> list[list[float]] | None:
    """Generate embeddings via local Ollama (emergency fallback only)."""
    try:
        response = ollama.embed(model=OLLAMA_MODEL, input=texts, keep_alive=60)
        return response.embeddings
    except (ConnectionError, OSError, Exception) as exc:  # noqa: BLE001
        logger.error("Ollama embedding failed: %s", exc)
        return None


def embed_texts(
    texts: list[str],
    rate_limiter: RateLimiter | None = None,
    input_type: str = "search_document",
    provider: str | None = None,
) -> list[list[float]]:
    """Embed a list of texts.

    Provider chain: Gemini Embedding 001 → Cohere → Ollama (emergency)

    Args:
        texts: Strings to embed.
        rate_limiter: Optional rate limiter.
        input_type: ``"search_document"`` for indexing,
            ``"search_query"`` for queries.
        provider: Force ``"gemini"``, ``"cohere"``, or ``"ollama"``.

    Returns:
        List of 768-dim float vectors.

    Raises:
        RuntimeError: If all providers are unavailable.
    """
    if not texts:
        return []

    if provider == "cohere":
        vectors = _embed_cohere(texts, rate_limiter=rate_limiter, input_type=input_type)
        if vectors is not None:
            _validate_dimensions(vectors)
            return vectors
        raise RuntimeError("Cohere embedding failed")

    if provider == "ollama":
        vectors = _embed_ollama(texts)
        if vectors is not None:
            _validate_dimensions(vectors)
            return vectors
        raise RuntimeError(f"Ollama embedding failed — is '{OLLAMA_MODEL}' running?")

    # Primary: Gemini Embedding 001
    if provider in (None, "gemini"):
        vectors = _embed_gemini(texts, rate_limiter=rate_limiter, input_type=input_type)
        if vectors is not None:
            logger.info("Embedded %d text(s) via Gemini (%s)", len(texts), GEMINI_EMBED_MODEL)
            _validate_dimensions(vectors)
            return vectors
        if provider == "gemini":
            raise RuntimeError("Gemini embedding failed")

    # Fallback: Cohere
    vectors = _embed_cohere(texts, rate_limiter=rate_limiter, input_type=input_type)
    if vectors is not None:
        logger.info("Embedded %d text(s) via Cohere (%s)", len(texts), COHERE_MODEL)
        _validate_dimensions(vectors)
        return vectors

    # Emergency: Ollama local
    vectors = _embed_ollama(texts)
    if vectors is not None:
        logger.info("Embedded %d text(s) via Ollama (%s) [emergency]", len(texts), OLLAMA_MODEL)
        _validate_dimensions(vectors)
        return vectors

    raise RuntimeError(
        "All embedding providers unavailable. "
        "Check GEMINI_API_KEY, COHERE_API_KEY, or start Ollama."
    )


def select_provider() -> str:
    """Test which embedding provider is available and return its name.

    Returns:
        ``"gemini"``, ``"cohere"``, or ``"ollama"``.

    Raises:
        RuntimeError: If no provider is available.
    """
    load_keys()
    if get_key("GEMINI_API_KEY"):
        test = _embed_gemini(["dimension test"])
        if test is not None:
            logger.info("Selected embedding provider: Gemini (%s, %d-dim)",
                        GEMINI_EMBED_MODEL, len(test[0]))
            return "gemini"

    if get_key("COHERE_API_KEY"):
        logger.info("Selected embedding provider: Cohere (%s)", COHERE_MODEL)
        return "cohere"

    if is_ollama_available():
        test = _embed_ollama(["dimension test"])
        if test is not None:
            logger.info("Selected embedding provider: Ollama (%s, %d-dim) [emergency]",
                        OLLAMA_MODEL, len(test[0]))
            return "ollama"

    raise RuntimeError(
        "No embedding provider available. "
        "Set GEMINI_API_KEY or COHERE_API_KEY, or start Ollama."
    )


def embed_single(text: str, **kwargs: object) -> list[float]:
    """Convenience wrapper for embedding a single text."""
    return embed_texts([text], **kwargs)[0]


def _validate_dimensions(vectors: list[list[float]]) -> None:
    """Warn if any vector doesn't match the expected dimension."""
    for i, vec in enumerate(vectors):
        if len(vec) != EMBEDDING_DIM:
            logger.warning(
                "Vector %d has dimension %d, expected %d",
                i, len(vec), EMBEDDING_DIM,
            )
