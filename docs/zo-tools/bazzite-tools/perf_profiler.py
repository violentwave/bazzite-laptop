#!/usr/bin/env python3
"""
perf_profiler.py - Performance profiler for Python AI system operations.

Profiles LLM latency, MCP tools, file I/O, LanceDB, and system snapshot.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import lancedb
    import numpy as np
    HAS_LANCEDB = True
except ImportError:
    HAS_LANCEDB = False


@dataclass
class LatencyStats:
    min_ms: float
    max_ms: float
    mean_ms: float
    p95_ms: float
    samples: list[float]


@dataclass
class LLMProfile:
    endpoint: str
    latency: LatencyStats


@dataclass
class MCPProfile:
    endpoint: str
    tool_stats: dict[str, LatencyStats]


@dataclass
class FileIOProfile:
    path: str
    min_ms: float
    max_ms: float
    mean_ms: float
    size_bytes: int


@dataclass
class LanceDBProfile:
    table: str
    rows: int
    search_ms: float
    index_type: str | None


@dataclass
class SystemSnapshot:
    cpu_percent: float
    memory_used_mb: float
    memory_available_mb: float
    load_avg_1m: float
    disk_read_mb_s: float | None
    disk_write_mb_s: float | None


@dataclass
class ProfileReport:
    timestamp: str
    llm_profile: LLMProfile | None
    mcp_profile: MCPProfile | None
    file_io_profile: list[FileIOProfile]
    lancedb_profile: list[LanceDBProfile]
    system_snapshot: SystemSnapshot | None
    errors: list[str]


class PerfProfiler:
    """Performance profiler for AI system components."""

    def __init__(self):
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.errors: list[str] = []

    def profile_llm_latency(
        self,
        endpoint: str = "http://127.0.0.1:8767/v1",
        n: int = 5
    ) -> LatencyStats:
        """
        Send n minimal completion requests, measure per-request latency.
        Returns {min, max, mean, p95, samples} in ms.
        """
        samples: list[float] = []

        payload = {
            "model": "fast",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }

        for i in range(n):
            try:
                start = time.perf_counter()
                response = self.client.post(
                    f"{endpoint}/chat/completions",
                    json=payload,
                    timeout=10,
                )
                end = time.perf_counter()
                response.raise_for_status()
                samples.append((end - start) * 1000)
            except Exception as e:
                self.errors.append(f"LLM request {i}: {e}")

        if not samples:
            return LatencyStats(min_ms=0, max_ms=0, mean_ms=0, p95_ms=0, samples=[])

        samples.sort()
        p95_idx = int(len(samples) * 0.95)

        return LatencyStats(
            min_ms=min(samples),
            max_ms=max(samples),
            mean_ms=sum(samples) / len(samples),
            p95_ms=samples[min(p95_idx, len(samples) - 1)],
            samples=samples,
        )

    def profile_mcp_tools(
        self,
        endpoint: str = "http://127.0.0.1:8766",
        tools: list[str] | None = None,
        n: int = 3
    ) -> dict[str, LatencyStats]:
        """
        Call each MCP tool n times via HTTP POST to /mcp.
        If tools=None, first fetches tool list.
        Returns per-tool stats dict.
        Only calls read-only tools (skip destructive).
        """
        tool_stats: dict[str, LatencyStats] = {}

        # Fetch tool list if not provided
        if tools is None:
            try:
                response = self.client.get(f"{endpoint}/tools", timeout=5)
                response.raise_for_status()
                data = response.json()
                tools = [t.get("name", t.get("id", "")) for t in data.get("tools", [])]
                # Filter destructive tools
                tools = [
                    t for t in tools
                    if not any(d in str(data).lower() for d in ["destructive", "write", "delete", "remove", "update"])
                ]
            except Exception as e:
                self.errors.append(f"Failed to fetch MCP tools: {e}")
                return tool_stats

        # Call each tool
        for tool_name in tools[:20]:  # Limit to first 20 tools
            samples: list[float] = []

            for i in range(n):
                try:
                    start = time.perf_counter()
                    response = self.client.post(
                        f"{endpoint}/mcp",
                        json={"tool": tool_name, "args": {}},
                        timeout=5,
                    )
                    end = time.perf_counter()
                    # Don't raise for error responses - tool might require args
                    samples.append((end - start) * 1000)
                except Exception as e:
                    self.errors.append(f"MCP tool {tool_name} call {i}: {e}")

            if samples:
                samples.sort()
                p95_idx = int(len(samples) * 0.95)
                tool_stats[tool_name] = LatencyStats(
                    min_ms=min(samples),
                    max_ms=max(samples),
                    mean_ms=sum(samples) / len(samples),
                    p95_ms=samples[min(p95_idx, len(samples) - 1)],
                    samples=samples,
                )

        return tool_stats

    def profile_file_io(
        self,
        paths: list[str] | None = None
    ) -> list[FileIOProfile]:
        """
        For each path, measure read latency (open+read) over 10 iterations.
        Reports {path: {min_ms, max_ms, mean_ms, size_bytes}}.
        Default paths: ~/security/llm-status.json, ~/security/.status, ~/security/release-watch.json
        """
        if paths is None:
            home = Path.home()
            paths = [
                str(home / "security" / "llm-status.json"),
                str(home / "security" / ".status"),
                str(home / "security" / "release-watch.json"),
            ]

        results: list[FileIOProfile] = []

        for path_str in paths:
            path = Path(path_str).expanduser()

            if not path.exists():
                results.append(FileIOProfile(
                    path=path_str,
                    min_ms=0,
                    max_ms=0,
                    mean_ms=0,
                    size_bytes=-1,
                ))
                continue

            samples: list[float] = []
            size_bytes = path.stat().st_size

            for _ in range(10):
                try:
                    start = time.perf_counter()
                    with open(path, "rb") as f:
                        _ = f.read()
                    end = time.perf_counter()
                    samples.append((end - start) * 1000)
                except Exception as e:
                    self.errors.append(f"File IO {path}: {e}")

            if samples:
                results.append(FileIOProfile(
                    path=path_str,
                    min_ms=min(samples),
                    max_ms=max(samples),
                    mean_ms=sum(samples) / len(samples),
                    size_bytes=size_bytes,
                ))
            else:
                results.append(FileIOProfile(
                    path=path_str,
                    min_ms=0,
                    max_ms=0,
                    mean_ms=0,
                    size_bytes=size_bytes,
                ))

        return results

    def profile_lancedb(self, db_path: str) -> list[LanceDBProfile]:
        """
        Open LanceDB at db_path, run vector search on each table (random 768-dim vector).
        Returns {table: {rows, search_ms, index_type}}.
        Uses lancedb Python package directly if available, else skips with warning.
        """
        if not HAS_LANCEDB:
            self.errors.append("lancedb not installed, skipping DB profile")
            return []

        results: list[LanceDBProfile] = []

        try:
            db = lancedb.connect(db_path)
            tables = db.table_names()

            for table_name in tables:
                try:
                    table = db.open_table(table_name)

                    # Get row count
                    rows = table.count_rows()

                    # Get schema info for index type
                    index_type = None
                    try:
                        # Check for vector index
                        schema = table.schema
                        if "vector" in str(schema):
                            index_type = "vector"
                    except Exception:
                        pass

                    # Run vector search with random vector
                    search_ms = 0.0
                    if "vector" in str(table.schema) or rows > 0:
                        vector = np.random.randn(768).astype(np.float32)
                        vector = vector / np.linalg.norm(vector)

                        start = time.perf_counter()
                        try:
                            table.search(vector).limit(1).to_list()
                        except Exception:
                            # Table might not have vector column
                            pass
                        end = time.perf_counter()
                        search_ms = (end - start) * 1000

                    results.append(LanceDBProfile(
                        table=table_name,
                        rows=rows,
                        search_ms=search_ms,
                        index_type=index_type,
                    ))

                except Exception as e:
                    self.errors.append(f"LanceDB table {table_name}: {e}")
                    results.append(LanceDBProfile(
                        table=table_name,
                        rows=-1,
                        search_ms=0,
                        index_type=None,
                    ))

        except Exception as e:
            self.errors.append(f"LanceDB connection: {e}")

        return results

    def collect_system_snapshot(self) -> SystemSnapshot | None:
        """
        Return point-in-time system metrics using only stdlib + optional psutil.
        {cpu_percent, memory_used_mb, memory_available_mb, load_avg_1m, disk_read_mb_s, disk_write_mb_s}
        Falls back to /proc parsing if psutil unavailable.
        """
        try:
            cpu_percent = 0.0
            memory_used_mb = 0.0
            memory_available_mb = 0.0
            load_avg_1m = 0.0
            disk_read_mb_s = None
            disk_write_mb_s = None

            if HAS_PSUTIL:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                memory_used_mb = mem.used / (1024 * 1024)
                memory_available_mb = mem.available / (1024 * 1024)
                load_avg = os.getloadavg()
                load_avg_1m = load_avg[0]

                # Disk IO requires sampling over time
                disk_start = psutil.disk_io_counters()
                time.sleep(0.1)
                disk_end = psutil.disk_io_counters()
                if disk_start and disk_end:
                    read_bytes = disk_end.read_bytes - disk_start.read_bytes
                    write_bytes = disk_end.write_bytes - disk_start.write_bytes
                    disk_read_mb_s = (read_bytes / (1024 * 1024)) / 0.1
                    disk_write_mb_s = (write_bytes / (1024 * 1024)) / 0.1
            else:
                # Fallback to /proc
                try:
                    # CPU usage estimation from /proc/stat
                    with open("/proc/stat") as f:
                        line = f.readline()
                        fields = line.split()[1:]
                        # idle is field 4
                        total = sum(int(x) for x in fields[:7])
                        idle = int(fields[3])
                        cpu_percent = 100 * (1 - idle / total) if total > 0 else 0
                except Exception:
                    pass

                try:
                    # Memory from /proc/meminfo
                    with open("/proc/meminfo") as f:
                        meminfo = f.read()
                    total_match = re.search(r"MemTotal:\s+(\d+)\s+kB", meminfo)
                    available_match = re.search(r"MemAvailable:\s+(\d+)\s+kB", meminfo)
                    if total_match and available_match:
                        total_kb = int(total_match.group(1))
                        available_kb = int(available_match.group(1))
                        memory_used_mb = (total_kb - available_kb) / 1024
                        memory_available_mb = available_kb / 1024
                except Exception:
                    pass

                try:
                    # Load average from /proc/loadavg
                    with open("/proc/loadavg") as f:
                        load = f.read().split()
                        load_avg_1m = float(load[0])
                except Exception:
                    pass

            return SystemSnapshot(
                cpu_percent=cpu_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                load_avg_1m=load_avg_1m,
                disk_read_mb_s=disk_read_mb_s,
                disk_write_mb_s=disk_write_mb_s,
            )

        except Exception as e:
            self.errors.append(f"System snapshot: {e}")
            return None

    def generate_report(
        self,
        results: ProfileReport,
        output_path: str
    ) -> dict[str, Any]:
        """
        Write JSON report with all profiling results + system snapshot.
        Atomic write. Also prints compact terminal table (stdlib only).
        """
        report = asdict(results)

        # Atomic write
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = output_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(report, f, indent=2)
        os.replace(tmp_file, output_file)

        # Terminal table (stdlib only, no rich)
        print("\n" + "=" * 60)
        print("PERFORMANCE PROFILE REPORT")
        print("=" * 60)
        print(f"Timestamp: {results.timestamp}")

        if results.system_snapshot:
            s = results.system_snapshot
            print("\nSystem:")
            print(f"  CPU: {s.cpu_percent:.1f}%")
            print(f"  Memory: {s.memory_used_mb:.0f}MB used, {s.memory_available_mb:.0f}MB available")
            print(f"  Load (1m): {s.load_avg_1m:.2f}")

        if results.llm_profile:
            l = results.llm_profile.latency
            print(f"\nLLM Latency ({results.llm_profile.endpoint}):")
            print(f"  Min: {l.min_ms:.1f}ms, Mean: {l.mean_ms:.1f}ms, P95: {l.p95_ms:.1f}ms")

        if results.mcp_profile:
            print(f"\nMCP Tools ({len(results.mcp_profile.tool_stats)} tools):")
            for name, stats in list(results.mcp_profile.tool_stats.items())[:5]:
                print(f"  {name}: {stats.mean_ms:.1f}ms avg")

        print(f"\nFile I/O ({len(results.file_io_profile)} files):")
        for fio in results.file_io_profile:
            status = "OK" if fio.size_bytes >= 0 else "MISSING"
            if fio.size_bytes >= 0:
                print(f"  {fio.path}: {fio.mean_ms:.2f}ms ({fio.size_bytes} bytes) [{status}]")
            else:
                print(f"  {fio.path}: MISSING")

        if results.lancedb_profile:
            print(f"\nLanceDB ({len(results.lancedb_profile)} tables):")
            for ldb in results.lancedb_profile:
                print(f"  {ldb.table}: {ldb.rows} rows, {ldb.search_ms:.2f}ms search")

        if results.errors:
            print(f"\nErrors ({len(results.errors)}):")
            for e in results.errors[:5]:
                print(f"  ! {e}")

        print("=" * 60)
        print(f"Report: {output_path}")

        return report

    def run(
        self,
        output_dir: str,
        skip: list[str] | None = None
    ) -> str:
        """
        Run all profilers except those in skip list.
        Returns report path.
        """
        if skip is None:
            skip = []

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / f"perf_profile_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"

        # Run components
        llm_profile = None
        if "llm" not in skip:
            latency = self.profile_llm_latency()
            llm_profile = LLMProfile(
                endpoint="http://127.0.0.1:8767/v1",
                latency=latency,
            )

        mcp_profile = None
        if "mcp" not in skip:
            tool_stats = self.profile_mcp_tools()
            mcp_profile = MCPProfile(
                endpoint="http://127.0.0.1:8766",
                tool_stats=tool_stats,
            )

        file_io_profile = []
        if "file_io" not in skip:
            file_io_profile = self.profile_file_io()

        lancedb_profile = []
        if "lancedb" not in skip and HAS_LANCEDB:
            db_path = str(Path.home() / "security" / "vector-db")
            lancedb_profile = self.profile_lancedb(db_path)

        system_snapshot = None
        if "system" not in skip:
            system_snapshot = self.collect_system_snapshot()

        report = ProfileReport(
            timestamp=datetime.now(UTC).isoformat(),
            llm_profile=llm_profile,
            mcp_profile=mcp_profile,
            file_io_profile=file_io_profile,
            lancedb_profile=lancedb_profile,
            system_snapshot=system_snapshot,
            errors=self.errors,
        )

        self.generate_report(report, str(report_file))
        return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="Performance Profiler")
    parser.add_argument("--output-dir", "-o", default="~/security/metrics", help="Output directory")
    parser.add_argument("--skip", help="Comma-separated components to skip")
    parser.add_argument("--json-only", action="store_true", help="Skip terminal output")

    args = parser.parse_args()

    skip = args.skip.split(",") if args.skip else []
    output_dir = Path(args.output_dir).expanduser()

    logging.basicConfig(
        level=logging.INFO if not args.json_only else logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    profiler = PerfProfiler()
    report_path = profiler.run(str(output_dir), skip=skip)

    if args.json_only:
        print(report_path)
    else:
        print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
