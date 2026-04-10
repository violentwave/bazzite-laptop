#!/usr/bin/env python3
"""
Bazzite Intelligence Scraper - Multi-source data gathering for bazzite-laptop AI system.

Scrapes every 2 hours:
- GitHub: commits, PRs, issues, releases from violentwave/bazzite-laptop + upstreams
- Security: CVEs, threat intel feeds
- Tech: Bazzite updates, LiteLLM news, MCP protocol changes
- Dependencies: Security updates for pip/npm packages

Saves to ~/security/intel/ with auto-ingestion into LanceDB RAG.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

# Configuration
REPO_OWNER = "violentwave"
REPO_NAME = "bazzite-laptop"
UPSTREAM_REPOS = [
    ("ublue-os", "bazzite"),
    ("BerriAI", "litellm"),
    ("modelcontextprotocol", "specification"),
    ("modelcontextprotocol", "python-sdk"),
]
INTEL_DIR = Path.home() / "security" / "intel"
STATE_FILE = INTEL_DIR / ".scraper_state.json"
INGEST_FILE = INTEL_DIR / "ingest" / "pending_ingest.jsonl"
LOG_FILE = INTEL_DIR / ".scraper.log"

# GitHub API
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Feed URLs
FEEDS = {
    "cisa_kev": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    "nvd_recent": "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=20",
    "fedora_bazzite": "https://discussion.fedoraproject.org/c/neighborhood/bazzite/77.rss",
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bazzite-scraper")


class IntelScraper:
    """Main scraper class for all intelligence sources."""

    def __init__(self):
        self.state = self._load_state()
        self.new_data: dict[str, list[dict]] = {
            "github_commits": [],
            "github_prs": [],
            "github_issues": [],
            "github_releases": [],
            "security_cves": [],
            "tech_news": [],
        }
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "bazzite-intel-scraper/1.0",
        }
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {GITHUB_TOKEN}"

    def _load_state(self) -> dict:
        """Load last-run state to avoid re-fetching."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {
            "last_commit_sha": "",
            "last_pr_check": "1970-01-01T00:00:00Z",
            "last_issue_check": "1970-01-01T00:00:00Z",
            "last_cve_etag": "",
            "last_run": "1970-01-01T00:00:00Z",
        }

    def _save_state(self) -> None:
        """Save current state for next run."""
        self.state["last_run"] = datetime.now(UTC).isoformat()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _make_id(self, data: str) -> str:
        """Generate stable ID for deduplication."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _save_json(self, category: str, data: list[dict]) -> Path:
        """Save data to dated JSON file."""
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        dir_path = INTEL_DIR / category
        dir_path.mkdir(parents=True, exist_ok=True)
        filepath = dir_path / f"{category.split('/')[-1]}_{date_str}.json"

        # Merge with existing if same day
        if filepath.exists():
            with open(filepath) as f:
                existing = json.load(f)
            # Deduplicate by ID
            existing_ids = {self._make_id(json.dumps(e, sort_keys=True)) for e in existing}
            for item in data:
                item_id = self._make_id(json.dumps(item, sort_keys=True))
                if item_id not in existing_ids:
                    existing.append(item)
            data = existing

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(data)} items to {filepath}")
        return filepath

    def _append_ingest(self, items: list[dict], source: str) -> None:
        """Append items to ingestion queue for LanceDB."""
        INGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INGEST_FILE, "a") as f:
            for item in items:
                ingest_record = {
                    "source": source,
                    "scraped_at": datetime.now(UTC).isoformat(),
                    "data": item,
                    "text": self._extract_text(item, source),
                }
                f.write(json.dumps(ingest_record) + "\n")

    def _extract_text(self, item: dict, source: str) -> str:
        """Extract searchable text from item for embedding."""
        if "github" in source:
            parts = [
                item.get("title", ""),
                item.get("body", ""),
                item.get("message", ""),
            ]
            return " ".join(p for p in parts if p)[:2000]
        elif "cve" in source:
            return f"{item.get('id', '')} {item.get('description', '')}"[:2000]
        return json.dumps(item)[:2000]

    def scrape_github_commits(self) -> list[dict]:
        """Scrape new commits from main repo."""
        logger.info(f"Scraping commits from {REPO_OWNER}/{REPO_NAME}")

        url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/commits"
        params = {"sha": "master", "per_page": 30}
        if self.state.get("last_commit_sha"):
            params["since"] = self.state["last_run"]

        try:
            with httpx.Client(headers=self.headers, timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                commits = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch commits: {e}")
            return []

        new_commits = []
        for commit in commits:
            sha = commit.get("sha", "")
            if sha == self.state.get("last_commit_sha"):
                break

            new_commits.append({
                "sha": sha[:7],
                "message": commit.get("commit", {}).get("message", ""),
                "author": commit.get("commit", {}).get("author", {}).get("name", ""),
                "date": commit.get("commit", {}).get("author", {}).get("date", ""),
                "url": commit.get("html_url", ""),
                "type": "commit",
            })

        if new_commits:
            self.state["last_commit_sha"] = commits[0].get("sha", "")
            logger.info(f"Found {len(new_commits)} new commits")
            self.new_data["github_commits"].extend(new_commits)

        return new_commits

    def scrape_github_prs(self) -> list[dict]:
        """Scrape open and recently merged PRs."""
        logger.info(f"Scraping PRs from {REPO_OWNER}/{REPO_NAME}")

        url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
        params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 20}

        try:
            with httpx.Client(headers=self.headers, timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                prs = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch PRs: {e}")
            return []

        since = datetime.fromisoformat(self.state["last_pr_check"].replace("Z", "+00:00"))
        new_prs = []

        for pr in prs:
            updated = pr.get("updated_at", "1970-01-01T00:00:00Z")
            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if updated_dt > since:
                new_prs.append({
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "state": pr.get("state"),
                    "body": pr.get("body", "")[:500],
                    "author": pr.get("user", {}).get("login", ""),
                    "created_at": pr.get("created_at"),
                    "updated_at": updated,
                    "url": pr.get("html_url"),
                    "type": "pr",
                })

        self.state["last_pr_check"] = datetime.now(UTC).isoformat()
        if new_prs:
            logger.info(f"Found {len(new_prs)} updated PRs")
            self.new_data["github_prs"].extend(new_prs)

        return new_prs

    def scrape_github_issues(self) -> list[dict]:
        """Scrape issues with security/bug labels."""
        logger.info(f"Scraping issues from {REPO_OWNER}/{REPO_NAME}")

        url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/issues"
        params = {
            "state": "all",
            "labels": "security,bug,enhancement",
            "sort": "updated",
            "per_page": 20,
        }

        try:
            with httpx.Client(headers=self.headers, timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                issues = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch issues: {e}")
            return []

        since = datetime.fromisoformat(self.state["last_issue_check"].replace("Z", "+00:00"))
        new_issues = []

        for issue in issues:
            if "pull_request" in issue:
                continue
            updated = issue.get("updated_at", "1970-01-01T00:00:00Z")
            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if updated_dt > since:
                new_issues.append({
                    "number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "state": issue.get("state"),
                    "body": issue.get("body", "")[:500],
                    "labels": [l.get("name") for l in issue.get("labels", [])],
                    "author": issue.get("user", {}).get("login", ""),
                    "updated_at": updated,
                    "url": issue.get("html_url"),
                    "type": "issue",
                })

        self.state["last_issue_check"] = datetime.now(UTC).isoformat()
        if new_issues:
            logger.info(f"Found {len(new_issues)} updated issues")
            self.new_data["github_issues"].extend(new_issues)

        return new_issues

    def scrape_github_releases(self, owner: str, repo: str) -> list[dict]:
        """Scrape releases from a repo."""
        logger.info(f"Scraping releases from {owner}/{repo}")

        url = f"{GITHUB_API}/repos/{owner}/{repo}/releases"
        params = {"per_page": 5}

        try:
            with httpx.Client(headers=self.headers, timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                releases = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch releases: {e}")
            return []

        new_releases = []
        for release in releases:
            published = release.get("published_at", "1970-01-01T00:00:00Z")
            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if published_dt > datetime.now(UTC) - timedelta(days=7):
                new_releases.append({
                    "repo": f"{owner}/{repo}",
                    "tag": release.get("tag_name", ""),
                    "name": release.get("name", ""),
                    "body": release.get("body", "")[:1000],
                    "published_at": published,
                    "url": release.get("html_url", ""),
                    "prerelease": release.get("prerelease", False),
                    "type": "release",
                })

        if new_releases:
            logger.info(f"Found {len(new_releases)} recent releases from {owner}/{repo}")
            self.new_data["github_releases"].extend(new_releases)

        return new_releases

    def scrape_cisa_kev(self) -> list[dict]:
        """Scrape CISA Known Exploited Vulnerabilities."""
        logger.info("Scraping CISA KEV catalog")

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(FEEDS["cisa_kev"])
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch CISA KEV: {e}")
            return []

        vulns = data.get("vulnerabilities", [])
        since = datetime.fromisoformat(self.state["last_run"].replace("Z", "+00:00"))

        new_vulns = []
        for vuln in vulns:
            added = vuln.get("dateAdded", "1970-01-01")
            try:
                added_dt = datetime.strptime(added, "%Y-%m-%d").replace(tzinfo=UTC)
                if added_dt > since:
                    new_vulns.append({
                        "cve": vuln.get("cveID", ""),
                        "vendor": vuln.get("vendorProject", ""),
                        "product": vuln.get("product", ""),
                        "vulnerability": vuln.get("vulnerabilityName", ""),
                        "date_added": added,
                        "due_date": vuln.get("dueDate", ""),
                        "type": "cisa_kev",
                    })
            except ValueError:
                continue

        new_vulns = sorted(new_vulns, key=lambda x: x["date_added"], reverse=True)[:10]

        if new_vulns:
            logger.info(f"Found {len(new_vulns)} new KEV entries")
            self.new_data["security_cves"].extend(new_vulns)

        return new_vulns

    def scrape_nvd_cves(self) -> list[dict]:
        """Scrape recent CVEs from NVD."""
        logger.info("Scraping NVD recent CVEs")

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=7)
        params = {
            "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "pubEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "resultsPerPage": 20,
        }

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(FEEDS["nvd_recent"], params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch NVD: {e}")
            return []

        cves = []
        for item in data.get("vulnerabilities", []):
            cve = item.get("cve", {})
            cve_id = cve.get("id", "")

            descriptions = cve.get("descriptions", [])
            desc = ""
            for d in descriptions:
                if d.get("lang") == "en":
                    desc = d.get("value", "")
                    break

            keywords = ["python", "node", "npm", "pip", "linux", "fedora", "cuda", "nvidia"]
            if any(kw in desc.lower() for kw in keywords):
                cves.append({
                    "cve": cve_id,
                    "description": desc[:500],
                    "published": cve.get("published", ""),
                    "type": "nvd_cve",
                })

        if cves:
            logger.info(f"Found {len(cves)} relevant CVEs")
            self.new_data["security_cves"].extend(cves)

        return cves

    def run_all(self) -> dict:
        """Execute full scrape cycle."""
        logger.info("=== Starting Bazzite Intel Scrape ===")

        self.scrape_github_commits()
        self.scrape_github_prs()
        self.scrape_github_issues()

        self.scrape_github_releases("ublue-os", "bazzite")
        self.scrape_github_releases("BerriAI", "litellm")
        self.scrape_github_releases("modelcontextprotocol", "specification")

        self.scrape_cisa_kev()
        self.scrape_nvd_cves()

        saved_files = {}
        for category, items in self.new_data.items():
            if items:
                if category == "github_releases":
                    saved_files[category] = self._save_json("github/releases", items)
                elif category == "security_cves":
                    saved_files[category] = self._save_json("security", items)
                else:
                    saved_files[category] = self._save_json(f"github/{category.split('_')[-1]}", items)
                self._append_ingest(items, category)

        self._save_state()

        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "files_saved": {k: str(v) for k, v in saved_files.items()},
            "counts": {k: len(v) for k, v in self.new_data.items() if v},
            "total_new": sum(len(v) for v in self.new_data.values()),
        }

        logger.info(f"=== Scrape Complete: {summary['total_new']} new items ===")
        return summary


def main():
    parser = argparse.ArgumentParser(description="Bazzite Intel Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Don't save state")
    parser.add_argument("--github-only", action="store_true", help="Only scrape GitHub")
    parser.add_argument("--security-only", action="store_true", help="Only scrape security feeds")
    args = parser.parse_args()

    scraper = IntelScraper()

    if args.github_only:
        scraper.scrape_github_commits()
        scraper.scrape_github_prs()
        scraper.scrape_github_issues()
        scraper.scrape_github_releases("ublue-os", "bazzite")
    elif args.security_only:
        scraper.scrape_cisa_kev()
        scraper.scrape_nvd_cves()
    else:
        summary = scraper.run_all()
        print(json.dumps(summary, indent=2))

    if not args.dry_run:
        scraper._save_state()


if __name__ == "__main__":
    main()
