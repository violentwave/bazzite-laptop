# S4: Voice Agent (Jarvis) — Design Spec

## Overview
Voice-enabled AI assistant for the Bazzite gaming laptop security/productivity dashboard. Extends the existing PySide6 dashboard (SP2) with Jarvis as the FIRST tab. Supports text + voice input (push-to-talk), streaming LLM responses, and 100% free operation via local STT/TTS combined with cloud free-tier LLM rotation.

**Hardware target:** i7-7700HQ, 16GB RAM, GTX 1060 6GB, Bazzite 43 (immutable Fedora Atomic).

## Approach
**Text-First (Phase 1):** Ship a working text assistant integrated into the dashboard before adding voice capabilities. Voice server runs in a separate venv with IPC, added in Phase 2.

## Architecture

### File Structure
```
ai/jarvis/                          # Main venv (existing .venv/)
  __init__.py
  agent.py                          # JarvisAgent orchestrator
  tools.py                          # ToolExecutor (YAML allowlist, no shell injection)
  memory.py                         # ConversationMemory (sliding window, provider-aware)
  intent.py                         # IntentClassifier (ONNX embed + @ruvector/router)
  protocol.py                       # IPC message types (shared between venvs)
  cache.py                          # Multi-layer cache coordinator

ai/voice/                           # Separate venv (voice-specific deps)
  __init__.py
  server.py                         # VoiceServer (Unix socket, asyncio event loop)
  stt.py                            # MoonshineSTT (ONNX inference wrapper)
  tts.py                            # KokoroTTS (ONNX inference wrapper via kokoro-onnx)
  audio.py                          # AudioCapture/Playback (sounddevice + PipeWire)

tray/jarvis_tab.py                  # JarvisTab QWidget (first tab in dashboard)
tray/jarvis_widget.py               # Phase 3: Floating compact widget

scripts/start-jarvis-voice.sh       # Voice server launcher
scripts/install-jarvis-voice.sh     # Voice venv setup

configs/jarvis-tools-allowlist.yaml  # Declarative tool definitions
```

### Data Flow
```
User input (text or voice)
        |
        v
  ai/jarvis/agent.py (JarvisAgent orchestrator)
        |
        +---> intent.py (ONNX embed + HNSW match)
        |         |
        |         +---> 40-50% local handler (template response, $0)
        |         +---> 10-15% cache hit (exact or semantic, $0)
        |         +---> 5-10% ReasoningBank pattern ($0)
        |         +---> 25-35% cloud LLM (free tier rotation, $0)
        |
        +---> tools.py (YAML allowlist execution)
        +---> memory.py (conversation context)
        +---> cache.py (multi-layer response cache)
        |
        v
  tray/jarvis_tab.py (streaming display via QThread + Qt signals)
```

### Voice Data Flow (Phase 2)
```
Microphone (PipeWire/sounddevice)
        |
        v
  ai/voice/server.py (Unix socket at $XDG_RUNTIME_DIR/jarvis-voice.sock)
        |
        +---> audio.py (AudioCapture, VAD gating)
        +---> stt.py (Moonshine Base ONNX, CPU)
        |         |
        |         v
        |     JSON-Lines IPC --> ai/jarvis/agent.py
        |                              |
        |                              v
        +<-- JSON-Lines IPC <-- TTS_SPEAK message
        |
        +---> tts.py (Kokoro v1.0 ONNX int8, CPU)
        +---> audio.py (AudioPlayback, PipeWire)
```

### IPC Protocol
Unix domain socket at `$XDG_RUNTIME_DIR/jarvis-voice.sock`. JSON-Lines protocol (one JSON object per line, newline-delimited). Defined in `ai/jarvis/protocol.py` (shared between venvs via copy or symlink).

