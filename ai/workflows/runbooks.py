"""Runbook registry and validation helpers for P132.

This module provides machine-readable runbook loading for high-risk,
human-in-the-loop orchestration workflows. Runbooks are documentation-first and
must align with existing policy, approval, and audit systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_APPROVAL_STATES = {"pending", "approved", "rejected", "not-required"}
_MANUAL_APPROVAL_MODES = {"manual-approval", "bounded", "read-only"}

_FORBIDDEN_PHRASES = (
    "bypass policy",
    "skip approval",
    "disable audit",
    "ignore approval",
    "disable policy",
)

_SECRETS_PATTERNS = (
    "sk-",
    "AIza",
    "xoxb-",
    "BEGIN PRIVATE KEY",
    "token=",
)


@dataclass(frozen=True)
class RunbookDefinition:
    """Normalized machine-readable runbook definition."""

    runbook_id: str
    title: str
    risk_tier: str
    execution_mode: str
    approval_required: bool
    approval_state: str
    trigger: str
    prerequisites: list[str]
    required_evidence: list[str]
    operator_steps: list[dict[str, Any]]
    escalation: dict[str, Any]
    verification: list[str]
    artifacts: list[str]
    policy_alignment: list[str]
    workflow_plan: list[dict[str, Any]]
    notes: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_runbook_workflow_dir() -> Path:
    return _repo_root() / "docs" / "runbooks" / "workflows"


def default_runbook_docs_dir() -> Path:
    return _repo_root() / "docs" / "runbooks"


def _validate_phrase_safety(payload: str) -> None:
    lowered = payload.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in lowered:
            raise ValueError(f"runbook contains forbidden bypass phrase: {phrase}")
    for marker in _SECRETS_PATTERNS:
        if marker.lower() in lowered:
            raise ValueError("runbook contains secret-like marker")


def _normalize_runbook(data: dict[str, Any], source: Path) -> RunbookDefinition:
    required = {
        "runbook_id",
        "title",
        "risk_tier",
        "execution_mode",
        "approval_required",
        "approval_state",
        "trigger",
        "prerequisites",
        "required_evidence",
        "operator_steps",
        "escalation",
        "verification",
        "artifacts",
        "policy_alignment",
        "workflow_plan",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"runbook {source} missing required keys: {missing}")

    approval_state = str(data["approval_state"])
    if approval_state not in _APPROVAL_STATES:
        raise ValueError(f"runbook {source} has invalid approval_state: {approval_state}")

    execution_mode = str(data["execution_mode"])
    if execution_mode not in _MANUAL_APPROVAL_MODES:
        raise ValueError(f"runbook {source} has invalid execution_mode: {execution_mode}")

    payload = yaml.safe_dump(data, sort_keys=True)
    _validate_phrase_safety(payload)

    steps = data.get("operator_steps") or []
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"runbook {source} requires non-empty operator_steps")

    workflow_plan = data.get("workflow_plan") or []
    if not isinstance(workflow_plan, list) or not workflow_plan:
        raise ValueError(f"runbook {source} requires non-empty workflow_plan")

    for entry in workflow_plan:
        if not isinstance(entry, dict) or not entry.get("id"):
            raise ValueError(f"runbook {source} workflow_plan entries require id")

    return RunbookDefinition(
        runbook_id=str(data["runbook_id"]),
        title=str(data["title"]),
        risk_tier=str(data["risk_tier"]),
        execution_mode=execution_mode,
        approval_required=bool(data["approval_required"]),
        approval_state=approval_state,
        trigger=str(data["trigger"]),
        prerequisites=[str(item) for item in data.get("prerequisites", [])],
        required_evidence=[str(item) for item in data.get("required_evidence", [])],
        operator_steps=list(steps),
        escalation=dict(data.get("escalation", {})),
        verification=[str(item) for item in data.get("verification", [])],
        artifacts=[str(item) for item in data.get("artifacts", [])],
        policy_alignment=[str(item) for item in data.get("policy_alignment", [])],
        workflow_plan=list(workflow_plan),
        notes=[str(item) for item in data.get("notes", [])],
    )


def load_runbook_definitions(workflow_dir: Path | None = None) -> list[RunbookDefinition]:
    """Load and validate all machine-readable runbook definitions."""
    root = workflow_dir or default_runbook_workflow_dir()
    definitions: list[RunbookDefinition] = []
    for path in sorted(root.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        definition = _normalize_runbook(raw, source=path)
        definitions.append(definition)
    return definitions


def get_runbook_registry(workflow_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return runbook registry suitable for workflow/runtime surfacing."""
    registry: dict[str, dict[str, Any]] = {}
    for item in load_runbook_definitions(workflow_dir):
        registry[item.runbook_id] = {
            "title": item.title,
            "risk_tier": item.risk_tier,
            "execution_mode": item.execution_mode,
            "approval_required": item.approval_required,
            "approval_state": item.approval_state,
            "trigger": item.trigger,
            "operator_steps": item.operator_steps,
            "escalation": item.escalation,
            "verification": item.verification,
            "artifacts": item.artifacts,
            "policy_alignment": item.policy_alignment,
            "workflow_plan": item.workflow_plan,
            "notes": item.notes,
        }
    return registry


def validate_runbook_docs(docs_dir: Path | None = None) -> dict[str, Any]:
    """Validate markdown runbooks for banned bypass/secret wording."""
    root = docs_dir or default_runbook_docs_dir()
    checked: list[str] = []
    for path in sorted(root.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        body = path.read_text(encoding="utf-8")
        _validate_phrase_safety(body)
        checked.append(str(path))
    return {"checked": checked, "count": len(checked)}
