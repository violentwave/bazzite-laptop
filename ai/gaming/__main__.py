"""CLI entry point for gaming optimization.

Usage:
    python -m ai.gaming analyze <log_path> [--game NAME] [--no-ai]
    python -m ai.gaming profile <game_name> [--refresh]
    python -m ai.gaming scan [--library PATH]
    python -m ai.gaming hardware
"""

import argparse
import json
import sys
from pathlib import Path

from ai.config import setup_logging


def cmd_analyze(args):
    from ai.gaming.hardware import get_hardware_snapshot  # noqa: PLC0415
    from ai.gaming.mangohud import (  # noqa: PLC0415
        analyze_performance,
        parse_mangohud_log,
        suggest_optimizations,
    )
    from ai.rate_limiter import RateLimiter  # noqa: PLC0415

    session = parse_mangohud_log(Path(args.log))
    issues = analyze_performance(session)

    result = {"session": session.to_dict(), "issues": [i.to_dict() for i in issues]}

    if issues and not args.no_ai:
        hardware = get_hardware_snapshot()
        limiter = RateLimiter()
        suggestions = suggest_optimizations(
            issues, session.game_name or args.game or "Unknown",
            hardware=hardware, rate_limiter=limiter,
        )
        result["ai_suggestions"] = suggestions

    print(json.dumps(result, indent=2))
    sys.exit(1 if any(i.severity == "critical" for i in issues) else 0)


def cmd_profile(args):
    from ai.gaming.hardware import get_hardware_snapshot  # noqa: PLC0415
    from ai.gaming.scopebuddy import get_profile, suggest_launch_options  # noqa: PLC0415
    from ai.rate_limiter import RateLimiter  # noqa: PLC0415

    profile = get_profile(args.game)
    if profile and not args.refresh:
        print(json.dumps(profile.to_dict(), indent=2))
        return

    hardware = get_hardware_snapshot()
    limiter = RateLimiter()
    profile = suggest_launch_options(args.game, hardware=hardware, rate_limiter=limiter)
    print(json.dumps(profile.to_dict(), indent=2))


def cmd_scan(args):
    from ai.gaming.scopebuddy import scan_steam_library  # noqa: PLC0415

    library = Path(args.library) if args.library else None
    games = scan_steam_library(library)
    print(json.dumps(games, indent=2))
    print(f"\nFound {len(games)} installed games.", file=sys.stderr)


def cmd_hardware(args):
    from ai.gaming.hardware import get_hardware_snapshot  # noqa: PLC0415

    snapshot = get_hardware_snapshot()
    print(json.dumps(snapshot.to_dict(), indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="python -m ai.gaming",
        description="Gaming optimization AI layer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Analyze MangoHud log")
    p_analyze.add_argument("log", help="Path to MangoHud CSV log file")
    p_analyze.add_argument("--game", default="", help="Game name override")
    p_analyze.add_argument("--no-ai", action="store_true", help="Skip LLM suggestions")
    p_analyze.set_defaults(func=cmd_analyze)

    p_profile = sub.add_parser("profile", help="Get/create game profile")
    p_profile.add_argument("game", help="Game name")
    p_profile.add_argument("--refresh", action="store_true", help="Force re-analysis")
    p_profile.set_defaults(func=cmd_profile)

    p_scan = sub.add_parser("scan", help="Scan Steam library")
    p_scan.add_argument("--library", help="Override library path")
    p_scan.set_defaults(func=cmd_scan)

    p_hw = sub.add_parser("hardware", help="Show hardware snapshot")
    p_hw.set_defaults(func=cmd_hardware)

    args = parser.parse_args()
    setup_logging()
    args.func(args)


if __name__ == "__main__":
    main()
