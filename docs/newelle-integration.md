# Newelle Integration: How Everything Connects

System: Acer Predator G3-571 | Bazzite 43 | Last updated: 2026-03-22

Newelle is the GTK4 AI chat/voice UI (installed as a Flatpak). It connects to
two localhost services that together give it tool access and LLM inference.

---

## Two Connection Points

```
Newelle (Flatpak)
  │
  ├── MCP tools  ──►  bazzite-mcp-bridge   127.0.0.1:8766  (FastMCP streamable-http)
  │                   ai/mcp_bridge/server.py
  │
  └── LLM chat   ──►  bazzite-llm-proxy    127.0.0.1:8767  (OpenAI-compatible)
                      ai/llm_proxy.py
```

Both services start automatically on login as **systemd user services** and bind
only to 127.0.0.1. They never touch 0.0.0.0 and they never share a process.

---

## Service 1: MCP Bridge (port 8766)

**Source:** `ai/mcp_bridge/server.py` + `ai/mcp_bridge/tools.py`
**Managed by:** `systemd/bazzite-mcp-bridge.service`

### What it does

Exposes **33 tools + 1 health endpoint** to Newelle via the Model Context
Protocol. Newelle can call any tool by name; the bridge validates, rate-limits,
and dispatches each call.

### Startup sequence

1. `create_app()` in `server.py` calls `load_keys(scope="threat_intel")` —
   only threat-intel keys are loaded here. `ai.router` is never imported
   (it would load all keys and widen the scope).
2. Tool definitions are loaded from `configs/mcp-bridge-allowlist.yaml`.
3. For each tool, FastMCP registers an explicit-argument handler function
   (FastMCP 3.x does not support `**kwargs`). The handler shape is determined
   by the tool's arg names: `hash`, `question`, `query`, `game`, `scan_type`.
4. FastMCP starts a streamable-http server on `127.0.0.1:8766`.

### Allowlist and validation

`configs/mcp-bridge-allowlist.yaml` is the single source of truth for all
tools. Three security gates run on every call:

1. **Allowlist check** — tool name must be in the YAML; unknown tools are
   rejected immediately.
2. **Bridge rate limit** — global 10 req/s, per-tool 2 req/s.
3. **Arg validation** — required fields, regex patterns, max lengths enforced
   against the YAML definition.

### Tool dispatch

`tools.py:execute_tool()` dispatches based on `source` in the YAML:

| source | what happens |
|--------|-------------|
| `command` | subprocess (static list, no shell=True) |
| `file_tail` | reads last N lines from a log file or directory |
| `json_file` | reads `~/security/.status`, filters to whitelisted keys |
| `python` | `_execute_python_tool()` — imports and calls Python directly |

All output is truncated to 4 KB. Paths containing `/home/lch` are redacted
to `[HOME]` before returning.

### The 33 tools

| Tool | Type | What it returns |
|------|------|----------------|
| `system.disk_usage` | command | `df -h` |
| `system.cpu_temps` | command | `sensors -j` |
| `system.gpu_status` | command | nvidia-smi CSV |
| `system.memory_usage` | command | `free -h` |
| `system.uptime` | command | `uptime` |
| `system.service_status` | command | `systemctl show` for 4 services |
| `system.llm_models` | python | Available LLM modes from litellm-config.yaml |
| `system.mcp_manifest` | python | List all tools with descriptions and args |
| `system.llm_status` | json_file | Provider health, token usage, active models |
| `system.key_status` | json_file | API key presence (set/missing, never values) |
| `security.last_scan` | file_tail | Last 20 lines of latest ClamAV scan log |
| `security.health_snapshot` | file_tail | Last 30 lines of latest health log |
| `security.status` | json_file | Filtered `.status` JSON (6 keys) |
| `security.threat_lookup` | python | Hash lookup via threat intel APIs |
| `security.run_scan` | python | Triggers `clamav-quick.service` via systemctl |
| `security.run_health` | python | Triggers `system-health.service` via systemctl |
| `security.run_ingest` | python | Runs `python -m ai.log_intel --all` |
| `knowledge.rag_query` | python | Queries LanceDB, returns context chunks |
| `knowledge.rag_qa` | python | LLM-synthesised answer from knowledge base |
| `knowledge.ingest_docs` | python | Re-embeds docs/ into LanceDB |
| `gaming.profiles` | python | Lists game profiles from scopebuddy |
| `gaming.mangohud_preset` | python | Returns MangoHud preset for a game |
| `logs.health_trend` | python | Last 7 health snapshots with deltas |
| `logs.scan_history` | python | Last 10 ClamAV scan results |
| `logs.anomalies` | python | Unacknowledged anomalies |
| `logs.search` | python | Semantic search across system logs |
| `logs.stats` | python | Log pipeline statistics |
| `code.search` | python | Pattern search across Python code (ripgrep) |
| `code.rag_query` | python | Semantic search over indexed Python code |
| `agents.security_audit` | python | Automated audit: scan + health + ingest + RAG |
| `agents.performance_tuning` | python | Temps, memory, disk, gaming profile analysis |
| `agents.knowledge_storage` | python | Vector DB health, ingestion freshness, disk |
| `agents.code_quality` | python | ruff + bandit + git status report |

`health` (built-in) returns `{"status": "ok", "tools": 33}`.

---

## Service 2: LLM Proxy (port 8767)

**Source:** `ai/llm_proxy.py`
**Managed by:** `systemd/bazzite-llm-proxy.service`

### What it does