```python
class MsgType(str, Enum):
    STT_START = "stt_start"       # Client -> Voice: begin recording
    STT_STOP = "stt_stop"         # Client -> Voice: stop recording
    STT_RESULT = "stt_result"     # Voice -> Client: final transcription
    STT_PARTIAL = "stt_partial"   # Voice -> Client: interim transcription
    TTS_SPEAK = "tts_speak"       # Client -> Voice: synthesize and play text
    TTS_STOP = "tts_stop"         # Client -> Voice: interrupt playback
    TTS_DONE = "tts_done"         # Voice -> Client: playback finished
    PING = "ping"                 # Keepalive request
    PONG = "pong"                 # Keepalive response
    ERROR = "error"               # Error report (either direction)
    SHUTDOWN = "shutdown"         # Client -> Voice: graceful shutdown
```

Each message is a JSON object with at minimum `{"type": "<MsgType>", "ts": <unix_ms>}`. Additional fields per type (e.g., `"text"` for STT_RESULT/TTS_SPEAK, `"code"` for ERROR).

## Intelligence Pipeline (Zero-Cost Strategy)

```
Voice --> Moonshine STT (local CPU, $0)
  --> AIDefence + LLM Guard scan (<15ms, $0)
  --> ONNX embed (cached, <1ms after first, $0)
  --> @ruvector/router HNSW intent match (<1ms)
      +-- 40-50% --> Local handler + template ($0)
      +-- 10-15% --> Exact-match cache hit ($0)
      +-- 5-10%  --> ReasoningBank pattern ($0)
      +-- 25-35% --> Cloud LLM (free tier rotation, $0)
            --> MoE/Q-Learning selects cheapest provider
            --> Cache response for next time
  --> Kokoro TTS (local CPU, $0)
```

**Estimated local handling rate:** 55-75% of all commands never touch a cloud API.

**Free-tier token budget (daily):**
| Provider | Daily Tokens | Notes |
|----------|-------------|-------|
| Mistral | ~33M | 1B/month, primary workhorse |
| z.ai Flash | unlimited | Throttled, OpenAI-compatible API |
| Gemini Flash-Lite | ~3.3M | 1,000 RPD at ~3,300 tokens avg |
| Groq | ~3M | Also provides free Whisper STT fallback |
| Cerebras | 1M | NEW provider, add to litellm config |
| Cloudflare Workers AI | ~200K | NEW provider, add to litellm config |
| **Total** | **~51M** | **~56,000 interactions/day free** |

## Components

### STT: Moonshine Base (ONNX)
- MIT license, ~500MB RAM, CPU-only inference via onnxruntime
- ONNX format avoids PyTorch dependency in voice venv for STT
- Toggle to Moonshine Small if accuracy insufficient (laptop fan noise environment)
- Models stored in `~/.cache/bazzite-ai/models/moonshine/`

### TTS: Kokoro v1.0 (ONNX int8)
- Apache 2.0 license, ~300MB RAM, 88MB model file
- Via `kokoro-onnx` Python wrapper (handles ONNX session management)
- CPU-only, int8 quantized for low memory and acceptable latency
- Models stored in `~/.cache/bazzite-ai/models/kokoro/`

### VAD: Voice Activity Detection
- **Phase 1:** `webrtcvad` (lightweight, no ML deps, sufficient for PTT)
- **Phase 2:** Silero VAD (ONNX, 2MB model) for continuous listening mode
- Requires `torch` CPU-only build for Silero (Phase 2 only)

### LLM: Existing ai/router.py
- Add `route_query_stream()` async generator (NEW) for streaming responses
- Uses existing `litellm.Router` with lazy init
- Add Cerebras and Cloudflare Workers AI to `configs/litellm-config.yaml`
- Task type routing: `fast` for simple queries, `reason` for complex, `batch` for summaries

### Intent Classification
- `@ruvector/router` (native Rust HNSW, <1ms lookup, 384-dim vectors)
- ONNX embedding model (matches existing nomic-embed-text dimensions)
- Intent categories: system_status, security_action, health_query, gaming_query, general_chat, tool_call
- Confidence threshold: >0.85 for local handler, <0.85 falls through to LLM

### Response Caching (4-layer)
| Layer | Backend | TTL | Hit Rate Target |
|-------|---------|-----|-----------------|
| L1 | LiteLLM built-in disk cache | 24h | 5-10% |
| L2 | llm-hooks.js exact-match cache | 1h | 10-15% |
| L3 | ReasoningBank HNSW pattern retrieval | session | 5-10% |
| L4 | LanceDB semantic cache (existing ~/security/vector-db/) | 7d | 5-10% |

