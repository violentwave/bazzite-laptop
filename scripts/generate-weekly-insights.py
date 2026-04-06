#!/usr/bin/env python3
"""Generate weekly AI layer insights and cache in LanceDB."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        from ai.insights import run_insights_generation
        result = run_insights_generation()
        logger.info("Insights generated: kind=%s at %s",
                    result.get("kind"), result.get("generated_at"))
    except Exception:
        logger.exception("generate-weekly-insights failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
