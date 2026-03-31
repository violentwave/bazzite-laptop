# Verified Dependencies
<!-- Last verified: 2026-03-30 | System: Acer Predator G3-571 | Bazzite 43 / Fedora Atomic -->

All versions pinned or noted below were confirmed working on this machine.
"AI layer" packages live in `.venv/`; system packages are managed by Bazzite / rpm-ostree.

---

## Python Runtime

| Item | Version | Notes |
|------|---------|-------|
| Python | 3.12.13 | Minimum 3.12 required (`pyproject.toml`) |
| pip | 25.1.1 | In `.venv` |

---

## AI Layer — Core (`.venv/`)

These are the packages actively used by `ai/`, `tray/`, and `tests/`.

| Package | Version | Used by |
|---------|---------|--------|
| litellm | 1.82.2 | `ai/router.py` — multi-provider LLM routing |
| lancedb | 0.30.1 | `ai/rag/` — vector database for embeddings (FTS indexes added) |
| fastmcp | 3.1.1 | `ai/mcp_bridge/server.py` — MCP server (3.2.0 upgrade blocked: no PyPI access) |
| uvicorn | 0.42.0 | `ai/llm_proxy.py` — ASGI server for LLM proxy |
| starlette | 0.52.1 | `ai/llm_proxy.py` — ASGI framework |
| python-dotenv | 1.2.2 | `ai/config.py` — loads keys from `keys.env` |
| PyYAML | 6.0.3 | `ai/router.py`, allowlist loading |
| pydantic | 2.12.5 | Data validation throughout |
| pydantic_core | 2.41.5 | Pydantic backend |
| httpx | 0.28.1 | HTTP client (used by litellm, fastmcp) |
| socksio | 1.0.0 | SOCKS proxy support for httpx in bubblewrap |
| requests | 2.32.5 | `ai/threat_intel/` — threat intel API calls |
| openai | 2.28.0 | litellm OpenAI-compatible provider support |
| ollama | 0.6.1 | `ai/rag/` — emergency local embedding fallback only |
| boto3 | 1.42.73 | `scripts/archive-logs-r2.py` — Cloudflare R2 log archiving |
| cohere | 5.20.7 | `ai/rag/embedder.py` — Cohere rerank for RAG QA |
| pillow | 12.1.1 | Image processing utilities |

---

## AI Layer — Dev / Test (`.venv/`)

| Package | Version | Used by |
|---------|---------|--------|
| pytest | 9.0.2 | Test runner |
| pytest-asyncio | 1.3.0 | Async test support |
| ruff | 0.15.6 | Linter + formatter (also system tool) |
| bandit | 1.9.4 | Security scanner (also system tool) |

---

## System Requirements (installed by rpm-ostree / Bazzite)

These must exist on the host — they are **not** installed via pip or npm.

| Tool | Version | Purpose |
|------|---------|--------|
| Python | 3.12.13 | Runtime |
| ruff | 0.15.6 | Lint (VS Code task, CI) |
| bandit | 1.9.4 | Security scan (VS Code task, CI) |
| shellcheck | 0.11.0 | Shell script linting |
| gpg (GnuPG) | 2.4.9 | Key management, sops decryption |
| sops | 3.12.2 | Secrets encryption/decryption for `configs/keys.env.enc` |
| ollama | 0.18.0 (client) | Local embedding inference (`nomic-embed-text`) |
| Node.js | v25.8.1 | Claude Flow CLI, npm plugins |
| npm | 11.11.0 | Package management for Claude Flow |

> **Note:** `ollama --version` reports client 0.18.0; the Python `ollama` SDK in `.venv` is 0.6.1.
> These version numbers are on different tracks — both are required.

---

## Node.js Packages (`package.json`)

| Package | Version | Purpose |
|---------|---------|--------|
| `@claude-flow/cli` | ^3.5.15 (dev) | RuFlo orchestration CLI |
| `@claude-flow/plugin-code-intelligence` | file:plugins/code-intelligence | Semantic code search plugin |
| `@claude-flow/plugin-test-intelligence` | file:plugins/test-intelligence | Predictive test selection plugin |
| `agentic-flow` | ^2.0.7 | Agentic workflow runtime |
| `vitest` | ^4.1.2 (dev) | Plugin test runner |
| `vite` | ^6.1.6 (dev) | Plugin build tool |

---

## LLM Providers (`configs/litellm-config.yaml`)

All providers are free-tier unless noted. Keys stored in `~/.config/bazzite-ai/keys.env`.

| Provider | Env Var | Task Types | Notes |
|----------|---------|-----------|-------|
| Google Gemini | `GEMINI_API_KEY` | fast, reason, batch, code, embed | Preferred for tool calling; Pro subscription |
| Groq | `GROQ_API_KEY` | fast, reason, batch, code | Speed-first; free tier |
| Mistral | `MISTRAL_API_KEY` | fast, reason, batch, code, embed | Codestral for code/batch; free tier |
| OpenRouter | `OPENROUTER_API_KEY` | fast, reason, batch, code | Routes to Llama and Claude |
| z.ai | `ZAI_API_KEY` | fast, reason, code | OpenAI-compatible at `api.z.ai`; paid |
| Cerebras | `CEREBRAS_API_KEY` | fast, batch | Fallback; free tier |
| Ollama (local) | — | embed | `nomic-embed-text`; emergency fallback only, no VRAM used in normal operation |