### Structured Output
- `instructor` library for Pydantic-validated tool call extraction
- Ensures LLM responses conform to expected schemas for tool invocations
- Falls back to regex extraction if instructor parsing fails

### Safety
- **AIDefence** (50+ patterns, <10ms): prompt injection, jailbreak, PII detection
- **LLM Guard** (offline, MIT license): secondary scanning for adversarial inputs
- Both gates run BEFORE any LLM submission
- Voice-specific threats: adversarial audio patterns, background TV/radio injection, multi-turn privilege escalation

### Rate Limiting
- Production rate limiter (in-memory token bucket) from existing `ai/rate_limiter.py`
- Trust-based per-subsystem quotas: Jarvis gets its own allocation separate from threat intel
- Add `rph` (requests per hour) window tracking alongside existing `rpm`/`rpd`

### Budget Control: ContinueGate
- Linear regression on cumulative token spend over time
- Detects budget acceleration (spending faster than sustainable rate)
- Triggers graceful degradation: switch to cheaper providers, increase cache aggressiveness
- Hard stop at configurable daily ceiling (default: 0, since everything is free tier)

## Tool Allowlist (configs/jarvis-tools-allowlist.yaml)

```yaml
# Jarvis Tool Definitions
# SECURITY: Commands are static — NEVER constructed from user input.
# SECURITY: No shell=True, no string interpolation, no user args in commands.

tools:
  # --- Read-only system queries (safe, no privilege needed) ---
  disk_usage:
    description: "Show disk usage for all mounted filesystems"
    command: ["df", "-h"]
    privileged: false

  cpu_temps:
    description: "Show CPU core temperatures"
    command: ["sensors", "-j"]
    privileged: false

  memory_usage:
    description: "Show RAM and swap usage"
    command: ["free", "-h"]
    privileged: false

  gpu_status:
    description: "Show NVIDIA GPU status (temp, memory, utilization)"
    command: ["nvidia-smi", "--query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"]
    privileged: false

  system_uptime:
    description: "Show system uptime and load average"
    command: ["uptime"]
    privileged: false

  service_status:
    description: "Show status of security-related services"
    command: ["systemctl", "is-active", "clamav-freshclam", "system-health.timer"]
    privileged: false

  last_scan_log:
    description: "Show the last ClamAV scan summary"
    command: ["tail", "-20", "/home/lch/security/logs/scan-latest.log"]
    privileged: false

  health_snapshot:
    description: "Show latest health snapshot summary"
    command: ["tail", "-30", "/var/log/system-health/health-latest.log"]
    privileged: false

  # --- Privileged tools (redirect to dashboard pkexec buttons) ---
  run_quick_scan:
    description: "Launch a quick ClamAV scan"
    privileged: true
    redirect: "dashboard:security:quick_scan"

  run_deep_scan:
    description: "Launch a deep ClamAV scan"
    privileged: true
    redirect: "dashboard:security:deep_scan"

  run_health_snapshot:
    description: "Run a full system health snapshot"
    privileged: true
    redirect: "dashboard:health:snapshot"
```

Tool execution rules:
1. `ToolExecutor` loads YAML at startup, rejects any tool not in the allowlist
2. Commands are `subprocess.run(cmd_list, capture_output=True, timeout=30)` — never `shell=True`
3. No user-supplied arguments are ever interpolated into commands
4. Privileged tools emit a Qt signal that activates the corresponding dashboard button (which uses `pkexec`)
5. Tool output is truncated to 2000 chars before passing to LLM context

## UI Design

### Jarvis Tab (first tab in dashboard)

The Jarvis tab becomes tab index 0 in `DashboardWindow.QTabWidget`, pushing Security/Health/About to indices 1/2/3.

