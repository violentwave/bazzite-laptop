# Phase 7 Master Plan — Bazzite AI Layer
## Stabilization, OpenCode Integration, GPU Optimization & Cloud Embeddings

**System:** Acer Predator G3-571 | Bazzite 43 | Last updated: 2026-03-22
**Author:** Claude Opus (claude.ai) + Perplexity Deep Research
**Status:** Planning — Ready for CC prompt generation

---

## Executive Summary

Phase 7 addresses four critical areas in priority order:

1. **EMERGENCY: Memory/Freeze Stabilization** — The system is freezing under
   memory pressure. Root causes: uncapped AI services, btrfs compressed readahead
   D-state bug, potential KDE/NVIDIA fd-leak, and no earlyoom failsafe.
2. **CRITICAL: External SSD + Storage Recovery** — Lost permissions break LanceDB
   symlink, gaming library, and R2 log archiving. Needs persistent fstab mount.
3. **HIGH: Cloud Embeddings Migration** — Switch from Ollama nomic-embed-text
   (300MB VRAM) to Jina AI v3 cloud embeddings (free tier, 768-dim, better quality).
   Permanently frees GPU VRAM for gaming/Wayland.
4. **HIGH: OpenCode Integration** — Vendor-neutral CLI coding agent pointing at
   the existing LLM proxy + MCP bridge. Plugins for context pruning, secret
   redaction, and safety.
5. **MEDIUM: GPU Optimization** — Thermal management, persistence mode, fan curve,
   clock offsets, and monitoring for the end-of-life GTX 1060.
6. **LOW: Activity-Aware Resource Control** — Dynamic cgroup priority shifting
   between gaming, coding, and AI workloads via GameMode hooks.

**Timeline:** 3 phases over ~3 weeks
**Risk level:** Phase 7A is low-risk (all reversible). Phase 7B moderate. Phase 7C low.

---

## Phase 7A — Emergency Stabilization (Week 1)

### 7A.1 — Fix Memory Freezes (DAY 1-2)

**Root causes identified by research:**

- **No earlyoom failsafe.** systemd-oomd alone fails to prevent desktop freezes
  under pathological memory pressure (known Fedora issue).
- **AI services uncapped.** LLM proxy (~20MB) and MCP bridge (~60MB) have no
  MemoryMax limits — if they leak or spawn heavy subprocesses, they consume
  freely.
- **btrfs compressed readahead D-state.** A kernel bug (patch submitted March
  2026) causes tasks to enter uninterruptible sleep during compressed readahead
  under memory pressure. Workaround: reduce read_ahead_kb.
- **KDE/NVIDIA fd-leak.** NVIDIA driver 580.95.05 has a confirmed file descriptor
  leak with Plasma 6 explicit sync (NVIDIA internal bug 5556719). Long sessions
  accumulate fds until kwin stalls.
- **vm.dirty_ratio too high.** Default 20% = 3.2GB dirty pages. Combined with
  ZRAM + high swappiness, write bursts from log archiving/R2/rag-embed stall
  other processes.

**Actions (all require sudo — Phase B manual steps):**

1. **Install earlyoom alongside systemd-oomd:**
   ```bash
   rpm-ostree install earlyoom
   # After reboot:
   sudo systemctl enable --now earlyoom.service
   ```
   Configure `/etc/sysconfig/earlyoom`:
   ```
   EARLYOOM_ARGS="-m 4 -M 90 --avoid '^(plasmashell|kwin_wayland|systemd|dbus)$' --prefer '^(Web Content|python3|ollama|Steam)$' -n --notification"
   ```
   Translation: kill when free RAM < 4% or swap > 90%. Never kill the desktop
   session. Prefer killing browser tabs, Python AI processes, Ollama, or Steam.

2. **Tune systemd-oomd thresholds:**
   Create `/etc/systemd/oomd.conf.d/90-bazzite.conf`:
   ```ini
   [OOM]
   SwapUsedLimit=80%
   DefaultMemoryPressureLimit=60%
   DefaultMemoryPressureDurationSec=20s
   ```
   Create `/etc/systemd/system/user.slice.d/90-oomd-protect.conf`:
   ```ini
   [Slice]
   ManagedOOMSwap=kill
   ManagedOOMMemoryPressure=kill
   ManagedOOMMemoryPressureLimit=60%
   MemoryMin=1G
   MemoryLow=2G
   ```

