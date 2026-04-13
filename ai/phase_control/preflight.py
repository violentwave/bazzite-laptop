"""Project-intelligence preflight for phase-control execution gating."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai.phase_control.models import PhaseRow
from ai.phase_control.result_models import PreflightRecord


def build_preflight_record(phase: PhaseRow, *, repo_path: str) -> PreflightRecord:
    """Build the unified preflight record for a phase execution attempt."""
    errors: list[str] = []
    query = _phase_query(phase)

    phase_context = {
        "phase_number": phase.phase_number,
        "phase_name": phase.phase_name,
        "status": phase.status.value,
        "dependencies": list(phase.dependencies),
        "execution_mode": phase.execution_mode,
        "risk_tier": phase.risk_tier,
        "allowed_tools": list(phase.allowed_tools),
    }

    artifact_context = _artifact_context(phase, repo_path, errors)
    code_context = _code_context(query, errors)
    pattern_context = _pattern_context(query, errors)
    health_signals = _health_context(errors)

    gate = _gate_decision(
        phase=phase,
        code_context=code_context,
        artifact_context=artifact_context,
        pattern_context=pattern_context,
        health_signals=health_signals,
        source_errors=errors,
    )
    summary = _build_summary(phase, gate, code_context, health_signals)

    _persist_preflight_summary(summary, code_context, errors)

    return PreflightRecord(
        schema_version="p75.v1",
        generated_at=datetime.now(tz=UTC).isoformat(),
        phase_context=phase_context,
        artifact_context=artifact_context,
        code_context=code_context,
        pattern_context=pattern_context,
        health_signals=health_signals,
        gate=gate,
        summary=summary,
        source_errors=errors,
    )


def _phase_query(phase: PhaseRow) -> str:
    prompt = (phase.execution_prompt or "").strip().replace("\n", " ")
    prompt = prompt[:240]
    return f"{phase.phase_name}. {prompt}".strip()


def _artifact_context(phase: PhaseRow, repo_path: str, errors: list[str]) -> dict:
    docs_dir = Path(repo_path) / "docs"
    try:
        candidates = sorted(
            list(docs_dir.glob("P*_PLAN.md")) + list(docs_dir.glob("P*_COMPLETION_REPORT.md")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except Exception as e:
        errors.append(f"artifact_context:{e}")
        return {"phase_docs": [], "handoff_entries": [], "artifact_register": ""}

    phase_docs = [str(p.relative_to(Path(repo_path))) for p in candidates[:8]]

    handoff_entries = []
    try:
        from ai.learning.handoff_parser import parse_handoff  # noqa: PLC0415

        entries = parse_handoff(Path(repo_path) / "HANDOFF.md")
        for entry in entries[:6]:
            handoff_entries.append(
                {
                    "timestamp": entry.timestamp,
                    "summary": entry.summary,
                    "done_tasks": entry.done_tasks[:3],
                }
            )
    except Exception as e:
        errors.append(f"handoff_context:{e}")

    return {
        "phase_docs": phase_docs,
        "handoff_entries": handoff_entries,
        "artifact_register": "docs/PHASE_ARTIFACT_REGISTER.md",
        "dependency_refs": [f"P{dep}" for dep in phase.dependencies],
    }


def _code_context(query: str, errors: list[str]) -> dict:
    context = {"fused": {}, "impact": {}, "changed_files": []}
    try:
        from ai.rag.code_query import code_fused_context  # noqa: PLC0415

        fused = code_fused_context(query, limit=3)
        context["fused"] = fused
        files: list[str] = []
        for row in fused.get("results", []):
            path = str(row.get("relative_path", "") or "")
            if path:
                files.append(path)
        context["changed_files"] = sorted(set(files))[:6]
    except Exception as e:
        errors.append(f"code_fused_context:{e}")

    if context["changed_files"]:
        try:
            from ai.code_intel.store import get_code_store  # noqa: PLC0415

            store = get_code_store()
            context["impact"] = store.query_impact(
                context["changed_files"], max_depth=2, include_tests=True
            )
        except Exception as e:
            errors.append(f"impact_context:{e}")

    return context


def _pattern_context(query: str, errors: list[str]) -> dict:
    output = {
        "task_patterns": [],
        "agent_knowledge": [],
        "shared_context": [],
    }
    try:
        from ai.learning.task_retriever import retrieve_similar_tasks  # noqa: PLC0415

        output["task_patterns"] = retrieve_similar_tasks(query, top_k=3)
    except Exception as e:
        errors.append(f"task_patterns:{e}")

    try:
        from ai.collab.knowledge_base import get_agent_knowledge  # noqa: PLC0415

        output["agent_knowledge"] = get_agent_knowledge().query_knowledge(query, top_k=3)
    except Exception as e:
        errors.append(f"agent_knowledge:{e}")

    try:
        from ai.collab.shared_context import get_shared_context  # noqa: PLC0415

        output["shared_context"] = get_shared_context().query_relevant(query, top_k=3)
    except Exception as e:
        errors.append(f"shared_context:{e}")

    return output


def _health_context(errors: list[str]) -> dict:
    output = {"timers": {}, "pipeline": {}, "providers": {}}
    try:
        from ai.agents.timer_sentinel import check_timers  # noqa: PLC0415

        output["timers"] = check_timers()
    except Exception as e:
        errors.append(f"timer_health:{e}")

    try:
        from ai.system.pipeline_status import get_pipeline_status  # noqa: PLC0415

        output["pipeline"] = get_pipeline_status()
    except Exception as e:
        errors.append(f"pipeline_health:{e}")

    try:
        from ai.router import get_health_snapshot  # noqa: PLC0415

        output["providers"] = get_health_snapshot()
    except Exception as e:
        errors.append(f"provider_health:{e}")

    return output


def _gate_decision(
    *,
    phase: PhaseRow,
    code_context: dict,
    artifact_context: dict,
    pattern_context: dict,
    health_signals: dict,
    source_errors: list[str],
) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []
    risk_is_high = phase.risk_tier.lower() == "high"

    timers_status = str(health_signals.get("timers", {}).get("status", "")).lower()
    pipeline_status = str(health_signals.get("pipeline", {}).get("status", "")).lower()

    if timers_status == "critical":
        if risk_is_high:
            blockers.append("timer_health_critical")
        else:
            warnings.append("timer_health_critical")
    elif timers_status in {"warning", "stale"}:
        warnings.append("timer_health_warning")

    if pipeline_status == "error":
        if risk_is_high:
            blockers.append("pipeline_health_error")
        else:
            warnings.append("pipeline_health_error")
    elif pipeline_status == "stale":
        warnings.append("pipeline_health_stale")

    providers = health_signals.get("providers", {}) or {}
    if providers:
        all_auth_broken = all(bool(v.get("auth_broken", False)) for v in providers.values())
        if all_auth_broken:
            if risk_is_high:
                blockers.append("provider_auth_all_broken")
            else:
                warnings.append("provider_auth_all_broken")
    else:
        warnings.append("provider_health_missing")

    fused_results = (code_context.get("fused") or {}).get("results", [])
    if not fused_results:
        if phase.risk_tier.lower() == "high":
            blockers.append("missing_code_context")
        else:
            warnings.append("missing_code_context")

    if not artifact_context.get("phase_docs"):
        warnings.append("missing_artifact_context")
    if not pattern_context.get("task_patterns"):
        warnings.append("missing_task_patterns")
    if source_errors and phase.risk_tier.lower() == "high":
        warnings.append("source_errors_present")

    severity = "block" if blockers else ("warning" if warnings else "ok")
    return {
        "allowed": len(blockers) == 0,
        "severity": severity,
        "blockers": blockers,
        "warnings": warnings,
        "source_errors": list(source_errors),
    }


def _build_summary(
    phase: PhaseRow,
    gate: dict,
    code_context: dict,
    health_signals: dict,
) -> str:
    fused_count = len((code_context.get("fused") or {}).get("results", []))
    timers = health_signals.get("timers", {}).get("status", "unknown")
    pipeline = health_signals.get("pipeline", {}).get("status", "unknown")
    return (
        f"Preflight P{phase.phase_number}: allowed={gate.get('allowed')} "
        f"severity={gate.get('severity')} fused_hits={fused_count} "
        f"warnings={len(gate.get('warnings', []))} "
        f"timers={timers} pipeline={pipeline}"
    )


def _persist_preflight_summary(summary: str, code_context: dict, errors: list[str]) -> None:
    try:
        from ai.collab.shared_context import get_shared_context  # noqa: PLC0415

        files = list(code_context.get("changed_files", []) or [])[:6]
        get_shared_context().add_context(
            context_type="preflight",
            content=summary,
            agent="phase_control",
            files=files,
            priority=2,
            ttl_hours=72,
        )
    except Exception as e:
        errors.append(f"persist_preflight_context:{e}")
