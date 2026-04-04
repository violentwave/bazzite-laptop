#!/usr/bin/env python3
import sys

from ai.insights import InsightsEngine


def main():
    engine = InsightsEngine()
    insights = engine.generate_weekly_insights()
    print(f"[weekly-insights] Generated {len(insights['insights'])} insights")
    for rec in insights.get("recommendations", []):
        print(f"  - {rec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
