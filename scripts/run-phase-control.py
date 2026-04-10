#!/usr/bin/env python3
"""Run one or more phase-control ticks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.config import load_keys  # noqa: E402
from ai.phase_control.models import PhaseRow, PhaseStatus  # noqa: E402
from ai.phase_control.notion_sync import InMemoryPhaseSync, NotionPhaseSync  # noqa: E402
from ai.phase_control.runner import PhaseControlRunner, RunnerConfig  # noqa: E402


def _load_seed(path: Path) -> list[PhaseRow]:
    """Load optional seed phases from JSON for local runner usage."""
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    phases: list[PhaseRow] = []
    for item in payload:
        phases.append(
            PhaseRow(
                phase_name=item["phase_name"],
                phase_number=int(item["phase_number"]),
                status=PhaseStatus(item.get("status", "Ready")),
                execution_prompt=item.get("execution_prompt", ""),
                validation_commands=item.get("validation_commands", []),
                done_criteria=item.get("done_criteria", []),
                dependencies=item.get("dependencies", []),
                backend=item.get("backend", "codex"),
                branch_name=item.get("branch_name"),
                allowed_tools=item.get("allowed_tools", []),
                execution_mode=item.get("execution_mode", "safe"),
                risk_tier=item.get("risk_tier", "medium"),
                approval_required=bool(item.get("approval_required", False)),
                approval_granted=bool(item.get("approval_granted", False)),
                timeout_seconds=int(item.get("timeout_seconds", 1800)),
                env_allowlist=item.get("env_allowlist", []),
                artifacts_dir=item.get("artifacts_dir", ""),
                slack_channel=item.get("slack_channel"),
                slack_thread_ts=item.get("slack_thread_ts"),
            )
        )
    return phases


def _build_sync_backend(args):
    """Build sync backend from CLI args with Notion as default."""
    if args.in_memory:
        phases = _load_seed(args.seed_json)
        return InMemoryPhaseSync(phases=phases)

    if not args.database_id:
        raise SystemExit("NOTION_PHASE_DATABASE_ID (or --database-id) is required")
    return NotionPhaseSync(database_id=args.database_id)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Phase-control runner")
    parser.add_argument("--once", action="store_true", help="Run a single tick and exit")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="Loop interval for non-once mode",
    )
    parser.add_argument(
        "--seed-json",
        type=Path,
        default=Path.home() / "security" / "phase-control-seed.json",
        help="Optional local phase seed file for standalone mode",
    )
    parser.add_argument(
        "--database-id",
        default="",
        help="Notion database ID for phase control rows",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="Use local in-memory seed mode (non-default development fallback)",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify Notion config and phase database access without mutating rows",
    )
    args = parser.parse_args()

    # Load keys before building backend so env var is available for default
    load_keys(scope="notion")
    if not args.database_id:
        args.database_id = os.environ.get("NOTION_PHASE_DATABASE_ID", "")

    try:
        sync = _build_sync_backend(args)
    except Exception as exc:
        print(json.dumps({"status": "config_error", "error": str(exc)}))
        return 1

    if args.smoke_test:
        if args.in_memory:
            phases = sync.list_phases()
            next_ready = sync.get_next_ready_phase()
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "mode": "in_memory",
                        "config_loaded": True,
                        "row_count": len(phases),
                        "next_ready_phase": next_ready.phase_number if next_ready else None,
                        "next_ready_phase_name": next_ready.phase_name if next_ready else None,
                    },
                    default=str,
                )
            )
            return 0
        try:
            result = sync.smoke_test()
        except Exception as exc:
            print(json.dumps({"status": "error", "mode": "notion", "error": str(exc)}))
            return 1
        print(json.dumps({"status": "ok", "mode": "notion", **result}, default=str))
        return 0

    runner = PhaseControlRunner(config=RunnerConfig(repo_path=str(Path.cwd())), sync_backend=sync)

    if args.once:
        try:
            print(json.dumps(runner.run_once(), default=str))
            return 0
        except Exception as exc:
            print(json.dumps({"status": "error", "error": str(exc)}))
            return 1

    while True:
        try:
            print(json.dumps(runner.run_once(), default=str))
        except Exception as exc:
            print(json.dumps({"status": "error", "error": str(exc)}))
            return 1
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
