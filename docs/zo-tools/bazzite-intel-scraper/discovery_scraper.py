#!/usr/bin/env python3
"""
Bazzite Discovery Scraper - Finds free APIs, optimized alternatives, and system improvements.

Runs every 6 hours to discover:
- Free LLM APIs and new provider tiers
- Lightweight alternatives to current dependencies  
- Better database/vector store options
- Security tools that integrate with threat intel
- AI/ML libraries for capability expansion
- Optimization opportunities for the bazzite-laptop system

Saves to ~/security/discovery/ with actionable recommendations.
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

# Configuration
DISCOVERY_DIR = Path.home() / "security" / "discovery"
REPORTS_DIR = DISCOVERY_DIR / "reports"
RAW_DIR = DISCOVERY_DIR / "raw"
LOG_FILE = DISCOVERY_DIR / ".discovery.log"

# GitHub search queries for relevant repos
REPO_QUERIES = {
    "vector_databases": [
        "vector database embedded python stars:>1000",
        "embedding database lightweight rust",
        "vector search engine open source",
    ],
    "llm_providers": [
        "free llm api provider",
        "openai alternative free tier",
        "local llm inference fast",
    ],
    "security_tools": [
        "threat intelligence api free",
        "security monitoring lightweight",
        "malware analysis python",
        "cve tracking open source",
    ],
    "mcp_tools": [
        "model context protocol server",
        "mcp bridge tools",
        "claude code tools open source",
    ],
    "optimization": [
        "lightweight python http client",
        "fastapi alternative minimal",
        "embedded database python",
        "async task queue lightweight",
    ],
    "ai_capabilities": [
        "rag framework python",
        "agent framework minimal",
        "function calling llm",
        "knowledge graph python",
    ],
}

# Hacker News/Reddit/Lobsters for trending
NEWS_SOURCES = {
    "hackernews": "https://hn.algolia.com/api/v1/search?tags=ask_hn,show_hn&query=free+AI+API",
    "github_trending_python": "https://github.com/trending/python?since=daily",
    "github_trending_rust": "https://github.com/trending/rust?since=daily",
}

# Current bazzite system dependencies to find alternatives for
CURRENT_DEPS = {
    "databases": ["lancedb", "sqlite3"],
    "http_clients": ["httpx", "requests"],
    "llm_routing": ["litellm"],
    "vector_search": ["lancedb"],
    "web_scraping": ["feedparser", "beautifulsoup4"],
    "security_intel": ["custom"],
    "async": ["asyncio", "aiohttp"],
    "testing": ["pytest"],
    "linting": ["ruff", "bandit"],
}

@dataclass
class DiscoveryItem:
    source: str
    category: str
    title: str
    url: str
    description: str
    discovered_at: str
    relevance_score: int  # 1-10
    action_type: str  # "integrate", "research", "monitor", "replace"
    potential_benefit: str
    current_alternative: str | None
    free_tier: bool | None
    license: str | None
    stars: int | None
    language: str | None
    
    def to_dict(self) -> dict:
        return asdict(self)

class DiscoveryScraper:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.discovered: list[DiscoveryItem] = []
        self.session = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Bazzite-Discovery-Scraper/1.0"},
        )
        
        # Load GitHub token if available
        self.github_token = self._load_github_token()
        if self.github_token:
            self.session.headers["Authorization"] = f"token {self.github_token}"
    
    def _load_github_token(self) -> str | None:
        try:
            keys_file = Path.home() / ".config" / "bazzite-ai" / "keys.env"
            if keys_file.exists():
                content = keys_file.read_text()
                for line in content.split("\n"):
                    if line.startswith("GITHUB_TOKEN="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception as e:
            logging.warning(f"Could not load GitHub token: {e}")
        return None
    
    def setup_dirs(self) -> None:
        """Ensure directory structure exists."""
        DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    def github_search(self, query: str, category: str) -> list[DiscoveryItem]:
        """Search GitHub for repositories."""
        items = []
        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            }
            resp = self.session.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for repo in data.get("items", [])[:5]:  # Top 5
                    # Determine action type based on category
                    action = "research"
                    if "optimization" in category or "lightweight" in query:
                        action = "replace"
                    elif "mcp" in category or "security" in category:
                        action = "integrate"
                    
                    # Calculate relevance score
                    score = min(10, int(repo.get("stargazers_count", 0) / 500) + 5)
                    if repo.get("topics") and any(t in ["security", "ai", "mcp", "llm"] for t in repo["topics"]):
                        score += 1
                    
                    item = DiscoveryItem(
                        source="github",
                        category=category,
                        title=repo.get("full_name", ""),
                        url=repo.get("html_url", ""),
                        description=repo.get("description", "") or "",
                        discovered_at=datetime.now(UTC).isoformat(),
                        relevance_score=min(10, score),
                        action_type=action,
                        potential_benefit=self._infer_benefit(category, repo),
                        current_alternative=self._find_current_alternative(category),
                        free_tier=True,  # Open source
                        license=repo.get("license", {}).get("spdx_id") if repo.get("license") else None,
                        stars=repo.get("stargazers_count"),
                        language=repo.get("language"),
                    )
                    items.append(item)
                    
        except Exception as e:
            logging.error(f"GitHub search failed for '{query}': {e}")
        
        return items
    
    def _infer_benefit(self, category: str, repo: dict) -> str:
        """Infer potential benefit from category and description."""
        desc = (repo.get("description", "") or "").lower()
        
        benefits = {
            "vector_databases": "Better vector search or smaller footprint than LanceDB",
            "llm_providers": "Additional free LLM tier or better routing",
            "security_tools": "Enhanced threat intel or monitoring capabilities",
            "mcp_tools": "Additional MCP tools for Claude Code integration",
            "optimization": "Reduced memory/CPU footprint or faster execution",
            "ai_capabilities": "New AI features: agents, RAG, knowledge graphs",
        }
        
        base = benefits.get(category, "Potential system improvement")
        
        # Refine based on keywords
        if "fast" in desc or "performance" in desc:
            base += "; PERFORMANCE BOOST"
        if "lightweight" in desc or "minimal" in desc:
            base += "; REDUCED FOOTPRINT"
        if "async" in desc:
            base += "; BETTER CONCURRENCY"
        if "embedded" in desc:
            base += "; NO EXTERNAL DEPENDENCIES"
            
        return base
    
    def _find_current_alternative(self, category: str) -> str | None:
        """Map category to current system component."""
        mapping = {
            "vector_databases": "lancedb",
            "llm_providers": "litellm + current providers",
            "security_tools": "custom threat_intel module",
            "mcp_tools": "existing 79 MCP tools",
            "optimization": "various current dependencies",
            "ai_capabilities": "current RAG + router",
        }
        return mapping.get(category)
    
    def search_free_llm_apis(self) -> list[DiscoveryItem]:
        """Search for free LLM APIs and tiers."""
        items = []
        
        # Known free tier providers to check for updates
        free_providers = [
            ("OpenRouter", "https://openrouter.ai/docs", "Free tier with rate limits"),
            ("Groq", "https://console.groq.com", "Free tier available"),
            ("Cerebras", "https://cerebras.ai", "Free tier for inference"),
            ("Gemini API", "https://ai.google.dev", "Free tier generous"),
            ("Mistral", "https://console.mistral.ai", "Free tier for testing"),
            ("Together AI", "https://together.xyz", "Free credits available"),
            ("Fireworks", "https://fireworks.ai", "Trial credits"),
        ]
        
        # Also search GitHub for "free LLM API" projects
        for query in REPO_QUERIES["llm_providers"]:
            items.extend(self.github_search(query, "llm_providers"))
        
        return items
    
    def search_optimization_opportunities(self) -> list[DiscoveryItem]:
        """Find lighter alternatives to current dependencies."""
        items = []
        
        for query in REPO_QUERIES["optimization"]:
            items.extend(self.github_search(query, "optimization"))
        
        # Specific searches for bazzite's needs
        lightweight_searches = [
            ("sqlite alternative embedded rust", "database"),
            ("http client rust python bindings", "http"),
            ("json parser simd", "parsing"),
            ("task queue minimal python", "queue"),
        ]
        
        for query, subcat in lightweight_searches:
            found = self.github_search(query, f"optimization_{subcat}")
            for item in found:
                item.potential_benefit = f"Replace {subcat} stack; REDUCED FOOTPRINT"
            items.extend(found)
        
        return items
    
    def search_database_improvements(self) -> list[DiscoveryItem]:
        """Find better vector database and storage options."""
        items = []
        
        for query in REPO_QUERIES["vector_databases"]:
            items.extend(self.github_search(query, "vector_databases"))
        
        # Specific vector DB comparison
        vector_dbs = [
            "chromadb",
            "qdrant",
            "weaviate",
            "milvus",
            "pgvector",
            "sqlite-vss",
        ]
        
        for db in vector_dbs:
            found = self.github_search(f"{db} vector database", "vector_databases")
            items.extend(found)
        
        return items
    
    def search_security_enhancements(self) -> list[DiscoveryItem]:
        """Find security tools that integrate with threat intel."""
        items = []
        
        for query in REPO_QUERIES["security_tools"]:
            items.extend(self.github_search(query, "security_tools"))
        
        # Specific security integrations
        security_searches = [
            "yara rules python",
            "sigma rules detection",
            "osquery python",
            "velociraptor client",
            "sysmon rust",
        ]
        
        for query in security_searches:
            found = self.github_search(query, "security_tools")
            for item in found:
                item.potential_benefit = "Enhanced endpoint monitoring + threat detection"
            items.extend(found)
        
        return items
    
    def search_mcp_expansions(self) -> list[DiscoveryItem]:
        """Find MCP servers and tools to expand beyond current 79."""
        items = []
        
        for query in REPO_QUERIES["mcp_tools"]:
            items.extend(self.github_search(query, "mcp_tools"))
        
        # Check modelcontextprotocol GitHub org
        try:
            url = "https://api.github.com/users/modelcontextprotocol/repos"
            resp = self.session.get(url, params={"per_page": 100})
            if resp.status_code == 200:
                repos = resp.json()
                for repo in repos[:20]:
                    item = DiscoveryItem(
                        source="github",
                        category="mcp_tools",
                        title=f"modelcontextprotocol/{repo['name']}",
                        url=repo["html_url"],
                        description=repo.get("description", ""),
                        discovered_at=datetime.now(UTC).isoformat(),
                        relevance_score=8 if "server" in repo["name"] else 6,
                        action_type="integrate",
                        potential_benefit="Official MCP server - direct integration",
                        current_alternative="existing MCP bridge tools",
                        free_tier=True,
                        license=repo.get("license", {}).get("spdx_id"),
                        stars=repo.get("stargazers_count"),
                        language=repo.get("language"),
                    )
                    items.append(item)
        except Exception as e:
            logging.error(f"MCP org search failed: {e}")
        
        return items
    
    def search_ai_capability_expansions(self) -> list[DiscoveryItem]:
        """Find AI/ML libraries to expand system intelligence."""
        items = []
        
        for query in REPO_QUERIES["ai_capabilities"]:
            items.extend(self.github_search(query, "ai_capabilities"))
        
        # Specific capability searches
        capability_searches = [
            ("graphrag microsoft", "knowledge graphs"),
            ("langgraph agent framework", "agent orchestration"),
            ("mem0 memory ai", "persistent memory"),
            ("haystack rag", "RAG improvements"),
            ("semantic cache llm", "caching"),
        ]
        
        for query, capability in capability_searches:
            found = self.github_search(query, "ai_capabilities")
            for item in found:
                item.potential_benefit = f"{capability.upper()} - expand system intelligence"
            items.extend(found)
        
        return items
    
    def generate_report(self) -> dict:
        """Generate actionable discovery report."""
        # Group by action type
        by_action = defaultdict(list)
        for item in self.discovered:
            by_action[item.action_type].append(item)
        
        # Group by category
        by_category = defaultdict(list)
        for item in self.discovered:
            by_category[item.category].append(item)
        
        # Top recommendations (score >= 8)
        top_picks = [item for item in self.discovered if item.relevance_score >= 8]
        top_picks.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Free APIs summary
        free_apis = [item for item in self.discovered 
                     if item.free_tier and item.category in ["llm_providers", "mcp_tools"]]
        
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_discovered": len(self.discovered),
                "top_recommendations": len(top_picks[:10]),
                "free_apis_found": len(free_apis),
                "integration_candidates": len(by_action["integrate"]),
                "replacement_candidates": len(by_action["replace"]),
                "research_candidates": len(by_action["research"]),
            },
            "top_recommendations": [item.to_dict() for item in top_picks[:10]],
            "free_apis_and_services": [item.to_dict() for item in free_apis[:15]],
            "by_action_type": {
                k: [item.to_dict() for item in v[:10]] 
                for k, v in by_action.items()
            },
            "by_category": {
                k: [item.to_dict() for item in v[:10]]
                for k, v in by_category.items()
            },
            "current_system_alternatives": self._generate_alternative_matrix(),
        }
        
        return report
    
    def _generate_alternative_matrix(self) -> dict:
        """Map current dependencies to discovered alternatives."""
        matrix = {}
        
        for category, current_deps in CURRENT_DEPS.items():
            alternatives = []
            for item in self.discovered:
                if item.current_alternative and any(dep.lower() in item.current_alternative.lower() 
                                                    for dep in current_deps):
                    alternatives.append({
                        "current": item.current_alternative,
                        "alternative": item.title,
                        "url": item.url,
                        "benefit": item.potential_benefit,
                        "score": item.relevance_score,
                    })
            matrix[category] = {
                "current": current_deps,
                "alternatives": alternatives[:5],
            }
        
        return matrix
    
    def save_results(self) -> None:
        """Save raw data and generated report."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        
        # Save all discovered items as JSONL
        raw_file = RAW_DIR / f"discovery_{timestamp}.jsonl"
        with open(raw_file, "w") as f:
            for item in self.discovered:
                f.write(json.dumps(item.to_dict()) + "\n")
        
        # Save report
        report = self.generate_report()
        report_file = REPORTS_DIR / f"report_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        # Save latest report as symlink
        latest = REPORTS_DIR / "latest.json"
        if latest.exists():
            latest.unlink()
        latest.symlink_to(report_file.name)
        
        logging.info(f"Saved {len(self.discovered)} items to {raw_file}")
        logging.info(f"Saved report to {report_file}")
        
        # Print summary to stdout
        print(f"\n{'='*60}")
        print(f"DISCOVERY REPORT - {timestamp}")
        print(f"{'='*60}")
        print(f"Total discovered: {report['summary']['total_discovered']}")
        print(f"Top recommendations: {report['summary']['top_recommendations']}")
        print(f"Free APIs found: {report['summary']['free_apis_found']}")
        print(f"\nTop 5 Picks:")
        for i, item in enumerate(report['top_recommendations'][:5], 1):
            print(f"  {i}. [{item['relevance_score']}/10] {item['title']}")
            print(f"     Action: {item['action_type']} | {item['potential_benefit'][:60]}...")
        print(f"\nSaved to: {report_file}")
    
    def run(self) -> None:
        """Execute full discovery scrape."""
        logging.info("=== Starting Bazzite Discovery Scrape ===")
        
        self.setup_dirs()
        
        # Run all discovery searches
        logging.info("Searching for free LLM APIs...")
        self.discovered.extend(self.search_free_llm_apis())
        time.sleep(2)  # Rate limit courtesy
        
        logging.info("Searching for optimization opportunities...")
        self.discovered.extend(self.search_optimization_opportunities())
        time.sleep(2)
        
        logging.info("Searching for database improvements...")
        self.discovered.extend(self.search_database_improvements())
        time.sleep(2)
        
        logging.info("Searching for security enhancements...")
        self.discovered.extend(self.search_security_enhancements())
        time.sleep(2)
        
        logging.info("Searching for MCP expansions...")
        self.discovered.extend(self.search_mcp_expansions())
        time.sleep(2)
        
        logging.info("Searching for AI capability expansions...")
        self.discovered.extend(self.search_ai_capability_expansions())
        
        # Deduplicate by URL
        seen = set()
        unique = []
        for item in self.discovered:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
        self.discovered = unique
        
        logging.info(f"Total unique discoveries: {len(self.discovered)}")
        
        if not self.dry_run:
            self.save_results()
        else:
            # Print preview
            print(f"\nDRY RUN - Would save {len(self.discovered)} items")
            for item in self.discovered[:5]:
                print(f"  - {item.title} ({item.relevance_score}/10)")
        
        logging.info("=== Discovery Scrape Complete ===")

def main():
    parser = argparse.ArgumentParser(description="Bazzite Discovery Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--category", type=str, help="Run single category only")
    args = parser.parse_args()
    
    # Setup logging
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    scraper = DiscoveryScraper(dry_run=args.dry_run)
    
    if args.category:
        # Run single category
        method = getattr(scraper, f"search_{args.category}", None)
        if method:
            scraper.setup_dirs()
            scraper.discovered = method()
            if not args.dry_run:
                scraper.save_results()
        else:
            print(f"Unknown category: {args.category}")
            sys.exit(1)
    else:
        scraper.run()

if __name__ == "__main__":
    main()
