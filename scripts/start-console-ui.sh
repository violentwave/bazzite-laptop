#!/bin/bash
# start-console-ui.sh — Start the Unified Control Console UI dev server
# Location: scripts/start-console-ui.sh
#
# PURPOSE:
#   Provides a simple, documented way to start the local web UI for the
#   Bazzite Unified Control Console. The UI requires an active dev server
#   and is NOT always-on — it must be started explicitly when needed.
#
# USAGE:
#   ./scripts/start-console-ui.sh [OPTIONS]
#
# OPTIONS:
#   --build    Build for production instead of starting dev server
#   --help     Show this help message
#
# EXAMPLES:
#   ./scripts/start-console-ui.sh              # Start dev server
#   ./scripts/start-console-ui.sh --build      # Build for production
#
# NOTES:
#   - The UI is available at http://localhost:3000 while the server runs
#   - Press Ctrl+C to stop the server
#   - The UI requires the MCP bridge and LLM proxy to be running
#   - See USER-GUIDE.md for full operator documentation

set -euo pipefail

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UI_DIR="${REPO_DIR}/ui"
UI_URL="http://localhost:3000"
DO_BUILD=false

# ─────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --build)
            DO_BUILD=true
            ;;
        --help|-h)
            cat << 'EOF'
Usage: start-console-ui.sh [OPTIONS]

Start the Unified Control Console UI dev server.

OPTIONS:
  --build      Build for production instead of starting dev server
  --help       Show this help message

EXAMPLES:
  ./scripts/start-console-ui.sh              # Start dev server
  ./scripts/start-console-ui.sh --build      # Build for production

NOTES:
  - The UI is available at http://localhost:3000 while the server runs
  - Press Ctrl+C to stop the server
  - The UI requires the MCP bridge and LLM proxy to be running
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────

# Check UI directory exists
if [[ ! -d "$UI_DIR" ]]; then
    echo "ERROR: UI directory not found at $UI_DIR"
    exit 1
fi

# Check package.json exists
if [[ ! -f "$UI_DIR/package.json" ]]; then
    echo "ERROR: package.json not found in $UI_DIR"
    echo "Run: cd $UI_DIR && npm install"
    exit 1
fi

# Check node_modules exists
if [[ ! -d "$UI_DIR/node_modules" ]]; then
    echo "ERROR: node_modules not found in $UI_DIR"
    echo "Run: cd $UI_DIR && npm install"
    exit 1
fi

# ─────────────────────────────────────────────────────────────
# Main execution
# ─────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════"
echo "  Bazzite Unified Control Console UI"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cd "$UI_DIR"

if [[ "$DO_BUILD" == true ]]; then
    echo "Building for production..."
    echo ""
    npm run build
    echo ""
    echo "✅ Build complete"
    echo "   Static files: $UI_DIR/dist/"
    echo ""
    echo "To serve the built files:"
    echo "  npx serve dist/"
else
    echo "Starting dev server..."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  URL:    $UI_URL"
    echo "  Stop:   Press Ctrl+C"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    npm run dev
fi