**Layout (top to bottom):**
```
+-------------------------------------------------------+
|  [Jarvis icon]  Jarvis Assistant    [voice: connected] |
+-------------------------------------------------------+
|                                                       |
|  Chat history (QScrollArea with custom message        |
|  widgets — user messages right-aligned, Jarvis        |
|  responses left-aligned, tool outputs in collapsible  |
|  code blocks)                                         |
|                                                       |
|  Streaming responses render incrementally via          |
|  QThread worker emitting textChunk(str) signal        |
|                                                       |
+-------------------------------------------------------+
|  [text input] [mic PTT] [send]                        |
+-------------------------------------------------------+
```

**Implementation details:**
- Chat history: `QScrollArea` containing a `QVBoxLayout` of message widgets
- Each message widget: `QLabel` with word wrap, styled via QPalette (follows KDE dark/light theme)
- Text input: `QLineEdit` with Enter-to-send, Shift+Enter for newline not needed (single line)
- PTT button: `QPushButton` with press-and-hold behavior (`pressed`/`released` signals)
- Send button: `QPushButton`, disabled while response is streaming
- Voice status indicator: `QLabel` with colored dot (green=connected, gray=disconnected, red=recording)
- Streaming: `QThread` subclass runs `async for chunk in route_query_stream(...)`, emits `textChunk` signal per chunk, UI appends to current response widget via signal-slot (thread-safe)
- Tool call results displayed in monospace font, collapsible via `QToolButton` toggle

### Floating Widget (Phase 3)

```
+----------------------------+
| [mic] [input...] [send]   |
| Last response preview...   |
+----------------------------+
```

- `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint`
- KDE global hotkey via `kglobalaccel` D-Bus API (e.g., Meta+J)
- Compact: single-line input + last response truncated to 2 lines + mic button
- Click response preview to open full dashboard Jarvis tab
- Position saved/restored via `QSettings("BazziteSecurity", "JarvisWidget")`

## Conversation Design

### System Prompt
Role-focused with dynamic context injection:

```
You are Jarvis, a security and system assistant for a Bazzite gaming laptop.

Current system status:
{status_from_security_dot_status}

You can run tools to check system health, disk usage, temperatures, and more.
For privileged actions (scans, health snapshots), you will redirect the user
to the dashboard buttons that handle authentication.

Be concise. Prefer bullet points for status reports. If you don't know
something, say so rather than guessing.
```

- Static portion: ~200 tokens
- Dynamic `~/security/.status` injection: ~300 tokens
- Total system context: ~500 tokens

### Conversation Memory
- **Default:** 15-turn sliding window (user + assistant pairs)
- **Provider-aware scaling:**
  - Groq (128K context): 30 turns
  - Gemini Flash-Lite (128K context): 30 turns
  - Cerebras (8K context): 8 turns
  - Mistral (32K context): 15 turns (default)
- **Summary compression:** At window limit, compress oldest turns into a single summary via one `fast` LLM call (~100 tokens output)
- **Phase 1:** Ephemeral per dashboard session (cleared on tab close)
- **Phase 3:** Persistent via LanceDB conversation store

### Status File Isolation
- Jarvis writes its own status to `~/security/.jarvis-status` (separate file)
- NEVER writes to `~/security/.status` (owned by ClamAV + health monitor)
- `.jarvis-status` schema: `{"state": "idle|thinking|speaking|error", "last_query": "...", "last_response_time_ms": N, "session_turns": N}`
- Atomic writes: read-modify-write + tmp + mv (same pattern as `.status`)

## Pre-S4 Fixes (MUST Complete Before Starting)

These are blocking issues in existing code that must be resolved before S4 work begins.

### 1. Rate Limiter Deadlock Fix
**Problem:** `_write_state()` in `ai/rate_limiter.py` acquires a lock internally but is called from methods that already hold the lock, causing potential deadlock.
**Fix:** Make `_write_state()` lock-free (assumes caller holds lock). Only acquire the lock at public API boundaries (`check_limit()`, `record_usage()`, etc.).

### 2. Amend "No Daemons" Constraint
**Problem:** CLAUDE.md AI Layer Rule 4 says "NEVER run AI as persistent daemons." Jarvis voice server is a persistent process (second permitted after the tray app).
**Fix:** Add explicit exception in CLAUDE.md: "Exception: Jarvis voice server (`ai/voice/server.py`) is a permitted persistent process, managed by `scripts/start-jarvis-voice.sh`. It must implement idle unload (5 min) and memory pressure guards."

