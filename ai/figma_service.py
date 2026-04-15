"""Figma integration for design artifact reconciliation.

Provides authenticated access to the Figma REST API for listing teams,
projects, and files. Used by the MCP bridge to reconcile Bazzite's Midnight
Glass Design Lab inventory against actual Figma project contents.

Security:
- FIGMA_PAT loaded at runtime from keys.env, never committed or logged
- All API calls use HTTPS
- Token is scoped to read-only access (personal access token)
- No write operations are supported by the Figma REST API for file creation

API Limitations (documented):
- The Figma REST API is read-only for file/project structure
- Cannot create new Figma files via API
- Cannot duplicate files via API
- Cannot move files between projects via API
- Can list teams, projects, files, and retrieve file metadata/node data
- File content and node data can be read but not written
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.config import get_key, load_keys

logger = logging.getLogger(__name__)

FIGMA_API_BASE = "https://api.figma.com/v1"
_MAX_RETRIES = 2
_TIMEOUT_SECONDS = 30


@dataclass
class FigmaTeam:
    id: str
    name: str


@dataclass
class FigmaProject:
    id: str
    name: str
    team_id: str | None = None


@dataclass
class FigmaFile:
    id: str
    name: str
    key: str | None = None
    thumbnail_url: str | None = None
    last_modified: str | None = None
    project_id: str | None = None


@dataclass
class FigmaReconciliationEntry:
    expected_name: str
    found: bool = False
    figma_file: FigmaFile | None = None
    figma_project_id: str | None = None
    notes: str = ""


@dataclass
class FigmaReconciliationReport:
    target_project_name: str
    target_project_id: str | None = None
    expected_artifacts: list[str] = field(default_factory=list)
    present: list[FigmaReconciliationEntry] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)
    api_limitations: list[str] = field(default_factory=list)
    generated_at: str = ""


def _get_pat() -> str | None:
    load_keys(scope="figma")
    return get_key("FIGMA_PAT")


def _figma_request(endpoint: str, pat: str) -> dict | list | None:
    url = f"{FIGMA_API_BASE}/{endpoint}"
    for attempt in range(_MAX_RETRIES + 1):
        try:
            req = Request(  # noqa: S310
                url,
                headers={
                    "X-Figma-Token": pat,
                    "Accept": "application/json",
                },
            )
            with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except HTTPError as e:
            if e.code == 401:
                logger.error("Figma PAT is invalid or expired (401)")
                return {
                    "error": "authentication_failed",
                    "error_detail": "Invalid or expired Figma PAT",
                    "status_code": 401,
                }
            if e.code == 403:
                logger.error("Figma PAT lacks required scope (403)")
                return {
                    "error": "permission_denied",
                    "error_detail": "PAT does not have access to this resource",
                    "status_code": 403,
                }
            if e.code == 404:
                return {
                    "error": "not_found",
                    "error_detail": f"Resource not found: {endpoint}",
                    "status_code": 404,
                }
            if e.code == 429:
                logger.warning("Figma API rate limit hit, attempt %d", attempt + 1)
                if attempt < _MAX_RETRIES:
                    import time

                    time.sleep(2**attempt)
                    continue
                return {
                    "error": "rate_limited",
                    "error_detail": "Figma API rate limit exceeded",
                    "status_code": 429,
                }
            body = e.read().decode("utf-8", errors="replace")[:500]
            logger.error("Figma API HTTP error %d: %s", e.code, body)
            return {"error": f"http_{e.code}", "error_detail": body, "status_code": e.code}
        except URLError as e:
            logger.error("Figma API connection error: %s", e.reason)
            return {"error": "connection_failed", "error_detail": str(e.reason)}
        except Exception as e:
            logger.error("Figma API unexpected error: %s", e)
            return {"error": "unexpected", "error_detail": str(e)}
    return None


def _is_error(data: Any) -> bool:
    return isinstance(data, dict) and "error" in data


def list_teams(pat: str | None = None) -> list[dict]:
    if pat is None:
        pat = _get_pat()
    if not pat:
        return [
            {
                "error": "figma_pat_missing",
                "error_detail": (
                    "FIGMA_PAT not found in keys.env. "
                    "Add FIGMA_PAT=your_token to ~/.config/bazzite-ai/keys.env"
                ),
                "operator_action": (
                    "Generate a Figma PAT at Settings > "
                    "Personal access tokens and add it to keys.env"
                ),
            }
        ]
    data = _figma_request("teams", pat)
    if data is None or _is_error(data):
        return (
            data
            if isinstance(data, list)
            else [data]
            if data
            else [{"error": "no_response", "error_detail": "Figma API returned no data"}]
        )
    teams = data if isinstance(data, list) else data.get("teams", [])
    return [{"id": t["id"], "name": t["name"]} for t in teams if "id" in t and "name" in t]


def list_projects(team_id: str, pat: str | None = None) -> list[dict]:
    if pat is None:
        pat = _get_pat()
    if not pat:
        return [{"error": "figma_pat_missing", "error_detail": "FIGMA_PAT not found in keys.env"}]
    data = _figma_request(f"teams/{team_id}/projects", pat)
    if data is None or _is_error(data):
        return data if isinstance(data, list) else [data] if data else [{"error": "no_response"}]
    projects = data.get("projects", []) if isinstance(data, dict) else data
    return [{"id": p["id"], "name": p["name"]} for p in projects if "id" in p and "name" in p]


def list_project_files(project_id: str, pat: str | None = None) -> list[dict]:
    if pat is None:
        pat = _get_pat()
    if not pat:
        return [{"error": "figma_pat_missing", "error_detail": "FIGMA_PAT not found in keys.env"}]
    data = _figma_request(f"projects/{project_id}/files", pat)
    if data is None or _is_error(data):
        return data if isinstance(data, list) else [data] if data else [{"error": "no_response"}]
    files = data.get("files", []) if isinstance(data, dict) else data
    return [
        {
            "id": f.get("id", ""),
            "name": f.get("name", ""),
            "key": f.get("key", ""),
            "thumbnail_url": f.get("thumbnail_url", ""),
            "last_modified": f.get("last_modified", ""),
        }
        for f in files
    ]


def get_file_metadata(file_key: str, pat: str | None = None) -> dict:
    if pat is None:
        pat = _get_pat()
    if not pat:
        return {"error": "figma_pat_missing", "error_detail": "FIGMA_PAT not found in keys.env"}
    data = _figma_request(f"files/{file_key}", pat)
    if _is_error(data):
        return data
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "last_modified": data.get("lastModified", ""),
        "thumbnail_url": data.get("thumbnailUrl", ""),
        "version": data.get("version", ""),
        "pages": [
            {"id": p.get("id", ""), "name": p.get("name", ""), "type": p.get("type", "")}
            for p in data.get("document", {}).get("children", [])
        ]
        if "document" in data
        else [],
    }


def find_bazzite_project(pat: str | None = None, project_name: str = "Bazzite") -> dict:
    if pat is None:
        pat = _get_pat()
    if not pat:
        return {"error": "figma_pat_missing", "error_detail": "FIGMA_PAT not found in keys.env"}

    teams = list_teams(pat)
    if not teams:
        return {
            "error": "no_teams",
            "error_detail": ("No teams found for this PAT. Verify the token has team access."),
        }
    if isinstance(teams, list) and teams and "error" in teams[0]:
        return teams[0]

    for team in teams:
        team_id = team.get("id", "")
        projects = list_projects(team_id, pat)
        if isinstance(projects, list) and projects and "error" in projects[0]:
            continue
        for project in projects:
            if project.get("name", "").lower() == project_name.lower():
                return {
                    "found": True,
                    "team_id": team_id,
                    "team_name": team.get("name", ""),
                    "project_id": project.get("id", ""),
                    "project_name": project.get("name", ""),
                }

    return {
        "found": False,
        "searched_teams": len(teams),
        "project_name_searched": project_name,
        "error": "project_not_found",
        "error_detail": (f"No Figma project named '{project_name}' found in accessible teams"),
        "operator_action": (
            f"Create a Figma project named '{project_name}' "
            "and add this PAT's account to it, "
            "or specify a different project name"
        ),
    }


def reconcile_design_lab(
    expected_artifacts: list[str],
    project_name: str = "Bazzite",
    pat: str | None = None,
) -> FigmaReconciliationReport:
    report = FigmaReconciliationReport(
        target_project_name=project_name,
        expected_artifacts=expected_artifacts,
        generated_at=datetime.now().isoformat(),
        api_limitations=[
            "Figma REST API is read-only for project/file structure",
            "Cannot create new Figma files via API",
            "Cannot duplicate files via API",
            "Cannot move files between projects via API",
            "Artifacts must be created manually in Figma and placed in the target project",
        ],
    )

    if pat is None:
        pat = _get_pat()
    if not pat:
        return report

    project_info = find_bazzite_project(pat, project_name)
    if not project_info.get("found", False):
        report.notes = (
            f"Project '{project_name}' not found: {project_info.get('error_detail', 'unknown')}"
        )
        return report

    report.target_project_id = project_info.get("project_id")

    files = list_project_files(report.target_project_id, pat)
    if isinstance(files, list) and files and "error" in files[0]:
        report.notes = f"Error listing files: {files[0].get('error_detail', 'unknown')}"
        return report

    existing_names = {f.get("name", "") for f in files}

    for artifact_name in expected_artifacts:
        if artifact_name in existing_names:
            matching = [f for f in files if f.get("name") == artifact_name]
            f = matching[0] if matching else {}
            entry = FigmaReconciliationEntry(
                expected_name=artifact_name,
                found=True,
                figma_file=FigmaFile(
                    id=f.get("id", ""),
                    name=f.get("name", ""),
                    key=f.get("key", ""),
                    thumbnail_url=f.get("thumbnail_url", ""),
                    last_modified=f.get("last_modified", ""),
                    project_id=report.target_project_id,
                ),
            )
            report.present.append(entry)

    for artifact_name in expected_artifacts:
        if artifact_name not in existing_names:
            report.missing.append(artifact_name)

    for file_name in existing_names:
        if file_name not in expected_artifacts:
            report.unexpected.append(file_name)

    return report


MIDNIGHT_GLASS_EXPECTED_ARTIFACTS = [
    "Midnight Glass - Color Tokens",
    "Midnight Glass - Typography",
    "Midnight Glass - Spacing & Grid",
    "Midnight Glass - Components",
    "Midnight Glass - Panels",
    "Midnight Glass - Chat Workspace",
    "Midnight Glass - Shell Gateway",
    "Midnight Glass - Security Dashboard",
    "Midnight Glass - Provider Cards",
    "Midnight Glass - Settings Panels",
    "Midnight Glass - Motion & Transitions",
    "Midnight Glass - Iconography",
]


def figma_list_teams() -> list[dict]:
    return list_teams()


def figma_list_projects(team_id: str) -> list[dict]:
    return list_projects(team_id)


def figma_list_project_files(project_id: str) -> list[dict]:
    return list_project_files(project_id)


def figma_get_file(file_key: str) -> dict:
    return get_file_metadata(file_key)


def figma_find_project(project_name: str = "Bazzite") -> dict:
    return find_bazzite_project(project_name=project_name)


def figma_reconcile(project_name: str = "Bazzite", artifact_names: list[str] | None = None) -> dict:
    artifacts = artifact_names or MIDNIGHT_GLASS_EXPECTED_ARTIFACTS
    report = reconcile_design_lab(expected_artifacts=artifacts, project_name=project_name)
    result = {
        "project_name": report.target_project_name,
        "project_id": report.target_project_id,
        "generated_at": report.generated_at,
        "total_expected": len(report.expected_artifacts),
        "found": len([e for e in report.present if e.found]),
        "missing": report.missing,
        "unexpected": report.unexpected,
        "api_limitations": report.api_limitations,
    }
    if report.notes:
        result["notes"] = report.notes
    if report.target_project_id:
        result["present_files"] = [
            {
                "name": e.expected_name,
                "figma_id": e.figma_file.id if e.figma_file else None,
                "last_modified": e.figma_file.last_modified if e.figma_file else None,
            }
            for e in report.present
        ]
    return result
