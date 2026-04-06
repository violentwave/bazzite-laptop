"""MCP Bridge tool implementations.

All tools are read-only. Subprocess commands are static lists (no shell=True,
no user argument interpolation). Output is truncated to 4KB max.
"""

import asyncio
import json
import logging
import re
import time
from pathlib import Path

import yaml

from ai.config import CONFIGS_DIR, PROJECT_ROOT, STATUS_FILE
from ai.security.inputvalidator import InputValidator
from ai.utils.freshness import format_freshness_age

logger = logging.getLogger("ai.mcp_bridge")

_LLM_STATUS_PATH = Path.home() / "security" / "llm-status.json"

_TOOL_OUTPUT_LIMITS: dict[str, int] = {
    "system.mcp_manifest": 16384,
    "security.threat_summary": 8192,
    "security.cve_check": 8192,
}
_DEFAULT_OUTPUT_LIMIT = 4096
_SUBPROCESS_TIMEOUT_S = 30

# Concurrency limit for subprocess tool calls
_subprocess_semaphore = asyncio.Semaphore(4)

# Bridge-level rate limiting (independent of provider limits)
_BRIDGE_RATE_GLOBAL = 10  # max 10 req/s global
_BRIDGE_RATE_PER_TOOL = 2  # max 2 req/s per tool

_global_call_times: list[float] = []
_per_tool_call_times: dict[str, list[float]] = {}

# Path redaction pattern
_HOME_PATTERN = re.compile(r"/home/lch")

# Allowlist loaded once at module import
_ALLOWLIST_PATH = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"
_allowlist: dict | None = None

# Input validator singleton (loaded once, thread-safe)
try:
    _VALIDATOR = InputValidator.from_default_config()
except Exception as e:
    logger.warning(f"InputValidator init failed: {e}, validation disabled")
    _VALIDATOR = None


def _check_bridge_rate(tool_name: str) -> None:
    """Check bridge-level rate limits. Raises ValueError if exceeded."""
    now = time.time()
    window = 1.0  # 1 second window

    # Global rate check
    _global_call_times[:] = [t for t in _global_call_times if now - t < window]
    if len(_global_call_times) >= _BRIDGE_RATE_GLOBAL:
        raise ValueError("[Bridge rate limited, slow down]")
    _global_call_times.append(now)

    # Per-tool rate check
    if tool_name not in _per_tool_call_times:
        _per_tool_call_times[tool_name] = []
    times = _per_tool_call_times[tool_name]
    times[:] = [t for t in times if now - t < window]
    if len(times) >= _BRIDGE_RATE_PER_TOOL:
        raise ValueError("[Bridge rate limited, slow down]")
    times.append(now)


def _validate_args(tool_def: dict, args: dict) -> None:
    """Validate tool arguments against the allowlist definition.

    Raises:
        ValueError: If validation fails.
    """
    arg_defs = tool_def.get("args")
    if arg_defs is None:
        return  # No args expected

    for arg_name, constraints in arg_defs.items():
        is_required = constraints.get("required", False)
        value = args.get(arg_name)

        if value is None:
            if is_required:
                raise ValueError(f"Argument '{arg_name}' is required")
            continue

        if not isinstance(value, str):
            raise ValueError(f"Argument '{arg_name}' must be a string")

        # Pattern validation (regex)
        pattern = constraints.get("pattern")
        if pattern and not re.match(pattern, value):
            raise ValueError(f"Argument '{arg_name}' does not match pattern '{pattern}'")

        # Length validation
        max_length = constraints.get("max_length")
        if max_length and len(value) > max_length:
            raise ValueError(f"Argument '{arg_name}' exceeds max length {max_length}")


