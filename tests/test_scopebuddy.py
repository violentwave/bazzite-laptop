"""Unit tests for ai/gaming/scopebuddy.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai.gaming.models import GameProfile, HardwareSnapshot
from ai.gaming.scopebuddy import (
    MANGOHUD_PRESETS,
    _filter_banned,
    _parse_vdf_simple,
    apply_mangohud_preset,
    get_profile,
    save_profile,
    scan_steam_library,
    suggest_launch_options,
)

# ── Sample Data ──

SAMPLE_VDF = '''"libraryfolders"
{
    "0"
    {
        "path"    "/tmp/test-steam"
        "apps"
        {
            "228980"    "291948790"
            "730"       "15789432"
        }
    }
}
'''

SAMPLE_ACF = '''"AppState"
{
    "appid"     "730"
    "name"      "Counter-Strike 2"
    "installdir"        "Counter-Strike Global Offensive"
    "SizeOnDisk"        "15789432"
}
'''

SAMPLE_ACF_2 = '''"AppState"
{
    "appid"     "228980"
    "name"      "Steamworks Common Redistributables"
    "installdir"        "Steamworks Common Redistributables"
    "SizeOnDisk"        "291948790"
}
'''


# ── VDF Parser Tests ──


class TestVDFParser:
    """Tests for the minimal VDF/ACF parser."""

    def test_parse_libraryfolders(self):
        """Verify path and apps extracted from libraryfolders.vdf."""
        result = _parse_vdf_simple(SAMPLE_VDF)
        folders = result["libraryfolders"]
        assert "0" in folders
        assert folders["0"]["path"] == "/tmp/test-steam"
        assert "apps" in folders["0"]
        assert folders["0"]["apps"]["730"] == "15789432"

    def test_parse_nested_keys(self):
        """Verify nested dict structure is preserved."""
        result = _parse_vdf_simple(SAMPLE_ACF)
        assert "AppState" in result
        app = result["AppState"]
        assert app["appid"] == "730"
        assert app["name"] == "Counter-Strike 2"
        assert app["installdir"] == "Counter-Strike Global Offensive"
        assert app["SizeOnDisk"] == "15789432"

    def test_parse_empty_string(self):
        """Empty input returns empty dict."""
        result = _parse_vdf_simple("")
        assert result == {}

    def test_parse_malformed(self):
        """Partial or malformed VDF does not crash."""
        # Just an opening brace, no content
        result = _parse_vdf_simple("{")
        assert isinstance(result, dict)

        # Key without value at end of input
        result = _parse_vdf_simple('"key"')
        assert isinstance(result, dict)

        # Unmatched close brace
        result = _parse_vdf_simple("}")
        assert isinstance(result, dict)


# ── Steam Library Scanner Tests ──


class TestSteamScanner:
    """Tests for scan_steam_library."""

    def test_scan_finds_games(self, tmp_path):
        """Create VDF + ACF in tmp_path, verify game is found."""
        steamapps = tmp_path / "steamapps"
        steamapps.mkdir()
        (steamapps / "appmanifest_730.acf").write_text(SAMPLE_ACF)

        games = scan_steam_library(library_path=tmp_path)
        assert len(games) == 1
        assert games[0]["name"] == "Counter-Strike 2"
        assert games[0]["appid"] == "730"
        assert games[0]["install_dir"] == "Counter-Strike Global Offensive"
        assert games[0]["size_bytes"] == 15789432
        assert games[0]["library_path"] == str(tmp_path)

    def test_scan_no_library_found(self):
        """No VDF files found returns empty list."""
        with patch("ai.gaming.scopebuddy._VDF_PATHS", [Path("/nonexistent/path.vdf")]):
            games = scan_steam_library()
            assert games == []

    def test_scan_skips_bad_acf(self, tmp_path):
        """Corrupt ACF is skipped; valid ones still found."""
        steamapps = tmp_path / "steamapps"
        steamapps.mkdir()
        (steamapps / "appmanifest_999.acf").write_text("CORRUPT DATA {{{{")
        (steamapps / "appmanifest_730.acf").write_text(SAMPLE_ACF)

        games = scan_steam_library(library_path=tmp_path)
        assert len(games) == 1
        assert games[0]["appid"] == "730"

    def test_scan_explicit_path(self, tmp_path):
        """library_path override works and ignores _VDF_PATHS."""
        steamapps = tmp_path / "steamapps"
        steamapps.mkdir()
        (steamapps / "appmanifest_730.acf").write_text(SAMPLE_ACF)
        (steamapps / "appmanifest_228980.acf").write_text(SAMPLE_ACF_2)

        games = scan_steam_library(library_path=tmp_path)
        assert len(games) == 2
        # Sorted by name
        assert games[0]["name"] == "Counter-Strike 2"
        assert games[1]["name"] == "Steamworks Common Redistributables"

    def test_scan_discovers_from_vdf(self, tmp_path):
        """When no library_path given, discovers from libraryfolders.vdf."""
        # Set up the steam library structure
        steamapps = tmp_path / "steamapps"
        steamapps.mkdir()
        (steamapps / "appmanifest_730.acf").write_text(SAMPLE_ACF)

        # Create a VDF pointing to tmp_path
        vdf_content = f'"libraryfolders"\n{{\n    "0"\n    {{\n        "path"    "{tmp_path}"\n        "apps"\n        {{\n            "730"    "15789432"\n        }}\n    }}\n}}\n'
        vdf_file = tmp_path / "libraryfolders.vdf"
        vdf_file.write_text(vdf_content)

        with patch("ai.gaming.scopebuddy._VDF_PATHS", [vdf_file]):
            games = scan_steam_library()
            assert len(games) == 1
            assert games[0]["name"] == "Counter-Strike 2"


# ── Game Profile Tests ──


class TestGameProfiles:
    """Tests for get_profile and save_profile."""

    def test_get_profile_exists(self, tmp_path):
        """Write JSON to tmp_path, patch PROFILES_PATH, verify retrieval."""
        profiles_file = tmp_path / "game-profiles.json"
        data = {
            "cyberpunk 2077": {
                "name": "Cyberpunk 2077",
                "appid": 1091500,
                "launch_options": "gamemoderun mangohud %command%",
                "mangohud_preset": "full",
                "gamemode": True,
                "notes": "runs well",
                "last_analyzed": "",
                "ai_suggestions": [],
            }
        }
        profiles_file.write_text(json.dumps(data))

        with patch("ai.gaming.scopebuddy.PROFILES_PATH", profiles_file):
            profile = get_profile("Cyberpunk 2077")
            assert profile is not None
            assert profile.name == "Cyberpunk 2077"
            assert profile.appid == 1091500
            assert profile.mangohud_preset == "full"

    def test_get_profile_missing(self, tmp_path):
        """No match returns None."""
        profiles_file = tmp_path / "game-profiles.json"
        profiles_file.write_text("{}")

        with patch("ai.gaming.scopebuddy.PROFILES_PATH", profiles_file):
            profile = get_profile("Nonexistent Game")
            assert profile is None

    def test_get_profile_case_insensitive(self, tmp_path):
        """'cyberpunk 2077' matches 'Cyberpunk 2077'."""
        profiles_file = tmp_path / "game-profiles.json"
        data = {
            "cyberpunk 2077": {
                "name": "Cyberpunk 2077",
                "appid": 1091500,
                "launch_options": "",
                "mangohud_preset": "default",
                "gamemode": True,
                "notes": "",
                "last_analyzed": "",
                "ai_suggestions": [],
            }
        }
        profiles_file.write_text(json.dumps(data))

        with patch("ai.gaming.scopebuddy.PROFILES_PATH", profiles_file):
            profile = get_profile("cyberpunk 2077")
            assert profile is not None
            assert profile.name == "Cyberpunk 2077"

    def test_save_profile_creates_file(self, tmp_path):
        """Profile save creates JSON file from scratch."""
        profiles_file = tmp_path / "profiles" / "game-profiles.json"

        with patch("ai.gaming.scopebuddy.PROFILES_PATH", profiles_file):
            profile = GameProfile(name="Half-Life 2", appid=220)
            save_profile(profile)

            assert profiles_file.exists()
            data = json.loads(profiles_file.read_text())
            assert "half-life 2" in data
            assert data["half-life 2"]["name"] == "Half-Life 2"

    def test_save_profile_updates_existing(self, tmp_path):
        """Updating an existing profile preserves other entries."""
        profiles_file = tmp_path / "game-profiles.json"
        initial = {
            "game a": {
                "name": "Game A",
                "appid": 100,
                "launch_options": "",
                "mangohud_preset": "default",
                "gamemode": True,
                "notes": "",
                "last_analyzed": "",
                "ai_suggestions": [],
            },
            "game b": {
                "name": "Game B",
                "appid": 200,
                "launch_options": "",
                "mangohud_preset": "default",
                "gamemode": True,
                "notes": "",
                "last_analyzed": "",
                "ai_suggestions": [],
            },
        }
        profiles_file.write_text(json.dumps(initial))

        with patch("ai.gaming.scopebuddy.PROFILES_PATH", profiles_file):
            updated = GameProfile(name="Game A", appid=100, launch_options="mangohud %command%")
            save_profile(updated)

            data = json.loads(profiles_file.read_text())
            assert data["game a"]["launch_options"] == "mangohud %command%"
            assert "game b" in data  # Other entry preserved

    def test_get_profile_file_missing(self, tmp_path):
        """Missing profiles file returns None gracefully."""
        profiles_file = tmp_path / "does-not-exist.json"

        with patch("ai.gaming.scopebuddy.PROFILES_PATH", profiles_file):
            profile = get_profile("anything")
            assert profile is None


# ── Suggest Launch Options Tests ──


class TestSuggestLaunchOptions:
    """Tests for suggest_launch_options."""

    @patch("ai.gaming.scopebuddy.route_query")
    def test_llm_suggestion(self, mock_route):
        """LLM response is used as launch options."""
        mock_route.return_value = "gamemoderun mangohud %command%"
        profile = suggest_launch_options("Counter-Strike 2")

        assert profile.name == "Counter-Strike 2"
        assert profile.launch_options == "gamemoderun mangohud %command%"
        mock_route.assert_called_once()
        assert mock_route.call_args[0][0] == "fast"

    def test_rate_limited_safe_default(self):
        """Rate-limited request returns safe default."""
        limiter = MagicMock()
        limiter.can_call.return_value = False

        profile = suggest_launch_options("Counter-Strike 2", rate_limiter=limiter)

        assert profile.launch_options == "gamemoderun mangohud %command%"
        limiter.can_call.assert_called_once_with("litellm")

    @patch("ai.gaming.scopebuddy.route_query")
    def test_prime_offload_filtered(self, mock_route):
        """Response containing banned PRIME vars gets those lines filtered out."""
        mock_route.return_value = (
            "__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia "
            "gamemoderun mangohud %command%\n"
            "gamemoderun mangohud %command%"
        )

        profile = suggest_launch_options("Test Game")

        # The line with banned patterns should be removed
        assert "__NV_PRIME_RENDER_OFFLOAD" not in profile.launch_options
        assert "__GLX_VENDOR_LIBRARY_NAME" not in profile.launch_options
        assert "gamemoderun mangohud %command%" in profile.launch_options

    @patch("ai.gaming.scopebuddy.route_query")
    def test_scaffold_response_returns_default(self, mock_route):
        """[SCAFFOLD] response falls back to safe default."""
        mock_route.return_value = "[SCAFFOLD] Would route 'fast' query to LiteLLM."

        profile = suggest_launch_options("Test Game")

        assert profile.launch_options == "gamemoderun mangohud %command%"

    @patch("ai.gaming.scopebuddy.route_query")
    def test_router_exception_returns_default(self, mock_route):
        """RuntimeError from router returns safe default."""
        mock_route.side_effect = RuntimeError("provider down")

        profile = suggest_launch_options("Test Game")

        assert profile.launch_options == "gamemoderun mangohud %command%"

    @patch("ai.gaming.scopebuddy.route_query")
    def test_all_banned_lines_yields_default(self, mock_route):
        """If every line is banned, fall back to safe default."""
        mock_route.return_value = (
            "__NV_PRIME_RENDER_OFFLOAD=1 %command%\n"
            "DRI_PRIME=1 %command%"
        )

        profile = suggest_launch_options("Test Game")

        assert profile.launch_options == "gamemoderun mangohud %command%"

    @patch("ai.gaming.scopebuddy.route_query")
    def test_hardware_context_included(self, mock_route):
        """Hardware snapshot is included in the prompt."""
        mock_route.return_value = "gamemoderun %command%"
        hw = HardwareSnapshot(
            gpu_name="GTX 1060",
            gpu_vram_total_mb=6144,
            cpu_model="i7-7700HQ",
            cpu_cores=4,
            ram_total_mb=16384,
            gpu_driver="535.183",
        )

        suggest_launch_options("Test Game", hardware=hw)

        prompt = mock_route.call_args[0][1]
        assert "GTX 1060" in prompt
        assert "6144" in prompt
        assert "i7-7700HQ" in prompt
        assert "535.183" in prompt

    @patch("ai.gaming.scopebuddy.route_query")
    def test_rate_limiter_records_call(self, mock_route):
        """Successful LLM call records usage with rate limiter."""
        mock_route.return_value = "gamemoderun %command%"
        limiter = MagicMock()
        limiter.can_call.return_value = True

        suggest_launch_options("Test Game", rate_limiter=limiter)

        limiter.record_call.assert_called_once_with("litellm")


# ── MangoHud Preset Tests ──


class TestMangoHudPresets:
    """Tests for apply_mangohud_preset."""

    def test_apply_default_preset(self, tmp_path):
        """Default preset writes expected keys to config."""
        config = tmp_path / "MangoHud.conf"

        result = apply_mangohud_preset("default", config_path=config)

        assert result == config
        content = config.read_text()
        assert "fps_limit=0" in content
        assert "gpu_stats" in content
        assert "cpu_stats" in content
        assert "frame_timing=1" in content

    def test_apply_full_preset(self, tmp_path):
        """Full preset has gpu_temp, cpu_temp, etc."""
        config = tmp_path / "MangoHud.conf"

        apply_mangohud_preset("full", config_path=config)

        content = config.read_text()
        assert "gpu_temp" in content
        assert "cpu_temp" in content
        assert "gpu_power" in content
        assert "cpu_power" in content
        assert "engine_version" in content
        assert "vulkan_driver" in content

    def test_apply_fps_only_preset(self, tmp_path):
        """fps_only preset has fps_only key and position."""
        config = tmp_path / "MangoHud.conf"

        apply_mangohud_preset("fps_only", config_path=config)

        content = config.read_text()
        assert "fps_only" in content
        assert "position=top-right" in content
        assert "font_size=24" in content

    def test_invalid_preset_raises(self, tmp_path):
        """Unknown preset name raises ValueError."""
        config = tmp_path / "MangoHud.conf"

        with pytest.raises(ValueError, match="Unknown preset"):
            apply_mangohud_preset("nonexistent", config_path=config)

    def test_config_file_created(self, tmp_path):
        """Config file exists after applying preset."""
        config = tmp_path / "subdir" / "MangoHud.conf"

        apply_mangohud_preset("minimal", config_path=config)

        assert config.exists()
        content = config.read_text()
        assert "fps_only" in content
        assert "no_display" in content

    def test_preset_overwrites_existing(self, tmp_path):
        """Applying a new preset replaces the old config completely."""
        config = tmp_path / "MangoHud.conf"
        config.write_text("old_content=yes\n")

        apply_mangohud_preset("fps_only", config_path=config)

        content = config.read_text()
        assert "old_content" not in content
        assert "fps_only" in content

    def test_preset_header_comment(self, tmp_path):
        """Config file includes preset name and generator in comments."""
        config = tmp_path / "MangoHud.conf"

        apply_mangohud_preset("default", config_path=config)

        content = config.read_text()
        assert "# MangoHud preset: default" in content
        assert "# Generated by bazzite-ai" in content


# ── Filter Banned Tests ──


class TestFilterBanned:
    """Tests for _filter_banned helper."""

    def test_removes_prime_offload(self):
        """Lines with PRIME offload vars are removed."""
        text = "__NV_PRIME_RENDER_OFFLOAD=1 %command%\ngamemoderun %command%"
        result = _filter_banned(text)
        assert "__NV_PRIME_RENDER_OFFLOAD" not in result
        assert "gamemoderun %command%" in result

    def test_removes_dri_prime(self):
        """DRI_PRIME lines are removed."""
        text = "DRI_PRIME=1 gamemoderun %command%"
        result = _filter_banned(text)
        assert result == ""

    def test_clean_text_unchanged(self):
        """Text without banned patterns passes through unchanged."""
        text = "gamemoderun mangohud %command%"
        result = _filter_banned(text)
        assert result == text

    def test_empty_input(self):
        """Empty string returns empty string."""
        assert _filter_banned("") == ""
