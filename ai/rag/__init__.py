"""RAG Security Intelligence — Phase 2.

Embeds ClamAV scan logs and health snapshots into LanceDB for semantic
search. Uses Ollama nomic-embed-text locally, with Cohere cloud fallback.

Modules:
    store     — LanceDB table management (security_logs, threat_intel)
    chunker   — Section-based log parser
    embedder  — Embedding generation (Ollama local, Cohere fallback)
    query     — Semantic search + LLM-augmented answers
"""
