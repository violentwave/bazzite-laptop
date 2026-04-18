"""
Deployment profiles for repeatable local Bazzite laptop deployments.

Defines three deployment modes:
- local-only: Core services (LLM proxy, MCP bridge)
- security-autopilot: Core + Security Autopilot surfaces
- agent-workbench: Core + Agent Workbench surfaces

Each profile validates required services, health endpoints, env vars, and project roots.
Fails closed on critical missing dependencies.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ProfileMode(Enum):
    LOCAL_ONLY = "local-only"
    SECURITY_AUTOPILOT = "security-autopilot"
    AGENT_WORKBENCH = "agent-workbench"


class CheckStatus(Enum):
    OK = "ok"  # noqa: S105
    FAIL = "fail"
    WARN = "warn"


@dataclass
class DeploymentCheck:
    name: str
    description: str
    critical: bool = True
    status: CheckStatus = CheckStatus.FAIL
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentProfile:
    name: str
    mode: ProfileMode
    description: str
    required_services: list[str] = field(default_factory=list)
    required_env_vars: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    optional_checks: list[str] = field(default_factory=list)
    checks: list[DeploymentCheck] = field(default_factory=list)


PROFILE_REGISTRY: dict[ProfileMode, DeploymentProfile] = {}


def _run_command(cmd: list[str], timeout: int = 5) -> tuple[int, str, str]:
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "command not found"
    except Exception as e:
        return -1, "", str(e)


def _check_service(service: str) -> tuple[CheckStatus, str]:
    code, stdout, stderr = _run_command(["systemctl", "--user", "is-active", f"{service}.service"])
    if code == 0 and "active" in stdout.lower():
        return CheckStatus.OK, "service active"
    return CheckStatus.FAIL, "service inactive or not found"


def _check_service_enabled(service: str) -> tuple[CheckStatus, str]:
    code, stdout, stderr = _run_command(["systemctl", "--user", "is-enabled", f"{service}.service"])
    if code == 0 and "enabled" in stdout.lower():
        return CheckStatus.OK, "service enabled"
    return CheckStatus.FAIL, "service not enabled"


def _check_port(port: int) -> tuple[CheckStatus, str]:
    code, stdout, stderr = _run_command(["ss", "-tln"])
    if code == 0 and f":{port} " in stdout:
        return CheckStatus.OK, f"port {port} listening"
    return CheckStatus.FAIL, f"port {port} not listening"


def _check_http_endpoint(url: str, timeout: int = 3) -> tuple[CheckStatus, str]:
    code, stdout, stderr = _run_command(["curl", "-sf", "--max-time", str(timeout), url])
    if code == 0:
        try:
            data = json.loads(stdout)
            if data.get("status") == "ok":
                return CheckStatus.OK, "health OK"
        except (json.JSONDecodeError, KeyError):
            return CheckStatus.OK, "endpoint responds"
    return CheckStatus.FAIL, "endpoint not responding"


def _check_env_var(name: str) -> tuple[CheckStatus, str]:
    present = name in os.environ
    if present:
        return CheckStatus.OK, "env var present (value hidden)"
    return CheckStatus.FAIL, "env var not set"


def _check_key_presence(key_name: str, keys_env_path: Path) -> tuple[CheckStatus, str]:
    if not keys_env_path.exists():
        return CheckStatus.FAIL, "keys.env not found"

    try:
        content = keys_env_path.read_text()
        stripped = "".join(c for c in content if not c.isspace())
        if key_name.lower() in stripped.lower():
            return CheckStatus.OK, f"{key_name} configured"
        for line in content.splitlines():
            if line.startswith(key_name) and "=" in line:
                return CheckStatus.OK, f"{key_name} configured"
        return CheckStatus.FAIL, f"{key_name} not configured"
    except PermissionError:
        return CheckStatus.FAIL, "keys.env not readable"
    except Exception as e:
        return CheckStatus.FAIL, f"error checking keys: {e}"


def _check_project_root(path: Path) -> tuple[CheckStatus, str]:
    if path.exists() and path.is_dir():
        return CheckStatus.OK, f"{path} exists"
    return CheckStatus.FAIL, f"{path} not found"


def _check_workbench_config(path: Path) -> tuple[CheckStatus, str]:
    if path.exists():
        try:
            content = json.loads(path.read_text())
            if "projects" in content or "sessions" in content:
                return CheckStatus.OK, "workbench config valid"
            return CheckStatus.WARN, "config missing projects/sessions"
        except json.JSONDecodeError:
            return CheckStatus.FAIL, "config invalid JSON"
    return CheckStatus.FAIL, "config not found"


def _check_ui_build(ui_dir: Path) -> tuple[CheckStatus, str]:
    build_script = ui_dir / "package.json"
    if not build_script.exists():
        return CheckStatus.FAIL, "package.json not found"

    code, stdout, stderr = _run_command(
        ["npm", "run", "build"],
        timeout=120,
    )
    if code == 0:
        return CheckStatus.OK, "UI build successful"
    return CheckStatus.FAIL, "UI build failed"


def _check_python_venv(venv_path: Path) -> tuple[CheckStatus, str]:
    if venv_path.exists() and venv_path.is_dir():
        python_bin = venv_path / "bin" / "python"
        if python_bin.exists():
            return CheckStatus.OK, f"venv at {venv_path}"
    return CheckStatus.FAIL, f"venv not found at {venv_path}"


def _get_repo_root() -> Path:
    return Path(__file__).parent.parent


def _get_keys_env_path() -> Path:
    return Path.home() / ".config" / "bazzite-ai" / "keys.env"


def validate_profile(profile: DeploymentProfile) -> list[DeploymentCheck]:
    repo_root = _get_repo_root()
    keys_env = _get_keys_env_path()

    for svc in profile.required_services:
        status, msg = _check_service(svc)
        check = DeploymentCheck(
            name=f"service:{svc}",
            description=f"User service {svc} is active",
            critical=True,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    for env_var in profile.required_env_vars:
        status, msg = _check_env_var(env_var)
        check = DeploymentCheck(
            name=f"env:{env_var}",
            description=f"Environment variable {env_var} is set",
            critical=False,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    if "keys" in profile.required_checks:
        key_names = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
        for key_name in key_names:
            status, msg = _check_key_presence(key_name, keys_env)
            check = DeploymentCheck(
                name=f"key:{key_name}",
                description=f"API key {key_name} is configured",
                critical=False,
                status=status,
                message=msg,
            )
            profile.checks.append(check)

    if "mcp-health" in profile.required_checks:
        status, msg = _check_port(8766)
        check = DeploymentCheck(
            name="mcp:8766",
            description="MCP bridge port 8766 is listening",
            critical=True,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    if "llm-health" in profile.required_checks:
        status, msg = _check_http_endpoint("http://127.0.0.1:8767/health")
        check = DeploymentCheck(
            name="llm:health",
            description="LLM proxy health endpoint responds",
            critical=True,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    if "project-root" in profile.required_checks:
        status, msg = _check_project_root(repo_root)
        check = DeploymentCheck(
            name="repo:root",
            description="Repository root exists",
            critical=True,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    if "venv" in profile.required_checks:
        venv_path = repo_root / ".venv"
        status, msg = _check_python_venv(venv_path)
        check = DeploymentCheck(
            name="python:venv",
            description="Python venv exists and is valid",
            critical=True,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    if "workbench-config" in profile.required_checks:
        wb_config = repo_root / "ai" / "agent_workbench" / "config.json"
        status, msg = _check_workbench_config(wb_config)
        check = DeploymentCheck(
            name="workbench:config",
            description="Agent Workbench config exists",
            critical=False,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    if "ui-build" in profile.optional_checks:
        ui_dir = repo_root / "ui"
        status, msg = _check_ui_build(ui_dir)
        check = DeploymentCheck(
            name="ui:build",
            description="UI can build successfully",
            critical=False,
            status=status,
            message=msg,
        )
        profile.checks.append(check)

    return profile.checks


def load_profile(mode: ProfileMode) -> DeploymentProfile | None:
    if mode == ProfileMode.LOCAL_ONLY:
        return DeploymentProfile(
            name="Local Only (Laptop)",
            mode=mode,
            description="Core services: LLM proxy + MCP bridge only",
            required_services=["bazzite-llm-proxy", "bazzite-mcp-bridge"],
            required_env_vars=[],
            required_checks=["mcp-health", "llm-health", "project-root", "venv"],
        )
    elif mode == ProfileMode.SECURITY_AUTOPILOT:
        return DeploymentProfile(
            name="Security Autopilot",
            mode=mode,
            description="Core + Security scanning and remediation",
            required_services=["bazzite-llm-proxy", "bazzite-mcp-bridge"],
            required_env_vars=[],
            required_checks=["mcp-health", "llm-health", "project-root", "venv", "keys"],
        )
    elif mode == ProfileMode.AGENT_WORKBENCH:
        return DeploymentProfile(
            name="Agent Workbench",
            mode=mode,
            description="Core + Agent Workbench for project/session management",
            required_services=["bazzite-llm-proxy", "bazzite-mcp-bridge"],
            required_env_vars=[],
            required_checks=[
                "mcp-health",
                "llm-health",
                "project-root",
                "venv",
                "workbench-config",
            ],
        )
    return None


def validate_all_profiles() -> dict[ProfileMode, list[DeploymentCheck]]:
    results = {}
    for mode in ProfileMode:
        profile = load_profile(mode)
        if profile:
            validate_profile(profile)
            results[mode] = profile.checks
    return results


def get_profile_summary(profile: DeploymentProfile) -> dict[str, Any]:
    passed = sum(1 for c in profile.checks if c.status == CheckStatus.OK)
    failed = sum(1 for c in profile.checks if c.status == CheckStatus.FAIL)
    warned = sum(1 for c in profile.checks if c.status == CheckStatus.WARN)

    critical_failed = [
        c.name for c in profile.checks if c.status == CheckStatus.FAIL and c.critical
    ]

    return {
        "profile": profile.name,
        "mode": profile.mode.value,
        "description": profile.description,
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "total": len(profile.checks),
        "critical_failed": critical_failed,
        "all_critical_passed": len(critical_failed) == 0,
    }


def register_profiles() -> None:
    for mode in ProfileMode:
        profile = load_profile(mode)
        if profile:
            PROFILE_REGISTRY[mode] = profile


register_profiles()
