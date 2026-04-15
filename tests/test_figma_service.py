"""Tests for figma_service module — P96 Figma reconciliation."""

from unittest.mock import patch

from ai.figma_service import (
    MIDNIGHT_GLASS_EXPECTED_ARTIFACTS,
    _is_error,
    find_bazzite_project,
    list_project_files,
    list_projects,
    list_teams,
    reconcile_design_lab,
)


class TestIsError:
    def test_error_dict(self):
        assert _is_error({"error": "something"}) is True

    def test_success_dict(self):
        assert _is_error({"status": "ok"}) is False

    def test_list(self):
        assert _is_error([1, 2, 3]) is False

    def test_none(self):
        assert _is_error(None) is False


class TestListTeams:
    def test_missing_pat(self):
        with patch("ai.figma_service._get_pat", return_value=None):
            result = list_teams()
            assert len(result) == 1
            assert result[0]["error"] == "figma_pat_missing"

    def test_invalid_pat(self):
        with patch("ai.figma_service._get_pat", return_value="bad_token"):
            with patch(
                "ai.figma_service._figma_request",
                return_value={
                    "error": "authentication_failed",
                    "error_detail": "Invalid or expired Figma PAT",
                    "status_code": 401,
                },
            ):
                result = list_teams()
                assert len(result) == 1
                assert result[0]["error"] == "authentication_failed"

    def test_successful_teams(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service._figma_request",
                return_value={
                    "teams": [
                        {"id": "team1", "name": "My Team"},
                        {"id": "team2", "name": "Other Team"},
                    ],
                },
            ):
                result = list_teams()
                assert len(result) == 2
                assert result[0]["name"] == "My Team"
                assert result[1]["name"] == "Other Team"


class TestListProjects:
    def test_missing_pat(self):
        with patch("ai.figma_service._get_pat", return_value=None):
            result = list_projects("team1")
            assert result[0]["error"] == "figma_pat_missing"

    def test_successful_projects(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service._figma_request",
                return_value={
                    "projects": [
                        {"id": "proj1", "name": "Bazzite"},
                        {"id": "proj2", "name": "Other"},
                    ],
                },
            ):
                result = list_projects("team1")
                assert len(result) == 2
                assert result[0]["name"] == "Bazzite"


class TestListProjectFiles:
    def test_missing_pat(self):
        with patch("ai.figma_service._get_pat", return_value=None):
            result = list_project_files("proj1")
            assert result[0]["error"] == "figma_pat_missing"

    def test_successful_files(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service._figma_request",
                return_value={
                    "files": [
                        {"id": "f1", "name": "Design System", "key": "abc123"},
                        {"id": "f2", "name": "Components", "key": "def456"},
                    ],
                },
            ):
                result = list_project_files("proj1")
                assert len(result) == 2
                assert result[0]["name"] == "Design System"


class TestFindBazziteProject:
    def test_finds_matching_project(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service.list_teams",
                return_value=[
                    {"id": "team1", "name": "My Team"},
                ],
            ):
                with patch(
                    "ai.figma_service.list_projects",
                    return_value=[
                        {"id": "proj1", "name": "Bazzite"},
                        {"id": "proj2", "name": "Other"},
                    ],
                ):
                    result = find_bazzite_project(pat="good_token")
                    assert result["found"] is True
                    assert result["project_name"] == "Bazzite"
                    assert result["project_id"] == "proj1"

    def test_project_not_found(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service.list_teams",
                return_value=[
                    {"id": "team1", "name": "My Team"},
                ],
            ):
                with patch(
                    "ai.figma_service.list_projects",
                    return_value=[
                        {"id": "proj1", "name": "Other Project"},
                    ],
                ):
                    result = find_bazzite_project(pat="good_token")
                    assert result["found"] is False
                    assert result["error"] == "project_not_found"

    def test_no_teams(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch("ai.figma_service.list_teams", return_value=[]):
                result = find_bazzite_project(pat="good_token")
                assert result.get("error") == "no_teams"

    def test_custom_project_name(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service.list_teams",
                return_value=[
                    {"id": "team1", "name": "Team"},
                ],
            ):
                with patch(
                    "ai.figma_service.list_projects",
                    return_value=[
                        {"id": "proj1", "name": "Custom Design"},
                    ],
                ):
                    result = find_bazzite_project(project_name="Custom Design", pat="good_token")
                    assert result["found"] is True
                    assert result["project_name"] == "Custom Design"


class TestReconcile:
    def test_full_reconciliation(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service.find_bazzite_project",
                return_value={
                    "found": True,
                    "team_id": "team1",
                    "project_id": "proj1",
                    "project_name": "Bazzite",
                },
            ):
                with patch(
                    "ai.figma_service.list_project_files",
                    return_value=[
                        {"id": "f1", "name": "Midnight Glass - Color Tokens", "key": "k1"},
                        {"id": "f2", "name": "Midnight Glass - Components", "key": "k2"},
                        {"id": "f3", "name": "Extra File", "key": "k3"},
                    ],
                ):
                    report = reconcile_design_lab(
                        expected_artifacts=[
                            "Midnight Glass - Color Tokens",
                            "Midnight Glass - Typography",
                            "Midnight Glass - Components",
                        ],
                    )

        assert report.target_project_id == "proj1"
        assert len(report.present) == 2
        assert "Midnight Glass - Typography" in report.missing
        assert "Extra File" in report.unexpected
        assert len(report.api_limitations) > 0

    def test_project_not_found(self):
        with patch("ai.figma_service._get_pat", return_value="good_token"):
            with patch(
                "ai.figma_service.find_bazzite_project",
                return_value={
                    "found": False,
                    "error": "project_not_found",
                },
            ):
                report = reconcile_design_lab(
                    expected_artifacts=["Test"],
                )

        assert report.target_project_id is None
        assert len(report.present) == 0

    def test_default_artifacts_list(self):
        assert len(MIDNIGHT_GLASS_EXPECTED_ARTIFACTS) == 12
        assert any("Color Tokens" in a for a in MIDNIGHT_GLASS_EXPECTED_ARTIFACTS)
        assert any("Components" in a for a in MIDNIGHT_GLASS_EXPECTED_ARTIFACTS)
