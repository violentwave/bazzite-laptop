#!/usr/bin/env python3
import sys

from ai.insights import run_insights_generation


def main():
    result = run_insights_generation()
    print(f"[weekly-insights] kind={result.get('kind')} at {result.get('generated_at')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
