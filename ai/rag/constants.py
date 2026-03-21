"""Shared constants for the RAG subsystem."""

EMBEDDING_DIM = 768

# Safety caps for document ingestion — prevents CPU/IO spikes from large trees
MAX_DOCS_PER_RUN = 200         # Max files processed per ingestion run
MAX_BYTES_PER_DOC = 512_000    # 512 KB — skip individual files larger than this
MAX_TOTAL_BYTES = 50_000_000   # 50 MB total input per run

# LanceDB table names
CODE_TABLE = "code_files"
