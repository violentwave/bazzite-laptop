# Bazzite AI Layer — System Profile

## Hardware
- Machine: Acer Predator G3-571, Bazzite 43 / KDE Plasma 6 / Wayland
- CPU: Intel i7-7700HQ (4c/8t), RAM: 16GB + ZRAM 7.7GB (zstd, swappiness=180)
- GPU: NVIDIA GTX 1060 Mobile 6GB (gaming/Wayland) + Intel HD 630 (hybrid mode)
- Storage: 256GB internal (LUKS/btrfs) + 1.8TB external SSD (/var/mnt/ext-ssd)
- User: lch

## VRAM Budget — HARD LIMITS
- Total VRAM: 6GB — gaming workloads claim 5.7GB minimum
- AI overhead budget: 0 VRAM (cloud embeddings — Gemini Embedding 001 is primary)
- Ollama nomic-embed-text is emergency local fallback only — do NOT load it by default
- NEVER suggest local LLM generation (no llama.cpp, no text-generation-webui, no Ollama gen)

## Security Rules (Non-Negotiable)
1. NEVER store API keys in code, scripts, or git
2. Keys live ONLY in ~/.config/bazzite-aikeys.env (chmod 600)
3. NEVER call cloud APIs without going through ai/ratelimiter.py
4. NEVER hardcode provider choices — all LLM calls via ai/router.py (LiteLLM V2)
5. NEVER use shell=True in subprocess calls
6. NEVER run as root or with sudo in automated scripts
7. MCP bridge tools are read-only — no system mutations
8. NEVER expose key values — only check presence
9. Atomic writes for security.status — read-modify-write + tmp/mv only

## Immutable OS Rules
- OS is Fedora Atomic (immutable). NEVER modify /usr
- Packages: rpm-ostree (system), Flatpak (apps), Distrobox (dev envs), Homebrew (user tools)
- NEVER lower vm.swappiness below 180 (ZRAM requires high swappiness)
- NEVER use PRIME offload env vars — crashes Proton games on this hardware
- NEVER use nvidia-xconfig — doesn't exist on immutable filesystem
- Python: uv only, project venv at ~/projects/bazzite-laptop/.venv — NEVER global pip

## Tooling Stack
- LLM Proxy: 127.0.0.1:8767 (OpenAI-compatible, LiteLLM V2 router)
- MCP Bridge: 127.0.0.1:8766 (FastMCP, 43 tools, allowlist-based)
- OpenCode: on-demand CLI pointing at LLM proxy (opencode.json)
- Ollama: 127.0.0.1:11434 (emergency embed fallback only — nomic-embed-text)
- Providers: Gemini, Groq, Mistral, OpenRouter, z.ai, Cerebras (health-weighted)
- Task types: fast, reason, batch, code (→ z.ai GLM), embed (→ Gemini Embedding 001)
- Resource control: active workload takes priority (systemd slices + GameMode hooks)

## Two-Phase Workflow
- Phase A: Agent edits files, runs pytest/ruff/bandit in .venv (no root needed)
- Phase B: Human manually runs sudo/systemctl/rpm-ostree in terminal

## Available Paths
- Repo: ~/projects/bazzite-laptop/
- AI modules: ~/projects/bazzite-laptop/ai/
- Venv: ~/projects/bazzite-laptop/.venv/
- Configs: ~/projects/bazzite-laptop/configs/
- Tests: ~/projects/bazzite-laptop/tests/
- API keys: ~/.config/bazzite-aikeys.env
- LanceDB: ~/security/vector-db/
- Status: ~/security/security.status

## Code Quality Standards
- Linting: ruff check ai/ tests/
- Security: bandit -r ai/ -c pyproject.toml
- Tests: pytest tests/ (510+ tests, must stay green)
- No global pip installs — uv only