### 3. Reverse VT Cascade Order
**Problem:** Current threat intel cascade hits VirusTotal first, consuming the limited 500/day quota before trying free-unlimited providers.
**Fix:** Reorder cascade to MalwareBazaar (unlimited) -> OTX (unlimited) -> VT (500/day, last resort).

## Phased Delivery

### Phase 1: Text Assistant

**Scope:** Full text-based Jarvis integrated into the dashboard. No voice, no floating widget.

**Deliverables:**
| File | Purpose |
|------|---------|
| `ai/jarvis/__init__.py` | Package init |
| `ai/jarvis/agent.py` | JarvisAgent orchestrator (intent -> route -> respond) |
| `ai/jarvis/tools.py` | ToolExecutor (YAML allowlist, subprocess, no shell) |
| `ai/jarvis/memory.py` | ConversationMemory (sliding window, provider-aware scaling) |
| `ai/jarvis/intent.py` | IntentClassifier (ONNX embed + cosine similarity) |
| `ai/jarvis/protocol.py` | IPC message types (MsgType enum, shared) |
| `ai/jarvis/cache.py` | Multi-layer cache coordinator (L1-L4) |
| `tray/jarvis_tab.py` | JarvisTab QWidget (first tab in dashboard) |
| `configs/jarvis-tools-allowlist.yaml` | Declarative tool definitions |
| `tests/test_jarvis_agent.py` | Agent orchestration tests |
| `tests/test_jarvis_tools.py` | Tool executor tests (allowlist enforcement) |
| `tests/test_jarvis_memory.py` | Conversation memory tests |
| `tests/test_jarvis_intent.py` | Intent classification tests |

**Changes to existing files:**
| File | Change |
|------|--------|
| `ai/router.py` | Add `route_query_stream()` async generator |
| `ai/config.py` | Add scoped `load_keys(scope="llm")` (Jarvis only gets LLM keys) |
| `ai/rate_limiter.py` | Fix deadlock + add `rph` window + per-subsystem quotas |
| `configs/litellm-config.yaml` | Add Cerebras + Cloudflare Workers AI providers |
| `configs/ai-rate-limits.json` | Add Cerebras + Cloudflare rate limit definitions |
| `tray/dashboard_window.py` | Insert Jarvis as first tab (index 0) |
| `requirements.txt` | Add `instructor` |

**Phase 1 does NOT include:** Voice server, PTT button functionality (button shown but disabled/grayed), floating widget, @ruvector/router (uses simpler cosine similarity in Phase 1).

### Phase 2: Voice

**Scope:** Full voice pipeline with push-to-talk. Separate venv for voice dependencies.

**Deliverables:**
| File | Purpose |
|------|---------|
| `ai/voice/__init__.py` | Package init |
| `ai/voice/server.py` | VoiceServer (asyncio, Unix socket, JSON-Lines) |
| `ai/voice/stt.py` | MoonshineSTT (ONNX inference, lazy load, idle unload) |
| `ai/voice/tts.py` | KokoroTTS (ONNX int8, via kokoro-onnx wrapper) |
| `ai/voice/audio.py` | AudioCapture/Playback (sounddevice + PipeWire) |
| `scripts/start-jarvis-voice.sh` | Voice server launcher (activates voice venv) |
| `scripts/install-jarvis-voice.sh` | Voice venv creation + dependency install |
| `tests/test_jarvis_voice_protocol.py` | IPC protocol tests |
| `tests/test_jarvis_stt.py` | STT wrapper tests (mocked ONNX) |
| `tests/test_jarvis_tts.py` | TTS wrapper tests (mocked ONNX) |

**Voice venv dependencies (`ai/voice/requirements.txt`):**
```
onnxruntime>=1.19.0,<1.21
kokoro-onnx>=0.4.0
numpy>=1.26.0,<2.1
sounddevice>=0.5.0
scipy>=1.14.0
pyyaml>=6.0
```

**Phase 2 additions (after core voice works):**
```
silero-vad>=5.1
torch>=2.2.0,<2.6          # CPU-only build
torchaudio>=2.2.0,<2.6     # CPU-only build
llm-guard                    # Offline scanners only
```

