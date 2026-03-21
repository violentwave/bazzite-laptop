# Log Intelligence Pipeline Design

**Date:** 2026-03-21
**Status:** Approved
**Goal:** Parse all system logs into LanceDB automatically, expose rich query tools via MCP bridge for Newelle, and run automatic anomaly detection.

## Architecture

```
ClamAV scan ──────┐
Health snapshot ───┤──▶ ai/log_intel/ingest.py ──▶ LanceDB (~/security/vector-db/)
freshclam update ──┘         │                              │
                             ▼                              ▼
                      anomalies.py              MCP Bridge (5 new tools)
                        │                              │
                        ▼                              ▼
                   .status JSON                    Newelle
```

## Components

### 1. `ai/log_intel/__init__.py`
Empty init.

### 2. `ai/log_intel/ingest.py` — Log Parser + Embedder

**Responsibilities:**
- Parse health snapshot logs → structured records (GPU temp, CPU temp, disk%, SMART status, service states)
- Parse ClamAV scan logs → structured records (files scanned, threats found/names, duration, scan type)
- Parse freshclam logs → signature version, update timestamp
- Embed text summaries via Ollama nomic-embed-text (768-dim, local)
- Store in LanceDB tables: `health_records`, `scan_records`, `sig_updates`
- Track last-ingested file via `~/security/vector-db/.ingest-state.json` to avoid reprocessing
- Exclude test scans (`scan_type == "test"`)

**CLI interface:**
```bash
python -m ai.log_intel.ingest --scan     # Ingest latest scan log only
python -m ai.log_intel.ingest --health   # Ingest latest health log only
python -m ai.log_intel.ingest --all      # Catch-up: ingest all new logs since last run
```

**LanceDB schemas:**

`health_records` table:
| Field | Type | Description |
|-------|------|-------------|
| id | utf8 | UUID |
| timestamp | utf8 | ISO timestamp from log |
| gpu_temp_c | float32 | GPU temperature |
| cpu_temp_c | float32 | CPU package temp |
| disk_usage_pct | float32 | Root filesystem % |
| steam_usage_pct | float32 | Steam drive % |
| ram_used_gb | float32 | RAM used |
| swap_used_gb | float32 | Swap used |
| smart_status | utf8 | "PASSED" / "FAILED" |
| services_ok | int32 | Count of active services |
| services_down | int32 | Count of inactive services |
| summary | utf8 | One-line human summary |
| source_file | utf8 | Log file path |
| vector | list(float32, 768) | Embedding of summary |

`scan_records` table:
| Field | Type | Description |
|-------|------|-------------|
| id | utf8 | UUID |
| timestamp | utf8 | ISO timestamp |
| scan_type | utf8 | "quick" / "deep" / "custom" |
| files_scanned | int32 | Total files scanned |
| threats_found | int32 | Infected file count |
| threat_names | utf8 | Comma-separated threat names |
| duration_s | float32 | Scan duration in seconds |
| quarantined | int32 | Files moved to quarantine |
| summary | utf8 | One-line summary |
| source_file | utf8 | Log file path |
| vector | list(float32, 768) | Embedding of summary |

`sig_updates` table:
| Field | Type | Description |
|-------|------|-------------|
| id | utf8 | UUID |
| timestamp | utf8 | ISO timestamp |
| sig_version | utf8 | ClamAV signature version |
| sig_count | int32 | Number of signatures |
| source_file | utf8 | freshclam log path |

### 3. `ai/log_intel/anomalies.py` — Automatic Detection

**Runs after each ingestion.** Checks for:
- Temperature spike: GPU/CPU > 90°C or >10°C above 7-day average
- Disk fill acceleration: >5% increase since last check
- New threats: any scan with threats_found > 0
- Failed services: services_down > 0
- SMART failure: smart_status != "PASSED"

**Output:** Stores anomaly records in LanceDB `anomalies` table:
| Field | Type | Description |
|-------|------|-------------|
| id | utf8 | UUID |
| timestamp | utf8 | When detected |
| category | utf8 | "thermal" / "disk" / "threat" / "service" / "smart" |
| severity | utf8 | "warning" / "critical" |
| message | utf8 | Human-readable description |
| acknowledged | bool | False until user/AI acknowledges |
| source_record_id | utf8 | FK to the triggering record |

Also updates `~/security/.status` with `anomaly_count` and `last_anomaly` fields.

### 4. Five New MCP Bridge Tools

Added to `configs/mcp-bridge-allowlist.yaml` and `ai/mcp_bridge/tools.py`:

**`logs.health_trend`** (no args)
- Returns last 7 health records as JSON with delta annotations
- Delta: "GPU +5°C", "Disk +1.2%", etc.

**`logs.scan_history`** (no args)
- Returns last 10 scan results as JSON
- Highlights any with threats

**`logs.anomalies`** (no args)
- Returns all unacknowledged anomaly records
- Newelle uses this to proactively warn the user

**`logs.search`** (args: query string, max 500 chars)
- Semantic vector search across all log tables
- Uses Ollama embedding + LanceDB vector search
- Returns top 5 matches with context

**`logs.stats`** (no args)
- Record counts per table, last ingestion time, DB size on disk
- Pipeline health check

### 5. Triggers

**Post-scan hook** — Add to ClamAV scan script (after scan completes):
```bash
# Skip test scans
if [ "$SCAN_TYPE" != "test" ]; then
    /home/lch/projects/bazzite-laptop/.venv/bin/python \
        -m ai.log_intel.ingest --scan &
fi
```

**Post-health hook** — Add to health snapshot script:
```bash
/home/lch/projects/bazzite-laptop/.venv/bin/python \
    -m ai.log_intel.ingest --health &
```

**Daily catch-up** — Update existing `rag-embed.timer` service to also run:
```bash
python -m ai.log_intel.ingest --all
```

### 6. Newelle System Prompt Update

Add to Newelle's tool routing:
```
- System health trends → call `logs.health_trend`
- Scan history/threats → call `logs.scan_history`
- Anything unusual/anomalies → call `logs.anomalies`
- Search logs by topic → call `logs.search` (needs query argument)
- Log pipeline status → call `logs.stats`
```

## Files Created/Modified

**New files:**
- `ai/log_intel/__init__.py`
- `ai/log_intel/ingest.py` — parser + embedder (~200 lines)
- `ai/log_intel/anomalies.py` — detection engine (~120 lines)
- `tests/test_log_intel.py` — unit tests

**Modified files:**
- `ai/mcp_bridge/tools.py` — add 5 tool handlers
- `ai/mcp_bridge/server.py` — update tool count 13→18
- `configs/mcp-bridge-allowlist.yaml` — add 5 tool entries
- `scripts/system-health-snapshot.sh` — add post-hook (1 line)
- `scripts/clamav-scan.sh` (or equivalent) — add post-hook (3 lines)

## Constraints

- No new systemd services or persistent daemons
- Embeddings via local Ollama only (nomic-embed-text, ~300MB VRAM)
- All ingestion runs in project venv (.venv/)
- LanceDB at ~/security/vector-db/ (existing path)
- Test scans excluded from ingestion
- Post-hooks run in background (&) to not delay the parent script
