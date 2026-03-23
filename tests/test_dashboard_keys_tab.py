"""Tests for the Keys tab in tray/dashboard_window.py.

Pure-logic tests (TestLoadKeyStatus) require no Qt.
Widget tests (TestKeysTabWidget) use the session-scoped qapp fixture from conftest.py.
"""

import json
from unittest.mock import patch

from tray.keys_tab import LLM_GROUP, THREAT_GROUP, load_key_status

# ---------------------------------------------------------------------------
# 1. Pure-logic: load_key_status()
# ---------------------------------------------------------------------------


class TestLoadKeyStatus:
    def test_returns_none_for_missing_file(self, tmp_path):
        result = load_key_status(tmp_path / "nonexistent.json")
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        assert load_key_status(bad) is None

    def test_parses_valid_key_status(self, tmp_path):
        payload = {
            "keys": {"GEMINI_API_KEY": "set", "GROQ_API_KEY": "missing"},
            "summary": {
                "all_llm_keys_present": False,
                "all_phase1_threat_keys_present": False,
                "all_phase6_threat_keys_present": False,
                "missing_keys": ["GROQ_API_KEY"],
            },
        }
        f = tmp_path / "key-status.json"
        f.write_text(json.dumps(payload), encoding="utf-8")

        result = load_key_status(f)
        assert result is not None
        assert result["keys"]["GEMINI_API_KEY"] == "set"
        assert result["keys"]["GROQ_API_KEY"] == "missing"
        assert result["summary"]["missing_keys"] == ["GROQ_API_KEY"]

    def test_key_group_constants_cover_expected_keys(self):
        assert "GEMINI_API_KEY" in LLM_GROUP
        assert "GROQ_API_KEY" in LLM_GROUP
        assert len(LLM_GROUP) == 12
        assert "VT_API_KEY" in THREAT_GROUP
        assert "NVD_API_KEY" in THREAT_GROUP
        assert len(THREAT_GROUP) == 6


# ---------------------------------------------------------------------------
# 2. Widget tests — require headless QApplication (qapp fixture)
# ---------------------------------------------------------------------------


class TestKeysTabWidget:
    def test_dashboard_has_four_tabs(self, qapp):
        """DashboardWindow must expose Security, Health, Keys, About tabs."""
        from tray.dashboard_window import DashboardWindow

        w = DashboardWindow()
        tabs = w.centralWidget()
        assert tabs.count() == 4
        labels = [tabs.tabText(i).strip() for i in range(tabs.count())]
        assert "Keys" in labels
        assert labels.index("Keys") < labels.index("About")
        w.deleteLater()

    def test_keys_tab_creates_without_error(self, qapp):
        """_build_keys() must return a widget and refs dict without raising."""
        from tray.dashboard_window import DashboardWindow

        w = DashboardWindow()
        assert w._keys_tab is not None
        assert isinstance(w._keys_refs, dict)
        assert "summary" in w._keys_refs
        assert "placeholder" in w._keys_refs
        assert "key_cards_row" in w._keys_refs
        w.deleteLater()

    def test_keys_tab_has_ref_for_every_known_key(self, qapp):
        """_build_keys() must create a label ref for every key in both groups."""
        from tray.dashboard_window import DashboardWindow

        w = DashboardWindow()
        refs = w._keys_refs
        for k in LLM_GROUP + THREAT_GROUP:
            assert f"key_{k}" in refs, f"Missing ref for key: {k}"
        w.deleteLater()

    def test_update_keys_shows_placeholder_when_no_file(self, qapp):
        """When key-status.json is absent, placeholder must be visible and cards hidden."""
        from tray.dashboard_window import DashboardWindow

        with patch("tray.dashboard_window.load_key_status", return_value=None):
            w = DashboardWindow()
            w._update_keys()
            assert not w._keys_refs["placeholder"].isHidden()
            assert w._keys_refs["key_cards_row"].isHidden()
            assert w._keys_refs["summary"].text() == "Run key status check"
        w.deleteLater()

    def test_update_keys_shows_summary_count(self, qapp):
        """_update_keys() must show correct set/total count derived from known groups."""
        from tray.dashboard_window import DashboardWindow

        all_keys = LLM_GROUP + THREAT_GROUP
        expected = f"{len(all_keys)}/{len(all_keys)}"
        status_data = {
            "keys": {k: "set" for k in all_keys},
            "summary": {"missing_keys": []},
        }
        with patch("tray.dashboard_window.load_key_status", return_value=status_data):
            w = DashboardWindow()
            w._update_keys()
            assert expected in w._keys_refs["summary"].text()
            assert w._keys_refs["placeholder"].isHidden() is True
        w.deleteLater()

    def test_update_keys_missing_key_label_contains_warning(self, qapp):
        """A key with status 'missing' must show ⚠ and a set key must show ✅."""
        from tray.dashboard_window import DashboardWindow

        status_data = {
            "keys": {"GEMINI_API_KEY": "set", "GROQ_API_KEY": "missing"},
            "summary": {"missing_keys": ["GROQ_API_KEY"]},
        }
        with patch("tray.dashboard_window.load_key_status", return_value=status_data):
            w = DashboardWindow()
            w._update_keys()
            assert "⚠" in w._keys_refs["key_GROQ_API_KEY"].text()
            assert "✅" in w._keys_refs["key_GEMINI_API_KEY"].text()
        w.deleteLater()

    def test_update_keys_hides_cards_then_restores_on_data(self, qapp):
        """Transitioning from no-data to data-present must restore key_cards_row."""
        from tray.dashboard_window import DashboardWindow

        all_keys = LLM_GROUP + THREAT_GROUP
        status_data = {"keys": {k: "set" for k in all_keys}, "summary": {}}
        w = DashboardWindow()
        with patch("tray.dashboard_window.load_key_status", return_value=None):
            w._update_keys()
            assert w._keys_refs["key_cards_row"].isHidden()
        with patch("tray.dashboard_window.load_key_status", return_value=status_data):
            w._update_keys()
            assert not w._keys_refs["key_cards_row"].isHidden()
        w.deleteLater()