CRITICAL: Voice venv MUST use `onnxruntime` (CPU), NEVER `onnxruntime-gpu`. GPU VRAM is reserved for games.

**Voice server behavior:**
- Lazy model loading: STT and TTS models loaded on first use, not at startup
- 5-minute idle unload: if no STT/TTS activity for 5 minutes, unload models from RAM
- Memory pressure guard: refuse to load models if < 1.5GB RAM available (`/proc/meminfo` check)
- CPU temp guard: throttle inference (add 500ms delay between chunks) if CPU > 85C (`sensors`)
- Moonshine Base default, toggle to Small via config if accuracy insufficient in noisy environment
- Models stored in `~/.cache/bazzite-ai/models/` (not in repo, not in /tmp)

**Changes to existing files:**
| File | Change |
|------|--------|
| `tray/jarvis_tab.py` | Enable PTT button, wire to voice server IPC |
| `CLAUDE.md` | Add Jarvis voice server daemon exception |

### Phase 3: Polish

**Scope:** Quality-of-life features, advanced intelligence, persistent memory.

**Deliverables:**
| File | Purpose |
|------|---------|
| `tray/jarvis_widget.py` | Floating compact widget |
| `ai/jarvis/moe_router.py` | MoE/Q-Learning adaptive provider selection |

**Features:**
- **Floating widget** with KDE global hotkey (`kglobalaccel` D-Bus, Meta+J default)
- **Persistent conversation memory** via LanceDB (`~/security/vector-db/jarvis-conversations/`)
- **GameMode-aware TTS muting:** query GameMode D-Bus API (`com.feralinteractive.GameMode`), mute TTS when active
- **MoE Router / Q-Learning Router:** track per-provider latency, quality, and cost; adaptively select cheapest provider meeting quality threshold
- **Cross-session memory** via mem0 (Apache 2.0) for long-term user preference learning
- **SONA trajectory training** on voice command patterns for faster intent matching
- **Claims-based tool restriction:** per-session tool access claims (restrict dangerous tools in voice-only mode)
- **@ruvector/router** upgrade: replace Phase 1 cosine similarity with native Rust HNSW for <1ms intent matching

## Security Considerations

### Key Isolation
- `load_keys(scope="llm")` returns ONLY LLM provider keys (Mistral, z.ai, Gemini, Groq, Cerebras, Cloudflare)
- Jarvis NEVER receives threat intel keys (VirusTotal, OTX, MalwareBazaar)
- Jarvis NEVER receives SOPS keys or encryption material

### Input Sanitization
- AIDefence scans ALL user input before processing (prompt injection, jailbreak patterns)
- LLM Guard (Phase 2) provides secondary offline scanning
- Both gates must pass before any LLM submission
- Failed scans return a canned safe response, never forward to LLM

### Tool Execution Security
- Static YAML allowlist loaded at startup — runtime additions impossible
- `subprocess.run(cmd_list)` — NEVER `shell=True`
- No user-supplied arguments interpolated into any command
- Privileged commands redirect to dashboard pkexec buttons (user must authenticate)
- Tool output truncated to 2000 chars (prevents LLM context overflow attacks)

### Voice-Specific Threats
| Threat | Mitigation |
|--------|-----------|
| Adversarial audio injection | AIDefence scans transcribed text, not raw audio |
| Background TV/radio pickup | VAD gating (Phase 2) + PTT-only (Phase 1) |
| Multi-turn privilege escalation | Conversation memory includes tool call history; refuse repeated privileged redirects |
| Replay attacks | Timestamps in IPC messages; reject messages older than 5s |
| Voice impersonation | Out of scope (single-user laptop, physical access assumed trusted) |

### File System Safety
- Jarvis status: `~/security/.jarvis-status` (own file, never touches `.status`)
- Atomic writes only (tmp + rename pattern)
- No write access to ClamAV logs, quarantine, or health logs
- Voice models in `~/.cache/` (standard XDG cache, expendable)

## Resource Budget

