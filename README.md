# Bazzite AI Layer

An AI enhancement layer for the Bazzite gaming laptop, providing voice-controlled system intelligence, security monitoring, and automation capabilities through a local LLM proxy and MCP bridge.

## Quick Stats

| Component | Count |
|-----------|-------|
| MCP Tools | 83 |
| Tests | 2297+ |
| Systemd Timers | 23 |
| LanceDB Tables | 26 |
| Cloud LLM Providers | 6 |

## Repository Structure

| Directory | Purpose |
|-----------|---------|
| `ai/` | Core AI logic: LLM router, MCP bridge, agents, skills |
| `docs/` | Documentation: architecture, guides, phase roadmaps |
| `scripts/` | Deployment, maintenance, and utility scripts |
| `configs/` | Configuration files for MCP, LiteLLM, rate limits |
| `systemd/` | User service definitions for MCP bridge and LLM proxy |
| `tests/` | Unit and integration test suite |
| `tray/` | PySide6 system tray application |

## Getting Started

### Prerequisites
- Bazzite Linux (Fedora Atomic-based)
- Python 3.12+ (managed via `uv` in `.venv/`)
- Node.js v25+ (for RuFlo orchestration)

### Installation
```bash
# Clone repository
git clone https://github.com:violentwave/bazzite-laptop.git
cd bazzite-laptop

# Install Python dependencies
uv pip install -r requirements-ai.txt

# Activate virtual environment
source .venv/bin/activate
```

### Start Services
```bash
# Build and deploy services
bash scripts/deploy-services.sh

# Start MCP Bridge and LLM Proxy
systemctl --user start bazzite-mcp-bridge.service bazzite-llm-proxy.service
```

## Documentation Index

- [Agent Reference](docs/AGENT.md) — Detailed architecture, tools, and system reference
- [User Guide](docs/USER-GUIDE.md) — End-user instructions for Newelle AI assistant
- [Changelog](docs/CHANGELOG.md) — Version history and release notes
- [Verified Dependencies](docs/verified-deps.md) — Audited dependency versions

## Critical Rules (Abbreviated)

1. **No PRIME offload variables** — crashes Proton games on hybrid graphics
2. **Never lower `vm.swappiness` below 180** — required for ZRAM performance
3. **No API keys in code/scripts** — runtime only via `keys.env`
4. **No `shell=True` in subprocess** — static argument lists only
5. **No writes to `/usr`** — immutable OS (Fedora Atomic)