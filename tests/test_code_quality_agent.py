"""Unit tests for ai/agents/code_quality_agent.py."""

import json
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

_CQ = "ai.agents.code_quality_agent"


class TestRunRuff:
    def test_clean_output(self):
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]")
            from ai.agents.code_quality_agent import _run_ruff

            result = _run_ruff()
        assert result["clean"] is True
        assert result["total_errors"] == 0
        assert result["error"] is None

    def test_with_errors(self):
        issues = [
            {"code": "E402", "message": "module level import"},
            {"code": "E402", "message": "module level import 2"},
            {"code": "I001", "message": "import block"},
        ]
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout=json.dumps(issues)
            )
            from ai.agents.code_quality_agent import _run_ruff

            result = _run_ruff()
        assert result["clean"] is False
        assert result["total_errors"] == 3
        assert result["by_rule"]["E402"] == 2
        assert result["by_rule"]["I001"] == 1

    def test_timeout_returns_error(self):
        import subprocess

        with patch(f"{_CQ}.subprocess.run", side_effect=subprocess.TimeoutExpired("ruff", 60)):
            from ai.agents.code_quality_agent import _run_ruff

            result = _run_ruff()
        assert result["error"] == "timeout"


class TestRunBandit:
    def test_clean_output(self):
        data = {"results": []}
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data))
            from ai.agents.code_quality_agent import _run_bandit

            result = _run_bandit()
        assert result["clean"] is True
        assert result["total_issues"] == 0

    def test_low_only_is_clean(self):
        data = {"results": [{"issue_severity": "LOW"}]}
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout=json.dumps(data))
            from ai.agents.code_quality_agent import _run_bandit

            result = _run_bandit()
        assert result["clean"] is True
        assert result["low"] == 1
        assert result["high"] == 0

    def test_high_severity_not_clean(self):
        data = {"results": [{"issue_severity": "HIGH"}]}
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout=json.dumps(data))
            from ai.agents.code_quality_agent import _run_bandit

            result = _run_bandit()
        assert result["clean"] is False
        assert result["high"] == 1


class TestRunGitStatus:
    def test_clean_repo(self):
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            from ai.agents.code_quality_agent import _run_git_status

            result = _run_git_status()
        assert result["dirty"] is False
        assert result["modified"] == 0
        assert result["untracked"] == 0

    def test_dirty_repo(self):
        porcelain = " M ai/agents/foo.py\n?? scripts/bar.sh\n M tests/test_foo.py\n"
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=porcelain)
            from ai.agents.code_quality_agent import _run_git_status

            result = _run_git_status()
        assert result["dirty"] is True
        assert result["modified"] == 2
        assert result["untracked"] == 1

    def test_git_failure_returns_clean(self):
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="")
            from ai.agents.code_quality_agent import _run_git_status

            result = _run_git_status()
        assert result["dirty"] is False


class TestRunPytestCollect:
    def test_parses_collected_count(self):
        output = "tests/test_foo.py::test_a\ntests/test_foo.py::test_b\n2 tests collected in 0.5s\n"
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            from ai.agents.code_quality_agent import _run_pytest_collect

            result = _run_pytest_collect()
        assert result["collected"] == 2
        assert result["count_known"] is True

    def test_failure_returns_zero(self):
        with patch(f"{_CQ}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="error output\n")
            from ai.agents.code_quality_agent import _run_pytest_collect

            result = _run_pytest_collect()
        assert result["count_known"] is False


class TestBuildRecommendations:
    def _call(self, **kwargs):
        defaults = {
            "ruff": {"total_errors": 0, "by_rule": {}, "clean": True, "error": None},
            "bandit": {"total_issues": 0, "high": 0, "medium": 0, "low": 0, "clean": True},
            "git": {"untracked": 0, "modified": 0, "staged": 0, "dirty": False, "error": None},
            "tests": {"collected": 594, "count_known": True},
        }
        defaults.update(kwargs)
        from ai.agents.code_quality_agent import _build_recommendations

        return _build_recommendations(**defaults)

    def test_all_clean_returns_clean(self):
        recs, status = self._call()
        assert status == "clean"
        assert any("excellent" in r.lower() for r in recs)

    def test_ruff_errors_returns_warnings(self):
        recs, status = self._call(
            ruff={"total_errors": 3, "by_rule": {"E402": 3}, "clean": False, "error": None}
        )
        assert status == "warnings"
        assert any("ruff" in r.lower() for r in recs)

    def test_bandit_high_returns_issues(self):
        recs, status = self._call(
            bandit={"total_issues": 1, "high": 1, "medium": 0, "low": 0, "clean": False}
        )
        assert status == "issues"
        assert any("HIGH" in r for r in recs)

    def test_bandit_medium_returns_warnings(self):
        recs, status = self._call(
            bandit={"total_issues": 1, "high": 0, "medium": 1, "low": 0, "clean": False}
        )
        assert status == "warnings"
        assert any("MEDIUM" in r for r in recs)

    def test_many_modified_returns_warnings(self):
        git = {"untracked": 0, "modified": 8, "staged": 0, "dirty": True, "error": None}
        recs, status = self._call(git=git)
        assert status == "warnings"
        assert any("uncommitted" in r.lower() for r in recs)

    def test_many_untracked_returns_warnings(self):
        git = {"untracked": 5, "modified": 0, "staged": 0, "dirty": True, "error": None}
        recs, status = self._call(git=git)
        assert status == "warnings"
        assert any("untracked" in r.lower() for r in recs)


def _run_code_patched(tmp_path):
    """Helper: run run_code_check with all collectors mocked."""
    patches = [
        patch(
            f"{_CQ}._run_ruff",
            return_value={"total_errors": 0, "by_rule": {}, "clean": True, "error": None},
        ),
        patch(
            f"{_CQ}._run_bandit",
            return_value={
                "total_issues": 0, "high": 0, "medium": 0, "low": 0, "clean": True, "error": None
            },
        ),
        patch(
            f"{_CQ}._run_git_status",
            return_value={
                "untracked": 0, "modified": 0, "staged": 0, "dirty": False, "error": None
            },
        ),
        patch(f"{_CQ}._run_git_log", return_value=["abc123 feat: something"]),
        patch(f"{_CQ}._run_pytest_collect", return_value={"collected": 594, "count_known": True}),
        patch(f"{_CQ}.CODE_REPORTS_DIR", tmp_path / "reports"),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from ai.agents.code_quality_agent import run_code_check

        return run_code_check()


class TestRunCodeCheck:
    def test_full_workflow_writes_report(self, tmp_path):
        result = _run_code_patched(tmp_path)

        assert result["status"] in ("clean", "warnings", "issues")
        assert "timestamp" in result
        assert "ruff" in result
        assert "bandit" in result
        assert "git" in result
        assert "tests" in result

        files = list((tmp_path / "reports").glob("code-*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["status"] == result["status"]

    def test_report_keys_complete(self, tmp_path):
        result = _run_code_patched(tmp_path)

        expected_keys = {
            "timestamp", "ruff", "bandit", "git", "tests", "recommendations", "status",
        }
        assert set(result.keys()) == expected_keys

    def test_clean_when_all_nominal(self, tmp_path):
        result = _run_code_patched(tmp_path)
        assert result["status"] == "clean"

    def test_git_includes_last_commits(self, tmp_path):
        result = _run_code_patched(tmp_path)
        assert "last_commits" in result["git"]
        assert len(result["git"]["last_commits"]) == 1
