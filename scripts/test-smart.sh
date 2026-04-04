#!/bin/bash
# Smart test runner with selective execution modes

set -euo pipefail
cd ~/projects/bazzite-laptop
source .venv/bin/activate

MODE="${1:-smart}"

case "$MODE" in
    smart)
        python -m pytest --testmon -m "not quarantined" "$@"
        ;;
    full)
        python -m pytest -n 4 --timeout=60 -m "not quarantined" "$@"
        ;;
    flaky)
        python -m pytest -m "quarantined" --reruns 3 --reruns-delay 1 "$@"
        ;;
    *)
        echo "Usage: test-smart.sh [smart|full|flaky]"
        echo "  smart  - selective runs via testmon (default)"
        echo "  full   - parallel runs with xdist"
        echo "  flaky  - re-run quarantined tests"
        exit 1
        ;;
esac
