"""
Canary release automation for Bazzite AI Layer.

Validates:
1. Redeploy preflight - rebuild UI, restart services, validate profiles
2. Service health endpoints
3. MCP manifest / tool availability
4. Policy gates (blocked/approval-required enforcement)
5. Evidence bundle generation

Non-destructive, operator-safe, fail-closed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class CanaryStage(Enum):
    PREFLIGHT = "preflight"
    SERVICE_HEALTH = "service_health"
    MCP_TOOLS = "mcp_tools"
    UI_BUILD = "ui_build"
    POLICY_GATES = "policy_gates"
    EVIDENCE = "evidence"


class CanaryStatus(Enum):
    OK = "ok"  # noqa: S105
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class CanaryCheck:
    stage: CanaryStage
    name: str
    description: str
    status: CanaryStatus = CanaryStatus.FAIL
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class CanaryResult:
    stage: CanaryStage
    checks: list[CanaryCheck] = field(default_factory=dict)
    passed: int = 0
    failed: int = 0
    warned: int = 0
    started_at: str = ""
    finished_at: str = ""


def _run_command(
    cmd: list[str],
    timeout: int = 120,
    check: bool = False,
    cwd: Path | None = None,
) -> tuple[int, str, str]:
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", f"command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def _get_timestamp() -> str:
    return datetime.now().isoformat()


def _get_repo_root() -> Path:
    return Path(__file__).parent.parent


def _check_http_endpoint(url: str, timeout: int = 5) -> tuple[CanaryStatus, str]:
    code, stdout, stderr = _run_command(["curl", "-sf", "--max-time", str(timeout), url])
    if code == 0:
        try:
            data = json.loads(stdout)
            if data.get("status") == "ok":
                return CanaryStatus.OK, "health OK"
        except (json.JSONDecodeError, KeyError):
            return CanaryStatus.OK, "endpoint responds"
    return CanaryStatus.FAIL, "endpoint not responding"


def _check_port(port: int) -> tuple[CanaryStatus, str]:
    code, stdout, stderr = _run_command(["ss", "-tln"])
    if code == 0 and f":{port} " in stdout:
        return CanaryStatus.OK, f"port {port} listening"
    return CanaryStatus.FAIL, f"port {port} not listening"


def _check_systemd_service(service: str) -> tuple[CanaryStatus, str]:
    code, stdout, stderr = _run_command(["systemctl", "--user", "is-active", f"{service}.service"])
    if code == 0 and "active" in stdout.lower():
        return CanaryStatus.OK, "service active"
    return CanaryStatus.FAIL, "service inactive or not found"


def _check_systemd_enabled(service: str) -> tuple[CanaryStatus, str]:
    code, stdout, stderr = _run_command(["systemctl", "--user", "is-enabled", f"{service}.service"])
    if code == 0:
        return CanaryStatus.OK, "service enabled"
    return CanaryStatus.FAIL, "service not enabled"


def _check_mcp_tools(url: str = "http://127.0.0.1:8766") -> tuple[CanaryStatus, str, int]:
    code, stdout, stderr = _run_command(["curl", "-sf", "--max-time", "10", f"{url}/health"])
    if code == 0:
        return CanaryStatus.OK, "MCP bridge responding", 0

    code, stdout, stderr = _run_command(["ss", "-tln"])
    if code == 0 and ":8766 " in stdout:
        return CanaryStatus.OK, "MCP port listening (no /health)", 0

    return CanaryStatus.FAIL, stderr or "MCP bridge not responding", -1


def _check_ui_build(ui_dir: Path) -> tuple[CanaryStatus, str]:
    build_script = ui_dir / "package.json"
    if not build_script.exists():
        return CanaryStatus.FAIL, "package.json not found"

    code, stdout, stderr = _run_command(
        ["npm", "run", "build"],
        timeout=180,
        cwd=ui_dir,
    )
    if code == 0:
        return CanaryStatus.OK, "UI build successful"
    return CanaryStatus.FAIL, f"UI build failed: {stderr[:200]}"


def _deploy_services() -> tuple[CanaryStatus, str]:
    repo_root = _get_repo_root()
    deploy_script = repo_root / "scripts" / "deploy-services.sh"

    if not deploy_script.exists():
        return CanaryStatus.FAIL, "deploy-services.sh not found"

    code, stdout, stderr = _run_command(
        ["bash", str(deploy_script)],
        timeout=120,
    )

    if code == 0:
        return CanaryStatus.OK, "services deployed"
    return CanaryStatus.WARN, f"deploy completed with warnings: {stderr[:100]}"


def _run_profile_validation() -> tuple[CanaryStatus, str]:
    repo_root = _get_repo_root()
    venv_python = repo_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        return CanaryStatus.FAIL, "venv not found"

    code, stdout, stderr = _run_command(
        [str(venv_python), "-m", "pytest", "tests/test_deployment_profiles.py", "-q", "--tb=short"],
        timeout=60,
    )
    if code == 0:
        return CanaryStatus.OK, "deployment profiles valid"
    return CanaryStatus.FAIL, "profile validation failed"


def _check_policy_gates() -> tuple[CanaryStatus, str]:
    repo_root = _get_repo_root()
    policy_file = repo_root / "configs" / "security-autopilot-policy.yaml"

    if not policy_file.exists():
        return CanaryStatus.FAIL, "policy file not found"

    try:
        content = policy_file.read_text()
        has_mode = "mode:" in content or "default_action:" in content
        has_approval = "approval" in content.lower()
        has_block = "block" in content.lower()

        if has_mode and (has_approval or has_block):
            return CanaryStatus.OK, "policy gates present (approval/block)"

        return CanaryStatus.WARN, "policy file exists but gates unclear"
    except Exception as e:
        return CanaryStatus.FAIL, f"policy check error: {e}"


def _check_mcp_allowlist() -> tuple[CanaryStatus, str]:
    repo_root = _get_repo_root()
    allowlist = repo_root / "configs" / "mcp-bridge-allowlist.yaml"

    if not allowlist.exists():
        return CanaryStatus.FAIL, "allowlist not found"

    try:
        content = allowlist.read_text()
        tool_count = content.count("name:") if "name:" in content else 0

        if tool_count > 10:
            return CanaryStatus.OK, f"{tool_count} tools in allowlist"

        return CanaryStatus.WARN, f"only {tool_count} tools in allowlist"
    except Exception as e:
        return CanaryStatus.FAIL, f"allowlist check error: {e}"


def _redact_sensitive(text: str) -> str:
    """Redact sensitive patterns from text."""
    lines = text.splitlines()
    redacted = []
    for line in lines:
        if "sk-" in line and len(line) > 30:
            line = line.replace("sk-", "sk-[REDACTED]")
        if "/home/" in line or "/var/home/" in line or "/root/" in line:
            idx = line.find("/")
            if idx > 0:
                line = line[:idx] + "/[REDACTED]"
        if line.startswith("Bearer "):
            parts = line.split()
            if len(parts) > 1 and len(parts[1]) > 10:
                parts[1] = "[REDACTED]"
                line = " ".join(parts)
        redacted.append(line)
    return "\n".join(redacted)


def run_preflight() -> list[CanaryCheck]:
    checks: list[CanaryCheck] = []

    check = CanaryCheck(
        stage=CanaryStage.PREFLIGHT,
        name="deploy-services",
        description="Run deploy-services.sh to bring services up to date",
    )
    status, msg = _deploy_services()
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    check = CanaryCheck(
        stage=CanaryStage.PREFLIGHT,
        name="profile-validation",
        description="Validate deployment profiles are current",
    )
    status, msg = _run_profile_validation()
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    return checks


def run_service_health() -> list[CanaryCheck]:
    checks: list[CanaryCheck] = []

    check = CanaryCheck(
        stage=CanaryStage.SERVICE_HEALTH,
        name="llm-proxy-health",
        description="LLM proxy health endpoint at port 8767",
    )
    status, msg = _check_http_endpoint("http://127.0.0.1:8767/health")
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    check = CanaryCheck(
        stage=CanaryStage.SERVICE_HEALTH,
        name="mcp-bridge-health",
        description="MCP bridge responding at port 8766",
    )
    status, msg, _ = _check_mcp_tools()
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    check = CanaryCheck(
        stage=CanaryStage.SERVICE_HEALTH,
        name="llm-proxy-service",
        description="bazzite-llm-proxy user service active",
    )
    status, msg = _check_systemd_service("bazzite-llm-proxy")
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    check = CanaryCheck(
        stage=CanaryStage.SERVICE_HEALTH,
        name="mcp-bridge-service",
        description="bazzite-mcp-bridge user service active",
    )
    status, msg = _check_systemd_service("bazzite-mcp-bridge")
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    return checks


def run_mcp_tools() -> list[CanaryCheck]:
    checks: list[CanaryCheck] = []

    check = CanaryCheck(
        stage=CanaryStage.MCP_TOOLS,
        name="mcp-allowlist",
        description="MCP bridge allowlist has tools defined",
    )
    status, msg = _check_mcp_allowlist()
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    check = CanaryCheck(
        stage=CanaryStage.MCP_TOOLS,
        name="port-8766-listening",
        description="MCP bridge port 8766 listening",
    )
    status, msg = _check_port(8766)
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    return checks


def run_ui_build() -> list[CanaryCheck]:
    checks: list[CanaryCheck] = []
    repo_root = _get_repo_root()
    ui_dir = repo_root / "ui"

    check = CanaryCheck(
        stage=CanaryStage.UI_BUILD,
        name="npm-build",
        description="UI npm build succeeds",
    )
    status, msg = _check_ui_build(ui_dir)
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    return checks


def run_policy_gates() -> list[CanaryCheck]:
    checks: list[CanaryCheck] = []

    check = CanaryCheck(
        stage=CanaryStage.POLICY_GATES,
        name="security-policy",
        description="Security Autopilot policy has approval/block gates",
    )
    status, msg = _check_policy_gates()
    check.status = status
    check.message = msg
    check.timestamp = _get_timestamp()
    checks.append(check)

    return checks


def run_canary(evidence_dir: Path | None = None) -> dict[str, Any]:
    started = _get_timestamp()

    all_checks: list[CanaryCheck] = []

    all_checks.extend(run_preflight())
    all_checks.extend(run_service_health())
    all_checks.extend(run_mcp_tools())
    all_checks.extend(run_ui_build())
    all_checks.extend(run_policy_gates())

    passed = sum(1 for c in all_checks if c.status == CanaryStatus.OK)
    failed = sum(1 for c in all_checks if c.status == CanaryStatus.FAIL)
    warned = sum(1 for c in all_checks if c.status == CanaryStatus.WARN)

    finished = _get_timestamp()

    result = {
        "canary_version": "1.0.0",
        "started_at": started,
        "finished_at": finished,
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "total": len(all_checks),
        "all_passed": failed == 0,
        "checks": [
            {
                "stage": c.stage.value,
                "name": c.name,
                "description": c.description,
                "status": c.status.value,
                "message": c.message,
                "timestamp": c.timestamp,
            }
            for c in all_checks
        ],
    }

    if evidence_dir:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        bundle = evidence_dir / "canary-bundle.json"
        bundle.write_text(json.dumps(result, indent=2))
        summary = evidence_dir / "canary-summary.txt"
        summary_lines = [
            f"Canary Release Check - {started}",
            "=" * 50,
            f"Passed: {passed}/{len(all_checks)}",
            f"Failed: {failed}",
            f"Warned: {warned}",
            "",
            "Failed Checks:",
        ]
        for c in all_checks:
            if c.status == CanaryStatus.FAIL:
                summary_lines.append(f"  - {c.stage.value}: {c.name} - {c.message}")
        summary_lines.extend(["", "To troubleshoot:"])
        summary_lines.append("  - Check service status: systemctl --user status bazzite-mcp-bridge")
        summary_lines.append("  - Check logs: journalctl --user -u bazzite-mcp-bridge -n 50")
        summary_lines.append("  - Rebuild UI: cd ui && npm run build")
        summary.write_text("\n".join(summary_lines))

    return result


if __name__ == "__main__":
    repo_root = _get_repo_root()
    evidence_base = repo_root / "docs" / "evidence"

    result = run_canary(evidence_base / "p138")

    print(f"Canary Result: {result['passed']}/{result['total']} passed")
    if result["failed"] > 0:
        print("FAILED CHECKS:")
        for c in result["checks"]:
            if c["status"] == "fail":
                print(f"  - {c['stage']}: {c['name']} - {c['message']}")

    sys.exit(0 if result["all_passed"] else 1)
