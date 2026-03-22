# Bazzite Gaming Skill Bundle

Tools for listing game profiles and retrieving MangoHud performance overlay
presets for games in the Steam library.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `gaming.profiles` | List all configured game profiles (game name, tuning notes, preset name) | none |
| `gaming.mangohud_preset` | Get the MangoHud overlay preset for a specific Steam game | `game` (string, max 100 chars, must match a Steam library title, required) |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "What games do I have profiles for?" | `gaming.profiles` |
| "Show me my game profiles" | `gaming.profiles` |
| "What MangoHud preset should I use for Elden Ring?" | `gaming.mangohud_preset` with `game="Elden Ring"` |
| "How is Cyberpunk 2077 configured?" | `gaming.mangohud_preset` with `game="Cyberpunk 2077"` |

---

## Safety Rules — NEVER violate these

- **NEVER suggest PRIME offload environment variables** in game launch options
  or anywhere else. The following will crash games on this hybrid GPU system
  and must never appear in any response:
  - `NV_PRIME_RENDER_OFFLOAD`
  - `__GLX_VENDOR_LIBRARY_NAME`
  - `__VK_LAYER_NV_optimus`
  - `prime-run`
  - `DRI_PRIME`

- **NEVER suggest `supergfxctl -m Dedicated`**. This system uses Bazzite's
  built-in hybrid GPU management. Switching to dedicated mode via supergfxctl
  requires a logout and can leave the system in an unstable state.

- **NEVER suggest ProtonUp-Qt** for managing Proton versions.
  Use **ProtonPlus** instead — it is the supported tool on this system.

- If a game name is not found in the Steam library, say so clearly rather
  than guessing or inventing a preset.
