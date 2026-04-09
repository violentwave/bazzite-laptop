# Bazzite Agents Skill Bundle

Tools for running automated multi-step AI agents. Each agent combines several
lower-level operations (scan, health, ingest, query) into a single call that
returns a structured report. All agents run synchronously and return a JSON
summary when complete.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `agents.security_audit` | Full security audit: triggers ClamAV scan + health snapshot + log ingest + RAG summary | none |
| `agents.performance_tuning` | Performance analysis: CPU/GPU temps, memory pressure, disk I/O, gaming profile state | none |
| `agents.knowledge_storage` | Vector DB health report: table sizes, ingestion freshness, embedding provider status | none |
| `agents.code_quality` | Code quality report: ruff + bandit results + git status summary for `ai/` and `tests/` | none |
| `agents.timer_health` | Validate all 16 systemd timers fired within expected windows; returns per-timer status and health | none |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "Run a full security audit" | `agents.security_audit` |
| "Do a complete security check" | `agents.security_audit` |
| "Is the system performing well?" | `agents.performance_tuning` |
| "Check for performance issues" | `agents.performance_tuning` |
| "How healthy is the knowledge base?" | `agents.knowledge_storage` |
| "When was the vector DB last updated?" | `agents.knowledge_storage` |
| "Any linting or security issues in the code?" | `agents.code_quality` |
| "Run a code quality check" | `agents.code_quality` |
| "Are all the systemd timers firing correctly?" | `agents.timer_health` |
| "Check timer health" | `agents.timer_health` |

---

## Safety Rules

- **`agents.security_audit`** triggers a real ClamAV scan in the background
  via systemd. It is equivalent to calling `security.run_scan` followed by
  `security.run_health` and `security.run_ingest`. Rate-limit to at most once
  per hour. Check `security.status` first if unsure whether a scan is already
  running.

- **`agents.code_quality`** runs ruff and bandit against the `ai/` source tree.
  It is read-only and does not modify any files. It may take 10–20 seconds.

- **`agents.performance_tuning`** reads live sensor data and systemd cgroup
  stats. It does not change any system settings. Results reflect a point-in-time
  snapshot; advise the user to re-run after workload changes.

- **`agents.knowledge_storage`** queries LanceDB table metadata only — it does
  not re-ingest or modify any vectors. If it reports stale embeddings, suggest
  `security.run_ingest` to refresh.