### Memory (RAM)
| Component | Idle | Active | Peak |
|-----------|------|--------|------|
| Dashboard (PySide6) | ~30MB | ~50MB | ~80MB |
| Jarvis agent (text only) | ~20MB | ~40MB | ~60MB |
| Voice server (models unloaded) | ~30MB | — | — |
| Voice server (STT loaded) | — | ~530MB | ~550MB |
| Voice server (STT + TTS loaded) | — | ~830MB | ~880MB |
| **Total (text only)** | **~50MB** | **~90MB** | **~140MB** |
| **Total (text + voice)** | **~80MB** | **~530MB** | **~880MB** |

### Gaming Mode Behavior
- Voice server: pause STT/TTS, unload models immediately (free ~800MB)
- Jarvis tab: text-only mode remains available (minimal resource usage)
- OOM score adjustment: set `oom_score_adj` to +500 for voice server process (killed before tray app or game)
- GameMode detection via D-Bus query on each voice activation attempt

### CPU
- STT inference: ~200ms per utterance on i7-7700HQ (Moonshine Base)
- TTS inference: ~150ms per sentence on i7-7700HQ (Kokoro int8)
- Intent classification: <5ms (ONNX embed + cosine/HNSW)
- No GPU usage (all CPU inference, GPU reserved for games)

## Dependencies

### Phase 1 (main venv additions)
```
instructor>=1.0.0    # Structured LLM output with Pydantic validation
```

### Phase 2 (voice venv, separate from main .venv/)
```
onnxruntime>=1.19.0,<1.21       # CPU-only inference runtime
kokoro-onnx>=0.4.0              # Kokoro TTS ONNX wrapper
numpy>=1.26.0,<2.1              # Array operations for audio
sounddevice>=0.5.0              # PipeWire/ALSA audio I/O
scipy>=1.14.0                   # Audio resampling
pyyaml>=6.0                     # Config parsing
```

### Phase 2 additions (after core voice works)
```
silero-vad>=5.1                 # Voice activity detection (requires torch)
torch>=2.2.0,<2.6              # CPU-only build (for Silero VAD only)
torchaudio>=2.2.0,<2.6         # CPU-only build (audio preprocessing)
llm-guard                       # Offline prompt injection scanners
```

### Phase 3 (main venv additions)
```
mem0ai>=0.1.0                   # Cross-session memory (Apache 2.0)
```

CRITICAL DEPENDENCY RULES:
- Voice venv: NEVER install `onnxruntime-gpu` — GPU VRAM is for games only
- Voice venv: Use CPU-only torch build (`--index-url https://download.pytorch.org/whl/cpu`)
- Main venv: `instructor` is the only new dependency for Phase 1
- Both venvs managed by `uv`, never system pip

## Bazzite OS Constraints

- Voice venv created by `scripts/install-jarvis-voice.sh` using `uv venv` in project directory
- `UV_CACHE_DIR=/tmp/uv-cache` required on Bazzite (read-only home cache issue)
- Audio I/O via PipeWire (Bazzite default), `sounddevice` auto-detects PipeWire backend
- No `rpm-ostree` packages needed (all Python deps in venvs)
- No `sudo` in any Jarvis code (privileged actions redirect to dashboard pkexec)
- Voice server launcher script uses absolute paths (matches `start-security-tray-qt.sh` pattern)
- Models downloaded to `~/.cache/bazzite-ai/models/` (survives updates, user-writable)

## Deployment (Two-Phase)

**Phase A (Claude Code):**
- Create all `ai/jarvis/` modules
- Create `tray/jarvis_tab.py`
- Create `configs/jarvis-tools-allowlist.yaml`
- Modify `ai/router.py` (add streaming), `ai/config.py` (scoped keys), `ai/rate_limiter.py` (fixes)
- Modify `tray/dashboard_window.py` (Jarvis as first tab)
- Modify `configs/litellm-config.yaml` (new providers)
- Add `instructor` to `requirements.txt`
- Create all test files in `tests/`
- Run `python -m pytest tests/ -v` to verify

