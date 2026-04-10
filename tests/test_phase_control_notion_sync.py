"""NotionPhaseSync adapter-boundary tests for P55."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx

from ai.phase_control.models import PhaseStatus
from ai.phase_control.notion_sync import NotionPhaseSync


def _page(
    *,
    page_id: str,
    phase_number: int,
    status: str,
    name: str,
    run_id: str = "",
    runner_host: str = "",
    lease_expires_at: str = "",
    deps: str = "",
) -> dict:
    return {
        "id": page_id,
        "properties": {
            "Phase Number": {"type": "number", "number": phase_number},
            "Phase Name": {
                "type": "title",
                "title": [{"plain_text": name}],
            },
            "Status": {"type": "status", "status": {"name": status}},
            "Execution Prompt": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "do work"}],
            },
            "Validation Commands": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "python -V"}],
            },
            "Done Criteria": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "tests pass"}],
            },
            "Dependencies": {
                "type": "rich_text",
                "rich_text": [{"plain_text": deps}],
            },
            "Run ID": {"type": "rich_text", "rich_text": [{"plain_text": run_id}]},
            "Runner Host": {
                "type": "rich_text",
                "rich_text": [{"plain_text": runner_host}],
            },
            "Started At": {"type": "date", "date": None},
            "Lease Expires At": {
                "type": "date",
                "date": {"start": lease_expires_at} if lease_expires_at else None,
            },
            "Slack Channel": {"type": "rich_text", "rich_text": [{"plain_text": "C1"}]},
            "Slack Thread TS": {"type": "rich_text", "rich_text": [{"plain_text": "1.1"}]},
            "Approval Granted": {"type": "checkbox", "checkbox": True},
            "Summary": {"type": "rich_text", "rich_text": []},
            "Blocker": {"type": "rich_text", "rich_text": []},
            "Validation Summary": {"type": "rich_text", "rich_text": []},
        },
    }


class _FakeNotion:
    pages: list[dict] = []
    updates: list[tuple[str, dict]] = []

    def __init__(self, config):
        self.config = config

    def query_database(self, database_id, filter_obj=None, limit=100):
        _ = (database_id, filter_obj, limit)
        return self.pages

    def get_page(self, page_id):
        return next(page for page in self.pages if page["id"] == page_id)

    def _request(self, method, endpoint, **kwargs):
        if method == "PATCH":
            page_id = endpoint.split("/")[-1]
            self.updates.append((page_id, kwargs.get("json", {})))
            props = kwargs.get("json", {}).get("properties", {})
            page = self.get_page(page_id)
            for key, value in props.items():
                p_type = page["properties"][key]["type"]
                page["properties"][key][p_type] = value[p_type]
        return {}

    def close(self):
        return None


@patch("ai.phase_control.notion_sync.is_notion_configured", return_value=True)
@patch("ai.phase_control.notion_sync.get_notion_config", return_value=object())
@patch("ai.phase_control.notion_sync.NotionClient", _FakeNotion)
def test_get_next_ready_phase_and_dependencies(*_):
    done = _page(page_id="p54", phase_number=54, status="Done", name="P54")
    ready = _page(page_id="p55", phase_number=55, status="Ready", name="P55", deps="54")
    blocked = _page(page_id="p56", phase_number=56, status="Ready", name="P56", deps="99")
    _FakeNotion.pages = [blocked, ready, done]
    sync = NotionPhaseSync(database_id="db1")

    phase = sync.get_next_ready_phase()
    assert phase is not None
    assert phase.phase_number == 55


@patch("ai.phase_control.notion_sync.is_notion_configured", return_value=True)
@patch("ai.phase_control.notion_sync.get_notion_config", return_value=object())
@patch("ai.phase_control.notion_sync.NotionClient", _FakeNotion)
def test_claim_lease_prevents_duplicate_owner_not_runid_only(*_):
    lease_end = (datetime.now(tz=UTC) + timedelta(minutes=5)).isoformat()
    _FakeNotion.pages = [
        _page(
            page_id="p55",
            phase_number=55,
            status="Ready",
            name="P55",
            run_id="run-a",
            runner_host="host-a",
            lease_expires_at=lease_end,
        )
    ]
    _FakeNotion.updates = []
    sync = NotionPhaseSync(database_id="db1")

    claimed = sync.claim_lease(
        55,
        run_id="run-a",
        runner_host="host-b",
        lease_seconds=600,
        slack_channel="C1",
        slack_thread_ts="1.1",
    )
    assert claimed is False
    assert _FakeNotion.updates == []


@patch("ai.phase_control.notion_sync.is_notion_configured", return_value=True)
@patch("ai.phase_control.notion_sync.get_notion_config", return_value=object())
@patch("ai.phase_control.notion_sync.NotionClient", _FakeNotion)
def test_claim_and_release_lease_round_trip(*_):
    _FakeNotion.pages = [
        _page(page_id="p55", phase_number=55, status="Ready", name="P55", lease_expires_at="")
    ]
    _FakeNotion.updates = []
    sync = NotionPhaseSync(database_id="db1")

    assert sync.claim_lease(
        55,
        run_id="run-b",
        runner_host="host-b",
        lease_seconds=120,
        slack_channel="C1",
        slack_thread_ts="1.1",
    )

    phase = sync.get_phase(55)
    assert phase is not None
    assert phase.run_id == "run-b"
    assert phase.runner_host == "host-b"

    assert sync.release_lease(55, run_id="run-b")
    phase = sync.get_phase(55)
    assert phase is not None
    assert phase.run_id is None
    assert phase.lease_expires_at is None
    assert phase.status == PhaseStatus.READY


def test_format_notion_error_maps_404_to_actionable_message():
    request = httpx.Request("POST", "https://api.notion.com/v1/databases/db1/query")
    response = httpx.Response(
        404,
        request=request,
        json={"object": "error", "code": "object_not_found", "message": "Could not find database"},
    )
    exc = httpx.HTTPStatusError("404", request=request, response=response)

    message = NotionPhaseSync._format_notion_error("db1", exc)

    assert "expects a Notion database ID" in message
    assert "integration is shared" in message
    assert "Could not find database" in message


def test_format_notion_error_maps_auth_failure_to_actionable_message():
    request = httpx.Request("POST", "https://api.notion.com/v1/databases/db1/query")
    response = httpx.Response(
        403,
        request=request,
        json={"object": "error", "code": "restricted_resource", "message": "Forbidden"},
    )
    exc = httpx.HTTPStatusError("403", request=request, response=response)

    message = NotionPhaseSync._format_notion_error("db1", exc)

    assert "Notion access denied" in message
    assert "Check NOTION_API_KEY" in message
    assert "Forbidden" in message


@patch("ai.phase_control.notion_sync.is_notion_configured", return_value=True)
@patch("ai.phase_control.notion_sync.get_notion_config", return_value=object())
@patch("ai.phase_control.notion_sync.NotionClient", _FakeNotion)
def test_smoke_test_reports_query_and_next_ready_phase(*_):
    done = _page(page_id="p54", phase_number=54, status="Done", name="P54")
    ready = _page(page_id="p55", phase_number=55, status="Ready", name="P55", deps="54")
    _FakeNotion.pages = [ready, done]
    sync = NotionPhaseSync(database_id="db1")

    result = sync.smoke_test()

    assert result["config_loaded"] is True
    assert result["query_ok"] is True
    assert result["row_count"] == 2
    assert result["next_ready_phase"] == 55