def _load_allowlist() -> dict:
    """Load the tool allowlist from YAML."""
    global _allowlist  # noqa: PLW0603
    if _allowlist is not None:
        return _allowlist
    try:
        with open(_ALLOWLIST_PATH) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError as exc:
        raise RuntimeError(f"allowlist not found: {_ALLOWLIST_PATH}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"failed to parse allowlist: {exc}") from exc
    _allowlist = data.get("tools", {})
    return _allowlist


def _truncate(text: str, limit: int = _DEFAULT_OUTPUT_LIMIT) -> str:
    """Truncate output to limit bytes, appending truncation marker if cut."""
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def _redact_paths(text: str) -> str:
    """Replace /home/lch with [HOME] to prevent path leakage."""
    return _HOME_PATTERN.sub("[HOME]", text)


def _read_file_tail(path: str, lines: int, pattern: str | None = None) -> str:
    """Read last N lines from a file or latest file in a directory.

    Skips empty files. For symlinks, resolves the target and uses it if
    non-empty. Falls back to logrotated files (pattern + "-*") when all
    primary files are empty (logrotate empties the original .log and stores
    data in health-*.log-YYYYMMDD).
    """
    p = Path(path)
    if p.is_dir() and pattern:
        import glob as globmod

        def _first_nonempty(globs: list[str]) -> Path | None:
            def _mtime(f: str) -> float:
                try:
                    return Path(f).stat().st_mtime
                except OSError:
                    return 0.0

            for fstr in sorted(globs, key=_mtime, reverse=True):
                fp = Path(fstr)
                if fp.is_symlink():
                    try:
                        resolved = fp.resolve()
                        if resolved.stat().st_size > 0:
                            return resolved
                    except OSError:
                        pass
                    continue
                try:
                    if fp.stat().st_size > 0:
                        return fp
                except OSError:
                    continue
            return None

        # Primary: e.g. health-*.log
        chosen = _first_nonempty(globmod.glob(str(p / pattern)))
        if chosen is None:
            # Fallback: logrotated copies e.g. health-*.log-20260323
            chosen = _first_nonempty(globmod.glob(str(p / (pattern + "-*"))))
        if chosen is None:
            raise FileNotFoundError(f"No non-empty files matching {pattern} in {path}")
        p = chosen

    all_lines = p.read_text().splitlines()
    return "\n".join(all_lines[-lines:])


def _read_status_file() -> dict:
    """Read and parse the status JSON file."""
    return json.loads(STATUS_FILE.read_text())


# Status key whitelist
_STATUS_ALLOWED_KEYS = {
    "state",
    "scan_type",
    "last_scan_time",
    "result",
    "health_status",
    "health_issues",
}


async def _run_subprocess(command: list[str]) -> str:
    """Run a subprocess with timeout and concurrency limiting."""
    async with _subprocess_semaphore:
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=_SUBPROCESS_TIMEOUT_S,
            )
            return _truncate(stdout.decode("utf-8", errors="replace"))
        except FileNotFoundError:
            return "[Command not found]"
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return "[Tool timed out]"


_GPU_THROTTLE_BITS: dict[int, str] = {
    0x02: "SW_POWER_CAP",
    0x08: "HW_SLOWDOWN",
    0x20: "HW_THERMAL",
    0x40: "HW_POWER_BRAKE",
    0x80: "SYNC_BOOST",
    0x100: "SW_THERMAL",
}
_GPU_TEMP_THROTTLE_THRESHOLD = 83  # °C — GTX 1060 thermal throttle point
_GPU_HEADROOM_WARN_C = 8  # °C below threshold → send warning


