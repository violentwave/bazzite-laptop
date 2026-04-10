#!/usr/bin/env python3
"""
intel_scraper.py - Linux security system intelligence scraper.

Context: FastMCP bridge on port 8766, LanceDB at ~/security/vector-db/,
runtime JSON files at ~/security/, API keys in ~/.config/bazzite-ai/keys.env
"""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

import httpx


class IntelScraper:
    """Intelligence scraper for Linux security system."""

    def __init__(self):
        self.output_dir: Path | None = None
        self.state: dict = {}
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.github_token = ""
        self._load_keys()

    def _load_keys(self) -> None:
        """Read GITHUB_TOKEN from ~/.config/bazzite-ai/keys.env"""
        keys_file = Path.home() / ".config" / "bazzite-ai" / "keys.env"
        if keys_file.exists():
            with open(keys_file) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        key, _, value = line.partition("=")
                        if key.strip() == "GITHUB_TOKEN":
                            self.github_token = value.strip()
                            break

    def _load_state(self, output_dir: Path) -> dict:
        """Load state file tracking last_run per source."""
        state_file = output_dir / ".scraper_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {
            "github_releases": "1970-01-01T00:00:00Z",
            "cisa_kev": "1970-01-01T00:00:00Z",
            "nvd_cves": "1970-01-01T00:00:00Z",
            "fedora_rss": "1970-01-01T00:00:00Z",
        }

    def _save_state(self) -> None:
        """Save state with atomic write."""
        if not self.output_dir:
            return
        state_file = self.output_dir / ".scraper_state.json"
        tmp_file = state_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(self.state, f, indent=2)
        os.replace(tmp_file, state_file)

    def _atomic_write_jsonl(self, filepath: Path, items: list[dict]) -> None:
        """Atomically write items as JSONL (append mode, dedup by url/cve)."""
        # Read existing to dedup
        existing_ids = set()
        if filepath.exists():
            with open(filepath) as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        # Use url or cve as dedup key
                        key = item.get("url") or item.get("cve") or item.get("link")
                        if key:
                            existing_ids.add(key)
                    except json.JSONDecodeError:
                        pass

        # Filter new items
        new_items = []
        for item in items:
            key = item.get("url") or item.get("cve") or item.get("link")
            if key and key not in existing_ids:
                new_items.append(item)
                existing_ids.add(key)

        if not new_items:
            return

        # Atomic append
        tmp_file = filepath.with_suffix(".tmp")
        mode = "a" if filepath.exists() else "w"
        with open(tmp_file, mode) as f:
            for item in new_items:
                f.write(json.dumps(item) + "\n")
        os.replace(tmp_file, filepath)

    def scrape_github_releases(
        self,
        owner: str,
        repo: str,
        since_days: int = 7
    ) -> list[dict]:
        """
        GitHub API v3 - fetch releases for a repo.
        
        Returns list of dicts: {
            repo, tag, name, body[:1000], published_at, url, prerelease
        }
        """
        since = datetime.now(UTC) - timedelta(days=since_days)

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "intel-scraper/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        results = []

        try:
            response = self.client.get(url, headers=headers, params={"per_page": 30})
            response.raise_for_status()
            releases = response.json()

            for release in releases:
                published = release.get("published_at", "")
                if not published:
                    continue

                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_dt < since:
                    continue

                results.append({
                    "repo": f"{owner}/{repo}",
                    "tag": release.get("tag_name", ""),
                    "name": release.get("name", ""),
                    "body": release.get("body", "")[:1000],
                    "published_at": published,
                    "url": release.get("html_url", ""),
                    "prerelease": release.get("prerelease", False),
                })

            logging.info(f"Found {len(results)} releases for {owner}/{repo}")

        except Exception as e:
            logging.error(f"Error fetching {owner}/{repo} releases: {e}")
            # Graceful error - return empty list

        return results

    def scrape_cisa_kev(self, since_days: int = 3) -> list[dict]:
        """
        Fetch CISA Known Exploited Vulnerabilities catalog.
        
        Returns list of dicts: {
            cve, vendor, product, vulnerability, date_added, due_date
        }
        """
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        since = datetime.now(UTC) - timedelta(days=since_days)
        results = []

        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            for vuln in data.get("vulnerabilities", []):
                date_added = vuln.get("dateAdded", "")
                if not date_added:
                    continue

                # Parse date (YYYY-MM-DD format, no timezone)
                try:
                    add_dt = datetime.fromisoformat(date_added)
                    # Make it offset-naive for comparison with since
                    if since.tzinfo:
                        # Make since naive by removing tzinfo
                        since_naive = since.replace(tzinfo=None)
                    else:
                        since_naive = since

                    if add_dt < since_naive:
                        continue
                except ValueError:
                    continue

                results.append({
                    "cve": vuln.get("cveID", ""),
                    "vendor": vuln.get("vendorProject", ""),
                    "product": vuln.get("product", ""),
                    "vulnerability": vuln.get("vulnerabilityName", "")[:500],
                    "date_added": date_added,
                    "due_date": vuln.get("dateDue", ""),
                })

            logging.info(f"Found {len(results)} new KEV entries")

        except Exception as e:
            logging.error(f"Error fetching CISA KEV: {e}")

        return results

    def scrape_nvd_cves(
        self,
        keywords: list[str] | None = None,
        days: int = 7
    ) -> list[dict]:
        """
        NVD REST API 2.0 - search CVEs by keywords.
        
        Returns list of dicts: {
            cve, description[:500], published, cvss_score, severity
        }
        """
        if keywords is None:
            keywords = ["python", "linux", "fedora", "nvidia", "node", "npm"]

        since = datetime.now(UTC) - timedelta(days=days)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S")

        keyword_param = " ".join(keywords)
        url = (
            f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            f"?lastModStartDate={since_str}"
            f"&keywordSearch={keyword_param}"
            f"&resultsPerPage=20"
        )

        results = []

        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            for item in data.get("vulnerabilities", []):
                cve = item.get("cve", {})
                cve_id = cve.get("id", "")

                descriptions = cve.get("descriptions", [])
                desc = ""
                for d in descriptions:
                    if d.get("lang") == "en":
                        desc = d.get("value", "")
                        break

                metrics = cve.get("metrics", {})
                cvss = metrics.get("cvssMetricV31", [{}])[0] if metrics else None

                cvss_score = None
                severity = None
                if cvss:
                    cvss_data = cvss.get("cvssData", {})
                    cvss_score = cvss_data.get("baseScore")
                    severity = cvss_data.get("baseSeverity")

                published = cve.get("published", "")
                if not published:
                    continue

                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_dt < since:
                    continue

                results.append({
                    "cve": cve_id,
                    "description": desc[:500],
                    "published": published,
                    "cvss_score": cvss_score,
                    "severity": severity,
                })

            logging.info(f"Found {len(results)} new NVD CVEs")

        except Exception as e:
            logging.error(f"Error fetching NVD CVEs: {e}")

        return results

    def scrape_fedora_rss(self) -> list[dict]:
        """
        Fetch Fedora Bazzite community RSS feed.
        
        Returns list of dicts: {title, link, published, summary[:300]}
        """
        url = "https://discussion.fedoraproject.org/c/neighborhood/bazzite/77.rss"
        results = []

        try:
            response = self.client.get(url)
            response.raise_for_status()

            if HAS_FEEDPARSER:
                feed = feedparser.parse(response.text)
                for entry in feed.get("entries", []):
                    results.append({
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": entry.get("summary", "")[:300],
                    })
            else:
                # Fallback to xml.etree
                root = ET.fromstring(response.content)
                # RSS 2.0 namespace
                ns = {"content": "http://purl.org/rss/1.0/modules/content/"}

                for item in root.findall(".//item"):
                    title = item.findtext("title", default="", namespaces=ns)
                    link = item.findtext("link", default="", namespaces=ns)
                    pub_date = item.findtext("pubDate", default="", namespaces=ns)

                    # Get description/summary
                    desc = item.findtext("description", default="", namespaces=ns)
                    if not desc:
                        content = item.find(".//content:encoded", namespaces=ns)
                        if content is not None:
                            desc = content.text or ""

                    results.append({
                        "title": title,
                        "link": link,
                        "published": pub_date,
                        "summary": desc[:300],
                    })

            logging.info(f"Found {len(results)} Fedora RSS items")

        except Exception as e:
            logging.error(f"Error fetching Fedora RSS: {e}")

        return results

    def run_all(self, output_dir: str) -> dict:
        """
        Run all scrapers, save dated JSONL files.
        
        Saves to output_dir/{category}_{YYYY-MM-DD}.jsonl (append mode, dedup)
        Returns summary dict with counts per category.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_path
        self.state = self._load_state(output_path)

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        summary: dict[str, Any] = {
            "scraped_at": datetime.now(UTC).isoformat(),
            "files": {},
            "counts": {},
        }

        # Track errors per source (graceful handling)
        errors = []

        # 1. GitHub Releases
        repos_to_watch = [
            ("ublue-os", "bazzite"),
            ("BerriAI", "litellm"),
            ("modelcontextprotocol", "specification"),
            ("modelcontextprotocol", "python-sdk"),
        ]

        all_releases = []
        for owner, repo in repos_to_watch:
            try:
                releases = self.scrape_github_releases(owner, repo, since_days=7)
                all_releases.extend(releases)
            except Exception as e:
                errors.append(f"{owner}/{repo}: {e}")
                logging.error(f"Failed to scrape {owner}/{repo}: {e}")

        if all_releases:
            filepath = output_path / f"github_releases_{today}.jsonl"
            self._atomic_write_jsonl(filepath, all_releases)
            summary["files"]["github_releases"] = str(filepath)
            summary["counts"]["github_releases"] = len(all_releases)
            self.state["github_releases"] = datetime.now(UTC).isoformat()

        # 2. CISA KEV
        try:
            kev_entries = self.scrape_cisa_kev(since_days=3)
            if kev_entries:
                filepath = output_path / f"cisa_kev_{today}.jsonl"
                self._atomic_write_jsonl(filepath, kev_entries)
                summary["files"]["cisa_kev"] = str(filepath)
                summary["counts"]["cisa_kev"] = len(kev_entries)
                self.state["cisa_kev"] = datetime.now(UTC).isoformat()
        except Exception as e:
            errors.append(f"cisa_kev: {e}")
            logging.error(f"Failed to scrape CISA KEV: {e}")

        # 3. NVD CVEs
        try:
            cves = self.scrape_nvd_cves(
                keywords=["python", "linux", "fedora", "nvidia", "node", "npm"],
                days=7
            )
            if cves:
                filepath = output_path / f"nvd_cves_{today}.jsonl"
                self._atomic_write_jsonl(filepath, cves)
                summary["files"]["nvd_cves"] = str(filepath)
                summary["counts"]["nvd_cves"] = len(cves)
                self.state["nvd_cves"] = datetime.now(UTC).isoformat()
        except Exception as e:
            errors.append(f"nvd_cves: {e}")
            logging.error(f"Failed to scrape NVD CVEs: {e}")

        # 4. Fedora RSS
        try:
            rss_items = self.scrape_fedora_rss()
            if rss_items:
                filepath = output_path / f"fedora_rss_{today}.jsonl"
                self._atomic_write_jsonl(filepath, rss_items)
                summary["files"]["fedora_rss"] = str(filepath)
                summary["counts"]["fedora_rss"] = len(rss_items)
                self.state["fedora_rss"] = datetime.now(UTC).isoformat()
        except Exception as e:
            errors.append(f"fedora_rss: {e}")
            logging.error(f"Failed to scrape Fedora RSS: {e}")

        # Save state
        self._save_state()

        # Add errors to summary if any
        if errors:
            summary["errors"] = errors

        total = sum(summary["counts"].values())
        summary["total_new"] = total

        logging.info(f"Scrape complete: {total} total items")
        return summary


def main():
    parser = argparse.ArgumentParser(description="Intel Scraper for Bazzite security system")
    parser.add_argument("--output-dir", default="~/security/intel", help="Output directory")
    parser.add_argument("--source", choices=["github", "cisa", "nvd", "fedora"], help="Run only specific source")
    parser.add_argument("--dry-run", action="store_true", help="Print counts, don't write")

    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser()

    scraper = IntelScraper()

    if args.dry_run:
        # Just print counts without writing
        print("=== DRY RUN ===")
        repos = [
            ("ublue-os", "bazzite"),
            ("BerriAI", "litellm"),
            ("modelcontextprotocol", "specification"),
            ("modelcontextprotocol", "python-sdk"),
        ]

        total = 0
        for owner, repo in repos:
            releases = scraper.scrape_github_releases(owner, repo, since_days=7)
            print(f"GitHub {owner}/{repo}: {len(releases)} releases")
            total += len(releases)

        kev = scraper.scrape_cisa_kev(since_days=3)
        print(f"CISA KEV: {len(kev)} entries")
        total += len(kev)

        cves = scraper.scrape_nvd_cves(days=7)
        print(f"NVD CVEs: {len(cves)} entries")
        total += len(cves)

        rss = scraper.scrape_fedora_rss()
        print(f"Fedora RSS: {len(rss)} items")
        total += len(rss)

        print(f"\nTotal: {total} items (not written)")
        return

    if args.source:
        # Run specific source only
        output_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        if args.source == "github":
            for owner, repo in [
                ("ublue-os", "bazzite"),
                ("BerriAI", "litellm"),
                ("modelcontextprotocol", "specification"),
                ("modelcontextprotocol", "python-sdk"),
            ]:
                releases = scraper.scrape_github_releases(owner, repo)
                if releases:
                    filepath = output_dir / f"github_releases_{today}.jsonl"
                    scraper._atomic_write_jsonl(filepath, releases)
                    print(f"Wrote {len(releases)} releases for {owner}/{repo}")

        elif args.source == "cisa":
            kev = scraper.scrape_cisa_kev()
            if kev:
                filepath = output_dir / f"cisa_kev_{today}.jsonl"
                scraper._atomic_write_jsonl(filepath, kev)
                print(f"Wrote {len(kev)} KEV entries")

        elif args.source == "nvd":
            cves = scraper.scrape_nvd_cves()
            if cves:
                filepath = output_dir / f"nvd_cves_{today}.jsonl"
                scraper._atomic_write_jsonl(filepath, cves)
                print(f"Wrote {len(cves)} CVEs")

        elif args.source == "fedora":
            rss = scraper.scrape_fedora_rss()
            if rss:
                filepath = output_dir / f"fedora_rss_{today}.jsonl"
                scraper._atomic_write_jsonl(filepath, rss)
                print(f"Wrote {len(rss)} RSS items")
    else:
        # Run all
        summary = scraper.run_all(str(output_dir))
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
