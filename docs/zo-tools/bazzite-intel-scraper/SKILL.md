---
name: bazzite-intel-scraper
description: Automated intelligence gathering for bazzite-laptop system - scrapes GitHub repo, security feeds, and AI/tech news every 2 hours to populate RAG knowledge base and trigger alerts on relevant updates
compatibility: Created for Zo Computer - Python 3.12+ with httpx, feedparser, GitHub API
metadata:
  author: topoman.zo.computer
  version: "1.0.0"
  created: 2026-04-06
---

# Bazzite Intel Scraper

Multi-source intelligence scraper for the bazzite-laptop AI system. Runs every 2 hours to gather:

1. **GitHub Repository Intelligence** - commits, PRs, issues, releases, security advisories
2. **Security Threat Feeds** - CVEs, threat intel, malware hashes
3. **Tech/AI News** - Bazzite updates, LiteLLM changes, MCP protocol news
4. **Dependency Updates** - pip packages, npm modules with security implications

## Output Format

All scraped data is saved to `~/security/intel/` with timestamps:

```
~/security/intel/
├── github/
│   ├── commits_YYYY-MM-DD.json
│   ├── prs_YYYY-MM-DD.json
│   ├── issues_YYYY-MM-DD.json
│   └── releases_YYYY-MM-DD.json
├── security/
│   ├── cves_YYYY-MM-DD.json
│   └── threat_intel_YYYY-MM-DD.json
├── tech_news/
│   └── bazzite_llm_YYYY-MM-DD.json
└── ingest/
    └── pending_ingest.jsonl  # Auto-ingested into LanceDB
```

## Installation

```bash
cd ~/workspace/Skills/bazzite-intel-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install httpx feedparser python-dateutil
```

## Usage

### Manual Run
```bash
cd ~/workspace/Skills/bazzite-intel-scraper
./scripts/scrape.sh
```

### As Scheduled Agent (every 2 hours)
The scraper is designed to run as a Zo Agent with 2-hour intervals.

## Key Sources

| Source | Type | Why Tracked |
|--------|------|-------------|
| violentwave/bazzite-laptop | GitHub | Own repo changes |
| ublue-os/bazzite | GitHub | Upstream OS updates |
| BerriAI/litellm | GitHub | LLM routing updates |
| modelcontextprotocol/spec | GitHub | MCP protocol changes |
| CISA KEV Feed | RSS | Critical vulnerabilities |
| NVD CVE Feed | RSS | General CVE tracking |
| OTX AlienVault Pulse | API | Threat intelligence |
| Fedora Bazzite Forum | RSS | Community issues |

## Integration with Bazzite System

1. **RAG Ingestion** - New data auto-ingested into `documents` table
2. **Alert Triggering** - Security CVEs → Alert system
3. **Handoff Updates** - Changes trigger HANDOFF.md updates via MCP
4. **Code Patterns** - New commits → Pattern extraction for code intelligence

## Configuration

Set in `~/.config/bazzite-ai/keys.env`:
```bash
GITHUB_TOKEN=ghp_...  # For higher rate limits
OTX_API_KEY=...       # For threat intel (optional)
```

## Tool Mapping

This skill uses these Zo tools:
- `Bash` - Script execution, file operations
- `Read` - Read existing intel files
- `Web` - HTTP requests to GitHub API, RSS feeds

## Alert Conditions

The scraper generates MCP alerts for:
- New CVEs affecting tracked dependencies
- New GitHub releases (security patches)
- Failed scraper runs (timer health)
- Breaking changes in MCP spec

## Discovery Scraper (Every 6 Hours)

Separate scraper focused on **finding improvements**, not monitoring:

### What It Finds
- **Free LLM APIs** - New providers, free tiers, pricing changes
- **Vector Database Alternatives** - Better/faster/lighter than LanceDB
- **Security Tools** - New threat intel sources, monitoring tools
- **MCP Expansions** - More tools for the MCP bridge beyond current 79
- **Optimization Opportunities** - Lighter alternatives to httpx, litellm, etc.
- **AI Capability Expansions** - RAG frameworks, agent orchestration, knowledge graphs

### Categories
- `vector_databases` - Chroma, Qdrant, Weaviate, Milvus, pgvector, sqlite-vss
- `llm_providers` - Free tiers, new APIs, local inference
- `security_tools` - YARA, Sigma, osquery, Velociraptor integrations
- `mcp_tools` - Official MCP servers, community bridges
- `optimization` - Faster/smaller alternatives to current deps
- `ai_capabilities` - LangGraph, GraphRAG, Mem0, Haystack, semantic caching

### Action Types
- **integrate** - Ready to add to your 79 MCP tools
- **replace** - Lighter alternative to current dependency
- **research** - Needs evaluation before adoption

### Output
```
~/security/discovery/
├── reports/
│   ├── report_YYYYMMDD_HHMMSS.json
│   └── latest.json (symlink)
├── raw/
│   └── discovery_YYYYMMDD_HHMMSS.jsonl
└── .discovery.log
```

### Relevance Scoring
1-10 based on:
- Stars/popularity (caps at 10k+ stars)
- Keywords matching bazzite needs
- Language (Python/Rust preferred)
- License (MIT/Apache 2.0 preferred)

### Requirements
GITHUB_TOKEN in `~/.config/bazzite-ai/keys.env`:
```
GITHUB_TOKEN=ghp_xxxxxxxxxx
```
Without token: Limited to 10 requests/hour (results in ~30 items)
With token: 5000 requests/hour (full discovery of 200+ items)

---

## Usage

### Manual Monitoring Scraper
```bash
cd /home/workspace/Skills/bazzite-intel-scraper
./scripts/scrape.sh
```

### Manual Discovery Scraper
```bash
./scripts/discovery.sh
# Or single category:
./scripts/discovery.sh --category llm_providers
```

### Scheduled Agents
Both scrapers run automatically via Zo agents:
- **Monitoring**: Every 2 hours → `~/security/intel/`
- **Discovery**: Every 6 hours → `~/security/discovery/`

### RAG Integration
Monitoring data auto-queues for LanceDB ingestion via `pending_ingest.jsonl`.
Discovery reports include `current_system_alternatives` mapping to help prioritize.

---

## Files
- `SKILL.md` - This documentation
- `scripts/scraper.py` - Main monitoring scraper (Python)
- `scripts/scrape.sh` - Wrapper for monitoring
- `scripts/discovery_scraper.py` - Discovery scraper (Python)
- `scripts/discovery.sh` - Wrapper for discovery
- `scripts/ingest_to_rag.py` - LanceDB ingestion helper
- `.venv/` - Python virtual environment