3. **Fix btrfs readahead D-state:**
   Create `/etc/systemd/system/btrfs-readahead-tune.service`:
   ```ini
   [Unit]
   Description=Reduce btrfs readahead to prevent D-state under memory pressure
   After=local-fs.target

   [Service]
   Type=oneshot
   ExecStart=/bin/bash -c 'echo 128 > /sys/fs/btrfs/$(findmnt -n -o UUID /)/bdi/read_ahead_kb'
   RemainAfterExit=yes

   [Install]
   WantedBy=multi-user.target
   ```

4. **Tune vm.dirty_ratio:**
   Create `/etc/sysctl.d/90-bazzite-vm.conf`:
   ```ini
   vm.dirty_background_ratio = 3
   vm.dirty_ratio = 10
   vm.dirty_expire_centisecs = 1500
   vm.dirty_writeback_centisecs = 300
   ```
   Note: vm.swappiness=180 stays UNTOUCHED.

5. **Fix KDE/NVIDIA fd-leak:**
   Create `~/.config/plasma-workspace/env/kwin-nvidia.sh`:
   ```bash
   #!/usr/bin/sh
   export KWIN_DRM_FORCE_MGPU_GL_FINISH=1
   ```
   Make executable: `chmod +x ~/.config/plasma-workspace/env/kwin-nvidia.sh`
   This forces a GPU flush per frame and reduces fd accumulation.

6. **Cap AI user services:**
   Add to `~/.config/systemd/user/bazzite-llm-proxy.service` [Service] section:
   ```ini
   MemoryAccounting=yes
   MemoryHigh=80M
   MemoryMax=150M
   CPUWeight=80
   TasksMax=32
   ```
   Add to `~/.config/systemd/user/bazzite-mcp-bridge.service` [Service] section:
   ```ini
   MemoryAccounting=yes
   MemoryHigh=80M
   MemoryMax=150M
   CPUWeight=60
   TasksMax=32
   ```

**Verification:**
- `systemctl status earlyoom.service` — should show active
- `cat /sys/fs/btrfs/$(findmnt -n -o UUID /)/bdi/read_ahead_kb` — should show 128
- `sysctl vm.dirty_ratio` — should show 10
- `systemctl --user show bazzite-llm-proxy.service -p MemoryMax` — should show 150M
- Run a heavy workload (game + browser + AI) and monitor with `systemd-cgtop`

**CC Prompt:** 7A.1 is Phase B only (all sudo). Create unit files in repo at
`systemd/` and `configs/`, user deploys manually.

---

### 7A.2 — Fix External SSD Permissions (DAY 2)

**Problem:** `/run/media/lch/SteamLibrary` loses permissions after reboot.
LanceDB symlink, Steam games, and R2 archiving all break.

**Solution:** Persistent fstab mount to `/var/mnt/ext-ssd`, bypassing udisks2.

**Actions:**
1. Find UUID: `lsblk -f | grep SteamLibrary`
2. Create mountpoint:
   ```bash
   sudo mkdir -p /var/mnt/ext-ssd
   sudo chown lch:lch /var/mnt/ext-ssd
   ```
3. Add to `/etc/fstab`:
   ```
   UUID=<YOUR-UUID>  /var/mnt/ext-ssd  ext4  rw,noatime,x-systemd.automount,x-systemd.idle-timeout=600,nofail  0  2
   ```
4. Test: `sudo mount -a && ls -ld /var/mnt/ext-ssd`
5. Update LanceDB symlink:
   ```bash
   rm ~/security/vector-db
   ln -s /var/mnt/ext-ssd/bazzite-ai/vector-db ~/security/vector-db
   ```
6. Update Steam library path in Steam settings to `/var/mnt/ext-ssd/...`
7. Update `ai/config.py` if any paths reference `/run/media/`

**CC Prompt:** Update `ai/config.py` path constants if needed. Everything else
is Phase B manual.

---

### 7A.3 — Migrate to Cloud Embeddings: Gemini Embedding 001 (DAY 3-4)

**Why:** Permanently frees 300MB VRAM. Top MTEB quality (68.32 avg, #1 on
multilingual leaderboard). You already have the API key configured. Free tier
is absurdly generous: 10 million TPM. No new dependency — Gemini is already
your primary LLM provider.

**Critical details:**
- Gemini Embedding 001 supports Matryoshka dimensions. We request
  `output_dimensionality=768` to match our existing LanceDB schema. Google
  explicitly recommends 768 as one of three optimal dimension sizes.
