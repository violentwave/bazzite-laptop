"""CLI entry point for the code quality pipeline.

Usage:
    python -m ai.code_quality [--format text|json|html] [--no-ai] [--max-fixes N]
"""

import argparse
import sys

from ai.code_quality.formatter import format_results
from ai.code_quality.runner import run_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Bazzite code quality pipeline")
    parser.add_argument("--format", choices=["text", "json", "html"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip AI fix suggestions")
    parser.add_argument("--max-fixes", type=int, default=10,
                        help="Max AI fix suggestions to generate (default: 10)")
    args = parser.parse_args()

    summaries = run_all()

    if not args.no_ai:
        from ai.code_quality.analyzer import analyze_findings  # noqa: PLC0415
        analyze_findings(summaries, max_suggestions=args.max_fixes)

    output = format_results(summaries, fmt=args.format)
    print(output)

    # Exit with error if any errors found
    total_errors = sum(s.error_count for s in summaries)
    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
