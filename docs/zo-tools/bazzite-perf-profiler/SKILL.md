---
name: bazzite-perf-profiler
description: Tracks system performance, resource usage, LLM costs, and API rate limits for bazzite-laptop AI layer
compatibility: Created for Zo Computer - Python 3.12+ with psutil
metadata:
  author: topoman.zo.computer
  version: "1.0.0"
  created: 2026-04-06
---

# Bazzite Performance Profiler

Monitors the bazzite-laptop AI system performance in real-time, tracking:
- CPU/Memory/Disk usage of MCP bridge, routers, and agents
- LLM provider costs and rate limits
- Database (LanceDB) query performance
- API call latency and error rates
- systemd timer health

## What It Does

1. **System Metrics** - CPU, RAM, disk I/O for key processes
2. **LLM Cost Tracking** - Per-provider token usage and estimated costs
3. **Rate Limit Monitoring** - Tracks remaining API quota across 6 providers
4. **Database Performance** - LanceDB query times, table sizes, vector counts
5. **Timer Health** - systemd timer execution status
6. **Alert Thresholds** - Triggers when limits approached
7. **Cost Optimization** - Suggests provider switching based on price/latency

## Integration with Bazzite System

- Reads from `ai/router.py` usage tracking
- Monitors `~/.bazzite-ai/llm-cache/` size
- Checks systemd timers: `systemctl list-timers`
- Saves to `~/security/metrics/` for trend analysis
- Alerts via MCP when thresholds breached

## Usage

### Quick Check
```bash
cd ~/workspace/Skills/bazzite-perf-profiler
./scripts/profile.sh
```

### Continuous Monitoring (5 minute intervals)
```bash
./scripts/profile.sh --watch --interval 300
```

### Generate Cost Report
```bash
./scripts/profile.sh --cost-report --days 7
```

## Metrics Collected

| Metric | Source | Threshold |
|--------|--------|-----------|
| CPU % | psutil | >80% alert |
| Memory % | psutil | >85% alert |
| Disk (security dir) | du | >5GB alert |
| LanceDB size | du | >1GB alert |
| LLM cost/hour | router.py | >$1/hour alert |
| Rate limit remaining | API headers | <20% alert |
| systemd timer lag | systemctl | >1hr alert |

## Output Format

```json
{
  "timestamp": "2026-04-06T14:30:00Z",
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "disk_usage_gb": 2.3
  },
  "llm_providers": {
    "gemini": {"cost_24h": 0.12, "rate_limit_remaining": 1480},
    "groq": {"cost_24h": 0.45, "rate_limit_remaining": 99500}
  },
  "database": {
    "lancedb_size_mb": 450,
    "table_counts": {"documents": 15234, "patterns": 892}
  },
  "alerts": ["groq_rate_limit_low: 5% remaining"]
}
```

## Files
- `scripts/profile.py` - Main profiler
- `scripts/profile.sh` - Wrapper script
- `references/optimizations.md` - Common optimization strategies