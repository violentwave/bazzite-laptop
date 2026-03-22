# Bazzite Dev Skill Bundle

Tools for searching and querying the project codebase and security knowledge
base. Supports both fast embedding-based search and LLM-synthesized answers.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `code.search` | Search Python source files by pattern using ripgrep | `query` (string, max 128 chars, required) |
| `code.rag_query` | Semantic (embedding-based) search over indexed Python code | `question` (string, max 500 chars, required) |
| `knowledge.rag_query` | Embedding-only search over the security knowledge base (no LLM call) | `query` (string, max 500 chars, required) |
| `knowledge.rag_qa` | Answer a question using the security knowledge base with LLM synthesis | `question` (string, max 500 chars, required) |
| `knowledge.ingest_docs` | Re-ingest reference documentation into the RAG vector database | none |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "Where is the rate limiter implemented?" | `code.search` with `query="rate_limiter"` |
| "How does the LLM router work?" | `code.rag_query` with `question="LLM router provider selection"` |
| "What does the MCP bridge do?" | `knowledge.rag_query` with `query="MCP bridge tools"` |
| "Explain how threat intel lookups work" | `knowledge.rag_qa` with `question="how does threat intel lookup work"` |
| "Update the knowledge base with new docs" | `knowledge.ingest_docs` |
| "Find all places that call litellm" | `code.search` with `query="litellm"` |
| "What is the router task type for fast queries?" | `knowledge.rag_qa` |

---

## Safety Rules

- **`knowledge.rag_qa`** calls a cloud LLM for synthesis and consumes tokens.
  Prefer `knowledge.rag_query` (embedding-only, no LLM cost) when the user
  just needs to find relevant passages rather than a synthesized answer.
- **`knowledge.ingest_docs`** is slow (re-indexes all docs). Only suggest it
  if the user explicitly asks to update the knowledge base or reports stale
  results.
- **`code.rag_query`** only covers Python files that have been indexed. If a
  search returns no results, fall back to `code.search` (ripgrep) which scans
  files directly.
- `question` values for `knowledge.rag_qa` and `code.rag_query` must be
  plain natural language — no shell special characters.
