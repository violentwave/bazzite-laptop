#!/usr/bin/env python3
"""
Bazzite Performance Profiler

Monitors system resources, LLM costs, API rate limits, and database performance
for the bazzite-laptop AI infrastructure.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

METRICS_DIR = Path.home() / "security" / "metrics"
LOG_FILE = METRICS_DIR / ".profiler.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_used_gb: float
    disk_total_gb: float
    load_average: tuple[float, float, float]


@dataclass
class ProcessMetrics:
    name: str
    pid: int
    cpu_percent: float
    memory_percent: float
    memory_mb: float


@dataclass
class LLMProviderMetrics:
    name: str
    tokens_24h: int = 0
    cost_24h: float = 0.0
    rate_limit_remaining: int | None = None
    rate_limit_reset: str | None = None
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0


@dataclass
class DatabaseMetrics:
    lancedb_path: str
    size_mb: float
    table_counts: dict[str, int] = field(default_factory=dict)
    last_query_time_ms: float = 0.0


@dataclass
class TimerMetrics:
    name: str
    last_execution: str
    next_execution: str
    lag_minutes: float
    status: str


@dataclass
class ProfileResult:
    timestamp: str
    system: SystemMetrics | None = None
    processes: list[ProcessMetrics] = field(default_factory=list)
    llm_providers: list[LLMProviderMetrics] = field(default_factory=list)
    database: DatabaseMetrics | None = None
    timers: list[TimerMetrics] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)


class PerformanceProfiler:
    # Process names to monitor
    MONITORED_PROCESSES = [
        "mcp-bridge",
        "litellm-router",
        "python.*scraper",
        "python.*agent",
        "lancedb",
    ]

    # LLM providers with pricing (per 1M tokens)
    PROVIDER_PRICING = {
        "gemini": {"input": 0.075, "output": 0.30},  # Flash pricing
        "groq": {"input": 0.59, "output": 0.79},    # Mixtral 8x7B
        "mistral": {"input": 0.60, "output": 0.60},
        "openrouter": {"input": 0.50, "output": 0.50},  # Approximate
        "zai": {"input": 0.0, "output": 0.0},        # Own model
        "cerebras": {"input": 0.60, "output": 0.60},
    }

    def __init__(self):
        self.result = ProfileResult(
            timestamp=datetime.now(UTC).isoformat()
        )
        self.alerts: list[str] = []

    def profile(self) -> ProfileResult:
        """Run complete system profile."""
        logger.info("Starting performance profile")

        self._collect_system_metrics()
        self._collect_process_metrics()
        self._collect_llm_metrics()
        self._collect_database_metrics()
        self._collect_timer_metrics()
        self._check_thresholds()

        self.result.alerts = self.alerts
        return self.result

    def _collect_system_metrics(self):
        """Collect overall system metrics."""
        if not HAS_PSUTIL:
            logger.warning("psutil not available, skipping system metrics")
            return

        try:
            vm = psutil.virtual_memory()
            du = psutil.disk_usage("/")
            load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

            self.result.system = SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=vm.percent,
                memory_used_gb=vm.used / (1024**3),
                memory_total_gb=vm.total / (1024**3),
                disk_used_gb=du.used / (1024**3),
                disk_total_gb=du.total / (1024**3),
                load_average=load,
            )
            logger.info(f"System: {self.result.system.cpu_percent:.1f}% CPU, "
                       f"{self.result.system.memory_percent:.1f}% RAM")
        except Exception as e:
            logger.error(f"System metrics failed: {e}")

    def _collect_process_metrics(self):
        """Collect metrics for monitored processes."""
        if not HAS_PSUTIL:
            return

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    name = proc.info['name']
                    # Check if matches any monitored pattern
                    for pattern in self.MONITORED_PROCESSES:
                        if re.search(pattern, name, re.IGNORECASE):
                            mem_mb = proc.info['memory_info'].rss / (1024**2) if proc.info['memory_info'] else 0
                            self.result.processes.append(ProcessMetrics(
                                name=name,
                                pid=proc.info['pid'],
                                cpu_percent=proc.info['cpu_percent'] or 0.0,
                                memory_percent=proc.info['memory_percent'] or 0.0,
                                memory_mb=mem_mb,
                            ))
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            logger.info(f"Found {len(self.result.processes)} monitored processes")
        except Exception as e:
            logger.error(f"Process metrics failed: {e}")

    def _collect_llm_metrics(self):
        """Collect LLM provider usage and rate limits."""
        # Estimate from router.py cache/logs
        cache_dir = Path.home() / ".bazzite-ai" / "llm-cache"

        # Default metrics for each provider
        for provider in ["gemini", "groq", "mistral", "openrouter", "zai", "cerebras"]:
            metrics = LLMProviderMetrics(name=provider)

            # Try to estimate from cache size
            provider_cache = cache_dir / provider
            if provider_cache.exists():
                size = sum(f.stat().st_size for f in provider_cache.rglob('*') if f.is_file())
                # Rough estimate: 4 chars ~= 1 token
                estimated_tokens = size // 4
                metrics.tokens_24h = estimated_tokens

                # Estimate cost
                pricing = self.PROVIDER_PRICING.get(provider, {"input": 0, "output": 0})
                avg_price = (pricing["input"] + pricing["output"]) / 2
                metrics.cost_24h = (estimated_tokens / 1_000_000) * avg_price

            # Read rate limits from cache metadata
            meta_file = cache_dir / f"{provider}_meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    metrics.rate_limit_remaining = meta.get("remaining")
                    metrics.rate_limit_reset = meta.get("reset")
                except json.JSONDecodeError:
                    pass

            self.result.llm_providers.append(metrics)

        logger.info(f"LLM: tracked {len(self.result.llm_providers)} providers")

    def _collect_database_metrics(self):
        """Collect LanceDB database metrics."""
        db_path = Path.home() / ".bazzite-ai" / "lancedb"

        if not db_path.exists():
            # Try alternative location
            db_path = Path.home() / ".local" / "share" / "bazzite-ai" / "lancedb"

        if db_path.exists():
            try:
                # Calculate size
                size_bytes = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file())
                size_mb = size_bytes / (1024**2)

                # Try to get table counts
                table_counts = {}
                for table_dir in db_path.iterdir():
                    if table_dir.is_dir():
                        # Count .lance files as proxy for rows
                        lance_files = list(table_dir.glob("*.lance"))
                        table_counts[table_dir.name] = len(lance_files)

                self.result.database = DatabaseMetrics(
                    lancedb_path=str(db_path),
                    size_mb=size_mb,
                    table_counts=table_counts,
                )
                logger.info(f"Database: {size_mb:.1f} MB, {len(table_counts)} tables")
            except Exception as e:
                logger.error(f"Database metrics failed: {e}")

    def _collect_timer_metrics(self):
        """Collect systemd timer status."""
        try:
            result = subprocess.run(
                ["systemctl", "list-timers", "--all", "--no-pager", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                # Try without JSON (older systemctl)
                result = subprocess.run(
                    ["systemctl", "list-timers", "--all", "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                # Parse text output
                for line in result.stdout.splitlines()[1:]:  # Skip header
                    if line.strip() and not line.startswith("-"):
                        parts = line.split()
                        if len(parts) >= 5:
                            self.result.timers.append(TimerMetrics(
                                name=parts[-1],
                                last_execution=parts[0],
                                next_execution=parts[1],
                                lag_minutes=0.0,
                                status="unknown",
                            ))
            else:
                # Parse JSON output
                try:
                    timers = json.loads(result.stdout)
                    for t in timers:
                        self.result.timers.append(TimerMetrics(
                            name=t.get("unit", "unknown"),
                            last_execution=t.get("last", ""),
                            next_execution=t.get("next", ""),
                            lag_minutes=0.0,
                            status=t.get("state", "unknown"),
                        ))
                except json.JSONDecodeError:
                    pass

            logger.info(f"Timers: tracked {len(self.result.timers)} systemd timers")
        except Exception as e:
            logger.warning(f"Timer metrics unavailable (systemctl): {e}")

    def _check_thresholds(self):
        """Check metric thresholds and generate alerts."""
        if self.result.system:
            sys = self.result.system

            if sys.cpu_percent > 80:
                self.alerts.append(f"HIGH_CPU: {sys.cpu_percent:.1f}%")
            if sys.memory_percent > 85:
                self.alerts.append(f"HIGH_MEMORY: {sys.memory_percent:.1f}%")

            # Check security directory size
            security_dir = Path.home() / "security"
            if security_dir.exists():
                try:
                    result = subprocess.run(
                        ["du", "-sb", str(security_dir)],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    size_bytes = int(result.stdout.split()[0])
                    size_gb = size_bytes / (1024**3)
                    if size_gb > 5:
                        self.alerts.append(f"SECURITY_DIR_LARGE: {size_gb:.1f} GB")
                except Exception:
                    pass

        # Check LLM rate limits
        for provider in self.result.llm_providers:
            if provider.rate_limit_remaining is not None:
                if provider.rate_limit_remaining < 100:
                    self.alerts.append(
                        f"{provider.name.upper()}_RATE_LIMIT_LOW: {provider.rate_limit_remaining}"
                    )

        # Check database size
        if self.result.database and self.result.database.size_mb > 1024:
            self.alerts.append(f"DATABASE_LARGE: {self.result.database.size_mb:.0f} MB")

        if self.alerts:
            logger.warning(f"Alerts: {self.alerts}")

    def save_snapshot(self) -> Path:
        """Save profile to JSON."""
        METRICS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        snapshot_path = METRICS_DIR / f"profile_{timestamp}.json"
        snapshot_path.write_text(json.dumps(asdict(self.result), indent=2, default=str))

        # Update latest symlink
        latest = METRICS_DIR / "latest_profile.json"
        if latest.exists():
            latest.unlink()
        latest.symlink_to(snapshot_path.name)

        logger.info(f"Snapshot saved: {snapshot_path}")
        return snapshot_path

    def generate_cost_report(self, days: int = 7) -> dict:
        """Generate historical cost report."""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        total_cost = 0.0
        provider_costs: dict[str, float] = {}

        # Aggregate all snapshots in date range
        for snapshot_file in METRICS_DIR.glob("profile_*.json"):
            try:
                data = json.loads(snapshot_file.read_text())
                snapshot_time = datetime.fromisoformat(data.get("timestamp", "").replace("Z", "+00:00"))

                if snapshot_time >= cutoff:
                    for provider in data.get("llm_providers", []):
                        name = provider.get("name", "unknown")
                        cost = provider.get("cost_24h", 0)
                        provider_costs[name] = provider_costs.get(name, 0) + cost
                        total_cost += cost
            except Exception:
                continue

        return {
            "period_days": days,
            "total_cost_usd": round(total_cost, 2),
            "provider_breakdown": provider_costs,
            "estimated_monthly": round(total_cost * (30 / days), 2),
        }


def print_summary(result: ProfileResult):
    """Print human-readable summary."""
    print(f"\n{'='*60}")
    print(f"PERFORMANCE PROFILE: {result.timestamp}")
    print(f"{'='*60}")

    if result.system:
        s = result.system
        print("\n🖥️  SYSTEM")
        print(f"  CPU: {s.cpu_percent:.1f}% (load: {s.load_average[0]:.2f})")
        print(f"  RAM: {s.memory_percent:.1f}% ({s.memory_used_gb:.1f}/{s.memory_total_gb:.1f} GB)")
        print(f"  Disk: {s.disk_used_gb:.1f}/{s.disk_total_gb:.1f} GB")

    if result.processes:
        print(f"\n🔧 MONITORED PROCESSES ({len(result.processes)})")
        for p in sorted(result.processes, key=lambda x: -x.memory_mb)[:5]:
            print(f"  {p.name[:25]:25} PID:{p.pid:6} MEM:{p.memory_mb:6.1f}MB CPU:{p.cpu_percent:5.1f}%")

    if result.llm_providers:
        print("\n🤖 LLM PROVIDERS (24h costs)")
        for prov in sorted(result.llm_providers, key=lambda x: -x.cost_24h):
            limit_str = f" ({prov.rate_limit_remaining} remaining)" if prov.rate_limit_remaining else ""
            print(f"  {prov.name:12} ${prov.cost_24h:.3f}{limit_str}")

    if result.database:
        print("\n🗄️  DATABASE")
        print(f"  LanceDB: {result.database.size_mb:.1f} MB")
        for table, count in result.database.table_counts.items():
            print(f"    - {table}: {count} items")

    if result.timers:
        print(f"\n⏰ SYSTEMD TIMERS ({len(result.timers)} active)")
        for t in result.timers[:3]:
            print(f"  {t.name}")

    if result.alerts:
        print("\n⚠️  ALERTS")
        for alert in result.alerts:
            print(f"  ! {alert}")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Profile bazzite-laptop AI system performance"
    )
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=300, help="Watch interval (seconds)")
    parser.add_argument("--cost-report", action="store_true", help="Generate cost report")
    parser.add_argument("--days", type=int, default=7, help="Cost report period (days)")
    parser.add_argument("--save", action="store_true", help="Save snapshot to file")
    args = parser.parse_args()

    if args.cost_report:
        profiler = PerformanceProfiler()
        report = profiler.generate_cost_report(args.days)
        print(f"\nCOST REPORT (Last {args.days} days)")
        print(f"Total: ${report['total_cost_usd']}")
        print(f"Estimated monthly: ${report['estimated_monthly']}")
        print("\nBy provider:")
        for name, cost in sorted(report['provider_breakdown'].items(), key=lambda x: -x[1]):
            print(f"  {name}: ${cost:.2f}")
        return

    if args.watch:
        print(f"Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop\n")
        try:
            while True:
                profiler = PerformanceProfiler()
                result = profiler.profile()
                print_summary(result)

                if args.save:
                    profiler.save_snapshot()

                if result.alerts:
                    print(f"\n🔔 {len(result.alerts)} alerts active!")

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    else:
        profiler = PerformanceProfiler()
        result = profiler.profile()
        print_summary(result)

        if args.save:
            snapshot_path = profiler.save_snapshot()
            print(f"\nSaved: {snapshot_path}")

        sys.exit(1 if result.alerts else 0)


if __name__ == "__main__":
    main()
