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

        arg_type = constraints.get("type", "string")

        if arg_type in {"string", "str"}:
            if not isinstance(value, str):
                raise ValueError(f"Argument '{arg_name}' must be a string")
        elif arg_type in {"integer", "int"}:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Argument '{arg_name}' must be an integer")
        elif arg_type in {"number", "float"}:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"Argument '{arg_name}' must be a number")
        elif arg_type in {"bool", "boolean"}:
            if not isinstance(value, bool):
                raise ValueError(f"Argument '{arg_name}' must be a boolean")
        else:
            if not isinstance(value, str):
                raise ValueError(f"Argument '{arg_name}' must be a string")

        # Pattern validation (regex)
        pattern = constraints.get("pattern")
        if pattern and isinstance(value, str) and not re.match(pattern, value):
            raise ValueError(f"Argument '{arg_name}' does not match pattern '{pattern}'")

        # Length validation
        max_length = constraints.get("max_length")
        if max_length and isinstance(value, str) and len(value) > max_length:
            raise ValueError(f"Argument '{arg_name}' exceeds max length {max_length}")

        min_value = constraints.get("min")
        max_value = constraints.get("max")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if min_value is not None and value < min_value:
                raise ValueError(f"Argument '{arg_name}' must be >= {min_value}")
            if max_value is not None and value > max_value:
                raise ValueError(f"Argument '{arg_name}' must be <= {max_value}")


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
    """Execute a tool and return redacted output safe to return to clients.

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
                "how_to_switch": "Set request model to one of these mode names "
                "(for example: 'fast', 'reason', or 'code').",
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

        # P84 Security Ops Center tools
        elif tool_name == "security.ops_overview":
            from ai.security_service import SECURITY_DIR, STATUS_FILE, get_overview  # noqa: PLC0415

            try:
                result = get_overview()

                # Check if critical files are missing
                missing_files = []
                if not STATUS_FILE.exists():
                    missing_files.append("security status")
                if not (SECURITY_DIR / "alerts.json").exists():
                    missing_files.append("alerts data")

                response = {
                    "success": True,
                    "data": result,
                }

                if missing_files:
                    response["partial_data"] = True
                    response["missing_sources"] = missing_files
                    response["operator_action"] = (
                        f"Some data sources unavailable: {', '.join(missing_files)}. "
                        "Run security scans to generate initial data."
                    )

                return json.dumps(response, indent=2)
            except Exception as e:
                logger.error("security.ops_overview failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "overview_unavailable",
                        "error": "Failed to get security overview",
                        "operator_action": "Check security service health and status files",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.ops_alerts":
            from ai.security_service import ALERTS_FILE, get_alerts  # noqa: PLC0415

            try:
                severity = args.get("severity")
                limit = args.get("limit", 50)

                # Check if alerts file exists
                if not ALERTS_FILE.exists():
                    return json.dumps(
                        {
                            "success": False,
                            "error_code": "alerts_file_unavailable",
                            "error": "Alerts file not found",
                            "operator_action": "Check security-alert.timer is enabled and running",
                            "alerts_file_path": str(ALERTS_FILE),
                        },
                        indent=2,
                    )

                alerts = get_alerts(severity=severity, limit=limit)
                return json.dumps(
                    {
                        "success": True,
                        "alerts": alerts,
                        "count": len(alerts),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.ops_alerts failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "alerts_unavailable",
                        "error": "Failed to get security alerts",
                        "operator_action": "Check alerts file and security service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.ops_findings":
            from ai.security_service import CLAMAV_LOG_DIR, get_findings  # noqa: PLC0415

            try:
                limit = args.get("limit", 20)
                findings = get_findings(limit=limit)

                # Check if log directory is accessible
                logs_available = CLAMAV_LOG_DIR.exists() and any(CLAMAV_LOG_DIR.glob("*.log"))

                return json.dumps(
                    {
                        "success": True,
                        "findings": findings,
                        "count": len(findings),
                        "logs_available": logs_available,
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.ops_findings failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "findings_unavailable",
                        "error": "Failed to get scan findings",
                        "operator_action": "Check ClamAV log directory permissions",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.ops_provider_health":
            from ai.security_service import get_provider_health_issues  # noqa: PLC0415

            try:
                issues = get_provider_health_issues()
                return json.dumps(
                    {
                        "success": True,
                        "issues": issues,
                        "count": len(issues),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.ops_provider_health failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_health_unavailable",
                        "error": "Failed to get provider health issues",
                        "operator_action": "Check LLM status file and provider service",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.ops_acknowledge":
            from ai.security_service import acknowledge_alert  # noqa: PLC0415

            try:
                alert_id = args.get("alert_id", "")
                if not alert_id:
                    return json.dumps(
                        {
                            "success": False,
                            "error_code": "alert_id_required",
                            "error": "Alert ID is required",
                            "operator_action": "Provide the alert_id to acknowledge",
                        },
                        indent=2,
                    )

                result = acknowledge_alert(alert_id)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error("security.ops_acknowledge failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "acknowledge_failed",
                        "error": "Failed to acknowledge alert",
                        "operator_action": "Check alert ID and security service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        # P121 Security Autopilot UI tools (read-only)
        elif tool_name == "security.autopilot_overview":
            from ai.security_autopilot.ui_service import get_autopilot_overview  # noqa: PLC0415

            try:
                return json.dumps(
                    {
                        "success": True,
                        "data": get_autopilot_overview(),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_overview failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_overview_unavailable",
                        "error": "Failed to load security autopilot overview",
                        "operator_action": "Check security service and autopilot modules",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.autopilot_findings":
            from ai.security_autopilot.ui_service import get_autopilot_findings  # noqa: PLC0415

            try:
                limit = args.get("limit", 50)
                findings = get_autopilot_findings(limit=limit)
                return json.dumps(
                    {
                        "success": True,
                        "findings": findings,
                        "count": len(findings),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_findings failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_findings_unavailable",
                        "error": "Failed to load security autopilot findings",
                        "operator_action": "Check source security signals and service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.autopilot_incidents":
            from ai.security_autopilot.ui_service import get_autopilot_incidents  # noqa: PLC0415

            try:
                limit = args.get("limit", 25)
                incidents = get_autopilot_incidents(limit=limit)
                return json.dumps(
                    {
                        "success": True,
                        "incidents": incidents,
                        "count": len(incidents),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_incidents failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_incidents_unavailable",
                        "error": "Failed to load security autopilot incidents",
                        "operator_action": "Check autopilot classifier inputs and service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.autopilot_evidence":
            from ai.security_autopilot.ui_service import get_autopilot_evidence  # noqa: PLC0415

            try:
                limit = args.get("limit", 25)
                evidence = get_autopilot_evidence(limit=limit)
                return json.dumps(
                    {
                        "success": True,
                        "bundles": evidence,
                        "count": len(evidence),
                        "persisted": False,
                        "operator_note": (
                            "Evidence bundles are redacted and derived in-memory for UI review"
                        ),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_evidence failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_evidence_unavailable",
                        "error": "Failed to load security autopilot evidence",
                        "operator_action": "Check autopilot evidence manager and upstream findings",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.autopilot_audit":
            from ai.security_autopilot.ui_service import get_autopilot_audit_events  # noqa: PLC0415

            try:
                limit = args.get("limit", 50)
                events = get_autopilot_audit_events(limit=limit)
                return json.dumps(
                    {
                        "success": True,
                        "events": events,
                        "count": len(events),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_audit failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_audit_unavailable",
                        "error": "Failed to load security autopilot audit events",
                        "operator_action": "Check autopilot audit ledger path and permissions",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.autopilot_policy":
            from ai.security_autopilot.ui_service import (  # noqa: PLC0415
                get_autopilot_policy_status,
            )

            try:
                return json.dumps(
                    {
                        "success": True,
                        "policy": get_autopilot_policy_status(),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_policy failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_policy_unavailable",
                        "error": "Failed to load security autopilot policy status",
                        "operator_action": "Check security-autopilot-policy.yaml configuration",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "security.autopilot_remediation_queue":
            from ai.security_autopilot.ui_service import (  # noqa: PLC0415
                get_autopilot_remediation_queue,
            )

            try:
                limit = args.get("limit", 25)
                queue = get_autopilot_remediation_queue(limit=limit)
                return json.dumps(
                    {
                        "success": True,
                        "queue": queue,
                        "count": len(queue),
                        "execution": "plan-only",
                        "operator_note": "No remediation is executed from this queue",
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("security.autopilot_remediation_queue failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "autopilot_queue_unavailable",
                        "error": "Failed to load security autopilot remediation queue",
                        "operator_action": "Check autopilot planner and policy services",
                        "details": str(e),
                    },
                    indent=2,
                )

        # P85/P94 Interactive Shell Gateway tools
        elif tool_name == "shell.create_session":
            from ai.shell_service import create_session  # noqa: PLC0415

            name = args.get("name")
            cwd = args.get("cwd")
            return json.dumps(create_session(name=name, cwd=cwd), indent=2)

        elif tool_name == "shell.list_sessions":
            from ai.shell_service import list_sessions  # noqa: PLC0415

            return json.dumps(list_sessions(), indent=2)

        elif tool_name == "shell.get_session":
            from ai.shell_service import get_session  # noqa: PLC0415

            session_id = args.get("session_id", "")
            return json.dumps(get_session(session_id), indent=2)

        elif tool_name == "shell.execute_command":
            from ai.shell_service import execute_command  # noqa: PLC0415

            session_id = args.get("session_id", "")
            command = args.get("command", "")
            return json.dumps(execute_command(session_id, command), indent=2)

        elif tool_name == "shell.terminate_session":
            from ai.shell_service import terminate_session  # noqa: PLC0415

            session_id = args.get("session_id", "")
            return json.dumps(terminate_session(session_id), indent=2)

        elif tool_name == "shell.get_context":
            from ai.shell_service import get_session_context  # noqa: PLC0415

            session_id = args.get("session_id", "")
            return json.dumps(get_session_context(session_id), indent=2)

        elif tool_name == "shell.get_audit_log":
            from ai.shell_service import get_audit_log  # noqa: PLC0415

            session_id = args.get("session_id")
            limit = args.get("limit", 100)
            return json.dumps(get_audit_log(session_id=session_id, limit=limit), indent=2)

        # P86 Project + Workflow + Phase Panels tools
        elif tool_name == "project.context":
            from ai.project_workflow_service import get_project_context  # noqa: PLC0415

            return json.dumps(get_project_context(), indent=2)

        elif tool_name == "project.workflow_history":
            from ai.project_workflow_service import get_workflow_history  # noqa: PLC0415

            limit = args.get("limit", 20)
            return json.dumps(get_workflow_history(limit=limit), indent=2)

        elif tool_name == "project.phase_timeline":
            from ai.project_workflow_service import get_phase_timeline  # noqa: PLC0415

            return json.dumps(get_phase_timeline(), indent=2)

        elif tool_name == "project.artifacts":
            from ai.project_workflow_service import get_recent_artifacts  # noqa: PLC0415

            limit = args.get("limit", 20)
            return json.dumps(get_recent_artifacts(limit=limit), indent=2)

        # P123 Agent Workbench tools
        elif tool_name == "workbench.project_register":
            from ai.agent_workbench import get_registry  # noqa: PLC0415

            registry = get_registry()
            tags_raw = args.get("tags", "")
            tags = [item.strip() for item in tags_raw.split(",") if item.strip()]
            project = registry.register_project(
                path=args.get("path", ""),
                name=args.get("name") or None,
                tags=tags,
                description=args.get("description", ""),
                allow_non_project_dirs=bool(args.get("allow_non_project_dirs", False)),
            )
            return json.dumps(
                {
                    "success": True,
                    "project": project.to_dict(),
                    "allowed_roots": registry.allowed_roots,
                },
                indent=2,
            )

        elif tool_name == "workbench.project_list":
            from ai.agent_workbench import get_registry  # noqa: PLC0415

            registry = get_registry()
            projects = [item.to_dict() for item in registry.list_projects()]
            return json.dumps(
                {"success": True, "projects": projects, "count": len(projects)},
                indent=2,
            )

        elif tool_name == "workbench.project_open":
            from ai.agent_workbench import get_registry  # noqa: PLC0415

            registry = get_registry()
            project = registry.open_project(args.get("project_id", ""))
            return json.dumps({"success": True, "project": project.to_dict()}, indent=2)

        elif tool_name == "workbench.project_status":
            from ai.agent_workbench import get_registry  # noqa: PLC0415

            registry = get_registry()
            status = registry.project_status(args.get("project_id", ""))
            return json.dumps({"success": True, **status}, indent=2)

        elif tool_name == "workbench.session_create":
            from ai.agent_workbench import get_session_manager  # noqa: PLC0415

            manager = get_session_manager()
            session = manager.create_session(
                project_id=args.get("project_id", ""),
                backend=args.get("backend", ""),
                cwd=args.get("cwd") or None,
                sandbox_profile=args.get("sandbox_profile", "conservative"),
                lease_minutes=int(args.get("lease_minutes", 0) or 0) or None,
            )
            return json.dumps({"success": True, "session": session.to_dict()}, indent=2)

        elif tool_name == "workbench.session_list":
            from ai.agent_workbench import get_session_manager  # noqa: PLC0415

            manager = get_session_manager()
            sessions = [
                item.to_dict()
                for item in manager.list_sessions(
                    project_id=args.get("project_id") or None,
                    status=args.get("status") or None,
                )
            ]
            return json.dumps(
                {"success": True, "sessions": sessions, "count": len(sessions)},
                indent=2,
            )

        elif tool_name == "workbench.session_get":
            from ai.agent_workbench import get_session_manager  # noqa: PLC0415

            manager = get_session_manager()
            session = manager.get_session(args.get("session_id", ""))
            if session is None:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "session_not_found",
                        "error": "Session not found",
                    },
                    indent=2,
                )
            return json.dumps({"success": True, "session": session.to_dict()}, indent=2)

        elif tool_name == "workbench.session_stop":
            from ai.agent_workbench import get_session_manager  # noqa: PLC0415

            manager = get_session_manager()
            session = manager.stop_session(args.get("session_id", ""))
            return json.dumps({"success": True, "session": session.to_dict()}, indent=2)

        elif tool_name == "workbench.git_status":
            from ai.agent_workbench import get_git_status_summary, get_registry  # noqa: PLC0415

            registry = get_registry()
            project = registry.get_project(args.get("project_id", ""))
            if project is None:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "project_not_found",
                        "error": "Project not found",
                    },
                    indent=2,
                )
            summary = get_git_status_summary(project.root_path)
            return json.dumps({"success": True, "git": summary.to_dict()}, indent=2)

        elif tool_name == "workbench.test_commands":
            from ai.agent_workbench import get_registry, get_test_hooks  # noqa: PLC0415

            registry = get_registry()
            project = registry.get_project(args.get("project_id", ""))
            if project is None:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "project_not_found",
                        "error": "Project not found",
                    },
                    indent=2,
                )

            hooks = get_test_hooks()
            hooks.ensure_defaults(project.project_id, project.root_path)
            execute = bool(args.get("execute", False))
            command_name = args.get("command_name", "")
            if execute:
                if not command_name:
                    return json.dumps(
                        {
                            "success": False,
                            "error_code": "command_name_required",
                            "error": "command_name is required when execute=true",
                        },
                        indent=2,
                    )
                result = hooks.execute_command(project.project_id, command_name, project.root_path)
                return json.dumps({"success": True, "execution": result}, indent=2)

            commands = hooks.list_commands(project.project_id)
            return json.dumps(
                {
                    "success": True,
                    "project_id": project.project_id,
                    "commands": commands,
                    "count": len(commands),
                },
                indent=2,
            )

        elif tool_name == "workbench.handoff_note":
            from ai.agent_workbench import append_handoff_note  # noqa: PLC0415

            artifacts_raw = args.get("artifacts", "")
            artifacts = [item.strip() for item in artifacts_raw.split(",") if item.strip()]
            result = append_handoff_note(
                summary=args.get("summary", ""),
                artifacts=artifacts,
                phase=args.get("phase", "P123"),
                session_id=args.get("session_id") or None,
            )
            return json.dumps(result, indent=2)

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

        elif tool_name == "code.fused_context":
            from ai.rag.code_query import code_fused_context  # noqa: PLC0415

            question = args.get("question", "")
            result = code_fused_context(question)
            return _truncate(_redact_paths(json.dumps(result, indent=2)))

        elif tool_name == "system.mcp_manifest":
            allowlist = _load_allowlist()
            compact_tools = {}
            for name, defn in allowlist.items():
                desc = defn.get("description", "")[:20]
                arg_defs = defn.get("args") or {}
                arg_names = list(arg_defs.keys()) if isinstance(arg_defs, dict) else []
                compact_tools[name] = {"desc": desc, "args": arg_names}
            manifest = {"tool_count": len(compact_tools), "tools": compact_tools}
            limit = _TOOL_OUTPUT_LIMITS.get("system.mcp_manifest", _DEFAULT_OUTPUT_LIMIT)
            return _truncate(json.dumps(manifest, separators=(",", ":")), limit)

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

        elif tool_name == "intel.scrape_now":
            result = await handle_intel_scrape_now(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "intel.ingest_pending":
            result = await handle_intel_ingest_pending(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "system.dep_scan":
            result = await handle_dep_scan(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "system.test_analysis":
            result = await handle_test_analysis(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "system.perf_profile":
            result = await handle_perf_profile(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "system.mcp_audit":
            result = await handle_mcp_audit(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "slack.list_channels":
            result = await handle_slack_list_channels(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "slack.post_message":
            result = await handle_slack_post_message(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "slack.list_users":
            result = await handle_slack_list_users(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "slack.get_history":
            result = await handle_slack_get_history(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.list":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_list

            result = await workflow_list(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.run":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_run

            result = await workflow_run(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.status":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_status

            result = await workflow_status(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.agents":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_agents

            result = await workflow_agents(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.handoff":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_handoff

            result = await workflow_handoff(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.status":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_status_steps

            result = await workflow_status_steps(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.history_steps":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_history_steps

            result = await workflow_history_steps(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.cancel":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_cancel_steps

            result = await workflow_cancel_steps(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "workflow.history":
            from ai.mcp_bridge.handlers.workflow_tools import workflow_history

            result = await workflow_history(args)
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "system.alert_history":
            from ai.alerts.history import get_recent  # noqa: PLC0415

            result = get_recent(limit=int(args.get("limit", 20)))
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "system.alert_rules":
            import dataclasses as _dc  # noqa: PLC0415

            from ai.alerts.rules import RulesEngine  # noqa: PLC0415

            engine = RulesEngine()
            rules = engine.get_all_rules()
            serializable = [_dc.asdict(r) if _dc.is_dataclass(r) else r.__dict__ for r in rules]
            return _truncate(json.dumps(serializable, indent=2, default=str))

        elif tool_name == "system.dep_audit":
            import dataclasses as _dc  # noqa: PLC0415

            from ai.system.depaudit import get_latest_report  # noqa: PLC0415

            report = get_latest_report()
            if report is None:
                return json.dumps({"status": "no_data", "message": "No audit reports found"})
            data = _dc.asdict(report) if _dc.is_dataclass(report) else report.__dict__
            return _truncate(json.dumps(data, indent=2, default=str))

        elif tool_name == "system.dep_audit_history":
            from ai.system.depaudit import get_report_history  # noqa: PLC0415

            result = get_report_history(limit=int(args.get("limit", 30)))
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "knowledge.task_patterns":
            from ai.learning.task_retriever import retrieve_similar_tasks  # noqa: PLC0415

            result = retrieve_similar_tasks(
                query=args.get("query", ""),
                top_k=int(args.get("top_k", 5)),
            )
            return _truncate(json.dumps(result, indent=2))

        elif tool_name == "knowledge.session_history":
            import dataclasses as _dc  # noqa: PLC0415

            from ai.learning.handoff_parser import parse_handoff  # noqa: PLC0415

            handoff_path = Path(__file__).parent.parent.parent / "HANDOFF.md"
            entries = parse_handoff(handoff_path)
            query = args.get("query", "").lower()
            limit = int(args.get("limit", 5))
            if query:
                entries = [
                    e
                    for e in entries
                    if query in (getattr(e, "description", "") or "").lower()
                    or query in (getattr(e, "summary", "") or "").lower()
                ]
            entries = entries[:limit]
            serializable = [_dc.asdict(e) if _dc.is_dataclass(e) else e.__dict__ for e in entries]
            return _truncate(json.dumps(serializable, indent=2, default=str))

        elif tool_name == "system.budget_status":
            from ai.budget import get_budget  # noqa: PLC0415

            budget = get_budget()
            return _truncate(json.dumps(budget.get_status(), indent=2))

        elif tool_name == "system.metrics_summary":
            from ai.metrics import get_metrics  # noqa: PLC0415

            result = get_metrics()
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "memory.search":
            from ai.memory import get_memory  # noqa: PLC0415

            mem = get_memory()
            result = mem.search_memories(
                query=args.get("query", ""),
                top_k=int(args.get("top_k", 5)),
            )
            return _truncate(result)

        elif tool_name == "provenance.timeline":
            from ai.provenance import get_provenance_graph  # noqa: PLC0415

            graph = get_provenance_graph()
            result = graph.query_timeline(
                workspace_id=args.get("workspace_id", ""),
                actor_id=args.get("actor_id") or None,
                project_id=args.get("project_id") or None,
                session_id=args.get("session_id") or None,
                record_id=args.get("record_id") or None,
                limit=int(args.get("limit", 50)),
            )
            return _truncate(_redact_paths(json.dumps(result, indent=2)))

        elif tool_name == "provenance.explain":
            from ai.provenance import get_provenance_graph  # noqa: PLC0415

            graph = get_provenance_graph()
            result = graph.explain_record(
                workspace_id=args.get("workspace_id", ""),
                actor_id=args.get("actor_id") or None,
                project_id=args.get("project_id") or None,
                session_id=args.get("session_id") or None,
                record_id=args.get("record_id", ""),
                depth=int(args.get("depth", 2)),
            )
            return _truncate(_redact_paths(json.dumps(result, indent=2)))

        elif tool_name == "provenance.what_changed":
            from ai.provenance import get_provenance_graph  # noqa: PLC0415

            graph = get_provenance_graph()
            result = graph.query_what_changed(
                workspace_id=args.get("workspace_id", ""),
                actor_id=args.get("actor_id") or None,
                project_id=args.get("project_id") or None,
                session_id=args.get("session_id") or None,
                limit=int(args.get("limit", 50)),
            )
            return _truncate(_redact_paths(json.dumps(result, indent=2)))

        elif tool_name == "system.provider_status":
            from ai.provider_intel import get_intel  # noqa: PLC0415

            intel = get_intel()
            return _truncate(json.dumps(intel.get_status(), indent=2))

        elif tool_name == "system.weekly_insights":
            from ai.insights import get_engine  # noqa: PLC0415

            engine = get_engine()
            limit = int(args.get("limit", 4))
            result = engine.get_cached_insights()[:limit]
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "collab.queue_status":
            from ai.collab.task_queue import get_queue  # noqa: PLC0415

            queue = get_queue()
            return _truncate(json.dumps(queue.get_queue_status(), indent=2))

        elif tool_name == "collab.add_task":
            from ai.collab.task_queue import TaskType, get_queue  # noqa: PLC0415

            queue = get_queue()
            try:
                task_type_val = TaskType(args.get("task_type", "implement_feature"))
            except ValueError:
                task_type_val = TaskType.IMPLEMENT_FEATURE
            task_id = queue.add_task(
                title=args.get("title", ""),
                task_type=task_type_val,
                description=args.get("description", ""),
                priority=int(args.get("priority", 3)),
            )
            return json.dumps({"task_id": task_id, "status": "created"})

        elif tool_name == "collab.search_knowledge":
            from ai.collab.knowledge_base import get_agent_knowledge  # noqa: PLC0415

            kb = get_agent_knowledge()
            result = kb.query_knowledge(
                query=args.get("query", ""),
                top_k=int(args.get("top_k", 5)),
            )
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "workflow.run":
            from ai.workflows.runner import execute_workflow  # noqa: PLC0415

            message = args.get("workflow_id") or args.get("steps") or ""
            result = await execute_workflow(user_message=message, task_type="fast")
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "workflow.list":
            from ai.workflows.definitions import get_workflow_store  # noqa: PLC0415

            store = get_workflow_store()
            result = store.list_workflows()
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "system.create_tool":
            from ai.tools.builder import get_builder  # noqa: PLC0415

            params_raw = args.get("parameters")
            params = json.loads(params_raw) if isinstance(params_raw, str) else params_raw
            builder = get_builder()
            result = builder.create_tool(
                name=args.get("name", ""),
                description=args.get("description", ""),
                handler_code=args.get("handler_code", ""),
                parameters=params,
                created_by=args.get("created_by", "system"),
            )
            return json.dumps(result, indent=2, default=str)

        elif tool_name == "system.list_dynamic_tools":
            from ai.tools.builder import get_builder  # noqa: PLC0415

            builder = get_builder()
            result = builder.list_dynamic_tools()
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.impact_analysis":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            changed = [f.strip() for f in args.get("changed_files", "").split(",") if f.strip()]
            include_tests = bool(args.get("include_tests", True))
            depth = int(args.get("max_depth", 3))
            result = store.query_impact(
                changed,
                max_depth=depth,
                include_tests=include_tests,
            )
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.dependency_graph":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            module = args.get("module", "")
            direction = args.get("direction", "both")
            depth = int(args.get("max_depth", 3))
            result = store.query_dependency_graph(module, direction=direction, max_depth=depth)
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.blast_radius":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            changed = [f.strip() for f in args.get("changed_files", "").split(",") if f.strip()]
            depth = int(args.get("max_depth", 3))
            result = store.query_blast_radius(changed, max_depth=depth)
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.find_callers":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            function_name = args.get("function_name", "")
            include_indirect = args.get("include_indirect", True)
            result = store.find_callers(function_name, include_indirect)
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.suggest_tests":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            changed = [f.strip() for f in args.get("changed_files", "").split(",") if f.strip()]
            result = store.suggest_tests(changed)
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.complexity_report":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            target = args.get("target", None)
            threshold = int(args.get("threshold", 10))
            result = store.get_complexity_report(target, threshold)
            return _truncate(json.dumps(result, indent=2, default=str))

        elif tool_name == "code.class_hierarchy":
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            class_name = args.get("class_name", "")
            result = store.get_class_hierarchy(class_name)
            return _truncate(json.dumps(result, indent=2, default=str))

        # P81 — Settings Service Tools
        elif tool_name == "settings.pin_status":
            from ai.settings_service import get_pin_manager  # noqa: PLC0415

            try:
                pm = get_pin_manager()
                return json.dumps(
                    {
                        "success": True,
                        "pin_is_set": pm.is_pin_set(),
                        "lockout": pm.get_lockout_status(),
                    },
                    indent=2,
                )
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "settings_backend_unavailable",
                        "error": "Settings backend unavailable",
                        "operator_action": "Check MCP bridge and settings service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.setup_pin":
            from ai.settings_service import setup_settings_pin  # noqa: PLC0415

            pin = args.get("pin")
            if not pin:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_required",
                        "error": "PIN is required",
                        "operator_action": "Provide a 4-6 digit PIN",
                    },
                    indent=2,
                )

            try:
                return json.dumps(setup_settings_pin(pin), indent=2)
            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_validation_failed",
                        "error": str(e),
                        "operator_action": "Provide a valid 4-6 digit PIN containing only numbers",
                    },
                    indent=2,
                )
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_setup_failed",
                        "error": "Failed to set up PIN",
                        "operator_action": "Check settings database permissions and try again",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.verify_pin":
            from ai.settings_service import unlock_settings  # noqa: PLC0415

            pin = args.get("pin")
            if not pin:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_required",
                        "error": "PIN is required",
                        "operator_action": "Enter your PIN to unlock settings",
                    },
                    indent=2,
                )

            try:
                result = unlock_settings(pin)
                return json.dumps(result, indent=2)
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "unlock_failed",
                        "error": "Failed to unlock settings",
                        "operator_action": "Check settings service health and try again",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.list_secrets":
            from ai.config import KEYS_ENV  # noqa: PLC0415
            from ai.settings_service import get_secrets_service  # noqa: PLC0415

            try:
                # Check if keys.env exists and is readable
                if not KEYS_ENV.exists():
                    return json.dumps(
                        {
                            "success": False,
                            "error_code": "keys_file_not_found",
                            "error": "API keys file not found",
                            "operator_action": f"Create {KEYS_ENV} or add API keys",
                            "keys_env_path": str(KEYS_ENV),
                        },
                        indent=2,
                    )

                service = get_secrets_service()
                secrets = service.list_secrets(include_values=False)
                return json.dumps(
                    [
                        {
                            "name": s.name,
                            "masked_value": s.masked_value,
                            "category": s.category,
                            "is_set": s.is_set,
                        }
                        for s in secrets
                    ],
                    indent=2,
                )
            except PermissionError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "keys_file_permission_denied",
                        "error": "Permission denied reading API keys file",
                        "operator_action": f"Check file permissions on {KEYS_ENV}",
                        "details": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "secrets_unavailable",
                        "error": "Failed to list secrets",
                        "operator_action": "Check MCP bridge logs and settings service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.reveal_secret":
            from ai.settings_service import get_secrets_service  # noqa: PLC0415

            key_name = args.get("key_name")
            pin = args.get("pin")

            if not key_name:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "key_name_required",
                        "error": "Secret key name is required",
                        "operator_action": "Provide the name of the secret to reveal",
                    },
                    indent=2,
                )

            if not pin:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_required",
                        "error": "PIN is required",
                        "operator_action": "Enter your PIN to reveal secrets",
                    },
                    indent=2,
                )

            try:
                service = get_secrets_service()
                result = service.reveal_secret_result(key_name, pin)
                if result.get("success"):
                    entry = result["entry"]
                    return json.dumps(
                        {
                            "name": entry.name,
                            "value": entry.value,
                            "masked_value": entry.masked_value,
                            "category": entry.category,
                        },
                        indent=2,
                    )
                return json.dumps(result, indent=2)
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "reveal_failed",
                        "error": "Failed to reveal secret",
                        "operator_action": "Check settings service health and try again",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.set_secret":
            from ai.settings_service import get_secrets_service  # noqa: PLC0415

            key_name = args.get("key_name")
            value = args.get("value")
            pin = args.get("pin")

            if not key_name:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "key_name_required",
                        "error": "Secret key name is required",
                        "operator_action": "Provide the name of the secret to set",
                    },
                    indent=2,
                )

            if value is None:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "value_required",
                        "error": "Secret value is required",
                        "operator_action": "Provide the secret value",
                    },
                    indent=2,
                )

            if not pin:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_required",
                        "error": "PIN is required",
                        "operator_action": "Enter your PIN to modify secrets",
                    },
                    indent=2,
                )

            try:
                service = get_secrets_service()
                result = service.set_secret_result(key_name, value, pin)
                return json.dumps(result, indent=2)
            except PermissionError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "keys_file_permission_denied",
                        "error": "Permission denied writing API keys file",
                        "operator_action": "Check file permissions on keys.env directory",
                        "details": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "set_secret_failed",
                        "error": "Failed to set secret",
                        "operator_action": "Check settings service health and try again",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.delete_secret":
            from ai.settings_service import get_secrets_service  # noqa: PLC0415

            key_name = args.get("key_name")
            pin = args.get("pin")

            if not key_name:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "key_name_required",
                        "error": "Secret key name is required",
                        "operator_action": "Provide the name of the secret to delete",
                    },
                    indent=2,
                )

            if not pin:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "pin_required",
                        "error": "PIN is required",
                        "operator_action": "Enter your PIN to delete secrets",
                    },
                    indent=2,
                )

            try:
                service = get_secrets_service()
                result = service.delete_secret_result(key_name, pin)
                return json.dumps(result, indent=2)
            except PermissionError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "keys_file_permission_denied",
                        "error": "Permission denied writing API keys file",
                        "operator_action": "Check file permissions on keys.env directory",
                        "details": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "delete_secret_failed",
                        "error": "Failed to delete secret",
                        "operator_action": "Check settings service health and try again",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "settings.audit_log":
            from ai.settings_service import get_audit_logger  # noqa: PLC0415

            try:
                audit = get_audit_logger()
                entries = audit.get_recent(args.get("limit", 100))
                return json.dumps(
                    {
                        "success": True,
                        "entries": entries,
                        "count": len(entries),
                    },
                    indent=2,
                )
            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "audit_log_unavailable",
                        "error": "Failed to retrieve audit log",
                        "operator_action": "Check settings service health and file permissions",
                        "details": str(e),
                    },
                    indent=2,
                )

        # P82 — Provider Service Tools
        elif tool_name == "providers.discover":
            from ai.provider_service import (  # noqa: PLC0415
                LITELLM_CONFIG_PATH,
                get_provider_service,
            )

            try:
                # Check config file exists
                if not LITELLM_CONFIG_PATH.exists():
                    return json.dumps(
                        {
                            "success": False,
                            "error_code": "config_unavailable",
                            "error": "LiteLLM configuration file not found",
                            "operator_action": "Create litellm-config.yaml or verify permissions",
                            "config_path": str(LITELLM_CONFIG_PATH),
                        },
                        indent=2,
                    )

                service = get_provider_service()
                providers = service.discover_providers()

                # Calculate counts
                configured_count = sum(1 for p in providers if p.is_configured)
                healthy_count = sum(1 for p in providers if p.is_healthy)
                degraded_count = sum(1 for p in providers if p.status == "degraded")
                blocked_count = sum(1 for p in providers if p.status == "blocked")

                return json.dumps(
                    {
                        "success": True,
                        "providers": [
                            {
                                "id": p.id,
                                "name": p.name,
                                "status": p.status,
                                "is_configured": p.is_configured,
                                "is_healthy": p.is_healthy,
                                "is_local": p.is_local,
                                "health_score": p.health_score,
                                "models": [
                                    {"id": m.id, "name": m.name, "task_types": m.task_types}
                                    for m in p.models
                                ],
                                "last_error": p.last_error,
                            }
                            for p in providers
                        ],
                        "counts": {
                            "total": len(providers),
                            "configured": configured_count,
                            "healthy": healthy_count,
                            "degraded": degraded_count,
                            "blocked": blocked_count,
                        },
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("providers.discover failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_discovery_failed",
                        "error": "Failed to discover providers",
                        "operator_action": "Check provider service health and configuration",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "providers.models":
            from ai.provider_service import get_provider_service  # noqa: PLC0415

            try:
                service = get_provider_service()
                models = service.get_model_catalog()

                return json.dumps(
                    {
                        "success": True,
                        "models": [
                            {
                                "id": m.id,
                                "name": m.name,
                                "provider": m.provider,
                                "task_types": m.task_types,
                            }
                            for m in models
                        ],
                        "count": len(models),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("providers.models failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "model_catalog_failed",
                        "error": "Failed to get model catalog",
                        "operator_action": "Check provider service health",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "providers.routing":
            from ai.provider_service import get_provider_service  # noqa: PLC0415

            try:
                service = get_provider_service()
                routing = service.get_routing_config()

                return json.dumps(
                    {
                        "success": True,
                        "routing": [
                            {
                                "task_type": r.task_type,
                                "task_label": r.task_label,
                                "primary_provider": r.primary_provider,
                                "fallback_chain": r.fallback_chain,
                                "eligible_models": [
                                    {"id": m.id, "name": m.name, "provider": m.provider}
                                    for m in r.eligible_models
                                ],
                                "health_state": r.health_state,
                                "caveats": r.caveats,
                            }
                            for r in routing
                        ],
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("providers.routing failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "routing_config_failed",
                        "error": "Failed to get routing configuration",
                        "operator_action": "Check LiteLLM configuration file",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "providers.refresh":
            from ai.provider_service import get_provider_service  # noqa: PLC0415

            try:
                service = get_provider_service()
                result = service.refresh()
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error("providers.refresh failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "refresh_failed",
                        "error": "Failed to refresh provider data",
                        "operator_action": "Check provider service health and file permissions",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "providers.health":
            from ai.provider_service import get_provider_service  # noqa: PLC0415

            try:
                service = get_provider_service()
                tracker = service.get_health_tracker()
                providers = service.discover_providers()

                health_data = {}
                auth_broken_providers = []
                cooldown_providers = []

                for p in providers:
                    h = tracker.get(p.id)
                    health_data[p.id] = {
                        "score": h.effective_score,
                        "success_count": h.success_count,
                        "failure_count": h.failure_count,
                        "consecutive_failures": h.consecutive_failures,
                        "is_disabled": h.is_disabled,
                        "auth_broken": h.auth_broken,
                    }
                    if h.auth_broken:
                        auth_broken_providers.append(p.id)
                    elif h.is_disabled:
                        cooldown_providers.append(p.id)

                return json.dumps(
                    {
                        "success": True,
                        "health": health_data,
                        "summary": {
                            "auth_broken_count": len(auth_broken_providers),
                            "auth_broken_providers": auth_broken_providers,
                            "cooldown_count": len(cooldown_providers),
                            "cooldown_providers": cooldown_providers,
                        },
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("providers.health failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "health_data_failed",
                        "error": "Failed to get provider health data",
                        "operator_action": "Check health tracker and provider service",
                        "details": str(e),
                    },
                    indent=2,
                )

        # P115: Provider Registry Tools
        elif tool_name == "provider.list":
            from ai.provider_registry import (  # noqa: PLC0415
                get_provider_registry,
            )

            try:
                registry = get_provider_registry()
                include_disabled = args.get("include_disabled", False)
                providers = registry.list_providers(include_disabled=include_disabled)

                return json.dumps(
                    {
                        "success": True,
                        "providers": [
                            {
                                "provider_id": p.provider_id,
                                "display_name": p.display_name,
                                "provider_type": p.provider_type,
                                "base_url": p.base_url,
                                "enabled": p.enabled,
                                "credential_ref": p.credential_ref,
                                "models": [
                                    {
                                        "id": m.id,
                                        "name": m.name,
                                        "task_types": m.task_types,
                                    }
                                    for m in p.models
                                ],
                                "health_status": p.health_status,
                                "last_error": p.last_error,
                            }
                            for p in providers
                        ],
                        "count": len(providers),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("provider.list failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_list_failed",
                        "error": "Failed to list providers",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "provider.create":
            from ai.provider_registry import (  # noqa: PLC0415
                get_provider_registry,
            )

            try:
                registry = get_provider_registry()
                provider_id = args.get("provider_id", "")
                display_name = args.get("display_name", "")
                provider_type = args.get("provider_type", "")
                base_url = args.get("base_url")
                credential_ref = args.get("credential_ref")
                models = args.get("models", [])
                routing_metadata = args.get("routing_metadata", {})
                notes = args.get("notes")

                record = registry.create_provider(
                    provider_id=provider_id,
                    display_name=display_name,
                    provider_type=provider_type,
                    base_url=base_url,
                    credential_ref=credential_ref,
                    models=models,
                    routing_metadata=routing_metadata,
                    notes=notes,
                )

                return json.dumps(
                    {
                        "success": True,
                        "provider_id": record.provider_id,
                        "message": f"Provider {provider_id} created",
                    },
                    indent=2,
                )
            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "validation_error",
                        "error": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("provider.create failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_create_failed",
                        "error": "Failed to create provider",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "provider.update":
            from ai.provider_registry import (  # noqa: PLC0415
                get_provider_registry,
            )

            try:
                registry = get_provider_registry()
                provider_id = args.get("provider_id", "")
                display_name = args.get("display_name")
                provider_type = args.get("provider_type")
                base_url = args.get("base_url")
                credential_ref = args.get("credential_ref")
                models = args.get("models")
                routing_metadata = args.get("routing_metadata")
                notes = args.get("notes")

                record = registry.update_provider(
                    provider_id=provider_id,
                    display_name=display_name,
                    provider_type=provider_type,
                    base_url=base_url,
                    credential_ref=credential_ref,
                    models=models,
                    routing_metadata=routing_metadata,
                    notes=notes,
                )

                return json.dumps(
                    {
                        "success": True,
                        "provider_id": record.provider_id,
                        "message": f"Provider {provider_id} updated",
                    },
                    indent=2,
                )
            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "validation_error",
                        "error": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("provider.update failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_update_failed",
                        "error": "Failed to update provider",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "provider.disable":
            from ai.provider_registry import (  # noqa: PLC0415
                get_provider_registry,
            )

            try:
                registry = get_provider_registry()
                provider_id = args.get("provider_id", "")

                record = registry.disable_provider(provider_id)

                return json.dumps(
                    {
                        "success": True,
                        "provider_id": record.provider_id,
                        "enabled": record.enabled,
                        "message": f"Provider {provider_id} disabled",
                    },
                    indent=2,
                )
            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_not_found",
                        "error": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("provider.disable failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_disable_failed",
                        "error": "Failed to disable provider",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "provider.enable":
            from ai.provider_registry import (  # noqa: PLC0415
                get_provider_registry,
            )

            try:
                registry = get_provider_registry()
                provider_id = args.get("provider_id", "")

                record = registry.enable_provider(provider_id)

                return json.dumps(
                    {
                        "success": True,
                        "provider_id": record.provider_id,
                        "enabled": record.enabled,
                        "message": f"Provider {provider_id} enabled",
                    },
                    indent=2,
                )
            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_not_found",
                        "error": str(e),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("provider.enable failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "provider_enable_failed",
                        "error": "Failed to enable provider",
                        "details": str(e),
                    },
                    indent=2,
                )

        elif tool_name == "provider.generate_routing":
            from ai.provider_registry import (  # noqa: PLC0415
                KNOWN_PROVIDERS,
                get_provider_registry,
            )

            try:
                registry = get_provider_registry()
                include_disabled = args.get("include_disabled", False)
                config = registry.generate_routing_config(
                    KNOWN_PROVIDERS, include_disabled=include_disabled
                )

                return json.dumps(
                    {
                        "success": True,
                        "routing": config,
                        "count": len(config),
                    },
                    indent=2,
                )
            except Exception as e:
                logger.error("provider.generate_routing failed: %s", e)
                return json.dumps(
                    {
                        "success": False,
                        "error_code": "routing_generation_failed",
                        "error": "Failed to generate routing config",
                        "details": str(e),
                    },
                    indent=2,
                )

        # P96 Figma Design Reconciliation tools
        elif tool_name == "figma.list_teams":
            from ai.figma_service import figma_list_teams  # noqa: PLC0415

            result = figma_list_teams()
            return json.dumps(result, indent=2)

        elif tool_name == "figma.list_projects":
            from ai.figma_service import figma_list_projects  # noqa: PLC0415

            team_id = args.get("team_id", "")
            result = figma_list_projects(team_id)
            return json.dumps(result, indent=2)

        elif tool_name == "figma.list_project_files":
            from ai.figma_service import figma_list_project_files  # noqa: PLC0415

            project_id = args.get("project_id", "")
            result = figma_list_project_files(project_id)
            return json.dumps(result, indent=2)

        elif tool_name == "figma.get_file":
            from ai.figma_service import figma_get_file  # noqa: PLC0415

            file_key = args.get("file_key", "")
            result = figma_get_file(file_key)
            return json.dumps(result, indent=2)

        elif tool_name == "figma.find_project":
            from ai.figma_service import figma_find_project  # noqa: PLC0415

            project_name = args.get("project_name", "Bazzite")
            result = figma_find_project(project_name)
            return json.dumps(result, indent=2)

        elif tool_name == "figma.reconcile":
            from ai.figma_service import figma_reconcile  # noqa: PLC0415

            project_name = args.get("project_name", "Bazzite")
            artifact_names = args.get("artifact_names")
            result = figma_reconcile(project_name, artifact_names)
            return json.dumps(result, indent=2)

        elif tool_name == "notion.search":
            result = await handle_notion_search(args)
            return json.dumps(result, indent=2)

        elif tool_name == "notion.get_page":
            result = await handle_notion_get_page(args)
            return json.dumps(result, indent=2)

        elif tool_name == "notion.get_page_content":
            result = await handle_notion_get_page_content(args)
            return json.dumps(result, indent=2)

        elif tool_name == "notion.query_database":
            result = await handle_notion_query_database(args)
            return json.dumps(result, indent=2)

        # P102: Dynamic Tool Discovery
        elif tool_name == "tool.discover":
            from ai.mcp_bridge.tool_discovery_handlers import handle_tool_discover  # noqa: PLC0415

            result = await handle_tool_discover(args)
            return result

        elif tool_name == "tool.register":
            from ai.mcp_bridge.tool_discovery_handlers import handle_tool_register  # noqa: PLC0415

            result = await handle_tool_register(args)
            return result

        elif tool_name == "tool.unregister":
            from ai.mcp_bridge.tool_discovery_handlers import (
                handle_tool_unregister,  # noqa: PLC0415
            )

            result = await handle_tool_unregister(args)
            return result

        elif tool_name == "tool.reload":
            from ai.mcp_bridge.tool_discovery_handlers import handle_tool_reload  # noqa: PLC0415

            result = await handle_tool_reload(args)
            return result

        elif tool_name == "tool.registry_stats":
            from ai.mcp_bridge.tool_discovery_handlers import (
                handle_tool_registry_stats,  # noqa: PLC0415
            )

            result = await handle_tool_registry_stats(args)
            return result

        elif tool_name == "tool.watch":
            from ai.mcp_bridge.tool_discovery_handlers import handle_tool_watch  # noqa: PLC0415

            result = await handle_tool_watch(args)
            return result

        # P103: MCP Tool Marketplace
        elif tool_name == "tool.pack_validate":
            from ai.mcp_bridge.tool_marketplace_handlers import (
                handle_tool_pack_validate,  # noqa: PLC0415
            )

            result = await handle_tool_pack_validate(args)
            return result

        elif tool_name == "tool.pack_export":
            from ai.mcp_bridge.tool_marketplace_handlers import (
                handle_tool_pack_export,  # noqa: PLC0415
            )

            result = await handle_tool_pack_export(args)
            return result

        elif tool_name == "tool.pack_import":
            from ai.mcp_bridge.tool_marketplace_handlers import (
                handle_tool_pack_import,  # noqa: PLC0415
            )

            result = await handle_tool_pack_import(args)
            return result

        elif tool_name == "tool.pack_list":
            from ai.mcp_bridge.tool_marketplace_handlers import (
                handle_tool_pack_list,  # noqa: PLC0415
            )

            result = await handle_tool_pack_list(args)
            return result

        elif tool_name == "tool.pack_install":
            from ai.mcp_bridge.tool_marketplace_handlers import (
                handle_tool_pack_install,  # noqa: PLC0415
            )

            result = await handle_tool_pack_install(args)
            return result

        elif tool_name == "tool.pack_remove":
            from ai.mcp_bridge.tool_marketplace_handlers import (
                handle_tool_pack_remove,  # noqa: PLC0415
            )

            result = await handle_tool_pack_remove(args)
            return result

        elif tool_name == "tool.optimization.recommend":
            from ai.mcp_bridge.tool_optimization_handlers import (
                handle_tool_optimization_recommend,  # noqa: PLC0415
            )

            result = await handle_tool_optimization_recommend(args)
            return result

        elif tool_name == "tool.optimization.stale_tools":
            from ai.mcp_bridge.tool_optimization_handlers import (
                handle_tool_optimization_stale_tools,  # noqa: PLC0415
            )

            result = await handle_tool_optimization_stale_tools(args)
            return result

        elif tool_name == "tool.optimization.cost_report":
            from ai.mcp_bridge.tool_optimization_handlers import (
                handle_tool_optimization_cost_report,  # noqa: PLC0415
            )

            result = await handle_tool_optimization_cost_report(args)
            return result

        elif tool_name == "tool.optimization.latency_report":
            from ai.mcp_bridge.tool_optimization_handlers import (
                handle_tool_optimization_latency_report,  # noqa: PLC0415
            )

            result = await handle_tool_optimization_latency_report(args)
            return result

        elif tool_name == "tool.optimization.anomalies":
            from ai.mcp_bridge.tool_optimization_handlers import (
                handle_tool_optimization_anomalies,  # noqa: PLC0415
            )

            result = await handle_tool_optimization_anomalies(args)
            return result

        elif tool_name == "tool.optimization.forecast":
            from ai.mcp_bridge.tool_optimization_handlers import (
                handle_tool_optimization_forecast,  # noqa: PLC0415
            )

            result = await handle_tool_optimization_forecast(args)
            return result

        elif tool_name == "tool.federation.discover":
            from ai.mcp_bridge.tool_federation_handlers import (
                handle_tool_federation_discover,  # noqa: PLC0415
            )

            result = await handle_tool_federation_discover(args)
            return result

        elif tool_name == "tool.federation.list_servers":
            from ai.mcp_bridge.tool_federation_handlers import (
                handle_tool_federation_list_servers,  # noqa: PLC0415
            )

            result = await handle_tool_federation_list_servers(args)
            return result

        elif tool_name == "tool.federation.inspect_server":
            from ai.mcp_bridge.tool_federation_handlers import (
                handle_tool_federation_inspect_server,  # noqa: PLC0415
            )

            result = await handle_tool_federation_inspect_server(args)
            return result

        elif tool_name == "tool.federation.audit":
            from ai.mcp_bridge.tool_federation_handlers import (
                handle_tool_federation_audit,  # noqa: PLC0415
            )

            result = await handle_tool_federation_audit(args)
            return result

        elif tool_name == "tool.federation.trust_score":
            from ai.mcp_bridge.tool_federation_handlers import (
                handle_tool_federation_trust_score,  # noqa: PLC0415
            )

            result = await handle_tool_federation_trust_score(args)
            return result

        elif tool_name == "tool.federation.disable":
            from ai.mcp_bridge.tool_federation_handlers import (
                handle_tool_federation_disable,  # noqa: PLC0415
            )

            result = await handle_tool_federation_disable(args)
            return result

        else:
            return f"[Tool '{tool_name}' not implemented]"

    except ImportError as e:
        return f"[Module not available: {e}]"
    except Exception as e:
        logger.error("Tool '%s' failed: %s", tool_name, e)
        return f"[Tool error: {e}]"


async def handle_intel_scrape_now(args: dict) -> dict:
    """Trigger intelligence scrape from all configured sources."""
    try:
        from pathlib import Path

        from ai.intel_scraper import IntelScraper  # noqa: PLC0415

        scraper = IntelScraper()
        output_dir = str(Path.home() / "security" / "intel")
        summary = scraper.run_all(output_dir)
        return {"status": "ok", "data": summary}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_dep_scan(args: dict) -> dict:
    """Scan venv dependencies for known vulnerabilities."""
    try:
        import json
        from pathlib import Path

        from ai.system.dep_scanner import DepVulnScanner  # noqa: PLC0415

        scanner = DepVulnScanner()
        venv = str(Path.home() / "projects" / "bazzite-laptop" / ".venv")
        output_dir = str(Path.home() / "security" / "intel" / "dependencies")
        report_path = scanner.run(venv, output_dir)
        with open(report_path) as f:
            return {"status": "ok", "data": json.load(f)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_test_analysis(args: dict) -> dict:
    """Analyze pytest output for failure patterns."""
    try:
        import json
        from pathlib import Path

        from ai.system.test_analyzer import TestFailureAnalyzer  # noqa: PLC0415

        inp = args.get("input", "")
        if not inp:
            return {"status": "error", "error": "input required"}
        analyzer = TestFailureAnalyzer()
        output_dir = str(Path.home() / "security" / "intel" / "tests")
        report_path = analyzer.run(inp, output_dir)
        with open(report_path) as f:
            return {"status": "ok", "data": json.load(f)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_perf_profile(args: dict) -> dict:
    """Run performance profiler for LLM, MCP, file I/O, LanceDB, and system."""
    try:
        from pathlib import Path

        from ai.system.perf_profiler import PerfProfiler  # noqa: PLC0415

        skip = args.get("skip", "")
        skip_list = skip.split(",") if skip else []

        profiler = PerfProfiler()
        output_dir = str(Path.home() / "security" / "metrics")
        report_path = profiler.run(output_dir, skip=skip_list)

        import json

        with open(report_path) as f:
            data = json.load(f)
        return {"status": "ok", "data": data, "report_path": report_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_mcp_audit(args: dict) -> dict:
    """Audit MCP bridge allowlist for missing handlers."""
    try:
        from pathlib import Path

        from ai.system.mcp_generator import MCPToolGenerator  # noqa: PLC0415

        tool_name = args.get("tool_name")
        project_root = str(Path.home() / "projects" / "bazzite-laptop")
        gen = MCPToolGenerator(project_root)

        if tool_name:
            result = gen.validate_tool(tool_name)
        else:
            result = gen.audit_all_tools()

        return {"status": "ok", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_intel_ingest_pending(args: dict) -> dict:
    """Ingest pending intel JSONL into LanceDB RAG."""
    try:
        from ai.system.ingest_pipeline import ingest_intel_to_rag  # noqa: PLC0415

        intel_dir = args.get("intel_dir")
        result = ingest_intel_to_rag(intel_dir)
        return {"status": "ok", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_slack_list_channels(args: dict) -> dict:
    """List Slack channels."""
    from ai.slack.handlers import handle_slack_list_channels as _handler

    return await _handler(args)


async def handle_slack_post_message(args: dict) -> dict:
    """Post a message to Slack."""
    from ai.slack.handlers import handle_slack_post_message as _handler

    return await _handler(args)


async def handle_slack_list_users(args: dict) -> dict:
    """List Slack users."""
    from ai.slack.handlers import handle_slack_list_users as _handler

    return await _handler(args)


async def handle_slack_get_history(args: dict) -> dict:
    """Get Slack channel history."""
    from ai.slack.handlers import handle_slack_get_history as _handler

    return await _handler(args)


async def handle_notion_search(args: dict) -> dict:
    """Search Notion pages and databases."""
    from ai.notion.handlers import handle_notion_search as _handler

    return await _handler(args)


async def handle_notion_get_page(args: dict) -> dict:
    """Get a Notion page by ID."""
    from ai.notion.handlers import handle_notion_get_page as _handler

    return await _handler(args)


async def handle_notion_get_page_content(args: dict) -> dict:
    """Get content blocks from a Notion page."""
    from ai.notion.handlers import handle_notion_get_page_content as _handler

    return await _handler(args)


async def handle_notion_query_database(args: dict) -> dict:
    """Query a Notion database."""
    from ai.notion.handlers import handle_notion_query_database as _handler

    return await _handler(args)
