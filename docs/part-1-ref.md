> **STATUS (2026-03-17):** This reference predates SP1-SP3 completion. The AI layer
> (`ai/router.py`, `ai/threat_intel/`, `ai/rag/`, `ai/code_quality/`, `ai/gaming/`)
> is now fully implemented, not scaffolding. The tray is now PySide6/Qt6
> (`tray/security_tray_qt.py`, `tray/dashboard_window.py`), not GTK3/AppIndicator3.
> S4 Voice Agent (Jarvis) design is complete. See CLAUDE.md for current state.

# Bazzite Gaming Laptop — Complete Engineering Reference
## Unified Project Documentation for AI, Software Engineers, and UI Designers

**System**: Acer Predator G3-571 | Bazzite 43 (Fedora Atomic / KDE6 / Wayland)
**Hardware**: Intel i7-7700HQ, 16GB RAM, NVIDIA GTX 1060 6GB + Intel HD 630, 256GB LUKS/btrfs + 1.8TB ext4 external
**Repo**: `github.com:violentwave/bazzite-laptop.git` (private, SSH auth)
**User**: lch
**Last Updated**: 2026-03-17
**Document Scope**: Covers BOTH the base security/gaming system AND the AI enhancement layer

---

## Table of Contents

1. [Project Overview and Architecture](#1-project-overview-and-architecture)
2. [System and Hardware Specifications](#2-system-and-hardware-specifications)
3. [Base Security System — Completed](#3-base-security-system--completed)
4. [AI Enhancement Layer — Phase 0 (Completed)](#4-ai-enhancement-layer--phase-0-completed)
5. [AI Enhancement Layer — Phase 1 (Planned)](#5-ai-enhancement-layer--phase-1-planned)
6. [AI Enhancement Layer — Phases 2–6 (Planned)](#6-ai-enhancement-layer--phases-26-planned)
7. [API Key Inventory and Integration Map](#7-api-key-inventory-and-integration-map)
8. [Python Dependencies and Toolchain](#8-python-dependencies-and-toolchain)
9. [LiteLLM Routing Configuration](#9-litellm-routing-configuration)
10. [Secrets Management Architecture](#10-secrets-management-architecture)
11. [File Manifest and Repo Layout](#11-file-manifest-and-repo-layout)
12. [UI Components and Design System](#12-ui-components-and-design-system)
13. [Systemd Units and Scheduling](#13-systemd-units-and-scheduling)
14. [Testing Infrastructure](#14-testing-infrastructure)
15. [Developer Workflow and Tooling](#15-developer-workflow-and-tooling)
16. [Placeholders, Stubs, and Incomplete Work](#16-placeholders-stubs-and-incomplete-work)
17. [Rejected Approaches and Do-Not-Use List](#17-rejected-approaches-and-do-not-use-list)
18. [Critical Rules — Never Violate](#18-critical-rules--never-violate)
19. [Known Issues and Quirks](#19-known-issues-and-quirks)
20. [Resource Budget and Performance Constraints](#20-resource-budget-and-performance-constraints)

---

## 1. Project Overview and Architecture

This project is a security-hardened, AI-enhanced gaming laptop running Bazzite 43 (an immutable Fedora Atomic distribution). It consists of two logical subsystems that share a single git repository.

**Subsystem A — Base Security/Gaming System** (complete, production): ClamAV antivirus with daemon mode, quarantine pipeline, HTML email alerts, system health monitoring (SMART, GPU, CPU, ZRAM), 9-state system tray app, USBGuard, firewalld (DROP zone), DNS-over-TLS, KDE Security menu, and full gaming optimization (Steam, GameMode, MangoHud, GE-Proton).

**Subsystem B — AI Enhancement Layer** (Phase 0 scaffolding complete, Phase 1+ planned): Cloud-first AI routing via LiteLLM, threat intelligence enrichment via VirusTotal/OTX/MalwareBazaar, RAG pipeline using LanceDB + Ollama embeddings, code quality automation, and gaming telemetry analysis. Designed as a "Cloud Brain + Local Memory" architecture where all LLM inference is offloaded to free-tier cloud APIs and only embeddings run locally.

Both subsystems live under `~/projects/bazzite-laptop/`. The AI layer is scoped entirely to the `ai/` subdirectory.

### High-Level Data Flow

```
User action or systemd timer
  → Shell wrapper (scripts/*.sh)
    → Activates .venv (Python 3.12)
      → Python module (ai/*.py)
        → rate_limiter.py checks provider limits
          → router.py sends to LiteLLM
            → Best available cloud provider responds
        → LanceDB for vector search (if RAG query)
        → Ollama for embeddings (if embedding task)
      → Results flow back to existing system
        → clamav-alert.sh (enriched threat intel in emails)
        → ~/security/.status (tray app picks up changes)
        → quarantine-hashes-enriched.jsonl (separate enrichment file)
```

### Two-Project Context Management

Development context is split across two Claude.ai projects to manage token budgets. Engineers should be aware of which project context they need when working on a given component.

The "Bazzite Laptop" Claude.ai project covers scripts, systemd, tray app, ClamAV, USBGuard, firewalld, KDE integration, MangoHud, and all base system components. The "Bazzite AI Layer" Claude.ai project covers the `ai/` directory, LiteLLM routing, LanceDB, Ollama, API integrations, threat intelligence, RAG, and code quality pipelines.

---

## 2. System and Hardware Specifications

### Hardware

| Component | Specification |
|-----------|---------------|
| Machine | Acer Predator G3-571 |
| CPU | Intel i7-7700HQ (4 cores / 8 threads) |
| RAM | 16 GB |
| Discrete GPU | NVIDIA GTX 1060 Mobile, 6 GB VRAM |
| Integrated GPU | Intel HD 630 |
| GPU Mode | Hybrid via supergfxctl (no Dedicated/MUX switch) |
| Internal SSD | 256 GB SK hynix SATA M.2 — LUKS encrypted, btrfs |
| External SSD | 1.8 TB SanDisk Extreme — ext4, Steam library |
| Displays | Laptop 1920×1080 (eDP on Intel iGPU) + Vizio TV via HDMI (NVIDIA GPU) |

### Software Stack

| Component | Version/Detail |
|-----------|----------------|
| OS | Bazzite 43 (Fedora Atomic, KDE 6, Wayland) |
| Kernel | 6.17.7 |
| NVIDIA Driver | 580.95.05 |
| CUDA | 13.0 |
| Vulkan | 1.4.341 |
| SELinux | Enforcing |
| ZRAM Swap | 7.7 GB zstd, vm.swappiness=180 |
| Python | 3.12.13 (in .venv) |
| Node.js | Available via Homebrew |

### Layered Packages (rpm-ostree — 6 total)

clamav, clamav-freshclam, clamd, gamemode, msmtp, usbguard.

### Flatpak Applications

Brave Browser, Discord, Protontricks, Flatseal, DistroShelf, ProtonPlus, Warehouse, Mission Center, Filelight, Gwenview, Haruna, KCalc, Okular.

---

## 3. Base Security System — Completed

This entire subsystem is production-deployed and tested. All scripts are ShellCheck-clean. All systemd services include security hardening (NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only, PrivateTmp, ReadWritePaths whitelist). CodeRabbit review passed. Security audit remediation completed 2026-03-15.

### 3.1 ClamAV Antivirus

**Architecture**: On-demand daemon mode. Start clamd@scan, scan with clamdscan, stop clamd@scan. This reclaims ~1.1 GB RAM between scans and reduced scan time from 75 minutes (standalone clamscan) to ~20 minutes (~76,000 files).

**Key details**: clamdscan runs with `--fdpass --multiscan` for parallel scanning across 8 threads. Socket at `/run/clamd.scan/clamd.sock`. Server-side exclusions via ExcludePath in `/etc/clamd.d/scan.conf` (clamdscan ignores --exclude-dir). Signal handler traps INT/TERM to stop clamd and reset tray state on interrupt. SELinux boolean `antivirus_can_scan_system = on`.

**Scan schedules**: Quick daily at noon (`/home/lch` + `/tmp`), deep weekly Friday 11PM (`/home/lch` + `/tmp` + `/var`), test scan on demand (EICAR pipeline validation in 30–60s).

**Key files**: `/usr/local/bin/clamav-scan.sh` (main scanner), `/usr/local/bin/clamav-alert.sh` (email alerts), `/etc/clamd.d/scan.conf` (daemon config), `/var/log/clamav-scans/` (logs, 60-day rotation).

### 3.2 Quarantine System

Location: `~/security/quarantine/` with root:lch 750 permissions. Every quarantined file gets `chmod 000` + `chattr +i` (immutable). SHA256 hashes logged to `~/security/quarantine-hashes.log` with VirusTotal links. Release manager at `/usr/local/bin/quarantine-release.sh` with path traversal prevention, `--list`, `--interactive`, and direct release modes.

### 3.3 Email Alert System

Transport: msmtp + Gmail app password. Config at `/home/lch/.msmtprc` (absolute path required — scripts run as root). Three HTML email templates: clean scan (green banner), threats detected (red banner with detail table), error (amber banner). Health summary appended to every scan email.

### 3.4 System Tray Security Monitor

`~/security/bazzite-security-tray.py` — Python + GObject + AppIndicator3.

**9-state icon machine**: healthy_idle (green/circle), scan_running (teal/ring, blinking), scan_complete (blue/checkmark, blink 30s), warning (yellow/triangle), scan_failed (red/X), scan_aborted (red/X, blinking), threats_found (red/X, blinking), health_warning (green+amber EKG pulse), unknown (yellow/triangle).

**7 SVG icons** at `~/security/icons/hicolor/scalable/status/` with freedesktop `index.theme`. ViewBox 48×48, shape-differentiated badges for colorblind accessibility. Interior glyphs visible at 22px panel size.

**Resilience**: SIGHUP ignored (survives terminal closure). PR_SET_NAME renames process to prevent `pkill clamscan` from killing the tray. AppIndicator3 icon cache-bust via `set_icon_full("")` before new icon. Launcher uses `setsid` for process detachment.

**Status file**: `~/security/.status` (JSON), polled every 3 seconds. All writers use read-modify-write + atomic rename pattern. ClamAV owns scan keys, health owns health keys — scripts never overwrite the whole file.

**Menu items**: Quick/deep/test scan triggers, health snapshot trigger, health submenu (status + issue count from JSON), test suite launcher, quarantine view/release, log viewers, quit.

### 3.5 System Health Monitoring

`/usr/local/bin/system-health-snapshot.sh` — daily at 8 AM via systemd timer with persistent catch-up.

**Monitors**: SMART health for both drives (sda SK hynix SATA, sdb WD SN580E NVMe), GPU temperature/power/VRAM/perf state/clocks/XID errors, CPU package and per-core temperatures, filesystem and inode usage, ZRAM compression ratio and utilization, vm.swappiness verification, service status (firewalld, ClamAV, supergfxctl, thermald, DNS, USBGuard, TRIM, SELinux).

**Delta tracking**: Stores previous SMART values in `/var/log/system-health/health-deltas.dat` and flags growing error counts between snapshots — catches degradation trends.

**Modes**: `--email`, `--quiet`, `--append` (for scan emails), `--selftest` (SMART extended test with sleep inhibit).

**Integration points**: Writes `health_status` and `health_issues` to `.status` JSON for tray. Appends compact summary to every ClamAV scan email. KDE menu entries for snapshot and log viewing.

### 3.6 Network and OS Security

**Firewall**: firewalld default zone DROP. All incoming blocked except dhcpv6-client. `log-denied=all`. Public WiFi toggle script at `/usr/local/bin/public-wifi-mode` (switches between DROP and HOME zones).

**DNS**: DNS-over-TLS via systemd-resolved. Primary 1.1.1.1 (Cloudflare), secondary 9.9.9.9 (Quad9).

**LUKS**: Partition `/dev/sda3`, Argon2id KDF (verified). Header backed up to `~/security/luks-backup/` and flash drive.

**USBGuard**: Active, policy-mode block, 12 devices whitelisted. Setup script with two-round interactive process.

**SSH**: Completely disabled.

**Browser**: Brave with Flatseal hardening — X11 disabled, smart cards disabled, CUPS disabled, Bluetooth disabled, Kerberos removed. Wayland-native.

### 3.7 Gaming Stack

Steam with Proton Experimental, GE-Proton via ProtonPlus, GameMode (rpm-ostree layered), MangoHud (pre-installed, F12 toggle, F11 CSV logging). Standard launch option: `gamemoderun mangohud %command%`. Marvel Rivals exception: `SteamDeck=1 gamemoderun mangohud %command%`.

Performance tuning: ZRAM 7.7GB zstd at swappiness 180, NVIDIA shader cache 4GB limit, `mq-deadline` I/O scheduler for external SSD, TCP Fast Open + no slow start after idle.

27 games tested. Notable broken: GTA V Online (BattlEye), skate. (EA anti-cheat).

### 3.8 Backup and Restore

Flash drive: SanDisk 128GB with Bazzite installer (bootable) + BazziteBackup partition. `backup.sh` creates full snapshot. `restore.sh` is interactive with step-by-step confirmations. Five documented restore scenarios: Claude Code config mess, broken but bootable, fully compromised, quick undo, LUKS header corruption.

### 3.9 Deployment

`sudo ./scripts/deploy.sh [--dry-run]` — syncs scripts to `/usr/local/bin/`, systemd units to `/etc/systemd/system/`, configs to `/etc/`, desktop files to `~/.local/share/applications/`, tray app and icons to `~/security/`.

### 3.10 Security Audit Remediation (Completed 2026-03-15)

Hardcoded `/dev/sdX` replaced with UUID/label lookups across backup.sh, system-health-snapshot.sh, and luks-upgrade.sh. Predictable `.tmp` files replaced with `mktemp`. LUKS backup permissions hardened. USBGuard policy output validation added. `audit_log()` functions added with directory creation, writability checks, and stderr fallback.

**Intentionally skipped** (evaluated as over-engineering): TOCTOU on lock files, socket-based IPC for tray, formal JSON schema validation.

---

## 4. AI Enhancement Layer — Phase 0 (Completed)

Phase 0 was completed across four Claude Code prompts on 2026-03-15, with commits `4ec3059`, `2f2b0cf`, and `d7cacbf` on master.

### 4.1 What Was Built

**Environment setup**: uv 0.10.10 installed (Flatpak sandbox path at `~/.var/app/com.visualstudio.code/bin/uv`). Python 3.12.13 venv at `~/projects/bazzite-laptop/.venv/`. sops 3.12.1 via Homebrew.

**Directory scaffolding**: `ai/` directory with subdirectories `threat_intel/`, `rag/`, `code_quality/`, `gaming/` — all with `__init__.py` files. `tests/` directory with `__init__.py`. Config directory `~/.config/bazzite-ai/` with `keys.env` template (chmod 600).

**Core Python modules (functional, not stubs)**:

`ai/config.py` — 12 path constants, `load_keys()` function (loads from `~/.config/bazzite-ai/keys.env` via python-dotenv), `get_key()` function (returns individual key values), `setup_logging()` function (configures Python logging per-module).

`ai/router.py` — `route_query()` scaffold function, YAML config loading from `configs/litellm-config.yaml`. This is a functional scaffold — the routing logic calls LiteLLM but requires API keys to be populated before it will actually work.

`ai/rate_limiter.py` — `RateLimiter` class with `can_call()`, `record_call()`, and `wait_time()` methods. Uses atomic writes with `fcntl` file locking. State stored at `~/.config/bazzite-ai/rate-limits-state.json`. Reads limit definitions from `configs/ai-rate-limits.json`.

**Configuration files**:

`pyproject.toml` — Python 3.12 target, Ruff config (line length 100, E402/I001 per-file-ignores for tray app GTK pattern), Bandit config, pytest config.

`requirements.txt` — 72 Python dependencies (locked versions). See Section 8 for full list.

`configs/litellm-config.yaml` — LiteLLM provider routing with fallback chains for fast/reason/batch/embed model names. See Section 9 for details.

`configs/ai-rate-limits.json` — Per-provider rate limit definitions (RPM, RPD, TPD) for all 24 providers.

`configs/keys.env.enc` — sops-encrypted template of keys.env (committed to git). Encrypted with GPG key `6CD80C886A02BA612ECEBB915AD7F142735A180F`.

**Tests**: `tests/test_config.py` (13 tests for path constants, key loading, logging setup), `tests/test_rate_limiter.py` (17 tests for rate limiting logic, file locking, atomic writes). All 30 tests passing.

**Linting**: Ruff clean (including tray app fix — added `tray/**` per-file-ignores for E402/I001 GTK import pattern, S110 noqa, reformatted STATE_CONFIG). Bandit clean.

### 4.2 What Phase 0 Did NOT Build

The following are directory stubs only (empty `__init__.py`):

- `ai/threat_intel/` — no lookup.py, formatters.py, or enrich.py yet
- `ai/rag/` — no chunker.py, store.py, embedder.py, or query.py yet
- `ai/code_quality/` — no indexer.py or ai_fix.py yet
- `ai/gaming/` — no mangohud_analyzer.py or scopebuddy_config.py yet

No shell wrappers in `scripts/` for AI features yet (threat-lookup.sh, embed-logs.sh, ai-query.sh, code-quality.sh, mangohud-analyzer.sh are all planned but not created).

No systemd units for AI features yet (ai-embed-logs.service/timer planned for Phase 2).

The `keys.env` file is a template with empty values. API keys have been acquired but NOT yet populated into the file. Keys will be added after Claude Code's `.env` read access is permanently blocked.

### 4.3 Locked Architecture Decisions (Authoritative)

These decisions were finalized during Phase 0 and must not be changed without explicit team review. The source of truth is `~/projects/Setup/phase0-1-locked-decisions.md`.

- Python 3.12 (not 3.11 or 3.13)
- OTXv2 SDK dropped — use raw `requests` for OTX AlienVault API
- sentence-transformers dropped — Ollama handles all embeddings
- `runuser -u lch` for root→user AI execution context
- Cascading API strategy: VirusTotal → OTX → MalwareBazaar (not parallel)
- 30-second hard timeout for threat lookups
- Batch mode for hash lookups (not one-at-a-time)
- Separate `quarantine-hashes-enriched.jsonl` file (don't modify existing `quarantine-hashes.log`)
- Rate limiter state at `~/.config/bazzite-ai/rate-limits-state.json`
- nomic-embed-text-v2-moe (not v1.5) for embeddings
- LanceDB v0.29+ native embedding registry (auto-embed on add/search)
- Ollama via `brew install` (not Flatpak or podman)
- LiteLLM Router in-script (no proxy server)
- Section-based chunking (not semantic)
- 768-dimensional vectors
- Cohere Embed v3 as cloud embedding fallback
- `embed-state.json` for deduplication tracking

---

## 5. AI Enhancement Layer — Phase 1 (Planned)

**Goal**: Enrich ClamAV scan emails with real threat intelligence data. When ClamAV quarantines a file, automatically look up its SHA256 hash against VirusTotal, OTX AlienVault, and MalwareBazaar, then inject threat family name, detection ratio, and risk assessment into the HTML alert email.

**Status**: Not started. All Phase 1 code is planned but not yet written.

### 5.1 Planned Components

`ai/threat_intel/lookup.py` — Core threat lookup engine. `lookup_hash(sha256: str) -> ThreatReport`. Cascading strategy: VirusTotal first (GET /files/{hash} via vt-py SDK), OTX AlienVault second (GET /indicators/file/{hash} via raw requests), MalwareBazaar third (POST /api/v1/ via requests). All calls routed through `ai/rate_limiter.py`. Returns dataclass with threat_name, family, risk_level, detection_ratio, description. 30-second hard timeout. Graceful degradation when APIs are rate-limited.

`ai/threat_intel/formatters.py` — `format_html_section(report: ThreatReport) -> str`. Generates HTML table matching existing clamav-alert.sh email visual style (same color palette, same table structure). Includes detection ratio, threat family, risk assessment text, and VirusTotal deep link.

`ai/threat_intel/enrich.py` — Batch enrichment of quarantine hashes. Reads `~/security/quarantine-hashes.log`, looks up any hash not already enriched. Writes results to separate `quarantine-hashes-enriched.jsonl` (one JSON object per line). Rate-limit aware — will not burn all 500 daily VT lookups in one run.

`scripts/threat-lookup.sh` — Shell wrapper. Activates `.venv`, calls `python -m ai.threat_intel.lookup --hash $1`, outputs HTML to stdout. Exit codes: 0=enriched, 1=no results, 2=all APIs rate-limited.

**Modification to existing `clamav-alert.sh`**: After threat found and before email composition, call `threat-lookup.sh` with the quarantined file's hash. Capture HTML output. Inject new "Threat Intelligence" section into email template after the existing threat details table. Graceful fallback if threat-lookup.sh is unavailable or fails.

`tests/test_threat_intel.py` — Mock VT/OTX/MalwareBazaar responses, test rate limiter integration, test HTML formatter output, test cascading fallback when APIs fail.

### 5.2 API Integration Details for Phase 1

**VirusTotal** (primary): vt-py SDK. Endpoint: `GET /files/{sha256}`. Returns detection ratio (e.g., "43/72"), threat family name, first/last submission dates. Rate limit: 4 requests per minute, 500 per day. Key env var: `VT_API_KEY`.

**OTX AlienVault** (secondary): Raw HTTP via requests. Endpoint: `GET /api/v1/indicators/file/{sha256}/general`. Returns pulse count, threat names, tags. Rate limit: 10,000 requests per hour. Key env var: `OTX_API_KEY`. The OTXv2 Python SDK was evaluated and rejected — raw requests are simpler and avoid an unnecessary dependency.

**MalwareBazaar** (tertiary/fallback): Raw HTTP via requests. Endpoint: `POST https://mb-api.abuse.ch/api/v1/` with `query=get_info&hash={sha256}`. Returns malware family, tags, delivery method. No API key required. No documented rate limits but usage should be respectful.

**No-signup APIs available but not yet integrated**: URLhaus (malicious URLs), ThreatFox (IOCs), CIRCL Hashlookup (known-file identification from NSRL database), Shodan InternetDB (open ports/vulns for IPs), CISA KEV (actively exploited vulnerabilities).

---

## 6. AI Enhancement Layer — Phases 2–6 (Planned)

All phases below are planned but have zero code written. They are listed here for architectural context and future sprint planning.

### Phase 2 — RAG Security Intelligence

**Goal**: Semantic memory for security events, AI-powered alert analysis.

Planned components: `ai/rag/chunker.py` (section-based log chunking), `ai/rag/store.py` (LanceDB abstraction at `~/security/vector-db/`), `ai/rag/embedder.py` (Ollama nomic-embed-text-v2-moe, 768-dim vectors, with Cohere Embed v3 cloud fallback), `ai/rag/query.py` (embed question → search LanceDB → format context → route to LLM via LiteLLM).

Shell wrappers: `scripts/embed-logs.sh`, `scripts/ai-query.sh`.

Systemd units: `systemd/ai-embed-logs.service` + `.timer` (daily at 9 AM, after 8 AM health snapshot).

Integration: When system-health-snapshot.sh detects WARNING/CRITICAL, call ai-query.py to search LanceDB for similar past events, bundle context, route to LLM, inject AI analysis into health alert email. New tray menu item: "Ask AI about this alert."

### Phase 3 — Code Quality Pipeline

**Goal**: Automated multi-linter analysis with AI fix suggestions.

Planned components: `scripts/code-quality.sh` (orchestrates Ruff + Bandit + ShellCheck + Semgrep, outputs unified JSON), `ai/code_quality/indexer.py` (Tree-sitter AST parsing for Python + Bash, embed into LanceDB code-index table), `ai/code_quality/ai_fix.py` (takes linter JSON, retrieves relevant code from LanceDB, sends to LLM for fix suggestions). Git pre-push hook. Expanded GitHub Actions CI.

### Phase 4 — Gaming Performance Analysis

**Goal**: AI analysis of MangoHud CSV telemetry + ScopeBuddy config generation.

Planned components: `ai/gaming/mangohud_analyzer.py` (parse /tmp/MangoHud/ CSVs, calculate avg FPS, 1%/0.1% lows, identify bottlenecks, route to LLM for analysis), `ai/gaming/scopebuddy_config.py` (generate per-game JSON configs for `~/.config/scopebuddy/`, hardcoded exclusion of PRIME offload variables).

### Phase 5 — Downloads Folder Watcher

**Goal**: inotify-based auto-scan of `~/Downloads` for new files, with threat intel lookup for anything suspicious.

### Phase 6 — Advanced Integrations (Future)

Evaluate and selectively implement: Cohere Rerank in RAG pipeline, AbuseIPDB in firewalld log analysis, NVD/OSV vulnerability scanning for rpm-ostree packages, Netdata ML anomaly detection (evaluate RAM impact), network WiFi analyzer.

---

## 7. API Key Inventory and Integration Map

### 7.1 Status Summary

All 17 keys acquired as of 2026-03-15. Keys are NOT yet populated in `keys.env` — file still contains empty template values. Seven additional APIs require no signup.

### 7.2 LLM Providers (9 Keys + 3 Paid Subscriptions)

| # | Provider | Key Env Var | Key Prefix | Free Limits | Integration Phase | Current Status |
|---|----------|-------------|------------|-------------|-------------------|----------------|
| 1 | Groq | `GROQ_API_KEY` | `gsk_` | ~30 RPM, 14,400 req/day | Phase 2 (interactive) | Key acquired, not yet populated |
| 2 | Mistral | `MISTRAL_API_KEY` | varies | 1B tokens/mo, 2 RPM | Phase 2 (batch + embed fallback) | Key acquired, not yet populated |
| 3 | OpenRouter | `OPENROUTER_API_KEY` | `sk-or-` | 20 RPM, 50 req/day | Phase 2 (fallback) | Key acquired, not yet populated |
| 4 | Cerebras | `CEREBRAS_API_KEY` | varies | ~1M tokens/day, 8K ctx | Phase 2 (fast inference) | Key acquired, not yet populated |
| 5 | Cohere | `COHERE_API_KEY` | varies | 1,000 calls/mo | Phase 2 (embed + rerank) | Key acquired, not yet populated |
| 6 | Hugging Face | `HF_TOKEN` | `hf_` | Rate-limited inference | Phase 2 (embed fallback) | Key acquired, not yet populated |
| 7 | GitHub Models | `GITHUB_TOKEN` | `ghp_` | 10-15 RPM | Phase 2 (reasoning fallback) | Key acquired, not yet populated |
| 8 | NVIDIA NIM | `NVIDIA_API_KEY` | `nvapi-` | 40 RPM | Phase 2 (NVIDIA models) | Key acquired, not yet populated |
| 9 | Cloudflare Workers AI | `CLOUDFLARE_API_TOKEN` | varies | 10K neurons/day | Future (edge tasks) | Key acquired, not yet populated |
| — | Google Gemini Pro | `GEMINI_API_KEY` | `AI` | Paid subscription | Phase 2 (heavy context) | Paid, key acquired |
| — | x.ai / Grok | `XAI_API_KEY` | varies | $30/mo subscription | Phase 2 (code gen) | Paid, key acquired |
| — | Claude Max | `ANTHROPIC_API_KEY` | varies | Paid subscription | Phase 2 (reasoning) | Paid, key acquired |

### 7.3 Threat Intelligence APIs (6 Keys + 7 No-Signup)

| # | Provider | Key Env Var | Free Limits | Integration Phase | Current Status |
|---|----------|-------------|-------------|-------------------|----------------|
| 10 | VirusTotal | `VT_API_KEY` | 4 RPM, 500/day | Phase 1 (primary hash lookup) | Key acquired, not yet populated |
| 11 | AbuseIPDB | `ABUSEIPDB_KEY` | 1,000 checks/day | Phase 6 (IP reputation) | Key acquired, not yet populated |
| 12 | OTX AlienVault | `OTX_API_KEY` | 10,000 req/hr | Phase 1 (secondary hash lookup) | Key acquired, not yet populated |
| 13 | NVD (NIST) | `NVD_API_KEY` | 50 req/30s | Phase 6 (CVE lookup) | Key acquired, not yet populated |
| 14 | GreyNoise Community | `GREYNOISE_KEY` | 50 lookups/week | Phase 6 (IP tiebreaker) | Key acquired, not yet populated |
| 15 | Hybrid Analysis | `HYBRID_ANALYSIS_KEY` | 5 RPM, 200/hr | Future (sandbox analysis) | Key acquired, not yet populated |

**No-signup APIs** (no key needed, generous or no documented limits):

| Provider | Endpoint | Use Case | Phase |
|----------|----------|----------|-------|
| MalwareBazaar | `bazaar.abuse.ch` | Malware hash lookup | Phase 1 (tertiary fallback) |
| URLhaus | `urlhaus.abuse.ch` | Malicious URL database | Future |
| ThreatFox | `threatfox.abuse.ch` | IOC sharing platform | Future |
| CIRCL Hashlookup | `hashlookup.circl.lu` | NSRL known-file identification | Future |
| Shodan InternetDB | `internetdb.shodan.io` | Open ports + vulns for IPs | Future |
| OSV (Google) | `osv.dev` | Open-source package vulns | Phase 6 |
| CISA KEV | `cisa.gov/known-exploited-vulnerabilities-catalog` | Actively exploited CVEs | Phase 6 |

### 7.4 Code Quality Platforms (2 Keys)

| # | Provider | Auth Method | Free Limits | Current Status |
|---|----------|-------------|-------------|----------------|
| 16 | Semgrep | GitHub SSO | 10 private repos free | Account created |
| 17 | DeepSource | GitHub SSO | Free for personal repos | Account created |
| — | CodeRabbit | GitHub integration | Unlimited private repos | Active, reviewing PRs |

### 7.5 Dropped / Unavailable APIs

| Provider | Reason |
|----------|--------|
| PhishTank | Personal signups disabled March 2026 |
| Together AI | Requires $5 minimum purchase |
| GreyNoise Personal | Personal tier no longer free (Community API at 50/week still works) |

---

## 8. Python Dependencies and Toolchain

### 8.1 Environment

Python 3.12.13 managed by uv 0.10.10. Virtual environment at `~/projects/bazzite-laptop/.venv/`. Never install packages globally or with `--break-system-packages`.

**Known quirk**: uv is installed at the Flatpak sandbox path `~/.var/app/com.visualstudio.code/bin/uv` (for Claude Code in VS Code). A separate install at `~/.local/bin/uv` is needed for regular terminal use.

### 8.2 Core Dependencies (72 packages in requirements.txt)

Key packages and their roles:

| Package | Role | Phase |
|---------|------|-------|
| litellm | Universal LLM API router | Phase 0 (installed), Phase 2 (active use) |
| lancedb | Disk-based vector database | Phase 0 (installed), Phase 2 (active use) |
| vt-py | VirusTotal Python SDK | Phase 1 |
| requests | HTTP client for OTX, MalwareBazaar, other APIs | Phase 1 |
| python-dotenv | Load keys.env securely | Phase 0 (active) |
| pyyaml | LiteLLM config loading | Phase 0 (active) |
| ollama | Ollama Python client | Phase 2 |
| tree-sitter, tree-sitter-python, tree-sitter-bash | AST parsing for code-aware RAG | Phase 3 |
| ruff | Python linter + formatter | Phase 0 (active in tests/CI) |
| bandit | Python security scanner | Phase 0 (active in tests/CI) |
| pytest | Test framework | Phase 0 (active) |
| inotify-simple | File system event watching | Phase 5 |
| semgrep | Cross-language SAST | Phase 3 |

### 8.3 Known importlib.metadata Issues

Three packages use `importlib.metadata.version()` instead of `__version__`: litellm, rich, python-dotenv. Direct `__version__` attribute access will raise AttributeError for these packages.

### 8.4 Known Sandbox Issues

LanceDB segfaults inside the VS Code Flatpak sandbox. It works correctly in a regular terminal. If LanceDB-related tests fail inside VS Code, run them from a regular terminal instead.

---

## 9. LiteLLM Routing Configuration

Located at `configs/litellm-config.yaml`. LiteLLM Router is used in-script (not as a proxy server). The routing strategy is `simple-shuffle` with 2 retries, 30s timeout, and 1 allowed failure before fallback.

### Model Name → Provider Chain

| Model Name | Priority | Provider | Model String | Use Case |
|------------|----------|----------|-------------|----------|
| `fast` | 1st | Groq | `groq/llama-3.3-70b-versatile` | Interactive speed (300+ tok/s) |
| `fast` | 2nd | Cerebras | `cerebras/llama-4-scout-17b-16e-instruct` | Ultra-fast fallback |
| `reason` | 1st | Anthropic (Claude) | `anthropic/claude-sonnet-4-20250514` | Deep analysis, reasoning |
| `reason` | 2nd | Google | `gemini/gemini-2.5-flash` | 2M context fallback |
| `batch` | 1st | Mistral | `mistral/codestral-latest` | Volume processing |
| `batch` | 2nd | Google | `gemini/gemini-2.0-flash` | Volume fallback |
| `embed` | 1st | Ollama (local) | `ollama/nomic-embed-text` | Local embeddings (primary) |
| `embed` | 2nd | Mistral | `mistral/mistral-embed` | Cloud embedding fallback |

Scripts call `route_query(task_type="fast", prompt="...")` and LiteLLM automatically handles failover.

### Rate Limits Configuration

Located at `configs/ai-rate-limits.json`. Every provider has RPM (requests per minute), RPD (requests per day), and/or TPD (tokens per day) limits defined. The `ai/rate_limiter.py` module checks these before every API call and blocks if limits would be exceeded.

---

## 10. Secrets Management Architecture

### File Layout

```
~/.config/bazzite-ai/
├── keys.env              # Plaintext keys, chmod 600, NEVER in git
├── .sops.yaml            # sops encryption rules (local GPG key)
└── rate-limits-state.json # Rate limiter state (atomic writes, fcntl locking)

~/projects/bazzite-laptop/configs/
├── keys.env.enc          # sops-encrypted copy of keys.env (committed to git)
├── litellm-config.yaml   # LiteLLM routing (references os.environ/ for keys)
└── ai-rate-limits.json   # Per-provider rate limit definitions
```

### Encryption

GPG key fingerprint: `6CD80C886A02BA612ECEBB915AD7F142735A180F`. sops requires flags `--input-type dotenv --output-type dotenv` for .env files.

Encrypt: `sops -e --input-type dotenv --output-type dotenv ~/.config/bazzite-ai/keys.env > configs/keys.env.enc`

Decrypt: `sops -d --input-type dotenv --output-type dotenv configs/keys.env.enc`

### Runtime Key Loading

Python scripts load keys via `ai/config.py`:

```python
from ai.config import load_keys, get_key
load_keys()  # calls dotenv.load_dotenv(~/.config/bazzite-ai/keys.env)
vt_key = get_key("VT_API_KEY")  # returns os.environ.get("VT_API_KEY")
```

Claude Code CANNOT read `.env`, `.key`, or `.pem` files — this is enforced by sandbox deny rules. Keys are loaded at runtime by Python scripts only.

---

## 11. File Manifest and Repo Layout

### Repository Structure

```
~/projects/bazzite-laptop/
├── ai/                              # AI enhancement layer (Phase 0 complete)
│   ├── __init__.py                  # ✅ Exists
│   ├── config.py                    # ✅ Functional (paths, key loading, logging)
│   ├── router.py                    # ✅ Scaffold (LiteLLM wrapper, needs keys)
│   ├── rate_limiter.py              # ✅ Functional (atomic writes, fcntl locking)
│   ├── threat_intel/                # ⬜ Stub (empty __init__.py only)
│   │   └── __init__.py
│   ├── rag/                         # ⬜ Stub (empty __init__.py only)
│   │   └── __init__.py
│   ├── code_quality/                # ⬜ Stub (empty __init__.py only)
│   │   └── __init__.py
│   └── gaming/                      # ⬜ Stub (empty __init__.py only)
│       └── __init__.py
├── tests/                           # ✅ 30 tests passing
│   ├── __init__.py
│   ├── test_config.py               # ✅ 13 tests
│   └── test_rate_limiter.py         # ✅ 17 tests
├── configs/
│   ├── litellm-config.yaml          # ✅ Complete routing config
│   ├── ai-rate-limits.json          # ✅ Complete rate limit definitions
│   └── keys.env.enc                 # ✅ Encrypted template (values empty)
├── scripts/                         # Base system scripts (all ✅ deployed)
│   ├── clamav-scan.sh               # ✅ Production (quick/deep/test)
│   ├── clamav-alert.sh              # ✅ Production (HTML emails)
│   ├── clamav-healthcheck.sh        # ✅ Production (infra checks)
│   ├── quarantine-release.sh        # ✅ Production (file release)
│   ├── bazzite-security-test.sh     # ✅ Production (15-test suite)
│   ├── system-health-snapshot.sh    # ✅ Production (health monitoring)
│   ├── system-health-test.sh        # ✅ Production (16-test suite)
│   ├── integration-test.sh          # ✅ Production (26 checks)
│   ├── start-security-tray.sh       # ✅ Production (tray launcher)
│   ├── public-wifi-mode             # ✅ Production (firewall toggle)
│   ├── deploy.sh                    # ✅ Production (repo → system sync)
│   ├── backup.sh                    # ✅ Production (full snapshot)
│   ├── restore.sh                   # ✅ Production (interactive restore)
│   ├── usbguard-setup.sh            # ✅ Production (device whitelist)
│   └── luks-upgrade.sh              # ✅ Production (LUKS management)
│   # Planned but NOT created:
│   # threat-lookup.sh, embed-logs.sh, ai-query.sh,
│   # code-quality.sh, mangohud-analyzer.sh, setup-ai-env.sh
├── systemd/                         # Base system timers/services
│   ├── clamav-quick.timer + .service    # ✅ Daily noon
│   ├── clamav-deep.timer + .service     # ✅ Friday 11 PM
│   ├── clamav-healthcheck.timer + .service  # ✅ Wednesday 2 PM
│   └── system-health.timer + .service   # ✅ Daily 8 AM
│   # Planned: ai-embed-logs.timer + .service (Phase 2)
├── tray/
│   └── bazzite-security-tray.py     # ✅ Production (9-state icon machine)
├── desktop/                         # KDE .desktop files (12 entries)
├── docs/                            # All documentation
├── .vscode/                         # VS Code workspace settings
├── .github/workflows/main.yml       # ShellCheck + syntax CI
├── pyproject.toml                   # ✅ Ruff/Bandit/pytest config
├── requirements.txt                 # ✅ 72 locked dependencies
├── .python-version                  # ✅ Pins Python 3.12
├── CLAUDE.md                        # ✅ Claude Code project context
└── .gitignore                       # ✅ AI exclusions included
```

### Key Runtime Paths (Not in Repo)

| Path | Purpose | Managed By |
|------|---------|------------|
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys | User (chmod 600) |
| `~/.config/bazzite-ai/rate-limits-state.json` | Rate limiter state | ai/rate_limiter.py |
| `~/security/.status` | Shared JSON (ClamAV + health + AI) | Multiple writers, atomic |
| `~/security/quarantine/` | Quarantined files | clamav-scan.sh |
| `~/security/quarantine-hashes.log` | Hash log with VT links | clamav-scan.sh |
| `~/security/vector-db/` | LanceDB data (planned) | ai/rag/ (Phase 2) |
| `~/security/icons/hicolor/` | 7 SVG tray icons + index.theme | Deployed via deploy.sh |
| `/var/log/clamav-scans/` | Scan logs (60-day rotation) | clamav-scan.sh |
| `/var/log/system-health/` | Health logs (90-day rotation) | system-health-snapshot.sh |

---

## 12. UI Components and Design System

### 12.1 System Tray Icon Design

**7 SVG icons** at `~/security/icons/hicolor/scalable/status/`. ViewBox 48×48. Each icon is a shield shape with a unique interior badge glyph:

| Icon File | Color | Badge | Maps To States |
|-----------|-------|-------|---------------|
| security-healthy-idle | Green | Filled circle | healthy_idle |
| security-scan-running | Teal | Hollow ring | scan_running |
| security-scan-complete | Blue | Checkmark | scan_complete |
| security-warning | Yellow | Triangle | warning, unknown |
| security-scan-failed | Red | X mark | scan_failed, scan_aborted, threats_found |
| security-health-warning | Green + amber | EKG pulse wave | health_warning |
| security-blank | Neutral | None | Used for blink animation |

**Design principles**: Shape-differentiated badges for colorblind accessibility (never rely on color alone). Interior glyphs must be visible at 22px KDE panel size. Badge shapes are distinctive even when desaturated.

**KDE integration**: All `.desktop` files use absolute SVG paths (`/home/lch/security/icons/hicolor/scalable/status/...`). KDE does not resolve custom icon theme names from `~/.local/share/icons/hicolor/`. Freedesktop `index.theme` installed with Context=Status, MinSize=16, MaxSize=256.

### 12.2 KDE Security Menu

12 entries under a dedicated "Security" category in the KDE Start Menu. Menu definition at `~/.config/menus/applications-merged/security.menu`. All terminal-based entries use `bash -c '...; echo "Press Enter to close"; read'` wrapper (not `konsole --hold`).

Entries: Deep Scan, Quick Scan, Firewall, Firewall Status, KWalletManager, Scan Logs, Start Security Monitor, System Health Snapshot, Update Email Password, USB Devices, View Health Logs, View Quarantine.

### 12.3 HTML Email Templates

Three email templates in `clamav-alert.sh` (inline HTML, not external files):

**Clean scan**: Green banner header, white body with file counts and scan duration, health summary footer.

**Threats detected**: Red banner header, threat detail table (filename, signature name, action taken), health summary footer. Phase 1 will add a "Threat Intelligence" section after the existing threat table.

**Error**: Amber banner header, error detail text, health summary footer.

All emails are sent via msmtp through Gmail with app password. HTML rendering targets Gmail web client.

### 12.4 Terminal UI

`clamav-scan.sh` includes colored terminal output (ANSI escape codes) for scan progress, status updates, and results. MangoHud overlay configurable via `~/.config/MangoHud/MangoHud.conf` with F12 toggle.

---

## 13. Systemd Units and Scheduling

### Active Timers (Deployed)

| Timer | Schedule | Service | Purpose |
|-------|----------|---------|---------|
| `clamav-quick.timer` | Daily at noon | `clamav-quick.service` | Quick ClamAV scan |
| `clamav-deep.timer` | Friday 11 PM | `clamav-deep.service` | Weekly deep scan |
| `clamav-healthcheck.timer` | Wednesday 2 PM | `clamav-healthcheck.service` | Security infra check |
| `system-health.timer` | Daily 8 AM | `system-health.service` | Hardware health monitoring |
| `fstrim.timer` | Weekly | Built-in | SSD TRIM maintenance |
| `logrotate.timer` | Daily | Built-in | Log rotation |

### Planned Timers (Not Yet Created)

| Timer | Schedule | Purpose | Phase |
|-------|----------|---------|-------|
| `ai-embed-logs.timer` | Daily 9 AM | Embed security logs into LanceDB | Phase 2 |

### Service Hardening (Applied to All 4 Custom Services)

All services include: `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=read-only`, `PrivateTmp=yes`, `ReadWritePaths=` with explicit write whitelist. Uses broad `/home/lch/security` path because atomic writes create `.status.tmp.$PID` files with unpredictable names.

---

## 14. Testing Infrastructure

### 14.1 Python Unit Tests (30 passing)

`tests/test_config.py` (13 tests): Path constant verification, key loading from dotenv, logging setup, missing key handling, path existence validation.

`tests/test_rate_limiter.py` (17 tests): Rate limit enforcement, `can_call()` / `record_call()` / `wait_time()` methods, atomic write verification, fcntl file locking, JSON state persistence, concurrent access safety.

Run with: `source .venv/bin/activate && python -m pytest tests/ -v`

### 14.2 Security Test Suite (15 tests)

`/usr/local/bin/bazzite-security-test.sh` — Five phases: prerequisites, infrastructure, scanning (EICAR), notifications, tray/menu. Creates EICAR test virus, validates full detection → quarantine → lockdown pipeline. Generates `~/security/test-report-*.log`. Accessible from tray menu.

### 14.3 Integration Test Suite (26 checks)

`/usr/local/bin/integration-test.sh` — Lock files, .desktop icon paths (absolute SVG verification), path traversal prevention, firewall zones, SELinux, USBGuard, ClamAV signatures, msmtp binary. Requires sudo.

### 14.4 Health Test Suite (16 tests)

`/usr/local/bin/system-health-test.sh` — Health monitoring installation, script execution, delta tracking, email capability, timer status, log creation.

### 14.5 Linting

Ruff (Python lint + format) and Bandit (Python security) are configured in `pyproject.toml` and run clean on the current codebase. ShellCheck runs in GitHub Actions CI. Semgrep planned for Phase 3.

---

## 15. Developer Workflow and Tooling

### 15.1 Claude Code (VS Code)

Installed at `~/.local/bin/claude` with bubblewrap sandbox always enabled. Settings at `~/.claude/settings.json`. Four active plugins: superpowers, code-review, feature-dev, frontend-design.

**Two-phase workflow**: Phase A (Claude Code does) — create/edit files, run tests, run linters, manage venv, install user-space tools, manage git. Phase B (user does manually) — sudo commands, deploy.sh, systemctl, integration tests.

**Deny list**: sudo, rm -rf, rpm-ostree, systemctl, reading .env/.key/.pem files.

**Allow list**: curl, wget, brew install, uv, git, pytest, ruff, bandit, ollama, sops, gpg.

### 15.2 VS Code

Flatpak install. Extensions: ShellCheck, Bash IDE, YAML, GitLens, Error Lens, Todo Tree, indent-rainbow, Ruff, SVG preview tools.

### 15.3 Git Workflow

```bash
cd ~/projects/bazzite-laptop/
git add <files>
git commit -m "feat/fix/docs/refactor/test/chore: description"
git push origin master
```

CodeRabbit reviews all PRs automatically. GitHub Actions runs ShellCheck + syntax validation on push.

### 15.4 Prompt Generation Workflow

Claude Code prompts are generated using the `/cc-prompter` skill pattern in Claude.ai. Prompts are numbered (cc-prompt-01, 02, 03...), scoped tightly with explicit deliverables checklist and DO NOT sections. Each prompt starts with `/feature-dev` and ends with `/code-review`. Output files go to `~/projects/Setup/` for reference.

---

## 16. Placeholders, Stubs, and Incomplete Work

### 16.1 Empty Stubs (Directory + __init__.py Only)

| Directory | Planned Contents | Target Phase |
|-----------|-----------------|--------------|
| `ai/threat_intel/` | lookup.py, formatters.py, enrich.py | Phase 1 |
| `ai/rag/` | chunker.py, store.py, embedder.py, query.py | Phase 2 |
| `ai/code_quality/` | indexer.py, ai_fix.py | Phase 3 |
| `ai/gaming/` | mangohud_analyzer.py, scopebuddy_config.py | Phase 4 |

### 16.2 Functional But Requires Keys

`ai/router.py` — The LiteLLM routing scaffold is functional code, but because `keys.env` contains empty template values, all actual API calls will fail with authentication errors until keys are populated. The `route_query()` function, YAML loading, and fallback chain logic are all implemented.

### 16.3 Shell Wrappers Not Yet Created

| Script | Purpose | Phase |
|--------|---------|-------|
| `scripts/threat-lookup.sh` | Activates venv, calls threat_intel.lookup | Phase 1 |
| `scripts/embed-logs.sh` | Activates venv, runs embedder on latest logs | Phase 2 |
| `scripts/ai-query.sh` | Activates venv, runs RAG query engine | Phase 2 |
| `scripts/code-quality.sh` | Orchestrates Ruff + Bandit + ShellCheck + Semgrep | Phase 3 |
| `scripts/mangohud-analyzer.sh` | Activates venv, runs MangoHud CSV analysis | Phase 4 |
| `scripts/setup-ai-env.sh` | One-shot environment setup (uv, venv, deps) | Phase 0 (was manual) |

### 16.4 Planned Modifications to Existing Files

| File | Planned Change | Phase |
|------|----------------|-------|
| `scripts/clamav-alert.sh` | Call threat-lookup.sh, inject threat intel HTML section | Phase 1 |
| `scripts/system-health-snapshot.sh` | Call ai-query.py when WARNING/CRITICAL detected | Phase 2 |
| `tray/bazzite-security-tray.py` | Add "Ask AI" menu item | Phase 2 |
| `scripts/deploy.sh` | Add AI scripts deployment section | Phase 1 |
| `scripts/backup.sh` | Add AI config + vector DB backup targets | Phase 2 |
| `scripts/integration-test.sh` | Add AI venv, keys.env permissions, import checks | Phase 1 |
| `.github/workflows/main.yml` | Add Ruff, Bandit, Semgrep CI jobs | Phase 3 |

### 16.5 API Keys Not Yet Populated

The `~/.config/bazzite-ai/keys.env` file exists with correct permissions (chmod 600) but all values are empty template strings. The user will populate keys after Claude Code's `.env` file read access is permanently blocked.

### 16.6 Ollama Not Yet Configured for AI Use

Ollama 0.18.0 is installed at `/usr/local/bin/ollama` with systemd service configured (ollama user, render/video groups for GPU access). However, the `nomic-embed-text-v2-moe` model has not yet been pulled. This is a Phase 2 task. The plan is to install Ollama via `brew install` (overriding the existing install) per locked architecture decisions.

### 16.7 LanceDB Data Directory

`~/security/vector-db/` is the planned location but has not been created yet. Subdirectories `security-logs/`, `code-index/`, and `threat-intel/` are planned for Phase 2.

---

## 17. Rejected Approaches and Do-Not-Use List

### Software Rejected After Evaluation

| Software | Rejection Reason |
|----------|-----------------|
| Local LLM generation (Qwen, DeepSeek, etc.) | 3-8 tok/s on GTX 1060. Monopolizes VRAM needed for gaming/Wayland. |
| ChromaDB | HNSW index lives in RAM. Competes with gaming on 16GB. LanceDB is disk-based. |
| OTXv2 Python SDK | Dropped in favor of raw HTTP requests — simpler, fewer dependencies. |
| sentence-transformers | Dropped — Ollama handles all embeddings locally. |
| Puter.js | Third-party proxy, no SLA, routes data through their infra. |
| DuckDuckGo AI wrappers | Reverse-engineered unofficial APIs. Will break without warning. |
| Codacy | Free only for open-source. This repo is private. |
| PhishTank | Personal signups disabled March 2026. |
| Together AI | Requires $5 minimum purchase. |
| SonarQube | 2-4GB RAM + Elasticsearch. Too heavy. |
| Wazuh | Full SIEM needing 4-8GB RAM. Competes with gaming. |
| Supabase | Pauses after 7 days inactivity. |
| Grafana + Loki | 500MB-1GB RAM. Deferred to Phase 6 evaluation. |
| Netdata | ~150MB RAM + 5% CPU. Deferred to Phase 6 evaluation. |
| clamonacc | On-access scanning causes severe gaming I/O performance impact. |

### Architectural Approaches Rejected

| Approach | Why |
|----------|-----|
| PRIME offload env vars | Crash all Proton games on this hardware |
| vm.swappiness below 180 | Starves ZRAM swap system |
| Two separate git repos | deploy.sh, backup.sh, and integration tests need unified access |
| LiteLLM proxy server | In-script Router is simpler, no persistent daemon |
| Parallel API calls for threat intel | Cascading (VT→OTX→MalwareBazaar) is more rate-limit friendly |
| Modifying quarantine-hashes.log | Separate enriched JSONL file preserves existing log format |
| "Pipe logs into 1M context window" | Inefficient, expensive, and imprecise compared to RAG |
| Semantic chunking | Section-based chunking is simpler and sufficient for log data |
| TOCTOU mitigation on lock files | Theoretical race condition, impractical to exploit |
| Socket-based IPC for tray | Polling JSON every 3s is simple and working |
| Formal JSON schema validation | Overkill for the simple `.status` file format |

---

## 18. Critical Rules — Never Violate

These rules apply to ALL engineers and AI assistants working on this project.

### System Rules

1. **NEVER use PRIME offload variables** (`__NV_PRIME_RENDER_OFFLOAD`, `__GLX_VENDOR_LIBRARY_NAME`, `__VK_LAYER_NV_optimus`). They crash Proton games on this hardware.
2. **NEVER lower vm.swappiness below 180**. Bazzite uses ZRAM — high swappiness is required.
3. **NEVER suggest nvidia-xconfig** — doesn't exist on Bazzite's immutable filesystem.
4. **NEVER suggest supergfxctl -m Dedicated** — only Integrated and Hybrid modes exist.
5. **NEVER suggest ProtonUp-Qt** — this system uses ProtonPlus.
6. **Prefer Flatpak → Homebrew → Distrobox → rpm-ostree** for software installation.

### AI Layer Rules

7. **NEVER run local LLM generation models**. Only `nomic-embed-text` for embeddings via Ollama.
8. **NEVER store API keys in code, scripts, or git**. Keys live in `keys.env` (chmod 600).
9. **NEVER install Python packages globally or with --break-system-packages**. Use uv and the project venv.
10. **NEVER run AI components as persistent daemons**. Everything is on-demand.
11. **NEVER call cloud APIs without going through rate_limiter.py**.
12. **NEVER hardcode API provider choices**. All LLM calls go through router.py.
13. **All shell wrappers go in scripts/**. All Python logic goes in ai/.
14. **LanceDB data lives at ~/security/vector-db/**. Not in repo, not in /tmp.
15. **The .status JSON file is shared**. AI scripts that update it MUST use read-modify-write + atomic rename. Only update AI-specific keys.

---

## 19. Known Issues and Quirks

| Issue | Impact | Workaround |
|-------|--------|------------|
| LanceDB segfaults in VS Code Flatpak sandbox | Cannot run LanceDB tests in VS Code terminal | Run tests in regular terminal |
| uv installed to Flatpak path | Claude Code uses different uv path than terminal | Install uv separately at `~/.local/bin/uv` for terminal use |
| sops requires special flags for .env files | Encrypt/decrypt fails without flags | Always use `--input-type dotenv --output-type dotenv` |
| litellm/rich/python-dotenv lack `__version__` | AttributeError on `pkg.__version__` | Use `importlib.metadata.version("pkg")` instead |
| KDE caches AppIndicator3 icons by name string | Tray icon doesn't update visually | Set icon to empty string before setting new icon |
| ClamAV 1.4.x cli_realpath warnings | Spam in output logs | Known bug, filtered from scan output |
| `~` resolves to /root/ when running as root | Email alerts fail if using `~` | All paths use absolute `/home/lch/...` |
| clamdscan ignores --exclude-dir flag | Exclusions don't work from CLI | Use ExcludePath in server-side scan.conf |

---

## 20. Resource Budget and Performance Constraints

Gaming performance is the top priority. All AI components are burst/on-demand with a strict resource budget.

| Component | RAM | VRAM | When Active |
|-----------|-----|------|-------------|
| LanceDB | ~10 MB (mmap) | 0 | On query only |
| Ollama + nomic-embed-text | ~200 MB | ~300 MB | Embedding only, then unloads |
| LiteLLM (in script) | ~50 MB | 0 | On API call only |
| threat-intel.py | ~30 MB | 0 | Per-scan only |
| **Total AI overhead** | **~290 MB** | **~300 MB** | **Burst, not continuous** |

**Hard constraint**: Nothing runs as a persistent daemon except the existing tray app (which polls `.status` every 3 seconds — negligible overhead). All AI components terminate after completing their task.

**Scheduling principle**: If in doubt, defer AI work to a systemd timer during off-hours (e.g., embedding at 9 AM when gaming is unlikely).

**VRAM is reserved for gaming**. The only local model allowed is nomic-embed-text (~300 MB VRAM). No local LLM generation models — all inference is cloud-based via free-tier APIs.

---

*End of document. For implementation details on specific phases, see the planning docs in `~/projects/Setup/` (not in git). For base system details, reference the "Bazzite Laptop" Claude.ai project. For AI layer development, reference the "Bazzite AI Layer" Claude.ai project.*
