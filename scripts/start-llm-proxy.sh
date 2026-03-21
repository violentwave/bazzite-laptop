#!/bin/bash
# Start the LLM router proxy for Newelle integration.
# Exposes ai/router.py as an OpenAI-compatible API on localhost.
# Provider chain: Gemini → Groq → z.ai → Mistral → OpenRouter → g4f
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

exec python -m ai.llm_proxy --bind 127.0.0.1 --port "${LLM_PROXY_PORT:-8767}"