async def _execute_gpu_tool(tool_name: str) -> str:
    """Query nvidia-smi for GPU performance and health data."""
    # Query all needed fields in one nvidia-smi call
    fields = (
        "temperature.gpu,"
        "pstate,"
        "clocks.gr,"
        "clocks.mem,"
        "power.draw,"
        "memory.used,"
        "memory.free,"
        "memory.total,"
        "fan.speed,"
        "clocks_throttle_reasons.active"
    )
    raw = await _run_subprocess(
        [
            "nvidia-smi",
            f"--query-gpu={fields}",
            "--format=csv,noheader,nounits",
        ]
    )

    if raw in ("[Command not found]", "[Tool timed out]"):
        return json.dumps({"error": "nvidia-smi not available"})

    parts = [p.strip() for p in raw.strip().split(",")]
    if len(parts) < 10:
        return json.dumps({"error": f"Unexpected nvidia-smi output: {raw!r}"})

    try:
        temp_c = int(parts[0])
        pstate = parts[1]
        clock_gr = parts[2]
        clock_mem = parts[3]
        power_w = parts[4]
        vram_used = parts[5]
        vram_free = parts[6]
        vram_total = parts[7]
        fan_pct = parts[8]
        throttle_hex = parts[9].strip()
    except (ValueError, IndexError) as e:
        return json.dumps({"error": f"Parse error: {e}", "raw": raw})

    headroom_c = _GPU_TEMP_THROTTLE_THRESHOLD - temp_c

    result: dict = {
        "temperature_c": temp_c,
        "pstate": pstate,
        "clocks_mhz": {"graphics": clock_gr, "memory": clock_mem},
        "power_draw_w": power_w,
        "vram_mb": {"used": vram_used, "free": vram_free, "total": vram_total},
        "fan_speed_pct": fan_pct,
        "throttle_reasons_raw": throttle_hex,
        "headroom_c": headroom_c,
    }

    if tool_name == "system.gpu_health":
        # Decode throttle reason bitmask
        try:
            throttle_val = (
                int(throttle_hex, 16) if throttle_hex.startswith("0x") else int(throttle_hex)
            )
        except ValueError:
            throttle_val = 0

        active_reasons = [name for bit, name in _GPU_THROTTLE_BITS.items() if throttle_val & bit]
        result["throttle_active"] = active_reasons
        result["is_throttling"] = bool(active_reasons)

        # Warn if headroom is dangerously low
        if headroom_c <= _GPU_HEADROOM_WARN_C:
            warn_msg = (
                f"GPU headroom only {headroom_c}°C ({temp_c}°C / {_GPU_TEMP_THROTTLE_THRESHOLD}°C)"
            )
            result["warning"] = warn_msg
            # Fire a desktop notification (best-effort, non-blocking)
            asyncio.ensure_future(
                _run_subprocess(
                    [
                        "notify-send",
                        "--urgency=critical",
                        "--icon=dialog-warning",
                        "GPU Thermal Warning",
                        warn_msg,
                    ]
                )
            )

    return json.dumps(result, indent=2)


_GPU_STATUS_FIELDS = "name, temperature_C, utilization_%, memory_MB, power_W, fan"


async def _execute_token_report() -> str:
    """Generate token usage report from llm-status.json.

    Returns structured report with freshness indicator.
    """
    import json

    from ai.utils.freshness import format_freshness_age

    status_path = _LLM_STATUS_PATH

    try:
        if not status_path.exists():
            return json.dumps(
                {
                    "error": "LLM status file not found",
                    "message": "Run the LLM proxy to generate status data",
                },
                indent=2,
            )

        data = json.loads(status_path.read_text())
    except json.JSONDecodeError:
        return json.dumps(
            {
                "error": "LLM status file is malformed",
                "message": "Status file contains invalid JSON",
            },
            indent=2,
        )
    except OSError as e:
        return json.dumps(
            {"error": f"Failed to read status file: {e}", "message": "Check file permissions"},
            indent=2,
        )

    # Build report from available data
    report: dict = {
        "generated_at": data.get("generated_at", "unknown"),
        "note": (
            "Daily/weekly rollups not yet available. Showing cumulative totals since proxy start."
        ),
    }

    # Extract usage data if available
    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    if usage:
        total_prompt = 0
        total_completion = 0
        total_requests = 0

        task_breakdown: dict[str, dict] = {}

        for task_type, stats in usage.items():
            if not isinstance(stats, dict):
                continue
            prompt = stats.get("prompt_tokens", 0) or 0
            completion = stats.get("completion_tokens", 0) or 0
            requests = stats.get("requests", 0) or 0

            total_prompt += prompt
            total_completion += completion
            total_requests += requests

            task_breakdown[task_type] = {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "requests": requests,
            }

        report["usage"] = {
            "total_tokens": total_prompt + total_completion,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "requests": total_requests,
        }

        if task_breakdown:
            report["usage"]["by_task"] = task_breakdown

    # Extract provider health data if available
    providers = data.get("providers", {}) if isinstance(data, dict) else {}
    if providers and isinstance(providers, dict):
        report["providers"] = {
            name: {
                "health_score": info.get("score", "unknown"),
                "auth_broken": info.get("auth_broken", False),
            }
            for name, info in providers.items()
            if isinstance(info, dict)
        }

    # Add freshness warning if stale
    freshness = format_freshness_age(data.get("generated_at"))
    if freshness:
        report["freshness_warning"] = freshness

    return json.dumps(report, indent=2)


