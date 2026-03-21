# Newelle Integration + MCP Bridge + Router Overhaul

**Date:** 2026-03-25
**Status:** Draft
**Replaces:** S4 Voice Agent (Jarvis) — removed 2026-03-25

## Context

Jarvis (custom AI assistant) was removed due to high memory usage and poor
performance. Replacing with Newelle (Flatpak GTK4 assistant) + MCP bridge for
system tool access + g4f for free LLM providers + router overhaul for
resilience.

## Goals

1. Newelle provides voice + chat UI (maintained externally, Flatpak)
2. MCP bridge exposes read-only system/security/gaming tools on localhost
3. g4f provides free-tier LLM access (on-demand subprocess)
4. Router gains health tracking, auto-demotion, g4f fallback, stream recovery
5. Zero impact on existing security/health/gaming infrastructure

## Non-Goals

- No mutations via MCP (scans, config writes stay in dashboard)
- No LLM proxy in bridge (Newelle uses g4f directly)
- No persistent daemons (on-demand only)
- No Newelle Flatpak sandboxing (needs filesystem read for logs)

---

## Architecture

```
Newelle (Flatpak, relaxed permissions: home:ro, network)
  ├── LLM: g4f (127.0.0.1:$G4F_PORT, default 1337)
  └── MCP: bridge (127.0.0.1:$MCP_PORT, default 8766)

MCP Bridge (ai/mcp_bridge/)
  ├── 13 read-only tools (system, security, knowledge, gaming)
  ├── Input validation (allowlist, regex, length limits)
  ├── Scoped keys: load_keys(scope="threat_intel") only
  ├── Rate limiting via ai/rate_limiter.py
  ├── Subprocess concurrency limit (semaphore, max 4)
  └── /health endpoint

g4f Manager (ai/g4f_manager.py — SINGLE OWNER, singleton via module-level instance)
  ├── On-demand subprocess start/stop
  ├── Startup timeout: 10s to bind port or fail
  ├── Max restart attempts: 3 per 15 minutes
  ├── Health probe: test completion request before routing traffic
  ├── Idle timeout: 5 minutes → kill
  └── PID file at $XDG_RUNTIME_DIR/g4f.pid (singleton lock)

Router V2 (ai/router.py rewrite)
  ├── Health-weighted provider selection (replaces simple-shuffle)
  ├── ProviderHealth: success rate, latency, auto-demotion
  ├── g4f as universal free-tier fallback (last in every chain)
  ├── Stream recovery: discard partial, restart on next provider
  ├── Rate limiter integration in provider selection
  └── Backward-compatible: route_query() + route_query_stream() unchanged
```

## Untouched (Safety Guarantee)

These files/systems are NOT modified:

- `ai/config.py` — path constants, key loading
- `ai/rate_limiter.py` — atomic file-locking rate limiter
- `ai/threat_intel/` — VT, OTX, MalwareBazaar cascade
- `ai/rag/` — LanceDB vector search
- `ai/gaming/` — ScopeBuddy, MangoHud
- `ai/code_quality/` — linter orchestration
- `tray/` — Security/Health/About dashboard tabs
- `systemd/` — ClamAV timers, health timer, all hardened services
- `scripts/` — all existing shell scripts
- `~/security/.status` — read-only from bridge, never written
- All 389 existing tests

---

## Component 1: Router Overhaul

### Provider Health Tracking (`ai/health.py`, ~100 lines)

```python
@dataclass
class ProviderHealth:
    name: str
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_latency_ms: float = 0.0
    last_error: str | None = None
    last_error_time: float | None = None
    disabled_until: float | None = None

    @property
    def score(self) -> float:
        """0.0-1.0 health score. Cold start = 0.5 (neutral)."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        success_rate = self.success_count / total
        avg_latency = self.total_latency_ms / total
        latency_score = max(0, 1.0 - (avg_latency / 10000))
        return 0.7 * success_rate + 0.3 * latency_score
```

### Auto-Demotion

- 3 consecutive failures → provider disabled for 5 minutes
- After 5 min: re-enable, send one test request
- If test succeeds: reset consecutive_failures, provider re-enters rotation
- If test fails: disable for 10 minutes (exponential backoff, max 30 min)

### Router Strategy (litellm.Router still used, wrapped)

