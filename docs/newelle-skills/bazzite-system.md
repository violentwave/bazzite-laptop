# Bazzite System Skill Bundle

Tools for monitoring hardware state, service status, logs, and LLM/MCP
configuration. Most tools are read-only and fast; exceptions are noted in
Safety Rules below.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `system.disk_usage` | Disk usage for all mounted filesystems (`df -h`) | none |
| `system.cpu_temps` | CPU core and sensor temperatures in JSON format | none |
| `system.gpu_status` | NVIDIA GPU temperature, memory used/total, power draw/limit | none |
| `system.gpu_perf` | GPU performance snapshot via nvidia-smi (clock speeds, utilization, power) | none |
| `system.gpu_health` | GPU throttle bit decoding + thermal headroom; warns at 8°C margin | none |
| `system.memory_usage` | System RAM and swap usage (`free -h`) | none |
| `system.uptime` | System uptime and load average | none |
| `system.service_status` | ActiveState for key systemd services (ClamAV, health timer, MCP bridge, LLM proxy) | none |
| `system.llm_status` | LLM provider health scores, token usage totals, and active model list | none |
| `system.key_status` | API key presence check (never exposes values); reads `~/security/key-status.json` | none |
| `system.llm_models` | Available LLM task types and their provider chains (reads live config) | none |
| `system.mcp_manifest` | Full list of all MCP tools with descriptions and argument schemas | none |
| `system.release_watch` | GitHub Releases + GHSA watcher results for tracked dependencies | none |
| `system.fedora_updates` | Fedora Bodhi pending security and package updates | none |
| `system.pkg_intel` | deps.dev package intelligence: advisories, provenance, version status | none |
| `logs.health_trend` | Last 7 health snapshots with delta trends (temps, disk, RAM) | none |
| `logs.search` | Semantic search across all system logs | `query` (string, max 500 chars, required) |
| `logs.stats` | Log pipeline statistics: record counts, last ingestion time, DB size | none |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "How much disk space is left?" | `system.disk_usage` |
| "Is the CPU running hot?" | `system.cpu_temps` |
| "What's the GPU temperature?" | `system.gpu_status` |
| "How much RAM is in use?" | `system.memory_usage` |
| "How long has the system been running?" | `system.uptime` |
| "Are all the AI services up?" | `system.service_status` |
| "What LLM providers are available?" | `system.llm_models` |
| "Which LLM providers are healthy right now?" | `system.llm_status` |
| "Are all my API keys configured?" | `system.key_status` |
| "What tools does the MCP bridge have?" | `system.mcp_manifest` |
| "Is the GPU being throttled?" | `system.gpu_health` |
| "Show me GPU clock speeds" | `system.gpu_perf` |
| "Any new security releases for my dependencies?" | `system.release_watch` |
| "Are there pending Fedora security updates?" | `system.fedora_updates` |
| "Check the safety record for this package" | `system.pkg_intel` with `package="<name>"` |
| "Has disk usage been growing lately?" | `logs.health_trend` |
| "Show temp trends over the last week" | `logs.health_trend` |
| "Find logs about GPU throttling" | `logs.search` with `query="GPU throttling"` |
| "How many log records are indexed?" | `logs.stats` |

---

## Safety Rules

- **composefs showing 100% disk usage is normal** on Bazzite (Fedora Atomic).
  The composefs overlay represents the immutable OS image layer, not a full
  disk. Never alarm the user about composefs utilization. Focus on writable
  partitions (`/home`, `/var`) when assessing actual disk pressure.

- `system.service_status` only reports the services explicitly listed in its
  systemd query. It does not cover all services. Use it for a quick sanity
  check rather than a comprehensive audit.

- `logs.search` performs semantic search over indexed logs. Results reflect
  what has been ingested — suggest `security.run_ingest` if results seem
  outdated.

- **`system.gpu_health`** emits a `notify-send` desktop notification when
  thermal headroom drops to 8°C or below. When this triggers, advise the
  user to check airflow or reduce workload — do not automatically trigger
  any performance changes.

- **`system.key_status`** only reports key *presence* (present/missing). It
  never reads or displays key values. Do not attempt to infer key values
  from its output.

- **`system.release_watch`** and **`system.fedora_updates`** are updated by
  daily timers. Results may be up to 24 hours old. Tell the user the
  `last_checked` timestamp when reporting findings.

- **`system.pkg_intel`** makes a live network call to deps.dev and may take
  several seconds on a slow connection. Warn the user to expect a brief wait.

- **`logs.scan_history`** and **`logs.anomalies`** are `logs.*` tools that
  appear in the **Security skill bundle** (`bazzite-security.md`), not here,
  because they report ClamAV scan results and security anomalies. Redirect
  the user to security-related queries for those tools.
