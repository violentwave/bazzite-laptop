"""Unit tests for ai/threat_intel/summary.py.

Covers:
  1. _latest_json: missing dir, empty dir, valid JSON, corrupt JSON
  2. build_summary: reads all dirs, handles missing dirs, valid output structure
  3. Atomic write: file is created, content is valid JSON
  4. _overall_status: escalation logic including CVE KEV/high-severity
"""

import json
import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

_MOD = "ai.threat_intel.summary"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data))
    return path


def _patch_dirs(dirs: dict, summary_dir: Path):
    """Return an ExitStack that patches _REPORT_DIRS and THREAT_SUMMARY_DIR."""
    import ai.threat_intel.summary as mod  # noqa: PLC0415

    stack = ExitStack()
    stack.enter_context(patch.object(mod, "_REPORT_DIRS", dirs))
    stack.enter_context(patch.object(mod, "THREAT_SUMMARY_DIR", summary_dir))
    return stack


def _missing_dirs(tmp_path: Path) -> dict:
    return {k: tmp_path / f"missing-{k}" for k in ("audit", "perf", "storage", "code", "cve")}


# ══════════════════════════════════════════════════════════════════════════════
# 1. _latest_json
# ══════════════════════════════════════════════════════════════════════════════


class TestLatestJson:
    def test_missing_dir_returns_none(self, tmp_path):
        from ai.threat_intel.summary import _latest_json

        assert _latest_json(tmp_path / "does-not-exist") is None

    def test_empty_dir_returns_none(self, tmp_path):
        from ai.threat_intel.summary import _latest_json

        empty = tmp_path / "empty"
        empty.mkdir()
        assert _latest_json(empty) is None

    def test_returns_latest_json(self, tmp_path):
        from ai.threat_intel.summary import _latest_json

        d = tmp_path / "reports"
        d.mkdir()
        old = d / "old.json"
        new = d / "new.json"
        _write_json(old, {"status": "old"})
        _write_json(new, {"status": "new"})
        # Bump mtime of new so it sorts first
        os.utime(new, (new.stat().st_mtime + 10, new.stat().st_mtime + 10))

        result = _latest_json(d)
        assert result == {"status": "new"}

    def test_corrupt_json_returns_none(self, tmp_path):
        from ai.threat_intel.summary import _latest_json

        d = tmp_path / "reports"
        d.mkdir()
        (d / "bad.json").write_text("not valid json {{")
        assert _latest_json(d) is None

    def test_non_json_files_ignored(self, tmp_path):
        from ai.threat_intel.summary import _latest_json

        d = tmp_path / "reports"
        d.mkdir()
        (d / "notes.txt").write_text("ignore me")
        assert _latest_json(d) is None