Wraps `ai/router.py` (LiteLLM) behind an **OpenAI-compatible HTTP API** so
Newelle can treat it like any OpenAI-compatible endpoint. Newelle is configured
to point its API base URL at `http://127.0.0.1:8767/v1/`.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Chat completions, streaming and non-streaming |
| `/v1/models` | GET | Lists four model names: fast, reason, batch, code |
| `/health` | GET | Liveness check |

### Model name mapping

Newelle sends a model name in the request body. The proxy maps it to a router
task type:

| Newelle model | Task type | Provider chain |
|---------------|-----------|----------------|
| `fast` / `auto` / `gpt-4o-mini` / `llama-3.3-70b` | `fast` | Groq → z.ai |
| `reason` / `gpt-4o` / `deepseek-chat` | `reason` | Gemini → z.ai → OpenRouter |
| `batch` | `batch` | Mistral → Gemini |
| `code` | `code` | z.ai GLM-4-32B |
| anything else | `fast` | Groq → z.ai |

The full provider chain with health-weighted fallback lives in
`ai/router.py` and `configs/litellm-config.yaml`.

### Streaming

When `"stream": true` is in the request body, the proxy calls
`route_query_stream()` and yields SSE chunks in OpenAI `chat.completion.chunk`
format. Each chunk has `finish_reason: null`; the final chunk has
`finish_reason: "stop"` followed by `data: [DONE]`.

---

## RAG Pipeline (knowledge.rag_query)

When Newelle calls `knowledge.rag_query` with `{"query": "..."}`, this is
the full call chain:

```
Newelle  ──►  MCP bridge (tools.py)
                │
                ├── validate "query" arg (allowlist: max_length 500, required)
                ├── from ai.rag.query import rag_query
                ├── rag_query(question, use_llm=False)
                │     │
                │     ├── embed_single(question, input_type="search_query")
                │     │     └── ollama.embed("nomic-embed-text", input=[question])
                │     │         → 768-dim float vector
                │     │
                │     ├── store.search_logs(vector, limit=5)
                │     ├── store.search_threats(vector, limit=5)
                │     └── store.search_docs(vector, limit=5)
                │           └── LanceDB at ~/security/vector-db/
                │               tables: security_logs, threat_intel, docs
                │
                └── return result.answer  (truncated to 4 KB)
```

`use_llm=False` means the answer is the raw concatenated context chunks, not
an LLM-generated response. This avoids calling cloud APIs from within the MCP
bridge process.

### Embedding providers

| Provider | Endpoint | Model | Dimension | When used |
|----------|----------|-------|-----------|-----------|
| Ollama (primary) | `http://127.0.0.1:11434` | `nomic-embed-text` | 768 | Ollama running |
| Cohere (fallback) | cloud | `embed-english-v3.0` | 1024 | Ollama down + key set |

The provider is selected once per ingestion run (`select_provider()`) and
locked for the whole batch to avoid dimension mismatches. Cohere 1024-dim
vectors are rejected by `store.add_doc_chunks()` (enforces EMBEDDING_DIM=768).

### Document ingestion

```bash
bash scripts/ingest-docs.sh          # incremental (skips unchanged files)
bash scripts/ingest-docs.sh --force  # re-embeds everything, ignores state file
```

`--force` clears the in-memory state before processing (stale state file is
not read). State is only written to disk when `chunks_created > 0`, so a
failed DB write cannot leave stale dedup entries.

State file location: `~/security/vector-db/.doc-ingest-state.json`

---

## Key File Map

```
ai/
  mcp_bridge/
    server.py       FastMCP app, tool registration, localhost guard
    tools.py        execute_tool(), all 33 dispatch handlers
  llm_proxy.py      Starlette app, /v1/chat/completions, model mapping, opt-in memory
  router.py         LiteLLM wrapper, health-weighted provider selection
  health.py         Provider health tracking, auto-demotion on failure
  rate_limiter.py   Cross-script rate limit coordinator
  config.py         Paths, APP_NAME, key loading
  key_manager.py    API key presence checker, writes ~/security/key-status.json
  rag/
    embedder.py     embed_texts(), select_provider(), Ollama + Cohere
    store.py        VectorStore, LanceDB tables, add/search methods
    query.py        rag_query(), QueryResult dataclass
    ingest_docs.py  chunk_markdown(), ingest_files(), --force dedup logic
    memory.py       Opt-in conversation memory (ENABLE_CONVERSATION_MEMORY=true)

configs/
  mcp-bridge-allowlist.yaml   All 33 tool definitions + validation rules
  litellm-config.yaml         LiteLLM provider routing config
  ai-rate-limits.json         Per-provider rate limits
  r2-config.yaml              Cloudflare R2 log archive settings

systemd/
  bazzite-mcp-bridge.service  User service: MCP bridge on :8766
  bazzite-llm-proxy.service   User service: LLM proxy on :8767
  log-archive.timer           Weekly Sunday 01:00 — upload old logs to R2
  log-archive.service         Oneshot: scripts/archive-logs-r2.py
```

---

## Security Constraints (enforced in code)

- MCP bridge **never imports `ai.router`** (would load all API keys into
  the bridge process scope)
- Both services **refuse to bind** to anything except 127.0.0.1 / ::1
- All subprocess commands are **static lists** (no `shell=True`, no user
  input interpolation)
- Output is **truncated to 4 KB** and `/home/lch` paths are **redacted**
- API keys live in `~/.config/bazzite-ai/keys.env` (chmod 600), never in git