async def _execute_gpu_status(command: list[str]) -> str:
    """Run nvidia-smi for gpu_status and return labeled human-readable output."""
    raw = await _run_subprocess(command)
    if raw.startswith("["):
        # Error sentinel from _run_subprocess ("[Command not found]", etc.)
        return raw

    parts = [f.strip() for f in raw.strip().split(",")]
    if len(parts) != 6:
        return f"{_GPU_STATUS_FIELDS} | {raw.strip()}"

    try:
        name, temp, util, mem, power, fan = parts
        return (
            f"GPU: {name} (temperature: {temp}°C, utilization: {util}%, "
            f"VRAM: {mem} MB, power: {power} W, fan: {fan})"
        )
    except ValueError:
        return f"{_GPU_STATUS_FIELDS} | {raw.strip()}"


async def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return redacted output safe to send to Newelle.

    Applies secret redaction as a final pass so no API key can leak even
    if a tool handler accidentally includes one.  ValueError from the
    allowlist / validation layer propagates unchanged.
    """
    result = await _dispatch_tool(tool_name, args)
    if _VALIDATOR is not None:
        result = _VALIDATOR.redact_secrets(result)
    return result


async def _dispatch_tool(tool_name: str, args: dict) -> str:
    """Internal tool dispatch — call execute_tool, not this function directly.

    Args:
        tool_name: The tool identifier (e.g. "system.disk_usage").
        args: Validated arguments dict.

    Returns:
        Tool output as a string.

    Raises:
        ValueError: If tool_name is not in the allowlist.
    """
    allowlist = _load_allowlist()
    if tool_name not in allowlist:
        raise ValueError(f"Unknown tool: '{tool_name}'")

    tool_def = allowlist[tool_name]
    _check_bridge_rate(tool_name)
    _validate_args(tool_def, args)

    if _VALIDATOR is not None:
        ok, violations = _VALIDATOR.validate_tool_args(tool_name, args)
        if not ok:
            sample = _VALIDATOR.redact_secrets(str(args)[:200])
            logger.warning(
                f"Input validation failed for {tool_name}: {violations} | args: {sample}"
            )
            raise ValueError("Input validation failed")

    # system.gpu_status: parse CSV into labeled human-readable output
    if tool_name == "system.gpu_status":
        return await _execute_gpu_status(tool_def["command"])

    # system.service_status: split into system and user scope calls
    if tool_name == "system.service_status":
        system_out = await _run_subprocess(
            [
                "systemctl",
                "show",
                "-p",
                "Id,ActiveState",
                "clamav-freshclam.service",
                "system-health.timer",
            ]
        )
        user_out = await _run_subprocess(
            [
                "systemctl",
                "--user",
                "show",
                "-p",
                "Id,ActiveState",
                "bazzite-mcp-bridge.service",
                "bazzite-llm-proxy.service",
            ]
        )
        parts = []
        if system_out.strip():
            parts.append("[system]\n" + system_out.strip())
        if user_out.strip():
            parts.append("[user]\n" + user_out.strip())
        return "\n\n".join(parts)

    # Subprocess-based tools
    if "command" in tool_def:
        return await _run_subprocess(tool_def["command"])

    # File tail tools
    if tool_def.get("source") == "file_tail":
        try:
            text = _read_file_tail(
                tool_def["path"],
                tool_def.get("lines", 20),
                tool_def.get("pattern"),
            )
            return _truncate(_redact_paths(text))
        except FileNotFoundError:
            return "No data yet -- run a snapshot first"

    # Status file tool
    if tool_def.get("source") == "json_file":
        try:
            if "path" in tool_def:
                data = json.loads(Path(tool_def["path"]).expanduser().read_text())
                freshness = (
                    format_freshness_age(data.get("generated_at"))
                    if isinstance(data, dict)
                    else None
                )
                json_str = json.dumps(data, indent=2)
                if freshness:
                    json_str = f"{json_str}\n\n[{freshness}]"
                return _truncate(json_str)
            data = _read_status_file()
            filtered = {k: v for k, v in data.items() if k in _STATUS_ALLOWED_KEYS}
            return json.dumps(filtered, indent=2)
        except FileNotFoundError:
            return "No data yet -- run a scan first"

    # Python module tools (threat_lookup, rag_query, gaming)
    if tool_def.get("source") == "python":
        return await _execute_python_tool(tool_name, tool_def, args)

    return f"[Tool '{tool_name}' has unsupported source type]"


async def _execute_python_tool(tool_name: str, tool_def: dict, args: dict) -> str:
    """Execute a Python-module-backed tool."""

    try:
        if tool_name == "security.threat_lookup":
            from ai.threat_intel.lookup import lookup_hash  # noqa: PLC0415

            result = lookup_hash(args["hash"])
            # Sanitize: strip raw_data, return only safe fields
            safe_fields = {
                "hash",
                "source",
                "family",
                "risk_level",
                "detection_ratio",
                "description",
                "tags",
            }
            if isinstance(result, dict):
                filtered = {k: v for k, v in result.items() if k in safe_fields}
                return json.dumps(filtered, indent=2)
            return _truncate(str(result))

        elif tool_name == "security.ip_lookup":
            from ai.threat_intel.ip_lookup import lookup_ip  # noqa: PLC0415

            result = lookup_ip(args["ip"])
            safe_fields = {
                "ip",
                "source",
                "abuse_score",
                "greynoise_classification",
                "recommendation",
                "ports",
                "vulns",
                "description",
            }
            data = json.loads(result.to_json())
            filtered = {k: v for k, v in data.items() if k in safe_fields}
            return json.dumps(filtered, indent=2)

        elif tool_name == "security.url_lookup":
            from ai.threat_intel.ioc_lookup import lookup_url  # noqa: PLC0415

            result = lookup_url(args["url"])
            safe_fields = {
                "ioc",
                "source",
                "threat_type",
                "malware_family",
                "risk_level",
                "tags",
                "description",
                "circl_hits",
            }
            data = json.loads(result.to_json())
            filtered = {k: v for k, v in data.items() if k in safe_fields}
            return json.dumps(filtered, indent=2)

        elif tool_name == "knowledge.rag_query":
            from ai.rag.query import rag_query  # noqa: PLC0415

            question = args.get("query") or args.get("question", "")
            result = rag_query(question, use_llm=False)
            return _truncate(result.answer)

        elif tool_name == "knowledge.rag_qa":
            from ai.rag.query import rag_query  # noqa: PLC0415

            question = args.get("question", "")
            result = rag_query(question, use_llm=True)
            if result.answer:
                return _truncate(_redact_paths(result.answer))
            # Fallback to raw context chunks if LLM answer is empty
            fallback = "\n\n".join(
                c.get("text", c.get("content", "")) for c in result.context_chunks
            )
            return _truncate(_redact_paths(fallback))

        elif tool_name == "knowledge.ingest_docs":
            from ai.rag.ingest_docs import ingest_directory  # noqa: PLC0415

            docs_dir = Path(__file__).parent.parent.parent / "docs"
            result = ingest_directory(docs_dir)
            return json.dumps(result, indent=2)

        elif tool_name == "knowledge.pattern_search":
            from ai.rag.pattern_query import search_patterns

            results = search_patterns(
                query=args.get("query", ""),
                language=args.get("language"),
                domain=args.get("domain"),
                limit=args.get("limit", 5),
            )
            formatted = []
            for r in results:
                formatted.append(
                    {
                        "title": r.get("title", ""),
                        "language": r.get("language", ""),
                        "domain": r.get("domain", ""),
                        "tags": r.get("tags", []),
                        "content": (r.get("content", "") or "")[:2000],
                    }
                )
            return _truncate(json.dumps(formatted))

        elif tool_name == "gaming.profiles":
            from ai.gaming.scopebuddy import list_profiles  # noqa: PLC0415

            return json.dumps(list_profiles(), indent=2)

        elif tool_name == "gaming.mangohud_preset":
            from ai.gaming.scopebuddy import get_preset  # noqa: PLC0415

            return json.dumps(get_preset(args["game"]), indent=2)

        elif tool_name == "logs.health_trend":
            from ai.log_intel.queries import health_trend  # noqa: PLC0415

            return json.dumps(health_trend(), indent=2, default=str)

        elif tool_name == "logs.scan_history":
            from ai.log_intel.queries import scan_history  # noqa: PLC0415

            return json.dumps(scan_history(), indent=2, default=str)

        elif tool_name == "logs.anomalies":
            from ai.log_intel.queries import get_anomalies  # noqa: PLC0415

            return json.dumps(get_anomalies(), indent=2, default=str)

        elif tool_name == "logs.search":
            from ai.log_intel.queries import search_logs  # noqa: PLC0415

            return json.dumps(search_logs(args["query"]), indent=2, default=str)

        elif tool_name == "logs.stats":
            from ai.log_intel.queries import pipeline_stats  # noqa: PLC0415

            return json.dumps(pipeline_stats(), indent=2, default=str)

        elif tool_name == "system.pipeline_status":
            from ai.log_intel.queries import pipeline_stats  # noqa: PLC0415

            return json.dumps(pipeline_stats(), indent=2, default=str)

        elif tool_name == "system.llm_models":
            import yaml as _yaml  # noqa: PLC0415

            cfg_path = Path(__file__).parent.parent.parent / "configs" / "litellm-config.yaml"
            with open(cfg_path) as f:
                cfg = _yaml.safe_load(f) or {}
            models: dict[str, list[str]] = {}
            for entry in cfg.get("model_list", []):
                mode = entry.get("model_name", "unknown")
                provider = entry.get("litellm_params", {}).get("model", "?")
                models.setdefault(mode, []).append(provider)
            result = {
                "modes": {k: {"providers": v, "count": len(v)} for k, v in models.items()},
                "how_to_switch": "In Newelle: Settings → API → Model field. "
                "Change from 'fast' to any mode name listed above.",
                "proxy_url": "http://127.0.0.1:8767/v1/",
            }
            return json.dumps(result, indent=2)

        elif tool_name == "security.run_scan":
            scan_type = args.get("scan_type", "quick")
            service = f"clamav-{scan_type}.service"
            result = await _run_subprocess(["systemctl", "start", service])
            return json.dumps(
                {
                    "triggered": True,
                    "service": service,
                    "message": f"ClamAV {scan_type} scan started. "
                    "Results will appear in logs.scan_history once complete.",
                }
            )

        elif tool_name == "security.run_health":
            # Clear a stale flock lock file if it's older than 5 minutes.
            # system-health-snapshot.sh uses flock(1) on this file to prevent
            # concurrent runs.  If a previous snapshot crashed without releasing
            # its fd (e.g. stuck on smartctl with a disconnected device), the old
            # inode retains the lock and all new runs silently exit 0 with no log.
            # Unlinking the file forces the next run to open a fresh inode which
            # has no locks, so flock -n succeeds regardless of the stuck process.
            _HEALTH_LOCK = Path("/var/log/system-health/.health-snapshot.lock")
            lock_cleared = False
            if _HEALTH_LOCK.exists():
                import time as _time  # noqa: PLC0415

                age_s = _time.time() - _HEALTH_LOCK.stat().st_mtime
                if age_s > 300:  # older than 5 minutes → stale
                    try:
                        _HEALTH_LOCK.unlink()
                        lock_cleared = True
                    except OSError:
                        pass  # permission denied — service will handle it

            proc = await asyncio.create_subprocess_exec(
                "systemctl",
                "start",
                "system-health.service",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode != 0:
                err = stderr_b.decode("utf-8", errors="replace").strip()
                return json.dumps(
                    {
                        "triggered": False,
                        "service": "system-health.service",
                        "error": err or f"systemctl exited {proc.returncode}",
                        "message": "Service failed to start. "
                        "Ensure system-health.service is deployed at "
                        "/etc/systemd/system/system-health.service.",
                    }
                )
            result_msg = (
                "Health snapshot started. "
                "Raw results available via security.health_snapshot in ~30 seconds. "
                "Indexed results in logs.health_trend after next ingestion "
                "(daily 9AM or manual security.run_ingest)."
            )
            if lock_cleared:
                result_msg += " (stale lock file cleared before start)"
            return json.dumps(
                {
                    "triggered": True,
                    "service": "system-health.service",
                    "message": result_msg,
                }
            )

        elif tool_name == "code.search":
            query = args.get("query", "")
            repo_root = str(PROJECT_ROOT)
            output = await _run_subprocess(
                [
                    "rg",
                    "--no-heading",
                    "--line-number",
                    "--max-count",
                    "20",
                    "--glob",
                    "*.py",
                    query,
                    repo_root,
                ]
            )
            if output == "[Command not found]":
                # rg not available — fall back to grep (-F: fixed string, not regex)
                output = await _run_subprocess(
                    [
                        "grep",
                        "-rn",
                        "-F",
                        "--include=*.py",
                        query,
                        repo_root,
                    ]
                )
            return _truncate(_redact_paths(output))

        elif tool_name == "code.rag_query":
            from ai.rag.code_query import code_rag_query  # noqa: PLC0415

            question = args.get("question", "")
            result = code_rag_query(question, use_llm=False)
            return _truncate(_redact_paths(json.dumps(result, indent=2)))

        elif tool_name == "system.mcp_manifest":
            allowlist = _load_allowlist()
            compact_tools = {}
            for name, defn in allowlist.items():
                desc = defn.get("description", "")[:40]
                arg_defs = defn.get("args") or {}
                arg_names = list(arg_defs.keys()) if isinstance(arg_defs, dict) else []
                compact_tools[name] = {"desc": desc, "args": arg_names}
            manifest = {"tool_count": len(compact_tools), "tools": compact_tools}
            limit = _TOOL_OUTPUT_LIMITS.get("system.mcp_manifest", _DEFAULT_OUTPUT_LIMIT)
            return _truncate(json.dumps(manifest), limit)

        elif tool_name == "agents.security_audit":
            from ai.agents.security_audit import run_audit  # noqa: PLC0415

            result = run_audit()
            return json.dumps(result, indent=2)

        elif tool_name == "agents.performance_tuning":
            from ai.agents.performance_tuning import run_tuning  # noqa: PLC0415

            result = run_tuning()
            return json.dumps(result, indent=2)

        elif tool_name == "agents.knowledge_storage":
            from ai.agents.knowledge_storage import run_storage_check  # noqa: PLC0415

            result = run_storage_check()
            return json.dumps(result, indent=2)

        elif tool_name == "agents.code_quality":
            from ai.agents.code_quality_agent import run_code_check  # noqa: PLC0415

            result = run_code_check()
            return json.dumps(result, indent=2)

        elif tool_name == "agents.timer_health":
            from ai.agents.timer_sentinel import check_timers  # noqa: PLC0415

            result = check_timers()
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "security.sandbox_submit":
            from ai.threat_intel.sandbox import submit_file  # noqa: PLC0415

            result = submit_file(args["file_path"])
            safe_fields = {
                "file_path",
                "sha256",
                "status",
                "verdict",
                "threat_score",
                "threat_level",
                "job_id",
                "description",
            }
            data = json.loads(result.to_json())
            filtered = {k: v for k, v in data.items() if k in safe_fields}
            return json.dumps(filtered, indent=2)

        elif tool_name == "security.cve_check":
            from ai.threat_intel.cve_scanner import scan_cves  # noqa: PLC0415

            result = scan_cves()
            return json.dumps(result, indent=2)

        elif tool_name == "security.threat_summary":
            from ai.threat_intel.summary import build_summary  # noqa: PLC0415

            result = build_summary()
            safe_fields = {
                "generated_at",
                "date",
                "overall_status",
                "missing_sources",
                "audit",
                "perf",
                "storage",
                "code",
                "cve",
            }
            filtered = {k: v for k, v in result.items() if k in safe_fields}
            return json.dumps(filtered, indent=2)

        elif tool_name == "system.pkg_intel":
            from ai.system.pkg_intel import mcp_handler  # noqa: PLC0415

            result = mcp_handler()
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "system.gpu_perf":
            return await _execute_gpu_tool(tool_name)

        elif tool_name == "system.gpu_health":
            return await _execute_gpu_tool(tool_name)

        elif tool_name == "system.cache_stats":
            from ai.cache import get_cache_stats  # noqa: PLC0415

            result = get_cache_stats()
            return json.dumps(result, indent=2)

        elif tool_name == "system.token_report":
            return await _execute_token_report()

        elif tool_name == "security.correlate":
            from ai.threat_intel.correlator import correlate_ioc  # noqa: PLC0415

            ioc = args.get("ioc", "")
            ioc_type = args.get("ioc_type", "hash")
            if not ioc:
                return json.dumps({"error": "Missing required argument: ioc"}, indent=2)
            report = correlate_ioc(ioc, ioc_type)
            return json.dumps(report.to_dict(), indent=2)

        elif tool_name == "security.recommend_action":
            from ai.threat_intel.playbooks import get_response_plan  # noqa: PLC0415

            finding_type = args.get("finding_type", "")
            finding_id = args.get("finding_id", "")
            if not finding_type or not finding_id:
                return json.dumps(
                    {"error": "Missing required arguments: finding_type, finding_id"},
                    indent=2,
                )
            response = get_response_plan(finding_type, finding_id)
            return json.dumps(response.to_dict(), indent=2)

        elif tool_name == "system.insights":
            from ai.insights import get_engine  # noqa: PLC0415

            result = get_engine().generate_on_demand()
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "security.run_ingest":
            proc = await asyncio.create_subprocess_exec(
                str(Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"),
                "-m",
                "ai.log_intel",
                "--all",
                cwd=str(Path(__file__).parent.parent.parent),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            return _truncate(stdout.decode("utf-8", errors="replace"))

        else:
            return f"[Tool '{tool_name}' not implemented]"

    except ImportError as e:
        return f"[Module not available: {e}]"
    except Exception as e:
        logger.error("Tool '%s' failed: %s", tool_name, e)
        return f"[Tool error: {e}]"