**Provider chain order (health-weighted at runtime):**
- `fast`: Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras
- `reason`: Gemini → Groq → Mistral → OpenRouter(Claude) → z.ai
- `batch`: Gemini → Groq → Mistral → OpenRouter → Cerebras
- `code`: Gemini → Groq → Mistral(Codestral) → OpenRouter(Claude) → z.ai
- `embed`: Gemini Embedding 001 (primary, free) → Cohere embed-english-v3.0 (fallback) → Ollama nomic-embed-text (emergency local)

---

## Threat Intel APIs (`configs/ai-rate-limits.json`)

Keys stored in `~/.config/bazzite-ai/keys.env`.

| Service | Env Var | Free Limits | Used by |
|---------|---------|------------|--------|
| VirusTotal | `VT_API_KEY` | 4 rpm, 500 rpd | `ai/threat_intel/lookup.py` |
| AbuseIPDB | `ABUSEIPDB_API_KEY` | 60 rpm, 1000 rpd | `ai/threat_intel/ip_lookup.py` |
| AlienVault OTX | `OTX_API_KEY` | 166 rpm, 10 000/hr | `ai/threat_intel/lookup.py` |
| GreyNoise | `GREYNOISE_API_KEY` | 5 rpm, 7 rpd | `ai/threat_intel/ip_lookup.py` |
| Hybrid Analysis | `HYBRID_ANALYSIS_API_KEY` | 5 rpm, 200 rpd | `ai/threat_intel/sandbox.py` |
| NVD (NIST) | `NVD_API_KEY` _(optional)_ | 50 per 30s (anon); higher with key | `ai/threat_intel/cve_scanner.py` |
| OSV (Google) | _(none)_ | 30 rpm, 10 000 rpd | `ai/threat_intel/cve_scanner.py` |
| CISA KEV | _(none)_ | No enforced limit (JSON feed) | `ai/threat_intel/cve_scanner.py` |
| Shodan InternetDB | _(none)_ | No enforced limit | `ai/threat_intel/ip_lookup.py` |
| MalwareBazaar | _(none)_ | No enforced limit | `ai/threat_intel/lookup.py` |
| URLhaus | _(none)_ | No enforced limit | `ai/threat_intel/ioc_lookup.py` |
| ThreatFox | _(none)_ | No enforced limit | `ai/threat_intel/ioc_lookup.py` |
| CIRCL Hashlookup | _(none)_ | No enforced limit | `ai/threat_intel/ioc_lookup.py` |
| GitHub Releases / GHSA | _(none)_ | 15 rpm, 500 rpd (anon) | `ai/system/release_watch.py` |
| Fedora Bodhi | _(none)_ | 10 rpm, 500 rpd | `ai/system/fedora_updates.py` |
| deps.dev | _(none)_ | 30 rpm, 5 000 rpd | `ai/system/pkg_intel.py` |

---

## Known Incompatibilities

| Dependency | Issue | Workaround |
|------------|-------|-----------|
| `litellm`, `rich`, `python-dotenv` | Do not expose `__version__` attribute | Use `importlib.metadata.version("package-name")` instead |
| `diskcache` | CVE-2025-69872 (pickle RCE) | Replaced with `ai/cache.py` (`JsonFileCache`) in Phase 11. No pickle, JSON-only. |
| `litellm.Router` | Does **not** check `litellm.cache` via `router.completion()` without `cache_responses=True`; caching is at `litellm.completion()` level | Integration-level cache testing requires a real router, not mocks |
| NVIDIA PRIME offload vars | `__NV_PRIME_RENDER_OFFLOAD`, `__GLX_VENDOR_LIBRARY_NAME`, `prime-run` **crash** Proton/Vulkan on GTX 1060 + Intel HD 630 with `nvidia-drm.modeset=1` | Never set these; games route to NVIDIA automatically via DXVK/Vulkan |
| `vm.swappiness` | Value of 180 is intentionally high for ZRAM; do **not** lower it | Leave at 180 |
| `/usr` modifications | Bazzite / Fedora Atomic uses an immutable OS; `sudo dnf install` and direct `/usr` edits do not survive updates | Use `rpm-ostree install` for system packages, Flatpak for apps |
| `ai/router.py` import in MCP bridge | Importing `ai.router` in the MCP bridge process loads all API keys unscoped | The bridge (`ai/mcp_bridge/`) must never import `ai.router` |
| `socksio` | Required for httpx SOCKS proxy support used by litellm inside bubblewrap sandbox | Installed explicitly; not auto-pulled by litellm |
| composefs (100% disk) | Shows as 100% full on `df`; this is normal for the Fedora Atomic immutable OS overlay | Not a real disk issue |
