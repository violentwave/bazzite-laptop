"""Notion sync and in-memory lease backend for phase-control."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

import httpx

from ai.notion.client import NotionClient, get_notion_config, is_notion_configured
from ai.phase_control.models import PhaseRow, PhaseStatus


class PhaseSyncBackend(Protocol):
    """Required persistence interface for phase-control state."""

    def get_next_ready_phase(self) -> PhaseRow | None: ...

    def get_phase(self, phase_number: int) -> PhaseRow | None: ...

    def update_phase(self, phase: PhaseRow) -> None: ...

    def claim_lease(
        self,
        phase_number: int,
        *,
        run_id: str,
        runner_host: str,
        lease_seconds: int,
        slack_channel: str | None,
        slack_thread_ts: str | None,
    ) -> bool: ...

    def renew_lease(self, phase_number: int, *, run_id: str, lease_seconds: int) -> bool: ...

    def release_lease(self, phase_number: int, *, run_id: str) -> bool: ...


class InMemoryPhaseSync:
    """Thread-safe in-memory backend used by tests and local dry runs."""

    def __init__(self, phases: list[PhaseRow] | None = None):
        self._lock = Lock()
        self._phases: dict[int, PhaseRow] = {}
        for phase in phases or []:
            self._phases[phase.phase_number] = phase

    def list_phases(self) -> list[PhaseRow]:
        """Return all phases in phase-number order."""
        with self._lock:
            return [replace(self._phases[k]) for k in sorted(self._phases)]

    def add_phase(self, phase: PhaseRow) -> None:
        """Insert or replace a phase row."""
        with self._lock:
            self._phases[phase.phase_number] = phase

    def get_phase(self, phase_number: int) -> PhaseRow | None:
        """Fetch a phase by number."""
        with self._lock:
            phase = self._phases.get(phase_number)
            return replace(phase) if phase else None

    def update_phase(self, phase: PhaseRow) -> None:
        """Persist a phase row update."""
        with self._lock:
            self._phases[phase.phase_number] = phase

    def _dependencies_satisfied(self, phase: PhaseRow) -> bool:
        for dep in phase.dependencies:
            dep_row = self._phases.get(dep)
            if dep_row is None or dep_row.status != PhaseStatus.DONE:
                return False
        return True

    def get_next_ready_phase(self) -> PhaseRow | None:
        """Pick the next eligible Ready phase honoring dependency completion."""
        with self._lock:
            for key in sorted(self._phases):
                phase = self._phases[key]
                if phase.status != PhaseStatus.READY:
                    continue
                if not self._dependencies_satisfied(phase):
                    continue
                if phase.has_active_lease():
                    continue
                return replace(phase)
        return None

    def claim_lease(
        self,
        phase_number: int,
        *,
        run_id: str,
        runner_host: str,
        lease_seconds: int,
        slack_channel: str | None,
        slack_thread_ts: str | None,
    ) -> bool:
        """Acquire lease ownership if no conflicting active lease exists."""
        with self._lock:
            phase = self._phases.get(phase_number)
            if phase is None:
                return False

            now = datetime.now(tz=UTC)
            if phase.has_active_lease(now=now) and phase.run_id != run_id:
                return False

            phase.run_id = run_id
            phase.runner_host = runner_host
            phase.started_at = phase.started_at or now
            phase.lease_expires_at = now + timedelta(seconds=lease_seconds)
            phase.slack_channel = slack_channel
            phase.slack_thread_ts = slack_thread_ts
            return True

    def renew_lease(self, phase_number: int, *, run_id: str, lease_seconds: int) -> bool:
        """Renew lease only for the active lease owner."""
        with self._lock:
            phase = self._phases.get(phase_number)
            if phase is None or phase.run_id != run_id:
                return False
            now = datetime.now(tz=UTC)
            phase.lease_expires_at = now + timedelta(seconds=lease_seconds)
            return True

    def release_lease(self, phase_number: int, *, run_id: str) -> bool:
        """Release lease only for current run owner."""
        with self._lock:
            phase = self._phases.get(phase_number)
            if phase is None or phase.run_id != run_id:
                return False
            phase.run_id = None
            phase.runner_host = None
            phase.lease_expires_at = None
            return True


class NotionPhaseSync:
    """Notion-backed phase sync implementation."""

    def __init__(self, database_id: str):
        if not database_id:
            raise ValueError("database_id is required")
        self.database_id = database_id

    @staticmethod
    def _format_notion_error(database_id: str, exc: Exception) -> str:
        """Return an operator-facing message for Notion API failures."""
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            detail = exc.response.text.strip()
            try:
                payload = exc.response.json()
                detail = payload.get("message") or payload.get("code") or detail
            except ValueError:
                pass

            if status_code == 404:
                return (
                    f"Notion database '{database_id}' could not be queried. "
                    "This runner uses POST /v1/databases/{id}/query and expects a Notion "
                    "database ID. Check NOTION_PHASE_DATABASE_ID, confirm the integration is "
                    "shared to that database, and verify the token belongs to the correct "
                    f"workspace. Notion said: {detail}"
                )
            if status_code in {401, 403}:
                return (
                    f"Notion access denied for database '{database_id}'. "
                    "Check NOTION_API_KEY, confirm the integration has access to the phase "
                    f"database, and verify the token belongs to the intended workspace. "
                    f"Notion said: {detail}"
                )
            return (
                f"Notion API error while querying database '{database_id}' "
                f"(HTTP {status_code}): {detail}"
            )

        return f"Notion query failed for database '{database_id}': {exc}"

    def _list_rows(self) -> list[PhaseRow]:
        """Query Notion and convert phase rows."""
        return [self._phase_from_page(page) for page in self._query_all()]

    def smoke_test(self) -> dict:
        """Read-only probe for control-plane config and database accessibility."""
        if not is_notion_configured():
            raise RuntimeError("Notion not configured: missing NOTION_API_KEY")

        rows = self._list_rows()
        rows.sort(key=lambda row: row.phase_number)
        done = {row.phase_number for row in rows if row.status == PhaseStatus.DONE}
        next_ready = None
        now = datetime.now(tz=UTC)
        for row in rows:
            if row.status != PhaseStatus.READY:
                continue
            if any(dep not in done for dep in row.dependencies):
                continue
            if row.has_active_lease(now=now):
                continue
            next_ready = row
            break

        return {
            "config_loaded": True,
            "database_id": self.database_id,
            "query_ok": True,
            "row_count": len(rows),
            "next_ready_phase": next_ready.phase_number if next_ready else None,
            "next_ready_phase_name": next_ready.phase_name if next_ready else None,
        }

    @staticmethod
    def _extract_text(prop: dict | None) -> str:
        def _concat(blocks: list[dict]) -> str:
            out: list[str] = []
            for item in blocks:
                plain = item.get("plain_text")
                if isinstance(plain, str) and plain:
                    out.append(plain)
                    continue
                text_obj = item.get("text") or {}
                content = text_obj.get("content")
                if isinstance(content, str) and content:
                    out.append(content)
            return "".join(out)

        if not prop:
            return ""
        p_type = prop.get("type")
        if p_type == "title":
            return _concat(prop.get("title", []))
        if p_type == "rich_text":
            return _concat(prop.get("rich_text", []))
        if p_type == "select":
            select = prop.get("select") or {}
            return select.get("name", "")
        if p_type == "status":
            status = prop.get("status") or {}
            return status.get("name", "")
        if p_type == "number":
            value = prop.get("number")
            return "" if value is None else str(value)
        if p_type == "checkbox":
            return "true" if bool(prop.get("checkbox")) else "false"
        if p_type == "date":
            date_v = prop.get("date") or {}
            return date_v.get("start", "")
        return ""

    @staticmethod
    def _extract_bool(prop: dict | None, default: bool = False) -> bool:
        if not prop:
            return default
        if prop.get("type") == "checkbox":
            return bool(prop.get("checkbox"))
        txt = NotionPhaseSync._extract_text(prop).strip().lower()
        if txt in {"true", "1", "yes", "y"}:
            return True
        if txt in {"false", "0", "no", "n"}:
            return False
        return default

    @staticmethod
    def _extract_int(prop: dict | None, default: int) -> int:
        if not prop:
            return default
        txt = NotionPhaseSync._extract_text(prop).strip()
        try:
            return int(float(txt)) if txt else default
        except ValueError:
            return default

    @staticmethod
    def _extract_list(prop: dict | None) -> list[str]:
        raw = NotionPhaseSync._extract_text(prop)
        if not raw.strip():
            return []
        if "\n" in raw:
            return [line.strip() for line in raw.splitlines() if line.strip()]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @staticmethod
    def _extract_datetime(prop: dict | None) -> datetime | None:
        txt = NotionPhaseSync._extract_text(prop).strip()
        if not txt:
            return None
        try:
            dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            return None

    @staticmethod
    def _parse_status(raw_status: str) -> PhaseStatus:
        normalized = raw_status.strip().lower()
        mapping = {
            "planned": PhaseStatus.PLANNED,
            "ready": PhaseStatus.READY,
            "in progress": PhaseStatus.IN_PROGRESS,
            "done": PhaseStatus.DONE,
            "complete": PhaseStatus.DONE,
            "completed": PhaseStatus.DONE,
            "needs review": PhaseStatus.NEEDS_REVIEW,
            "blocked": PhaseStatus.BLOCKED,
            "cancelled": PhaseStatus.CANCELLED,
        }
        return mapping.get(normalized, PhaseStatus.PLANNED)

    @staticmethod
    def _phase_from_page(page: dict) -> PhaseRow:
        props = page.get("properties", {})

        def pick(*names: str) -> dict | None:
            for name in names:
                if name in props:
                    return props[name]
            return None

        status = NotionPhaseSync._parse_status(NotionPhaseSync._extract_text(pick("Status")))
        phase_number = NotionPhaseSync._extract_int(
            pick("Phase Number", "Phase #", "PhaseNumber"),
            0,
        )
        phase_name = NotionPhaseSync._extract_text(pick("Phase Name", "Name", "Phase"))
        validation_summary_text = NotionPhaseSync._extract_text(
            pick("Validation Summary", "ValidationSummary")
        )
        validation_summary: dict | None = None
        if validation_summary_text.strip():
            try:
                validation_summary = json.loads(validation_summary_text)
            except json.JSONDecodeError:
                validation_summary = {"raw": validation_summary_text}

        row = PhaseRow(
            phase_name=phase_name or f"Phase-{phase_number}",
            phase_number=phase_number,
            status=status,
            execution_prompt=NotionPhaseSync._extract_text(
                pick("Execution Prompt", "ExecutionPrompt")
            ),
            validation_commands=NotionPhaseSync._extract_list(
                pick("Validation Commands", "ValidationCommands")
            ),
            done_criteria=NotionPhaseSync._extract_list(pick("Done Criteria", "DoneCriteria")),
            dependencies=[
                int(v[1:]) if v.lower().startswith("p") and v[1:].isdigit() else int(v)
                for v in NotionPhaseSync._extract_list(pick("Dependencies"))
                if v.isdigit() or (v.lower().startswith("p") and v[1:].isdigit())
            ],
            backend=NotionPhaseSync._extract_text(pick("Backend")) or "codex",
            branch_name=NotionPhaseSync._extract_text(pick("Branch", "Branch Name")) or None,
            allowed_tools=NotionPhaseSync._extract_list(pick("Allowed Tools", "AllowedTools")),
            execution_mode=NotionPhaseSync._extract_text(pick("Execution Mode", "ExecutionMode"))
            or "safe",
            risk_tier=NotionPhaseSync._extract_text(pick("Risk Tier", "RiskTier")) or "medium",
            approval_required=NotionPhaseSync._extract_bool(
                pick("Approval Required", "ApprovalRequired")
            ),
            approval_granted=NotionPhaseSync._extract_bool(
                pick("Approval Granted", "ApprovalGranted")
            ),
            timeout_seconds=NotionPhaseSync._extract_int(
                pick("Timeout Seconds", "TimeoutSeconds"),
                1800,
            ),
            env_allowlist=NotionPhaseSync._extract_list(pick("Env Allowlist", "EnvAllowlist")),
            artifacts_dir=NotionPhaseSync._extract_text(pick("Artifacts Dir", "ArtifactsDir")),
            run_id=NotionPhaseSync._extract_text(pick("Run ID", "RunID")) or None,
            runner_host=NotionPhaseSync._extract_text(pick("Runner Host", "RunnerHost")) or None,
            started_at=NotionPhaseSync._extract_datetime(pick("Started At", "StartedAt")),
            lease_expires_at=NotionPhaseSync._extract_datetime(
                pick("Lease Expires At", "LeaseExpiresAt")
            ),
            slack_channel=NotionPhaseSync._extract_text(pick("Slack Channel", "SlackChannel"))
            or None,
            slack_thread_ts=NotionPhaseSync._extract_text(pick("Slack Thread TS", "SlackThreadTS"))
            or None,
            blocker=NotionPhaseSync._extract_text(pick("Blocker")) or None,
            validation_summary=validation_summary,
            summary=NotionPhaseSync._extract_text(pick("Summary")),
            metadata={"notion_page_id": page.get("id")},
        )
        return row

    @staticmethod
    def _build_property_update(prop: dict, value) -> dict:
        p_type = prop.get("type")
        if p_type == "title":
            content = "" if value is None else str(value)
            return {"title": [{"type": "text", "text": {"content": content}}]}
        if p_type == "rich_text":
            content = "" if value is None else str(value)
            return {"rich_text": [{"type": "text", "text": {"content": content}}]}
        if p_type == "status":
            return {"status": {"name": str(value)}}
        if p_type == "select":
            return {"select": {"name": str(value)}}
        if p_type == "number":
            if value is None or value == "":
                return {"number": None}
            return {"number": int(value)}
        if p_type == "checkbox":
            return {"checkbox": bool(value)}
        if p_type == "date":
            if value is None:
                return {"date": None}
            if isinstance(value, datetime):
                return {"date": {"start": value.astimezone(UTC).isoformat()}}
            return {"date": {"start": str(value)}}
        return {}

    @staticmethod
    def _set_if_present(updates: dict, props: dict, name: str, value) -> None:
        if name not in props:
            return
        built = NotionPhaseSync._build_property_update(props[name], value)
        if built:
            updates[name] = built

    def _query_all(self) -> list[dict]:
        if not is_notion_configured():
            return []
        client = NotionClient(get_notion_config())
        try:
            return client.query_database(self.database_id, filter_obj=None, limit=100)
        except Exception as exc:
            raise RuntimeError(self._format_notion_error(self.database_id, exc)) from exc
        finally:
            client.close()

    def _update_page(self, page_id: str, updates: dict) -> bool:
        if not updates:
            return True
        if not is_notion_configured():
            return False
        client = NotionClient(get_notion_config())
        try:
            client._request("PATCH", f"/v1/pages/{page_id}", json={"properties": updates})
            return True
        except Exception:
            return False
        finally:
            client.close()

    def get_next_ready_phase(self) -> PhaseRow | None:
        """Fetch next eligible Ready phase from Notion."""
        rows = self._list_rows()
        rows.sort(key=lambda row: row.phase_number)

        done = {row.phase_number for row in rows if row.status == PhaseStatus.DONE}
        now = datetime.now(tz=UTC)
        for row in rows:
            if row.status != PhaseStatus.READY:
                continue
            if any(dep not in done for dep in row.dependencies):
                continue
            if row.has_active_lease(now=now):
                continue
            return row
        return None

    def get_phase(self, phase_number: int) -> PhaseRow | None:
        """Get phase row from Notion."""
        for page in self._query_all():
            row = self._phase_from_page(page)
            if row.phase_number == phase_number:
                return row
        return None

    def update_phase(self, phase: PhaseRow) -> None:
        """Persist phase row to Notion."""
        page_id = str(phase.metadata.get("notion_page_id", ""))
        if not page_id:
            current = self.get_phase(phase.phase_number)
            if current is None:
                return
            page_id = str(current.metadata.get("notion_page_id", ""))
            if not page_id:
                return
            phase.metadata["notion_page_id"] = page_id

        client = NotionClient(get_notion_config())
        try:
            page = client.get_page(page_id)
            props = page.get("properties", {})
        finally:
            client.close()

        updates: dict = {}
        self._set_if_present(updates, props, "Status", phase.status.value)
        self._set_if_present(updates, props, "Run ID", phase.run_id)
        self._set_if_present(updates, props, "Runner Host", phase.runner_host)
        self._set_if_present(updates, props, "Started At", phase.started_at)
        self._set_if_present(updates, props, "Lease Expires At", phase.lease_expires_at)
        self._set_if_present(updates, props, "Slack Channel", phase.slack_channel)
        self._set_if_present(updates, props, "Slack Thread TS", phase.slack_thread_ts)
        self._set_if_present(updates, props, "Blocker", phase.blocker)
        self._set_if_present(
            updates,
            props,
            "Validation Summary",
            json.dumps(phase.validation_summary) if phase.validation_summary is not None else "",
        )
        self._set_if_present(updates, props, "Summary", phase.summary)
        self._set_if_present(updates, props, "Approval Granted", phase.approval_granted)
        self._update_page(page_id, updates)

    def claim_lease(
        self,
        phase_number: int,
        *,
        run_id: str,
        runner_host: str,
        lease_seconds: int,
        slack_channel: str | None,
        slack_thread_ts: str | None,
    ) -> bool:
        """Acquire row lease in Notion."""
        phase = self.get_phase(phase_number)
        if phase is None:
            return False

        now = datetime.now(tz=UTC)
        if phase.has_active_lease(now=now):
            current_owner = (phase.run_id or "", phase.runner_host or "")
            requested_owner = (run_id, runner_host)
            if current_owner != requested_owner:
                return False

        phase.run_id = run_id
        phase.runner_host = runner_host
        phase.started_at = phase.started_at or now
        phase.lease_expires_at = now + timedelta(seconds=lease_seconds)
        if slack_channel is not None:
            phase.slack_channel = slack_channel
        if slack_thread_ts is not None:
            phase.slack_thread_ts = slack_thread_ts
        self.update_phase(phase)
        return True

    def renew_lease(self, phase_number: int, *, run_id: str, lease_seconds: int) -> bool:
        """Renew Notion lease."""
        phase = self.get_phase(phase_number)
        if phase is None:
            return False
        if phase.run_id != run_id or phase.runner_host is None:
            return False
        phase.lease_expires_at = datetime.now(tz=UTC) + timedelta(seconds=lease_seconds)
        self.update_phase(phase)
        return True

    def release_lease(self, phase_number: int, *, run_id: str) -> bool:
        """Release Notion lease."""
        phase = self.get_phase(phase_number)
        if phase is None:
            return False
        if phase.run_id != run_id or phase.runner_host is None:
            return False
        phase.run_id = None
        phase.runner_host = None
        phase.lease_expires_at = None
        self.update_phase(phase)
        return True
