"""Steam library scanner, game profile manager, and MangoHud preset writer.

ScopeBuddy discovers installed Steam games, manages per-game configuration
profiles, generates AI-suggested launch options (with safety filtering),
and writes MangoHud preset configurations.

Usage:
    from ai.gaming.scopebuddy import scan_steam_library, suggest_launch_options
    games = scan_steam_library()
    profile = suggest_launch_options("Counter-Strike 2")
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ai.config import APP_NAME
from ai.gaming.models import GameProfile, HardwareSnapshot

if TYPE_CHECKING:
    from ai.rate_limiter import RateLimiter

logger = logging.getLogger(APP_NAME)

# ── Path Constants ──

PROFILES_PATH = Path.home() / ".config" / "bazzite-ai" / "game-profiles.json"

_VDF_PATHS = [
    Path.home() / ".steam" / "steam" / "libraryfolders.vdf",
    Path.home() / ".local" / "share" / "Steam" / "libraryfolders.vdf",
]

MANGOHUD_CONFIG_PATH = Path.home() / ".config" / "MangoHud" / "MangoHud.conf"

# ── MangoHud Presets ──

MANGOHUD_PRESETS: dict[str, dict[str, str]] = {
    "default": {
        "fps_limit": "0",
        "gpu_stats": "",
        "cpu_stats": "",
        "ram": "",
        "vram": "",
        "frametime": "",
        "frame_timing": "1",
    },
    "minimal": {
        "fps_limit": "0",
        "fps_only": "",
        "no_display": "",
        "output_folder": "~/.local/share/MangoHud",
        "log_duration": "0",
    },
    "full": {
        "fps_limit": "0",
        "gpu_stats": "",
        "gpu_temp": "",
        "gpu_power": "",
        "gpu_mem_clock": "",
        "cpu_stats": "",
        "cpu_temp": "",
        "cpu_power": "",
        "ram": "",
        "vram": "",
        "frametime": "",
        "frame_timing": "1",
        "engine_version": "",
        "vulkan_driver": "",
        "wine": "",
    },
    "fps_only": {
        "fps_only": "",
        "position": "top-right",
        "font_size": "24",
    },
}

# ── Safety: banned launch-option patterns ──
# NEVER use PRIME offload env vars -- they crash games on this hardware.

_BANNED_PATTERNS = [
    "__NV_PRIME_RENDER_OFFLOAD",
    "__GLX_VENDOR_LIBRARY_NAME",
    "__VK_LAYER_NV_optimus",
    "prime-run",
    "DRI_PRIME",
]

_SAFE_DEFAULT = "gamemoderun mangohud %command%"


# ── VDF / ACF Parser ──


def _parse_vdf_simple(text: str) -> dict:
    """Minimal VDF parser for libraryfolders.vdf and appmanifest ACF files.

    Handles nested brace blocks and quoted key-value pairs.
    Uses a stack-based state machine approach.

    Args:
        text: Raw VDF/ACF file content.

    Returns:
        Nested dict representing the VDF structure.
    """
    root: dict = {}
    stack: list[dict] = [root]
    # Match quoted strings (with content), or braces — no capture group
    raw_tokens = re.findall(r'"[^"]*"|\{|\}', text)
    # Strip quotes from quoted tokens, leave braces as-is
    tokens = [t[1:-1] if t.startswith('"') else t for t in raw_tokens]

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "{":  # noqa: S105
            i += 1
            continue
        if token == "}":  # noqa: S105
            if len(stack) > 1:
                stack.pop()
            i += 1
            continue

        # We have a key string
        key = token
        i += 1
        if i >= len(tokens):
            break

        next_token = tokens[i]
        if next_token == "{":  # noqa: S105
            # Key opens a new block
            new_block: dict = {}
            stack[-1][key] = new_block
            stack.append(new_block)
            i += 1
        elif next_token == "}":  # noqa: S105
            # Stray key before close brace — ignore gracefully
            continue
        else:
            # Key-value pair
            stack[-1][key] = next_token
            i += 1

    return root


# ── Steam Library Scanner ──


def scan_steam_library(library_path: Path | None = None) -> list[dict]:
    """Find all installed Steam games across all library folders.

    If library_path is given, scan only that folder. Otherwise discover
    library folders from libraryfolders.vdf.

    Returns:
        Sorted list of dicts with keys:
        name, appid, install_dir, size_bytes, library_path
    """
    library_dirs: list[Path] = []

    if library_path is not None:
        library_dirs.append(library_path)
    else:
        for vdf_path in _VDF_PATHS:
            if vdf_path.exists():
                try:
                    vdf_data = _parse_vdf_simple(vdf_path.read_text())
                except (OSError, UnicodeDecodeError) as e:
                    logger.warning("Could not read %s: %s", vdf_path, e)
                    continue

                folders = vdf_data.get("libraryfolders", {})
                for _idx, folder_info in folders.items():
                    if isinstance(folder_info, dict) and "path" in folder_info:
                        library_dirs.append(Path(folder_info["path"]))
                break  # Use first found VDF

    games: list[dict] = []
    for lib_dir in library_dirs:
        steamapps = lib_dir / "steamapps"
        if not steamapps.is_dir():
            continue

        for acf_file in steamapps.glob("appmanifest_*.acf"):
            try:
                acf_text = acf_file.read_text()
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Skipping bad ACF %s: %s", acf_file, e)
                continue

            try:
                acf_data = _parse_vdf_simple(acf_text)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to parse ACF %s", acf_file)
                continue

            app_state = acf_data.get("AppState", {})
            name = app_state.get("name", "")
            appid = app_state.get("appid", "")
            if not name or not appid:
                continue

            games.append({
                "name": name,
                "appid": appid,
                "install_dir": app_state.get("installdir", ""),
                "size_bytes": int(app_state.get("SizeOnDisk", "0") or "0"),
                "library_path": str(lib_dir),
            })

    games.sort(key=lambda g: g["name"])
    return games


# ── Game Profile Management ──


def _load_profiles() -> dict[str, GameProfile]:
    """Load game profiles from PROFILES_PATH.

    Returns:
        Dict mapping lowercase game name to GameProfile.
        Empty dict if file is missing or corrupt.
    """
    if not PROFILES_PATH.exists():
        return {}
    try:
        raw = json.loads(PROFILES_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load game profiles: %s", e)
        return {}

    profiles: dict[str, GameProfile] = {}
    for key, data in raw.items():
        profiles[key.lower()] = GameProfile.from_dict(data)
    return profiles


def _save_profiles(profiles: dict[str, GameProfile]) -> None:
    """Atomic write: tmp + os.replace to PROFILES_PATH."""
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {key: profile.to_dict() for key, profile in profiles.items()}
    fd, tmp_path = tempfile.mkstemp(
        dir=str(PROFILES_PATH.parent),
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, PROFILES_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def list_profiles() -> dict:
    """Return all saved game profiles as a serializable dict.

    Returns:
        Dict mapping game name to profile dict, or a message if none configured.
    """
    profiles = _load_profiles()
    if not profiles:
        return {"message": "Gaming profiles not yet configured"}
    return {k: v.to_dict() for k, v in profiles.items()}


def get_preset(game: str) -> dict:
    """Get MangoHud preset settings for a game based on its profile.

    Args:
        game: Game name to look up.

    Returns:
        Dict with preset name and settings, or a helpful message if not configured.
    """
    profile = get_profile(game)
    if profile is None:
        return {
            "message": f"No profile configured for '{game}'",
            "available_presets": list(MANGOHUD_PRESETS.keys()),
        }
    preset_name = profile.mangohud_preset or "default"
    if preset_name not in MANGOHUD_PRESETS:
        preset_name = "default"
    return {
        "game": game,
        "preset": preset_name,
        "settings": MANGOHUD_PRESETS[preset_name],
    }


def get_profile(game_name: str) -> GameProfile | None:
    """Get a game profile by name (case-insensitive).

    Args:
        game_name: The game name to look up.

    Returns:
        The GameProfile if found, otherwise None.
    """
    profiles = _load_profiles()
    return profiles.get(game_name.lower())


def save_profile(profile: GameProfile) -> None:
    """Save or update a game profile.

    Args:
        profile: The GameProfile to save. Keyed by lowercase name.
    """
    profiles = _load_profiles()
    profiles[profile.name.lower()] = profile
    _save_profiles(profiles)


# ── AI-Suggested Launch Options ──


def _filter_banned(text: str) -> str:
    """Remove any lines containing banned PRIME offload patterns."""
    lines = text.splitlines()
    filtered = []
    for line in lines:
        if any(pat in line for pat in _BANNED_PATTERNS):
            logger.warning("Filtered banned pattern from LLM response: %s", line.strip())
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def suggest_launch_options(
    game_name: str,
    hardware: HardwareSnapshot | None = None,
    rate_limiter: RateLimiter | None = None,
) -> GameProfile:
    """Generate AI-suggested launch options for a game.

    CRITICAL safety rules enforced:
    - Prompt explicitly forbids PRIME offload env vars.
    - Prompt explicitly forbids lowering vm.swappiness.
    - Post-processing filters any banned patterns from the response.
    - If LLM is unavailable or rate-limited, returns safe defaults.

    Args:
        game_name: Name of the game to generate options for.
        hardware: Optional hardware snapshot for context.
        rate_limiter: Optional rate limiter instance.

    Returns:
        A GameProfile with suggested launch_options.
    """
    # Check rate limit before calling LLM
    if rate_limiter is not None and not rate_limiter.can_call("litellm"):
        logger.info("Rate limited; using safe default for %s", game_name)
        return GameProfile(name=game_name, launch_options=_SAFE_DEFAULT)

    hw_context = ""
    if hardware is not None:
        hw_context = (
            f"\nHardware: GPU={hardware.gpu_name} ({hardware.gpu_vram_total_mb}MB VRAM), "
            f"CPU={hardware.cpu_model} ({hardware.cpu_cores} cores), "
            f"RAM={hardware.ram_total_mb}MB, Driver={hardware.gpu_driver}"
        )

    prompt = (
        f"Suggest Steam launch options for '{game_name}' on Bazzite Linux "
        f"(Fedora Atomic, NVIDIA GTX 1060 + Intel HD 630).{hw_context}\n\n"
        "RULES:\n"
        "- NEVER use PRIME offload environment variables "
        "(__NV_PRIME_RENDER_OFFLOAD, __GLX_VENDOR_LIBRARY_NAME, "
        "__VK_LAYER_NV_optimus, prime-run, DRI_PRIME). They crash games.\n"
        "- NEVER suggest lowering vm.swappiness. 180 is correct for ZRAM.\n"
        "- Include gamemoderun and mangohud if appropriate.\n"
        "- Return ONLY the launch options string, nothing else.\n"
    )

    try:
        from ai.router import route_query  # noqa: PLC0415

        response = route_query("fast", prompt)
    except (RuntimeError, ValueError) as e:
        logger.warning("LLM query failed for %s: %s", game_name, e)
        return GameProfile(name=game_name, launch_options=_SAFE_DEFAULT)

    if rate_limiter is not None:
        rate_limiter.record_call("litellm")

    # Scaffold response means LLM is not live yet
    if response.startswith("[SCAFFOLD]"):
        logger.info("Scaffold response; using safe default for %s", game_name)
        return GameProfile(name=game_name, launch_options=_SAFE_DEFAULT)

    # Post-process: filter any banned patterns that slipped through
    filtered = _filter_banned(response)
    if not filtered:
        filtered = _SAFE_DEFAULT

    return GameProfile(name=game_name, launch_options=filtered)


# ── MangoHud Preset Writer ──


def apply_mangohud_preset(
    preset: str,
    config_path: Path | None = None,
) -> Path:
    """Write a MangoHud preset to the config file.

    Uses atomic write (tmp + rename) to avoid partial writes.

    Args:
        preset: Name of the preset (default, minimal, full, fps_only).
        config_path: Override for the MangoHud config path.

    Returns:
        The path the config was written to.

    Raises:
        ValueError: If preset name is not recognized.
    """
    if preset not in MANGOHUD_PRESETS:
        valid = ", ".join(sorted(MANGOHUD_PRESETS.keys()))
        raise ValueError(f"Unknown preset '{preset}'. Valid presets: {valid}")

    target = config_path or MANGOHUD_CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    settings = MANGOHUD_PRESETS[preset]
    lines = [f"# MangoHud preset: {preset}", f"# Generated by {APP_NAME}", ""]
    for key, value in settings.items():
        if value:
            lines.append(f"{key}={value}")
        else:
            lines.append(key)
    content = "\n".join(lines) + "\n"

    fd, tmp_path = tempfile.mkstemp(
        dir=str(target.parent),
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Applied MangoHud preset '%s' to %s", preset, target)
    return target
