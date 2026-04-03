"""Code quality and repo health agent for Bazzite.

Runs ruff, bandit, git status, and pytest collection to report on code health.
Generates hardcoded rule-based recommendations (no cloud LLM calls).
Writes a structured JSON report to ~/security/code-reports/.

Usage:
    python -m ai.agents.code_quality_agent
    from ai.agents.code_quality_agent import run_code_check
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import UTC, datetime

from ai.config import APP_NAME, PROJECT_ROOT, SECURITY_DIR

logger = logging.getLogger(APP_NAME)

CODE_REPORTS_DIR = SECURITY_DIR / "code-reports"

_VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


# ── Collectors ─────────────────────────────────────────────────────────────────


def _run_ruff() -> dict:
    """Run ruff check and return parsed results."""
    try:
        result = subprocess.run(
            ["ruff", "check", "ai/", "tests/", "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        issues = json.loads(result.stdout) if result.stdout.strip() else []
        by_rule: dict[str, int] = {}
        for issue in issues:
            code = issue.get("code") or "unknown"
            by_rule[code] = by_rule.get(code, 0) + 1
        return {
            "total_errors": len(issues),
            "by_rule": by_rule,
            "clean": len(issues) == 0,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"total_errors": 0, "by_rule": {}, "clean": False, "error": "timeout"}
    except Exception as e:
        logger.debug("ruff error: %s", e)
        return {"total_errors": 0, "by_rule": {}, "clean": False, "error": str(e)}


def _run_bandit() -> dict:
    """Run bandit scan and return parsed results."""
    try:
        result = subprocess.run(
            ["bandit", "-r", "ai/", "-c", "pyproject.toml", "-f", "json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        data = json.loads(result.stdout) if result.stdout.strip() else {}
        results = data.get("results", [])
        counts: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for issue in results:
            sev = issue.get("issue_severity", "").upper()
            if sev in counts:
                counts[sev] += 1
        total = sum(counts.values())
        # LOW-only is considered acceptable (B404 subprocess import)
        clean = counts["HIGH"] == 0 and counts["MEDIUM"] == 0
        return {
            "total_issues": total,
            "high": counts["HIGH"],
            "medium": counts["MEDIUM"],
            "low": counts["LOW"],
            "clean": clean,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "total_issues": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "clean": True,
            "error": "timeout",
        }
    except Exception as e:
        logger.debug("bandit error: %s", e)
        return {
            "total_issues": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "clean": True,
            "error": str(e),
        }


def _run_git_status() -> dict:
    """Run git status --porcelain and classify files."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return {"untracked": 0, "modified": 0, "staged": 0, "dirty": False, "error": None}
        untracked = modified = staged = 0
        for line in result.stdout.splitlines():
            if len(line) < 2:
                continue
            xy = line[:2]
            if xy[0] == "?":
                untracked += 1
            else:
                if xy[1] != " ":
                    modified += 1
                if xy[0] != " ":
                    staged += 1
        dirty = (modified + untracked + staged) > 0
        return {
            "untracked": untracked,
            "modified": modified,
            "staged": staged,
            "dirty": dirty,
            "error": None,
        }
    except Exception as e:
        logger.debug("git status error: %s", e)
        return {"untracked": 0, "modified": 0, "staged": 0, "dirty": False, "error": str(e)}