- Default is 3072-dim — you MUST pass 768 explicitly or vectors won't fit.
- Each request accepts only ONE input text (not batches). The embedder must
  loop with rate limiting during bulk re-ingestion.
- ALL vectors must be re-embedded. Different model = different latent space.
- Uses your existing `GEMINI_API_KEY` — no new key needed.
- LiteLLM natively maps `dimensions` to Gemini's `outputDimensionality`.

**Migration plan:**

1. **No new API key needed.** `GEMINI_API_KEY` is already in `keys.env` and
   `configs/litellm-config.yaml`. Skip straight to code changes.

2. **Update ai/rag/embedder.py** (CC prompt):
   - Replace Ollama embed calls with LiteLLM Gemini embedding calls:
```python
     response = litellm.embedding(
         model="gemini/gemini-embedding-001",
         input=[text],  # single text per call — Gemini limitation
         dimensions=768,
         task_type="RETRIEVAL_DOCUMENT",  # for ingestion
     )
```
   - Use `task_type="RETRIEVAL_QUERY"` for search queries
   - Keep Cohere as fallback (already exists)
   - Add 100ms delay between calls during bulk re-ingestion to avoid 429s
     (known issue: free tier can 429 on rapid sequential embedding requests)
   - Route through `ai/rate_limiter.py`
   - Add Gemini embedding entry to `configs/ai-rate-limits.json`:
```json
     "gemini_embed": {
       "rpm": 1500,
       "rpd": 10000,
       "tpm": 10000000,
       "note": "gemini-embedding-001 free tier"
     }
```

3. **Re-embed all 5 LanceDB tables** (CC prompt):
   - Drop and recreate: `security_logs`, `threat_intel`, `docs`,
     `health_records`, `scan_records`
   - LanceDB pattern: `db.drop_table("name")` then
     `db.create_table("name", data, mode="overwrite")`
   - Re-run full ingestion: `python -m ai.log_intel --all`
   - Re-run doc ingestion: `bash scripts/ingest-docs.sh --force`
   - Migration script must include backoff: if 429, wait 2s and retry (max 3)

4. **Update Ollama keep_alive** (kept as emergency-only fallback):
   - In any remaining Ollama calls, set `keep_alive=60` (seconds)
   - Model unloads after 60s idle → VRAM freed
   - Ollama is now third in the chain, used only if both cloud providers fail

5. **Update docs and key_manager:**
   - Update `ai/config.py` embedding constants (model name, default dim)
   - Update `verified-deps.md` — primary embed is now Gemini, not Ollama
   - No change to `ai/key_manager.py` — GEMINI_API_KEY already tracked

**Provider chain (embed task type):**
```
Gemini Embedding 001 (primary, cloud, free) → Cohere Embed v3 (fallback) → Ollama nomic (emergency local)
```

