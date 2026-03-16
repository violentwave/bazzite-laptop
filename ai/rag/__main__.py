"""CLI entry point for RAG security queries.

Usage:
    python -m ai.rag "What threats were found?"
    python -m ai.rag --question "GPU temperature trends" --no-llm
    python -m ai.rag --question "ClamAV scan results" --format json
"""

import argparse
import sys

from ai.config import load_keys, setup_logging
from ai.rag.query import format_result, rag_query


def main() -> None:
    """CLI entry point for RAG security intelligence queries."""
    parser = argparse.ArgumentParser(
        description="RAG security intelligence query engine",
    )
    parser.add_argument(
        "question_positional",
        nargs="?",
        default=None,
        help="Natural language question (positional, for quick use)",
    )
    parser.add_argument(
        "--question",
        dest="question_flag",
        default=None,
        help="Natural language question (alternative to positional)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Context-only mode — skip LLM synthesis",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max results per table (default: 5)",
    )
    args = parser.parse_args()

    # Resolve question from positional or flag
    question = args.question_positional or args.question_flag
    if not question:
        parser.error("A question is required (positional or --question)")

    load_keys()
    setup_logging()

    result = rag_query(
        question=question,
        limit=args.limit,
        use_llm=not args.no_llm,
    )

    output = format_result(result, fmt=args.format)
    print(output)  # noqa: T201

    sys.exit(0)


main()