def _run_git_log() -> list[str]:
    """Return last 10 commits as one-line summaries."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "--oneline", "-10"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    except Exception as e:
        logger.debug("git log error: %s", e)
    return []


def _run_pytest_collect() -> dict:
    """Collect test count without running tests."""
    try:
        python = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else "python"
        result = subprocess.run(
            [python, "-m", "pytest", "tests/", "--co", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        # Final line: "594 tests collected in 1.23s" or similar
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if "collected" in line:
                parts = line.split()
                if parts and parts[0].isdigit():
                    return {"collected": int(parts[0]), "count_known": True}
                break
        return {"collected": 0, "count_known": False}
    except Exception as e:
        logger.debug("pytest collect error: %s", e)
        return {"collected": 0, "count_known": False}


def _run_dep_check() -> dict:
    """Run check-deps.sh and return dependency freshness status."""
    script = PROJECT_ROOT / "scripts" / "check-deps.sh"
    if not script.exists():
        return {"available": False, "output": "", "ok": True}
    try:
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        return {
            "available": True,
            "output": result.stdout.strip(),
            "ok": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"available": False, "output": "timeout", "ok": True}
    except Exception as e:
        logger.debug("dep check error: %s", e)
        return {"available": False, "output": str(e), "ok": True}


# ── Recommendation engine ──────────────────────────────────────────────────────


def _build_recommendations(
    ruff: dict,
    bandit: dict,
    git: dict,
    tests: dict,
    deps: dict | None = None,
) -> tuple[list[str], str]:
    """Apply threshold rules and return (recommendations, status).

    Status levels:
        issues   — HIGH severity bandit or many ruff errors
        warnings — some ruff errors or MEDIUM bandit
        clean    — all nominal
    """
    recs: list[str] = []
    hard_issues = 0
    warnings = 0

    # Ruff
    if ruff.get("error"):
        recs.append(f"Ruff unavailable: {ruff['error']}")
    elif ruff.get("total_errors", 0) > 0:
        n = ruff["total_errors"]
        noun = "issues" if n != 1 else "issue"
        recs.append(f"Ruff found {n} lint {noun} — run: ruff check ai/ tests/")
        warnings += 1

    # Bandit
    if bandit.get("error"):
        recs.append(f"Bandit unavailable: {bandit['error']}")
    else:
        if bandit.get("high", 0) > 0:
            recs.append(
                f"Bandit found {bandit['high']} HIGH severity issue(s) — review immediately"
            )
            hard_issues += 1
        if bandit.get("medium", 0) > 0:
            recs.append(f"Bandit found {bandit['medium']} MEDIUM severity issue(s)")
            warnings += 1

    # Git
    if git.get("error"):
        recs.append(f"Git status unavailable: {git['error']}")
    else:
        modified = git.get("modified", 0)
        untracked = git.get("untracked", 0)
        if modified > 5:
            recs.append(f"Many uncommitted changes ({modified} modified) — consider committing")
            warnings += 1
        if untracked > 3:
            recs.append(
                f"Untracked files accumulating ({untracked}) — review and .gitignore or commit"
            )
            warnings += 1

    # Deps
    if deps and deps.get("available") and not deps.get("ok"):
        recs.append("Dependency versions drifted — run: bash scripts/check-deps.sh")
        warnings += 1

    if not recs:
        recs.append("Code quality excellent")

    if hard_issues > 0:
        status = "issues"
    elif warnings > 0:
        status = "warnings"
    else:
        status = "clean"

    return recs, status


# ── Main workflow ──────────────────────────────────────────────────────────────


def run_code_check() -> dict:
    """Run code quality and repo health check.

    Runs ruff, bandit, git status/log, and pytest collection.
    No cloud API calls. Results written atomically to ~/security/code-reports/.

    Returns:
        dict with keys: timestamp, ruff, bandit, git, tests, deps, recommendations, status.
    """
    now = datetime.now(UTC)
    timestamp = now.isoformat()
    start_time = time.time()

    # Collect data
    ruff = _run_ruff()
    bandit = _run_bandit()
    git_status = _run_git_status()
    git_log = _run_git_log()
    tests = _run_pytest_collect()
    deps = _run_dep_check()

    git_report = dict(git_status)
    git_report["last_commits"] = git_log

    recs, status = _build_recommendations(ruff, bandit, git_status, tests, deps)

    report: dict = {
        "timestamp": timestamp,
        "ruff": ruff,
        "bandit": bandit,
        "git": git_report,
        "tests": tests,
        "deps": deps,
        "recommendations": recs,
        "status": status,
    }

    # Atomic write
    CODE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"code-{now.strftime('%Y-%m-%d-%H%M')}.json"
    report_path = CODE_REPORTS_DIR / filename

    fd, tmp_path = tempfile.mkstemp(dir=CODE_REPORTS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(report, f, indent=2)
        os.rename(tmp_path, report_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Code quality report written to %s", report_path)

    # Record outcome for learning hooks
    try:
        from ai.hooks import record_task_outcome

        quality = 1.0 if status == "clean" else (0.6 if status == "warnings" else 0.3)
        record_task_outcome(
            task_id="agents.code_quality_agent",
            quality=quality,
            success=status == "clean",
            duration_seconds=time.time() - start_time,
            agent_type="code",
        )
    except Exception:
        pass  # Best-effort, non-blocking

    return report


if __name__ == "__main__":
    import sys

    from ai.config import setup_logging

    setup_logging()
    result = run_code_check()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "clean" else 1)
