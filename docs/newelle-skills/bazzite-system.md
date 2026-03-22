# Bazzite System Skill Bundle

Tools for monitoring hardware state, service status, logs, and LLM/MCP
configuration. All tools are read-only and fast.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `system.disk_usage` | Disk usage for all mounted filesystems (`df -h`) | none |
| `system.cpu_temps` | CPU core and sensor temperatures in JSON format | none |
| `system.gpu_status` | NVIDIA GPU temperature, memory used/total, power draw/limit | none |
| `system.memory_usage` | System RAM and swap usage (`free -h`) | none |
| `system.uptime` | System uptime and load average | none |
| `system.service_status` | ActiveState for key systemd services (ClamAV, health timer, MCP bridge, LLM proxy) | none |
| `system.llm_models` | Available LLM task types and their provider chains (reads live config) | none |
| `system.mcp_manifest` | Full list of all MCP tools with descriptions and argument schemas | none |
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
| "What tools does the MCP bridge have?" | `system.mcp_manifest` |
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
