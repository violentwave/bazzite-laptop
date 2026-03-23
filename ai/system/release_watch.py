"""Release watch — upstream dependency monitoring via GitHub.

Checks each watched repository for new releases and GHSA advisories.
Writes ~/security/release-watch.json with update_available flags.

Usage:
    python -m ai.system.release_watch [--check] [--repo owner/repo]
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime

import requests

from ai.config import APP_NAME, SECURITY_DIR, get_key, load_keys, setup_logging
from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Constants ─────────────────────────────────────────────────────────────────

RELEASE_WATCH_PATH = SECURITY_DIR / "release-watch.json"
_GH_BASE = "https://api.github.com"

WATCHED_REPOS = [
    "ublue-os/bazzite",
    "ollama/ollama",
    "python/cpython",
    "nodejs/node",
    "astral-sh/uv",
    "astral-sh/ruff",
    "lancedb/lancedb",
    "BerriAI/litellm",
    "jdx/mise",
    "FiloSottile/age",
    "getsops/sops",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _gh_headers() -> dict[str, str]:
    """Build GitHub API headers, adding auth if GITHUB_TOKEN is set."""
    token = get_key("GITHUB_TOKEN")
    hdrs = {"Accept": "application/vnd.github+json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    return hdrs


def _fetch_latest_release(
    repo: str,
    rate_limiter: RateLimiter,
) -> dict | None:
    """Fetch latest release for a repo. Returns None on error or rate-limit."""
    if not rate_limiter.can_call("github_releases"):
        logger.info("GitHub rate limited, skipping %s", repo)
        return None

    url = f"{_GH_BASE}/repos/{repo}/releases/latest"
    try:
        resp = requests.get(url, headers=_gh_headers(), timeout=15)
        rate_limiter.record_call("github_releases")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("GitHub release fetch failed for %s: %s", repo, e)
        return None

    return {
        "tag_name": data.get("tag_name", ""),
        "published_at": (data.get("published_at") or "")[:10],  # date only
        "html_url": data.get("html_url", ""),
        "summary": (data.get("body") or "")[:200],
    }


def _fetch_advisories(repo: str, rate_limiter: RateLimiter) -> int:
    """Return count of public security advisories for repo, 0 on error."""
    if not rate_limiter.can_call("github_releases"):
        return 0

    url = f"{_GH_BASE}/repos/{repo}/security-advisories"
    try:
        resp = requests.get(url, headers=_gh_headers(), timeout=15)
        rate_limiter.record_call("github_releases")
        if resp.status_code in (404, 403):
            return 0
        resp.raise_for_status()
        data = resp.json()
        return len(data) if isinstance(data, list) else 0
    except requests.RequestException:
        return 0


def _load_cache() -> dict:
    """Load existing release-watch.json, return empty dict on failure."""
    try:
        if RELEASE_WATCH_PATH.exists():
            return json.loads(RELEASE_WATCH_PATH.read_text()).get("repos", {})
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _write_report(repos: dict) -> None:
    """Atomic write to ~/security/release-watch.json."""
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "checked_at": datetime.now(tz=UTC).isoformat(),
        "repos": repos,
    }
    tmp = RELEASE_WATCH_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(RELEASE_WATCH_PATH)


# ── Orchestration ─────────────────────────────────────────────────────────────


def check_releases(
    repos: list[str] | None = None,
    rate_limiter: RateLimiter | None = None,
) -> dict:
    """Check GitHub for new releases of watched repositories.

    Args:
        repos: List of 'owner/repo' strings. Defaults to WATCHED_REPOS.
        rate_limiter: Injectable RateLimiter; defaults to shared instance.

    Returns:
        Dict with checked_at and repos map.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    if repos is None:
        repos = WATCHED_REPOS

    cached = _load_cache()
    result: dict[str, dict] = {}

    for repo in repos:
        release = _fetch_latest_release(repo, rate_limiter)
        if release is None:
            # Preserve previous data if available, skip silently otherwise
            if repo in cached:
                result[repo] = cached[repo]
            continue

        prev_tag = cached.get(repo, {}).get("latest", "")
        update_available = bool(prev_tag) and prev_tag != release["tag_name"]

        advisory_count = _fetch_advisories(repo, rate_limiter)

        result[repo] = {
            "latest": release["tag_name"],
            "published": release["published_at"],
            "url": release["html_url"],
            "summary": release["summary"],
            "update_available": update_available,
            "advisory_count": advisory_count,
        }

    _write_report(result)
    updates = sum(1 for v in result.values() if v.get("update_available"))
    return {
        "checked_at": datetime.now(tz=UTC).isoformat(),
        "repos_checked": len(result),
        "updates_available": updates,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for release watching."""
    parser = argparse.ArgumentParser(
        description="Check GitHub releases for watched dependencies"
    )
    parser.add_argument(
        "--check", action="store_true", help="Run release check (default action)"
    )
    parser.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        help="Check a single repo instead of the full list",
    )
    args = parser.parse_args()

    load_keys()
    setup_logging()

    repos = [args.repo] if args.repo else None
    summary = check_releases(repos=repos)
    print(json.dumps(summary, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