`litellm.Router` is still used for the actual LLM calls (completion, embedding).
The rewrite wraps it with a custom selection layer:
- Provider ordering: health-weighted (replaces litellm's `simple-shuffle`)
- Retry logic: router.py manages fallback chain (not litellm's built-in retries)
- `litellm.Router.num_retries` set to 0 — our code handles retries
- `route_query()`, `route_query_stream()`, `reset_router()` signatures preserved

### Provider Selection

```
For a given task_type:
  1. Get all configured providers for this task type
  2. Filter out: disabled providers, rate-limited providers
  3. Sort by health score (descending)
  4. Append g4f as final fallback (always available)
  5. Try providers in order until one succeeds
```

### Stream Recovery

- Buffer streamed chunks as `list[str]` in memory (not yielded immediately)
- On failure mid-stream: discard buffer, retry on next provider from same messages
- On success: yield all buffered chunks as one batch, then stream remaining live
- Buffer limit: 2KB total string length — after 2KB successfully buffered,
  commit to this provider: flush buffer to consumer, stream remaining live
- Post-commit failure: raise `RuntimeError` (partial output already sent, cannot recover)
- Exception type preserved: `RuntimeError` for all LLM failures (backward compat)

### g4f Fallback Integration

Every task type in litellm-config.yaml gets g4f appended as final entry:

```yaml
# Added automatically by router, not in YAML
# Equivalent to:
- model_name: "fast"  # (and reason, batch, code)
  litellm_params:
    model: openai/auto
    api_key: "dummy"
    api_base: http://127.0.0.1:${G4F_PORT}/v1
```

g4f entry is injected at runtime by the router, not stored in YAML.
Only attempted when all paid providers fail or are rate-limited.

### Health State

- In-memory only (acceptable for laptop — restarts are rare)
- Optional: checkpoint to `$XDG_RUNTIME_DIR/router-health.json` on shutdown
  for warm restart (nice-to-have, not required for MVP)

### File Changes

| File | Action | Lines (est.) |
|------|--------|-------------|
| `ai/router.py` | Rewrite (same API surface) | ~300 |
| `ai/health.py` | New | ~100 |
| `ai/g4f_manager.py` | New | ~100 |
| `configs/litellm-config.yaml` | Add health_settings section | +10 |
| `configs/ai-rate-limits.json` | Add g4f entry | +1 |

---

## Component 2: MCP Bridge Server

### Server (`ai/mcp_bridge/server.py`, ~150 lines)

- FastMCP HTTP server
- Bind: `127.0.0.1:${MCP_BRIDGE_PORT:-8766}`
- Startup guard: refuse to start if `load_keys(scope="threat_intel")` fails
- `/health` endpoint returning `{"status": "ok", "tools": <actual_count>, "g4f": "running|stopped"}`
- Health endpoint imports `G4FManager` singleton to check g4f status
- Named logger: `logging.getLogger("ai.mcp_bridge")`

### Tools (`ai/mcp_bridge/tools.py`, ~120 lines)

| Tool | Command/Source | Args | Validation |
|------|---------------|------|-----------|
| `system.disk_usage` | `["df", "-h"]` | None | — |
| `system.cpu_temps` | `["sensors", "-j"]` | None | — |
| `system.gpu_status` | `["nvidia-smi", "--query-gpu=..."]` | None | — |
| `system.memory_usage` | `["free", "-h"]` | None | — |
| `system.uptime` | `["uptime"]` | None | — |
| `system.service_status` | `["systemctl", "is-active", "clamav-freshclam", "system-health.timer"]` | None | Static service list, no user args |
| `security.last_scan` | `tail -20 scan-latest.log` | None | — |
| `security.health_snapshot` | `tail -30 health-latest.log` | None | — |
| `security.status` | Read `~/security/.status` | None | — |
| `security.threat_lookup` | `ai.threat_intel.lookup` | `hash` | `^[a-fA-F0-9]{32,64}$` (MD5/SHA1/SHA256) |
| `knowledge.rag_query` | `ai.rag.query` | `question` | `str, len ≤ 500` |
| `gaming.profiles` | `ai.gaming.scopebuddy` | None | — |
| `gaming.mangohud_preset` | `ai.gaming.scopebuddy` | `game` | Must exist in library |

All subprocess commands: static lists, no `shell=True`, no user arg interpolation.
All output truncated to 4KB max (append `"...[truncated]"` if cut, to avoid broken JSON).
Subprocess concurrency: `asyncio.Semaphore(4)` — max 4 concurrent tool calls.
Bridge-level rate limiting: 10 req/s global, 2 req/s per tool (independent of provider limits).

### Entry Point (`ai/mcp_bridge/__main__.py`, ~15 lines)

```python
"""python -m ai.mcp_bridge entry point."""
# 1. Parse --bind and --port from argv (defaults: 127.0.0.1, 8766)
# 2. Call load_keys(scope="threat_intel") — exit 1 on failure
# 3. Start FastMCP server
# 4. Register SIGTERM handler for graceful shutdown (stop g4f, close server)
# 5. Run event loop
```

Does NOT start g4f on startup — g4f starts lazily on first router fallback request.

### Allowlist (`configs/mcp-bridge-allowlist.yaml`)

Same security pattern as the deleted `jarvis-tools-allowlist.yaml`. Static YAML,
loaded once at startup. Unknown tool names rejected.

### Security Model

```
Layer 1: 127.0.0.1 binding (unreachable from network)
Layer 2: Tool name must exist in allowlist.yaml
Layer 3: Argument validation (regex, length, membership)
Layer 4: Static subprocess commands (no shell, no interpolation)
Layer 5: Output truncation (4KB cap)
Layer 6: Rate limiting (threat_intel calls via ai/rate_limiter.py)
Layer 7: Key scoping (load_keys(scope="threat_intel") only)
Layer 8: ai/config.py assumed side-effect-free at import time
```

Keys that are NEVER loaded in the bridge process:
`GROQ_API_KEY`, `ZAI_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`,
`MISTRAL_API_KEY`, `CEREBRAS_API_KEY`, `CLOUDFLARE_API_KEY`

### Response Sanitization

- `security.threat_lookup`: Strip `raw_data` from ThreatReport. Return only:
  hash, source, family, risk_level, detection_ratio, description, tags.
- `knowledge.rag_query`: Return only `answer` string. Strip `context_chunks`
  and `sources` (which contain filesystem paths). Use `use_llm=False` (embedding-only).
- `security.last_scan` / `security.health_snapshot`: Redact full filesystem paths
  (`/home/lch/...` → `[HOME]/...`) before returning.
- `security.status`: Whitelist allowed keys from .status JSON (state, scan_type,
  last_scan_time, result, health_status, health_issues). Strip everything else.

### Error Handling

- Missing log files: return `"No data yet — run a snapshot first"`
- Subprocess timeout: 30s per command, return `"[Tool timed out]"`
- Missing sensors/nvidia-smi: return `"[Command not found]"`
- Rate-limited threat lookups: return `"[Rate limited, try in Xs]"`
- Bridge-level rate exceeded: return `"[Bridge rate limited, slow down]"`

---

## Component 3: g4f Manager (`ai/g4f_manager.py`, ~100 lines)

Single lifecycle owner, importable by both router and MCP bridge.
Module-level singleton: `_manager = G4FManager()` at bottom of module.

**CRITICAL: Environment scrubbing.** g4f subprocess MUST NOT inherit API keys.
The manager builds a clean environment before spawning:

```python
class G4FManager:
    """Singleton manager for the g4f subprocess."""

    # Keys that must NEVER be passed to g4f
    _SCRUB_KEYS = {
        "GROQ_API_KEY", "ZAI_API_KEY", "GEMINI_API_KEY",
        "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "CEREBRAS_API_KEY",
        "CLOUDFLARE_API_KEY", "VT_API_KEY", "OTX_API_KEY", "ABUSEIPDB_KEY",
    }

    def __init__(self, port: int = None, idle_timeout: int = 300):
        self._port = port or int(os.environ.get("G4F_PORT", "1337"))
        self._idle_timeout = idle_timeout
        self._process: subprocess.Popen | None = None
        self._last_request: float = 0.0
        self._restart_count: int = 0
        self._restart_window_start: float = 0.0
        xdg = os.environ.get("XDG_RUNTIME_DIR")
        if not xdg:
            raise RuntimeError("XDG_RUNTIME_DIR not set — cannot create PID file safely")
        self._pid_file = Path(xdg) / "g4f.pid"

    def _clean_env(self) -> dict[str, str]:
        """Return os.environ minus all API keys."""
        return {k: v for k, v in os.environ.items() if k not in self._SCRUB_KEYS}

    def ensure_running(self) -> bool:
        """Start g4f if not running. Returns True if healthy."""
        # 1. Check PID file for existing instance
        # 2. If not running, check restart budget (max 3 per 15 min)
        # 3. Start subprocess SANDBOXED with SCRUBBED env:
        #    subprocess.Popen(
        #        ["systemd-run", "--user", "--scope",
        #         "-p", "ProtectHome=yes",
        #         "-p", "NoNewPrivileges=yes",
        #         "-p", "PrivateTmp=yes",
        #         "-p", "MemoryMax=512M",
        #         sys.executable, "-m", "g4f", "api",
        #         "--port", str(self._port), "--bind", "127.0.0.1"],
        #        env=self._clean_env()
        #    )
        #    Fallback if systemd-run unavailable: bwrap --ro-bind / / --tmpfs $HOME
        # 4. Wait up to 10s for port to respond (socket connect probe)
        # 5. Health probe: send test completion request via httpx
        # 6. Write PID file
        # 7. Return True/False

    def stop(self) -> None:
        """Kill g4f subprocess and remove PID file."""

    def idle_check(self) -> None:
        """Kill g4f if no requests for idle_timeout seconds."""

    def record_request(self) -> None:
        """Update last_request timestamp."""
```

Circuit breaker: after 3 failed starts in 15 minutes, stop trying for 30 minutes.
Log clearly: `"g4f circuit breaker open — too many restart failures"`.

**g4f CLI note:** The actual command may be `python -m g4f api` (not `python -m g4f`).
Verify during implementation with `python -m g4f --help`.

---

## Component 4: Newelle Configuration (Manual)

```bash
# Install
flatpak install flathub io.github.qwersyk.Newelle

# Grant permissions — SCOPED, not blanket home:ro
# Read security/health logs but NOT keys.env
flatpak override --user --filesystem=~/security:ro io.github.qwersyk.Newelle
flatpak override --user --filesystem=/var/log/system-health:ro io.github.qwersyk.Newelle
flatpak override --user --nofilesystem=~/.config/bazzite-ai io.github.qwersyk.Newelle
flatpak override --user --nofilesystem=~/.ssh io.github.qwersyk.Newelle
flatpak override --user --nofilesystem=~/.gnupg io.github.qwersyk.Newelle
flatpak override --user --share=network io.github.qwersyk.Newelle

# In Newelle settings:
#   LLM Provider: Custom OpenAI-compatible
#   Base URL: http://127.0.0.1:1337/v1
#   API Key: "dummy"
#   Model: auto
#
#   MCP Server: http://127.0.0.1:8766
```

---

## New Files

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `ai/health.py` | ~100 | Provider health tracking |
| `ai/g4f_manager.py` | ~100 | g4f subprocess lifecycle (singleton) |
| `ai/mcp_bridge/__init__.py` | ~5 | Package marker |
| `ai/mcp_bridge/__main__.py` | ~10 | `python -m ai.mcp_bridge` entry point |
| `ai/mcp_bridge/server.py` | ~150 | FastMCP server + tool registration |
| `ai/mcp_bridge/tools.py` | ~120 | Tool implementations |
| `configs/mcp-bridge-allowlist.yaml` | ~50 | Static tool definitions |
| `scripts/start-mcp-bridge.sh` | ~10 | Launch script |

## Modified Files

| File | Change |
|------|--------|
| `ai/router.py` | Rewrite: health tracking, g4f fallback, stream recovery (~300 lines) |
| `configs/litellm-config.yaml` | Add `health_settings` section |
| `configs/ai-rate-limits.json` | Add `g4f` provider entry |
| `requirements.txt` | Add `g4f[slim]>=7.0.0`, `fastmcp>=1.0.0` |
| `CLAUDE.md` | Update AI Rule #4 exception for g4f idle timeout |
| `.claude/rules/ai-layer.md` | Remove stale Jarvis exception, add g4f/MCP notes |

## New Tests

| File | Covers |
|------|--------|
| `tests/test_health.py` | Health scoring, auto-demotion, cold start, recovery |
| `tests/test_g4f_bridge.py` | Subprocess lifecycle, circuit breaker, idle timeout, PID file |
| `tests/test_router_v2.py` | Health-weighted selection, fallback chains, stream recovery |
| `tests/test_router_compat.py` | Backward compat: existing route_query/route_query_stream |
| `tests/test_mcp_server.py` | Tool registration, /health endpoint, allowlist enforcement |
| `tests/test_mcp_tools.py` | Each tool output, truncation, error handling, missing files |
| `tests/test_mcp_security.py` | Input validation, key scoping, argument rejection, concurrency semaphore |
| `tests/test_g4f_env.py` | g4f environment scrubbing — verify no API keys in subprocess env |

---

## Dependencies

| Package | Size | Purpose | Risk |
|---------|------|---------|------|
| `g4f[slim]` | ~15MB | Free LLM proxy (no browser deps) | GPL v3, community-maintained |
| `fastmcp` | ~2MB | MCP server framework | MIT, lightweight |

---

## Hard Rules (NEVER violate)

1. **NEVER import g4f in any `ai/` module.** g4f is GPL v3. Only interact via
   subprocess + HTTP. This keeps our code license-clean.
2. **NEVER pass API keys to the g4f subprocess.** Environment scrubbing is mandatory.
3. **NEVER expose MCP bridge on 0.0.0.0.** Localhost only. Add startup assertion.
4. **NEVER use shell=True** in any MCP bridge subprocess call.
5. **NEVER accept dynamic service names** in `system.service_status`. Static list only.
6. **NEVER import `ai/router.py` in the MCP bridge process.** The router calls
   `load_keys()` (unscoped) which loads ALL keys into the process environment.
   If the bridge later spawns g4f, those keys leak. RAG queries in the bridge
   MUST use `use_llm=False` — embedding-only, no LLM augmentation.
7. **NEVER send sensitive data through g4f.** No file paths, system info, API keys,
   or user-identifying content. g4f routes through unknown intermediaries.
8. **g4f MUST run sandboxed.** Use `systemd-run --user` or `bwrap` to confine g4f:
   `ProtectHome=yes`, `NoNewPrivileges=yes`, `PrivateTmp=yes`, `ReadOnlyPaths=/`.
   Without sandboxing, a compromised g4f can read keys.env, SSH keys, etc.
9. **g4f idle timeout is on-demand** — 5 min idle kill matches the removed Jarvis
   voice server exception. This is an intentional, documented exception to AI Rule #4.
10. **g4f fallback in router is an intentional exception** to AI Rule #6
    ("never hardcode API providers"). It is a local-only fallback, not a hardcoded cloud provider.

---

## Known Limitations

1. **g4f is inherently fragile.** Free-tier providers break without notice.
   g4f is the *last* fallback, not the primary path. When all providers
   (paid + g4f) fail, queries return an explicit error.

2. **Newelle is GTK4.** It will look non-native alongside the KDE/Qt dashboard.
   Accepted tradeoff — they are separate apps serving different purposes.

3. **No LLM proxy in bridge.** Newelle's LLM quality depends on g4f's
   available models. For security-critical analysis, use the dashboard's
   AI tools (threat_intel, RAG) which still route through paid providers.

4. **Health state is in-memory.** Router restart loses provider history.
   Acceptable for laptop use — cold start probes all providers anyway.

---

## Review Findings Incorporated

### From Architecture Review (CONDITIONAL PASS)

- [x] 1b: Circuit breaker added to g4f_manager (startup timeout, max restarts)
- [x] 1c: Single g4f lifecycle owner at `ai/g4f_manager.py` (module-level singleton)
- [x] 1d: /health endpoint added to MCP bridge
- [x] 3a: Cold start score = 0.5 (neutral)
- [x] 3b: Stream recovery: discard partial + restart (2KB commit threshold)
- [x] 3c: Rate limiter checked during provider selection
- [x] 3d/3e: Ports configurable via env vars ($MCP_BRIDGE_PORT, $G4F_PORT)
- [x] 5d: Subprocess concurrency semaphore (max 4)
- [x] 7f: Allowlist at `configs/mcp-bridge-allowlist.yaml`
- [x] 7c: Named loggers for all new components
- [x] 7d: Bridge startup guard on key loading failure

### From Security Audit (5 PASS, 5 CONCERN → all remediated)

- [x] #1 Key Exposure: Newelle Flatpak scoped to ~/security:ro, keys.env blocked
- [x] #2 Command Injection: PASS — static command lists, no shell=True
- [x] #3 Data Exfiltration: Response sanitization added (strip raw_data, paths, context)
- [x] #4 Privilege Escalation: PASS — user-level, read-only tools
- [x] #5 DoS: Bridge-level rate limiting added (10 req/s global, 2/s per tool)
- [x] #6 Network Exposure: PASS — 127.0.0.1 binding + startup assertion
- [x] #7 g4f Risks: g4f sandboxed via systemd-run (ProtectHome, NoNewPrivileges, MemoryMax)
- [x] #8 Flatpak Bypass: Bridge NEVER imports ai/router.py, RAG uses use_llm=False
- [x] #9 Supply Chain: Dependencies pinned, g4f subprocess-only (GPL isolation)
- [x] #10 Existing System: PASS — additive architecture, no modifications

### Security Posture

- Keys never leave bridge process (scoped loading, router never imported in bridge)
- No shell=True, no user arg interpolation
- Static command lists only
- 127.0.0.1 binding (network-unreachable) + startup assertion
- Output truncation (4KB + `...[truncated]`)
- Response sanitization (strip raw_data, file paths, context chunks)
- Rate limiting: provider-level + bridge-level (10 req/s global)
- g4f sandboxed: systemd-run --user with ProtectHome, NoNewPrivileges, MemoryMax=512M
- g4f environment scrubbed: all API keys removed before subprocess spawn
- Newelle Flatpak scoped: ~/security:ro only, keys/SSH/GPG explicitly blocked
