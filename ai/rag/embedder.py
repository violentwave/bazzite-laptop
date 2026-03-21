"""Embedding generation for the RAG pipeline.

Primary: Ollama nomic-embed-text-v2-moe (local, 768-dim)
Fallback: Cohere embed-english-v3.0 (cloud, rate-limited)

Usage:
    from ai.rag.embedder import embed_texts
    vectors = embed_texts(["text1", "text2"])
"""

import logging

import cohere
import httpx
import ollama

from ai.config import APP_NAME, get_key, load_keys
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Constants ──

EMBEDDING_DIM = 768
OLLAMA_MODEL = "nomic-embed-text"
COHERE_MODEL = "embed-english-v3.0"
OLLAMA_BASE_URL = "http://localhost:11434"


def is_ollama_available() -> bool:
    """Check if Ollama server is running and the model is available."""
    try:
        models_response = ollama.list()
        available = [m.model for m in models_response.models]
        # Model names may include a tag like ":latest"
        return any(
            name == OLLAMA_MODEL or name.startswith(f"{OLLAMA_MODEL}:")
            for name in available
        )
    except (ConnectionError, httpx.ConnectError, Exception):  # noqa: BLE001
        return False


def _embed_ollama(texts: list[str]) -> list[list[float]] | None:
    """Generate embeddings via local Ollama server.

    Uses the ``ollama`` Python package. Returns None if Ollama is
    unavailable or the model isn't pulled.
    """
    try:
        response = ollama.embed(model=OLLAMA_MODEL, input=texts)
        vectors: list[list[float]] = response.embeddings
        return vectors
    except (ConnectionError, OSError, Exception) as exc:  # noqa: BLE001
        logger.error("Ollama embedding failed: %s", exc)
        return None


def _embed_cohere(
    texts: list[str],
    rate_limiter: RateLimiter | None = None,
    input_type: str = "search_document",
) -> list[list[float]] | None:
    """Generate embeddings via Cohere API (cloud fallback).

    Requires COHERE_API_KEY in environment. Uses *input_type* to distinguish
    indexing (``search_document``) from query-time (``search_query``) embeddings.
    Rate-limited via :mod:`ai.rate_limiter`.

    Returns None if key is missing or rate limited.
    """
    load_keys()
    api_key = get_key("COHERE_API_KEY")
    if api_key is None:
        logger.debug("COHERE_API_KEY not set, skipping Cohere fallback")
        return None

    if rate_limiter is not None and not rate_limiter.can_call("cohere"):
        logger.warning("Cohere rate limit reached, skipping fallback")
        return None

    try:
        client = cohere.ClientV2(api_key=api_key)
        response = client.embed(
            texts=texts,
            model=COHERE_MODEL,
            input_type=input_type,
            embedding_types=["float"],
        )
        vectors: list[list[float]] = list(response.embeddings.float_)

        if rate_limiter is not None:
            rate_limiter.record_call("cohere")

        return vectors
    except Exception:  # noqa: BLE001
        logger.exception("Cohere embedding call failed")
        return None


def embed_texts(
    texts: list[str],
    rate_limiter: RateLimiter | None = None,
    input_type: str = "search_document",
    provider: str | None = None,
) -> list[list[float]]:
    """Embed a list of texts, trying Ollama first, then Cohere fallback.

    Args:
        texts: List of strings to embed.
        rate_limiter: Optional rate limiter for Cohere calls.
        input_type: ``"search_document"`` for indexing,
            ``"search_query"`` for queries.
        provider: Force a specific provider (``"ollama"`` or ``"cohere"``).
            If None, tries Ollama first then Cohere.

    Returns:
        List of 768-dim float vectors, one per input text.

    Raises:
        RuntimeError: If both Ollama and Cohere are unavailable.
    """
    if not texts:
        return []

    # If provider is forced, skip the other
    if provider == "cohere":
        vectors = _embed_cohere(texts, rate_limiter=rate_limiter, input_type=input_type)
        if vectors is not None:
            logger.info("Embedded %d text(s) via Cohere (%s)", len(texts), COHERE_MODEL)
            _validate_dimensions(vectors)
            return vectors
        raise RuntimeError("Cohere embedding failed")

    # Primary: Ollama (local)
    vectors = _embed_ollama(texts)
    if vectors is not None:
        logger.info("Embedded %d text(s) via Ollama (%s)", len(texts), OLLAMA_MODEL)
        _validate_dimensions(vectors)
        return vectors

    if provider == "ollama":
        raise RuntimeError(
            f"Ollama embedding failed — is '{OLLAMA_MODEL}' pulled and the server running?"
        )

    # Fallback: Cohere (cloud)
    vectors = _embed_cohere(texts, rate_limiter=rate_limiter, input_type=input_type)
    if vectors is not None:
        logger.info("Embedded %d text(s) via Cohere (%s)", len(texts), COHERE_MODEL)
        _validate_dimensions(vectors)
        return vectors

    raise RuntimeError(
        "All embedding providers unavailable. "
        "Ensure Ollama is running with the "
        f"'{OLLAMA_MODEL}' model pulled, or set COHERE_API_KEY."
    )


def select_provider() -> str:
    """Test which embedding provider is available and return its name.

    Call once at the start of a batch ingestion to ensure all vectors
    use the same model (and thus the same dimension).

    Returns:
        ``"ollama"`` or ``"cohere"``.

    Raises:
        RuntimeError: If no provider is available.
    """
    if is_ollama_available():
        # Verify with a real embed call
        test = _embed_ollama(["dimension test"])
        if test is not None:
            logger.info("Selected embedding provider: Ollama (%s, %d-dim)",
                        OLLAMA_MODEL, len(test[0]))
            return "ollama"

    load_keys()
    if get_key("COHERE_API_KEY"):
        logger.info("Selected embedding provider: Cohere (%s)", COHERE_MODEL)
        return "cohere"

    raise RuntimeError(
        "No embedding provider available. "
        f"Start Ollama with '{OLLAMA_MODEL}' or set COHERE_API_KEY."
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
                i,
                len(vec),
                EMBEDDING_DIM,
            )