**Why not Jina v3:** Jina requires a new API key and has 100K TPM free (vs
Gemini's 10M TPM — 100x more headroom). Gemini is already your primary LLM
provider, already has the key configured, and scores higher on MTEB. One fewer
dependency to manage, forever.

**CC Prompt chain:** 3 prompts — embedder rewrite, re-ingestion script, docs update.
```

---

Also update this line in the **Resource Budget** table near the bottom of the plan. Find:
```
| Jina v3 API | ~5MB (httpx client) | 0 | During embed batches |
```

Replace with:
```
| Gemini Embed API | ~5MB (litellm client) | 0 | During embed batches |

---

### 7A.4 — Update Priority Model: "Active Task First" (DAY 4-5)

**Change:** Replace "Gaming ALWAYS takes priority" with "Active task takes
priority." The system should be context-aware about what you're doing.

**Implementation:**

1. **Update all docs** that say "Gaming ALWAYS takes priority":
   - USER-GUIDE.md, AGENT.md, project-instructions, system profile
   - New language: "The active workload takes priority. When gaming, AI services
     are throttled. When coding, AI gets normal priority. Resource control is
     managed via systemd slices and GameMode hooks."

2. **Create systemd slices** (Phase B):
   ```
   /etc/systemd/system/ai.slice — CPUWeight=200, MemoryHigh=1.5G, MemoryMax=2G
   ```
   Assign LLM proxy and MCP bridge to `Slice=ai.slice`.

3. **GameMode hooks** (Phase B):
   `~/.config/gamemode.ini` start/end commands that throttle AI services
   when any game launches via `gamemoderun`.

**CC Prompt:** Update docs only. Slice files and GameMode config created in
repo, deployed manually.

---

## Phase 7B — OpenCode Integration (Week 2)

### 7B.1 — Fix LLM Proxy Non-Streaming Path (DAY 1)

**Problem:** The non-streaming path in `ai/llm_proxy.py` sends only the last
user message to `route_query()`, discarding conversation history. OpenCode
relies on multi-turn context.

**Solution:** Add `route_chat(task_type, messages, **kwargs)` that passes full
messages array to LiteLLM. Update non-streaming path to use it.

**Also:** OpenCode's built-in OpenAI provider expects the Responses API event
stream, not legacy Chat Completions streaming. The documented workaround is to
set `streaming: false` in the provider options, which preserves full multi-turn
history via complete response parsing.

**CC Prompt:** Single-file edit to `ai/llm_proxy.py` + tests.

---

### 7B.2 — Configure OpenCode (DAY 1-2)

**opencode.json** pointing at the local proxy (NOT directly at z.ai):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "openai": {
      "apiKey": "sk-bazzite-local",
      "baseURL": "http://127.0.0.1:8767/v1",
      "options": {
        "streaming": false
      }
    }
  },
  "model": "openai/code",
  "small_model": "openai/fast",
  "instructions": ["docs/bazzite-ai-system-profile.md"],
  "plugins": []
}
```

Key decisions:
- Use built-in `openai` provider type (not `@ai-sdk/openai-compatible`)
  to avoid the baseURL forwarding bug documented in OpenCode issue #5674
- `streaming: false` avoids the Responses API format mismatch
- `model: "openai/code"` maps to our router's `code` task type
- `small_model: "openai/fast"` maps to `fast` for cheap operations
- Start with empty plugins, add one at a time after verification

**MCP bridge connection:**
OpenCode's MCP config for the bazzite bridge needs a small stdio-to-HTTP
shim since our bridge uses streamable-http, not stdio. Options:
- Write a tiny `scripts/mcp-stdio-bridge.sh` wrapper
- Or configure OpenCode to use our bridge as a remote HTTP MCP server
  (depends on OpenCode's current remote MCP support)

**CC Prompt:** Create opencode.json + MCP shim script.

---

### 7B.3 — Install Verified Plugins (DAY 2-3)

**Tier 1: Efficiency (install first)**

| Plugin | npm name | Version | Purpose |
|--------|----------|---------|---------|
| Dynamic Context Pruning | `@tarquinen/opencode-dcp` | 3.0.4 | Prune old tool outputs, save 30-60% tokens |
| opencode-snip | `opencode-snip` | 1.x | Trim shell command output 60-90% |
| Tokenscope | `@ramtinj95/opencode-tokenscope` | 1.5.x | Per-session token tracking |

**Tier 2: Safety (install next)**

| Plugin | npm name | Version | Purpose |
|--------|----------|---------|---------|
| opencode-vibeguard | `opencode-vibeguard` | 0.1.0 | Redact secrets before LLM calls |

**Tier 3: Workflow (project-level)**

| Plugin | npm name | Version | Purpose |
|--------|----------|---------|---------|
| opencode-handoff | `opencode-handoff` | 0.5+ | Session continuation summaries |
| @plannotator/opencode | `@plannotator/opencode` | 0.6.x | Visual plan review in browser |

**Local plugin (no npm):**
`.opencode/plugins/guard-destructive.js` — blocks `rm -rf`, `git reset --hard`,
`systemctl`, `rpm-ostree`, writes to `/usr` or `/etc`. Uses `tool.execute.before`
hook.

`.opencode/plugins/env-protection.js` — blocks reading `.env`, `keys.env`,
`.pem`, `.key` files. Already created per Perplexity research.

**DCP configuration** (`.opencode/dcp.jsonc`):
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/Opencode-DCP/opencode-dynamic-context-pruning/master/dcp.schema.json",
  "strategies": {
    "dedupe": { "enabled": true },
    "supersedeWrites": { "enabled": true },
    "summarizeLargeOutputs": {
      "enabled": true,
      "maxTokensBeforeSummary": 2000
    }
  },
  "protectSystemMessages": true,
  "protectedTools": [
    "system.llm_status",
    "security.status",
    "system.key_status",
    "system.mcp_manifest"
  ],
  "protectedFilePatterns": [
    "**/ai/config/**",
    "**/.env*",
    "**/keys*",
    "**/bazzite-ai-system-profile.md"
  ]
}
```

