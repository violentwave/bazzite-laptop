# Bazzite Gaming Laptop Project
## System: Acer Predator G3-571 | Bazzite 43 | NVIDIA GTX 1060 + Intel HD 630

## Rules
- This is an immutable OS (Fedora Atomic). Do NOT modify /usr directly.
- Use rpm-ostree for system packages, flatpak for apps.
- Never use sudo rm -rf, curl piped to bash, or wget without permission.
- Custom configs go in /etc/ (survives updates) or ~/.config/ (user configs).
- Test all changes before committing.
- NEVER use PRIME offload env vars in game launch options — they crash games.
- NEVER lower vm.swappiness — 180 is correct for ZRAM.

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- MangoHud config: ~/.config/MangoHud/MangoHud.conf
- DNS config: /etc/systemd/resolved.conf.d/dns-over-tls.conf
- WiFi script: /usr/local/bin/public-wifi-mode
- Claude Code settings: ~/.claude/settings.json
- Backup scripts: /mnt/backup/ (on USB flash drive sdc3)
