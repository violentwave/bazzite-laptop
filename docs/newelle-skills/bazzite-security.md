# Bazzite Security Skill Bundle

Tools for querying ClamAV scan history, system health, threat intelligence,
and triggering background security operations. All read operations are
instant; trigger operations start a background systemd job.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `security.status` | Current security/health status JSON (state, last scan time, result, health issues) | none |
| `security.last_scan` | Last 20 lines of the most recent ClamAV scan log | none |
| `security.health_snapshot` | Last 30 lines of the most recent health snapshot | none |
| `security.threat_lookup` | Look up a file hash in threat intel sources (VirusTotal, OTX, MalwareBazaar) | `hash` (MD5/SHA-1/SHA-256, 32–64 hex chars, required) |
| `security.run_scan` | Trigger a ClamAV scan in the background via systemd | `scan_type` (`"quick"` or `"deep"`, optional, default: quick) |
| `security.run_health` | Trigger a system health snapshot in the background | none |
| `security.run_ingest` | Trigger log ingestion to update the intelligence database | none |
| `logs.scan_history` | Last 10 ClamAV scan results with threat details | none |
| `logs.anomalies` | Unacknowledged anomalies: threats detected, temperature spikes, disk issues | none |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "Am I clean? Any threats?" | `security.status` → `logs.scan_history` |
| "When was the last scan?" | `security.status` |
| "Show me the latest scan log" | `security.last_scan` |
| "Check this hash: abc123…" | `security.threat_lookup` with `hash=<value>` |
| "Run a quick scan" | `security.run_scan` with `scan_type="quick"` |
| "Run a full deep scan" | `security.run_scan` with `scan_type="deep"` |
| "Any anomalies or warnings?" | `logs.anomalies` |
| "Update the security database" | `security.run_ingest` |
| "How is the system health?" | `security.health_snapshot` |
| "Trigger a health check" | `security.run_health` |

---

## Safety Rules

- **`security.run_scan`** starts a real ClamAV scan via systemd. Rate-limit to
  at most once per hour. Warn the user if a scan is already in progress
  (check `security.status` first).
- **`security.threat_lookup`** requires a valid hex hash: 32 chars (MD5),
  40 chars (SHA-1), or 64 chars (SHA-256). Reject anything else with a clear
  error message before calling the tool.
- **`security.run_health`** and **`security.run_ingest`** are low-cost
  background operations but should not be triggered in tight loops.
- Never display raw file paths or internal module names from error messages
  to the user — summarize results in plain language.