**Phase B (User manually, for voice server only):**
- Run `bash scripts/install-jarvis-voice.sh` (creates voice venv)
- Copy voice launcher: `sudo cp scripts/start-jarvis-voice.sh /usr/local/bin/`
- Start voice server: `/usr/local/bin/start-jarvis-voice.sh`
- Optionally add to autostart (after tray, before desktop ready)

## Rollback

- **Phase 1:** Remove Jarvis tab from `dashboard_window.py` (revert to Security as first tab). `ai/jarvis/` can remain inert.
- **Phase 2:** Kill voice server (`pkill -f jarvis-voice`). Remove from autostart. Dashboard reverts to text-only mode automatically (PTT button grays out when voice socket unavailable).
- **Phase 3:** Remove floating widget autostart. Persistent memory remains in LanceDB but is not loaded without the widget.

## Testing

### Phase 1 Tests
- `tests/test_jarvis_agent.py`: Agent orchestration (intent routing, tool dispatch, streaming mock, error handling)
- `tests/test_jarvis_tools.py`: Allowlist enforcement (reject unknown tools, no shell injection, privileged redirect, output truncation, timeout handling)
- `tests/test_jarvis_memory.py`: Sliding window (15 turns, provider scaling, summary compression trigger, ephemeral clear)
- `tests/test_jarvis_intent.py`: Intent classification (known intents, unknown fallthrough, confidence thresholds, edge cases)
- `tests/test_jarvis_cache.py`: Multi-layer cache (L1-L4 hit/miss, TTL expiry, cache invalidation)

### Phase 2 Tests
- `tests/test_jarvis_voice_protocol.py`: IPC message serialization, deserialization, unknown type handling, timestamp validation
- `tests/test_jarvis_stt.py`: STT wrapper (mocked ONNX session, transcription flow, error recovery)
- `tests/test_jarvis_tts.py`: TTS wrapper (mocked ONNX session, synthesis flow, interrupt handling)
- `tests/test_jarvis_voice_server.py`: Server lifecycle (startup, client connect, idle unload, memory pressure guard, shutdown)

### Manual Smoke Tests
1. Start dashboard -> verify Jarvis is first tab
2. Type query -> verify streaming response appears
3. Type "disk usage" -> verify tool executes and output displays
4. Type "run quick scan" -> verify redirect to dashboard Security tab button
5. (Phase 2) Hold PTT -> speak -> verify transcription + response + audio playback
6. (Phase 2) Verify voice server idle unload after 5 minutes
7. (Phase 3) Press Meta+J -> verify floating widget appears

### Regression
- All 374+ existing tests must continue passing after each phase
- `ruff check ai/ tray/ tests/` must pass
- `bandit -r ai/ -c pyproject.toml` must pass

## Known Limitations

- **Moonshine accuracy in noisy environments:** Laptop fan noise may degrade STT accuracy. Mitigation: toggle to Moonshine Small model, or use Groq Whisper STT as cloud fallback.
- **Kokoro voice quality:** int8 quantization trades quality for speed/memory. Acceptable for a system assistant; not suitable for creative voice work.
- **No wake word:** Phase 1-2 use PTT only. Always-on wake word detection (Phase 4+) would require additional CPU overhead and a dedicated wake word model.
- **Single language:** English only. Moonshine and Kokoro support English; multilingual would require different models.
- **No conversation export:** Phase 1-2 conversations are ephemeral. Phase 3 adds persistence but no export to file.
- **PipeWire assumption:** Audio I/O assumes PipeWire (Bazzite default). PulseAudio fallback untested.

## Success Criteria

1. Text input to response in <3 seconds (cache hit: <100ms)
2. Voice input to audio response in <5 seconds end-to-end (Phase 2)
3. 55-75% of commands handled locally without any cloud API call
4. 100% of remaining commands handled by free-tier providers ($0/month)
5. Zero prompt injection vulnerabilities (AIDefence + LLM Guard gate)
6. Zero impact on gaming performance when voice is paused
7. All 374+ existing tests continue passing after each phase
8. Dashboard RAM usage < 150MB (text-only mode)
9. Voice server gracefully unloads within 10 seconds of gaming mode activation
10. Jarvis never writes to `~/security/.status` (uses own `.jarvis-status`)