# ══════════════════════════════════════════════════════════════════════════════
# 2. build_summary: output structure
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildSummary:
    def _make_dirs(self, tmp_path: Path) -> dict:
        dirs = {
            "audit": tmp_path / "audit-reports",
            "perf": tmp_path / "perf-reports",
            "storage": tmp_path / "storage-reports",
            "code": tmp_path / "code-reports",
            "cve": tmp_path / "cve-reports",
        }
        for d in dirs.values():
            d.mkdir()
        return dirs

    def test_all_dirs_present_produces_all_sections(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = self._make_dirs(tmp_path)
        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        _write_json(dirs["audit"] / "a.json", {"status": "clean", "rag_summary": "ok"})
        _write_json(dirs["perf"] / "p.json", {"status": "clean", "recommendations": []})
        _write_json(dirs["storage"] / "s.json", {"status": "clean", "recommendations": []})
        _write_json(dirs["code"] / "c.json", {
            "status": "clean", "ruff_issues": 0, "bandit_issues": 0,
        })
        _write_json(dirs["cve"] / "v.json", {
            "packages_scanned": 100, "total_cves": 0, "high_severity": 0, "kev_cves": 0,
        })

        with _patch_dirs(dirs, summary_dir):
            result = build_summary()

        assert "audit" in result
        assert "perf" in result
        assert "storage" in result
        assert "code" in result
        assert "cve" in result
        assert result["missing_sources"] == []

    def test_missing_dir_listed_in_missing_sources(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = self._make_dirs(tmp_path)
        dirs["cve"] = tmp_path / "nonexistent-cve"  # does not exist

        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        _write_json(dirs["audit"] / "a.json", {"status": "clean", "rag_summary": ""})
        _write_json(dirs["perf"] / "p.json", {"status": "clean", "recommendations": []})
        _write_json(dirs["storage"] / "s.json", {"status": "clean", "recommendations": []})
        _write_json(dirs["code"] / "c.json", {
            "status": "clean", "ruff_issues": 0, "bandit_issues": 0,
        })

        with _patch_dirs(dirs, summary_dir):
            result = build_summary()

        assert "cve" in result["missing_sources"]
        assert "cve" not in result

    def test_all_dirs_missing_produces_valid_result(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = _missing_dirs(tmp_path)
        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        with _patch_dirs(dirs, summary_dir):
            result = build_summary()

        assert result["overall_status"] == "unknown"
        assert set(result["missing_sources"]) == {"audit", "perf", "storage", "code", "cve"}

    def test_required_top_level_keys_present(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = _missing_dirs(tmp_path)
        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        with _patch_dirs(dirs, summary_dir):
            result = build_summary()

        for key in ("generated_at", "date", "overall_status", "missing_sources"):
            assert key in result


# ══════════════════════════════════════════════════════════════════════════════
# 3. Atomic write
# ══════════════════════════════════════════════════════════════════════════════


class TestAtomicWrite:
    def test_file_created_in_threat_summary_dir(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = _missing_dirs(tmp_path)
        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        with _patch_dirs(dirs, summary_dir):
            build_summary()

        files = list(summary_dir.glob("threat-*.json"))
        assert len(files) == 1

    def test_written_file_is_valid_json(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = _missing_dirs(tmp_path)
        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        with _patch_dirs(dirs, summary_dir):
            build_summary()

        written = list(summary_dir.glob("threat-*.json"))[0]
        data = json.loads(written.read_text())
        assert "overall_status" in data

    def test_no_tmp_files_left_behind(self, tmp_path):
        from ai.threat_intel.summary import build_summary

        dirs = _missing_dirs(tmp_path)
        summary_dir = tmp_path / "threat-summary"
        summary_dir.mkdir()

        with _patch_dirs(dirs, summary_dir):
            build_summary()

        assert not list(summary_dir.glob("*.tmp"))


# ══════════════════════════════════════════════════════════════════════════════
# 4. _overall_status escalation
# ══════════════════════════════════════════════════════════════════════════════


class TestOverallStatus:
    def test_all_clean_returns_clean(self):
        from ai.threat_intel.summary import _overall_status

        sections = {
            "audit": {"status": "clean"},
            "cve": {"high_severity": 0, "kev_cves": 0},
        }
        assert _overall_status(sections) == "clean"

    def test_one_issues_escalates(self):
        from ai.threat_intel.summary import _overall_status

        sections = {
            "audit": {"status": "issues"},
            "perf": {"status": "clean"},
        }
        assert _overall_status(sections) == "issues"

    def test_kev_cves_escalates_to_critical(self):
        from ai.threat_intel.summary import _overall_status

        sections = {
            "audit": {"status": "clean"},
            "cve": {"high_severity": 2, "kev_cves": 1},
        }
        assert _overall_status(sections) == "critical"

    def test_high_severity_cve_escalates_to_issues(self):
        from ai.threat_intel.summary import _overall_status

        sections = {
            "audit": {"status": "clean"},
            "cve": {"high_severity": 3, "kev_cves": 0},
        }
        assert _overall_status(sections) == "issues"

    def test_no_sections_returns_unknown(self):
        from ai.threat_intel.summary import _overall_status

        assert _overall_status({}) == "unknown"

    def test_warnings_beats_clean(self):
        from ai.threat_intel.summary import _overall_status

        sections = {
            "perf": {"status": "warnings"},
            "audit": {"status": "clean"},
        }
        assert _overall_status(sections) == "warnings"