Critical: `protectSystemMessages: true` keeps the system prompt stable for
provider-side prompt caching.

**Vibeguard configuration** (`.opencode/vibeguard.json`):
```json
{
  "patterns": [
    { "name": "API_KEY", "regex": "[A-Za-z0-9_\\-]{32,}" },
    { "name": "BEARER_TOKEN", "regex": "Bearer [A-Za-z0-9._\\-]+" },
    { "name": "HOME_PATH", "regex": "/home/lch" }
  ],
  "deterministic": true
}
```

`deterministic: true` ensures the same secret always gets the same placeholder,
which is critical for prompt caching — the prefix stays identical between calls.

**CC Prompt chain:** 3 prompts — plugin configs, local plugins, verification.

---

### 7B.4 — LiteLLM Disk Cache (DAY 3)

**Enable multi-tier caching in the LLM proxy:**

1. **L1: In-memory** — 60s TTL for hot health checks
2. **L2: Disk cache** — on external SSD to reduce internal SSD wear

Configuration in `ai/router.py`:
```python
import litellm
from litellm.caching.caching import Cache

litellm.cache = Cache(
    type="disk",
    disk_cache_dir="/var/mnt/ext-ssd/bazzite-ai/llm-cache",
)
```

Per-request namespace via `cache` parameter:
```python
response = await litellm.acompletion(
    model="...",
    messages=messages,
    cache={"namespace": "opencode", "ttl": 3600}
)
```

TTL strategy:
- `fast` task type: TTL=300s (5 min) — health checks, quick lookups
- `code` task type: TTL=3600s (1 hour) — code generation
- `reason` task type: TTL=1800s (30 min) — analysis
- `batch` task type: TTL=86400s (24 hours) — bulk operations

**CC Prompt:** Single edit to `ai/router.py` + cache config.

---

### 7B.5 — RuFlo Re-Integration as MCP Sidecar (DAY 4-5)

RuFlo v3.5 exposes a full MCP server with 215 tools. Re-integrate as a manual
coding sidecar — NOT a persistent daemon.

**Configuration:**
- Point RuFlo at the same LiteLLM proxy: `http://127.0.0.1:8767/v1`
- Use the same `bazzite-ai-system-profile.md` as system context
- Keep only `code-intelligence` and `test-intelligence` plugins
- RuVector WASM embeddings for local meta-knowledge storage

**OpenCode MCP entry for RuFlo:**
```json
{
  "mcp": {
    "servers": {
      "ruflo": {
        "command": "npx",
        "args": ["-y", "ruflo@latest"],
        "env": {}
      }
    }
  }
}
```

**Rules:**
- Never run as a background daemon
- Never auto-start via systemd
- `npx claude-flow` for manual dev sessions only
- RuFlo memory is for dev process meta-knowledge only
- Long-term project knowledge stays in LanceDB RAG

**CC Prompt:** Config file creation + documentation update.

---

## Phase 7C — GPU Optimization & Polish (Week 3)

### 7C.1 — GPU Thermal & Performance (DAY 1-3)

**IMPORTANT: The GTX 1060 GP106M is on NVIDIA's end-of-life path. Driver
580.95.05 is the last feature driver. Security patches end October 2028.
Every hardware optimization matters more now.**

**Physical (user manual — NOT automatable):**
1. Clean fan ducts and heatsink fins (compressed air)
2. Replace thermal paste on CPU and GPU die (Thermal Grizzly Kryonaut Extreme)
3. Replace VRAM thermal pads (Thermal Grizzly Carbonaut 1.0mm/1.5mm assortment)
4. Expected result: 10-20°C reduction in peak GPU temp

**Software (Phase B manual):**

