#!/bin/bash
# setup-ai-env.sh — One-shot bootstrap for the AI enhancement layer
# Run from: ~/projects/bazzite-laptop/
# Usage: bash scripts/setup-ai-env.sh
#
# This script:
#   1. Installs uv (if not present)
#   2. Creates the Python 3.12 venv
#   3. Installs all Python dependencies
#   4. Creates the config directory for API keys
#   5. Verifies the installation
#
# Prerequisites:
#   - Homebrew installed (for sops): /home/linuxbrew/.linuxbrew/
#   - GPG key exists (for sops encryption)
#   - Git repo cloned to ~/projects/bazzite-laptop/
#
# This does NOT:
#   - Fill in API keys (do that manually)
#   - Run sops encrypt/decrypt (do that manually)
#   - Install Ollama or pull models (Phase 2)
#   - Deploy scripts to /usr/local/bin/ (use deploy.sh)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=== Bazzite AI Layer — Environment Setup ==="
echo "Repo: $REPO_DIR"
echo ""

# --- Step 1: Check/install uv ---
if command -v uv &>/dev/null; then
    echo "[OK] uv $(uv --version 2>/dev/null | head -1)"
else
    echo "[INSTALL] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "[OK] uv installed at ~/.local/bin/uv"
fi
echo ""

# --- Step 2: Create venv ---
if [[ -d .venv ]]; then
    echo "[OK] .venv already exists"
else
    echo "[CREATE] Creating Python 3.12 venv..."
    uv venv .venv --python 3.12
    echo "[OK] .venv created"
fi
source .venv/bin/activate
echo "[OK] Python $(python --version 2>&1)"
echo ""

# --- Step 3: Install deps ---
echo "[INSTALL] Installing Python dependencies..."
uv pip install -r requirements.txt
echo "[OK] Dependencies installed"
echo ""

# --- Step 4: Config directory ---
CONFIG_DIR="$HOME/.config/bazzite-ai"
if [[ -d "$CONFIG_DIR" ]]; then
    echo "[OK] $CONFIG_DIR exists"
else
    echo "[CREATE] Creating $CONFIG_DIR..."
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    echo "[OK] Created with chmod 700"
fi

if [[ -f "$CONFIG_DIR/keys.env" ]]; then
    PERMS=$(stat -c %a "$CONFIG_DIR/keys.env")
    if [[ "$PERMS" == "600" ]]; then
        echo "[OK] keys.env exists (chmod 600)"
    else
        echo "[WARN] keys.env exists but permissions are $PERMS (should be 600)"
        chmod 600 "$CONFIG_DIR/keys.env"
        echo "[FIX] Set to chmod 600"
    fi
else
    echo "[WARN] keys.env not found — create it and add your API keys"
    echo "       Template: configs/keys.env.enc (decrypt with sops)"
fi
echo ""

# --- Step 5: Check sops ---
if command -v sops &>/dev/null; then
    echo "[OK] sops $(sops --version 2>/dev/null | head -1)"
else
    echo "[WARN] sops not found — install with: brew install sops"
fi

# --- Step 6: Check GPG ---
GPG_COUNT=$(gpg --list-keys 2>/dev/null | grep -c "^pub" || true)
if [[ "$GPG_COUNT" -gt 0 ]]; then
    echo "[OK] GPG keys found ($GPG_COUNT)"
else
    echo "[WARN] No GPG keys — generate one with: gpg --full-generate-key"
fi
echo ""

# --- Step 7: Verify imports ---
echo "=== Verifying Python imports ==="
FAIL=0
for mod in "ai.config" "ai.router" "ai.rate_limiter" "dotenv" "rich" "tenacity" "requests" "vt"; do
    if python -c "import $mod" 2>/dev/null; then
        echo "[OK] import $mod"
    else
        echo "[FAIL] import $mod"
        FAIL=1
    fi
done

# lancedb may segfault in Flatpak — skip in VS Code
if [[ -z "${FLATPAK_ID:-}" ]]; then
    if python -c "import lancedb" 2>/dev/null; then
        echo "[OK] import lancedb"
    else
        echo "[FAIL] import lancedb"
        FAIL=1
    fi
else
    echo "[SKIP] lancedb (Flatpak sandbox — test from regular terminal)"
fi

echo ""

# --- Step 8: Run tests ---
echo "=== Running tests ==="
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
TEST_EXIT=${PIPESTATUS[0]}
if [[ "$TEST_EXIT" -ne 0 ]]; then
    echo "[WARN] Some tests failed (exit code $TEST_EXIT)"
    FAIL=1
fi
echo ""

# --- Summary ---
echo "==============================="
if [[ "$FAIL" -eq 0 ]]; then
    echo "  AI environment ready!"
else
    echo "  Some imports failed — check above"
fi
echo ""
echo "  Next steps:"
echo "  1. Fill in API keys: ~/.config/bazzite-ai/keys.env"
echo "  2. Re-encrypt: sops --config ~/.config/bazzite-ai/.sops.yaml --input-type dotenv --output-type dotenv -e ~/.config/bazzite-ai/keys.env > configs/keys.env.enc"
echo "  3. Deploy: sudo ./scripts/deploy.sh"
echo "==============================="