1. **Enable NVIDIA persistence mode:**
   Create `/etc/systemd/system/nvidia-persistence.service`:
   ```ini
   [Unit]
   Description=Enable NVIDIA persistence mode
   After=multi-user.target

   [Service]
   Type=oneshot
   ExecStart=/usr/bin/nvidia-smi -pm 1
   RemainAfterExit=yes

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable Coolbits for fan control + clock offsets:**
   Create `/etc/X11/xorg.conf.d/20-nvidia-coolbits.conf`:
   ```
   Section "Device"
       Identifier "NVIDIA Card"
       Driver "nvidia"
       Option "Coolbits" "28"
       Option "RegistryDwords" "PowerMizerEnable=0x1; PerfLevelSrc=0x2222; PowerMizerLevel=0x3; PowerMizerDefault=0x3"
   EndSection
   ```
   Coolbits=28 unlocks: fan control (4) + clock offsets (8) + voltage display (16).
   RegistryDwords forces maximum performance mode on AC power (fixes PowerMizer
   stuck in P2/P3 during gaming).

3. **Apply conservative GPU clock offset (-75MHz):**
   After repasting confirms thermal stability, apply incrementally:
   ```bash
   nvidia-settings -a '[gpu:0]/GPUGraphicsClockOffset[3]=-75'
   ```
   Start at -50, test stability, increment by -25. -75 to -100 is typical
   sweet spot for GP106M. Reduces temps 5-8°C.

4. **Install GreenWithEnvy for fan curve management:**
   ```bash
   flatpak install flathub com.leinardi.gwe
   ```
   Configure fan curve: 30% idle, 45% at 50°C, 60% at 60°C, 80% at 70°C,
   100% at 78°C.

**NEVER DO:**
- Never set fan to 100% permanently (7-year-old bearings will fail)
- Never apply liquid metal (exposed copper contacts = dead GPU)
- Never upgrade to NVIDIA driver 590+ (Pascal dropped, black screen)
- Never use `nvidia-smi -pl` (mobile GPU, will fail silently)

---

### 7C.2 — GPU Health MCP Tool (DAY 2-3)

**New MCP tool: `system.gpu_perf`**

Add to `ai/mcp_bridge/tools.py` — queries nvidia-smi for:
- Temperature, pstate, clock speeds, power draw
- VRAM usage (used/free/total)
- Throttle reasons (SW_THERMAL, HW_THERMAL, SW_POWER_CAP, etc.)
- Temperature headroom (83°C throttle threshold - current temp)
- Fan speed

**New MCP tool: `system.gpu_health`**

Richer diagnostic version with throttle reason interpretation:
```python
GPU_THROTTLE_BITS = {
    0x02: "SW_POWER_CAP",
    0x08: "HW_SLOWDOWN",
    0x20: "HW_THERMAL",
    0x40: "HW_POWER_BRAKE",
    0x80: "SYNC_BOOST",
    0x100: "SW_THERMAL",
}
```

Log throttle events to `health_records` LanceDB table for trend analysis.
Fire `notify-send` warning when headroom drops below 8°C.

**CC Prompt:** New tool implementation + allowlist update + tests.

---

### 7C.3 — Documentation Refresh (DAY 4-5)

Update all project documentation to reflect Phase 7 changes:

1. **USER-GUIDE.md** — Add OpenCode section, cloud embeddings, GPU monitoring
2. **AGENT.md** — Update tool count (43+), add OpenCode agent instructions
3. **project-instructions-updated.md** — "Active task first" policy, OpenCode
   constraints, Jina v3 embedding config
4. **verified-deps.md** — Add Jina API, remove Ollama as primary
5. **newelle-integration.md** — Update tool inventory, caching details
6. **CHANGELOG.md** — Phase 7 entry with all changes

**CC Prompt:** Documentation-only prompt with explicit scope boundaries.

---

## Decision Log

### Gemini Embedding 001 over Jina v3 / Voyage AI
Gemini wins on every axis: you already have the API key working in LiteLLM,
it scores highest on MTEB multilingual (68.32), the free tier is 10M TPM
(100x Jina's 100K TPM), it supports 768-dim via Matryoshka (exact LanceDB
match), and it eliminates a dependency rather than adding one. Jina would
require a new key, new rate limit config, and a new vendor relationship.
Voyage AI requires adding a payment method. Gemini requires nothing new.

### OpenCode over Claude Code / Codex CLI / Gemini CLI
OpenCode is vendor-neutral, supports MCP servers, points at our existing
proxy, and has a healthy plugin ecosystem. Claude Code locks you to Anthropic.
Codex CLI locks you to OpenAI. Gemini CLI locks you to Google.

### earlyoom + systemd-oomd (hybrid) over either alone
systemd-oomd handles cgroup-aware pressure kills (intelligent). earlyoom
handles raw memory floor emergency kills (reliable). Running both covers
both failure modes without conflict.

### Cloud embeddings over local Ollama
300MB VRAM permanently freed. Better retrieval quality (MTEB 0.766 vs nomic's
lower scores). No GPU keep_alive complexity. No Ollama dependency for core
RAG pipeline. Ollama kept as emergency local fallback only.

### streaming:false for OpenCode proxy
OpenCode expects the Responses API event stream format, not legacy Chat
Completions streaming. Our LiteLLM proxy speaks Chat Completions. Setting
streaming:false avoids the format mismatch entirely and preserves full
multi-turn conversation history.

---

## CC Prompt Sequence (Execution Order)

| # | Prompt | Phase | Scope |
|---|--------|-------|-------|
| 1 | Create systemd unit files for earlyoom, oomd config, btrfs-readahead, sysctl, KDE env | 7A.1 | `systemd/`, `configs/` |
| 2 | Update ai/config.py for new SSD mount path | 7A.2 | `ai/config.py` only |
| 3 | Rewrite ai/rag/embedder.py for Jina v3 primary + Cohere fallback + Ollama emergency | 7A.3 | `ai/rag/embedder.py`, `ai/config.py` |
| 4 | Add Jina rate limits + key manager update | 7A.3 | `configs/`, `ai/key_manager.py` |
| 5 | Create re-embedding migration script | 7A.3 | `scripts/migrate-embeddings.sh` |
| 6 | Update all "gaming first" docs to "active task first" | 7A.4 | `docs/` only |
| 7 | Fix llm_proxy.py non-streaming conversation history | 7B.1 | `ai/llm_proxy.py`, `tests/` |
| 8 | Create opencode.json + MCP shim + local plugins | 7B.2-3 | `.opencode/`, `opencode.json` |
| 9 | Add LiteLLM disk cache to router.py | 7B.4 | `ai/router.py` |
| 10 | RuFlo config + docs | 7B.5 | `configs/`, `docs/` |
| 11 | GPU health MCP tools | 7C.2 | `ai/mcp_bridge/tools.py`, `configs/` |
| 12 | Full documentation refresh | 7C.3 | `docs/` |

**Manual steps (Phase B, between CC prompts):**
- After prompt 1: Deploy unit files, enable earlyoom, reboot
- After prompt 2: Mount SSD, update symlinks
- After prompt 3-5: Get Jina API key, add to keys.env, re-encrypt, run migration
- After prompt 8: Install OpenCode (`npm i -g @opencode-ai/opencode` or Homebrew)
- After prompt 11: Deploy allowlist, restart MCP bridge

---

## Resource Budget (Post-Phase 7)

| Component | RAM | VRAM | When Active |
|-----------|-----|------|-------------|
| LLM Proxy | ~20MB (capped 150MB) | 0 | Always |
| MCP Bridge | ~60MB (capped 150MB) | 0 | Always |
| LanceDB | ~10MB (mmap) | 0 | On query only |
| Ollama | 0 (not loaded) | 0 | Emergency embed only |
| Jina v3 API | ~5MB (httpx client) | 0 | During embed batches |
| PySide6 tray | ~80MB | 0 | Always |
| OpenCode | ~100MB | 0 | On-demand CLI |
| **Total AI overhead** | **~275MB** (was ~400MB) | **0** (was ~300MB) | **Services + burst** |

**Net savings: ~125MB RAM, ~300MB VRAM freed permanently.**

---

## Metrics for Success

1. **Zero system freezes** over 2 weeks of mixed gaming/coding/AI use
2. **300MB VRAM freed** — nvidia-smi shows 0 AI VRAM use when not gaming
3. **OpenCode completes a refactor loop** in < 5 minutes (describe → tests pass)
4. **LLM disk cache hit rate** > 30% after 1 week of use
5. **GPU temps** stay below 80°C during sustained gaming (post-repaste)
6. **External SSD** mounts reliably after 5+ reboots
7. **RAG query quality** maintained or improved (spot-check 10 queries)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Jina free tier rate limit hit | Embed failures | Cohere fallback + Ollama emergency |
| OpenCode plugins break on update | Lost coding session | Pin versions, handoff plugin for recovery |
| earlyoom kills something important | Data loss | --avoid list protects desktop + critical processes |
| GPU repaste damages hardware | Dead GPU | Use paste not liquid metal, watch teardown videos first |
| btrfs readahead fix causes perf regression | Slower reads | Monitor with `iostat`, revert if needed (just delete the service) |
| LiteLLM disk cache fills SSD | Storage pressure | Cache on external SSD, weekly purge via timer |
