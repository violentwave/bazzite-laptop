# Bazzite Gaming Laptop: Optimization, Security & Automation Guide
## Acer Predator G3-571 — Project Reference Document

**System**: Acer Predator G3-571 | Bazzite 42/43 (KDE6/Wayland) | Username: lch
**Hardware probe**: REDACTED
**GPUs**: NVIDIA GTX 1060 Mobile 6GB + Intel HD 630 (Hybrid/Optimus)
**CPU**: Intel i7-7700HQ | **RAM**: 16GB | **Vulkan**: 1.4.341
**NVIDIA Driver**: 580.95.05 | **CUDA**: 13.0
**Internal storage**: 256GB SK hynix SSD (OS only, LUKS encrypted)
**External storage**: 1.8TB SanDisk Extreme SSD at /run/media/lch/SteamLibrary (ext4)
**Displays**: Laptop 1920x1080 (eDP) + Vizio TV via HDMI (on NVIDIA GPU)

---

## COMPLETED SETUP — DO NOT REDO

### GPU & Display Configuration ✅
- supergfxctl enabled and running in **Hybrid mode** (only Integrated/Hybrid available — no Dedicated mode on this hardware)
- `nvidia-drm.modeset=1` added via `rpm-ostree kargs --append=nvidia-drm.modeset=1` — **required for HDMI output on Wayland**
- Intel HD 630 is default desktop renderer; NVIDIA GTX 1060 handles games via Proton/DXVK automatically
- Dual display working: laptop eDP + TV via HDMI on NVIDIA GPU
- HDMI audio routing to TV configured in KDE audio settings

### ⚠️ CRITICAL: Launch Options
**PRIME offload environment variables CRASH games on this system. Do NOT use them:**
```
# ❌ DO NOT USE — causes games to fail to launch:
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia gamemoderun mangohud %command%

# ❌ ALSO CRASHES:
__NV_PRIME_RENDER_OFFLOAD=1 __VK_LAYER_NV_optimus=NVIDIA_only VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json gamemoderun mangohud %command%
```

**Correct launch options that work on this system:**
```
# ✅ Standard launch option for ALL games:
gamemoderun mangohud %command%

# ✅ Marvel Rivals ONLY (needs SteamDeck flag):
SteamDeck=1 gamemoderun mangohud %command%
```

The NVIDIA GPU handles rendering through Proton/DXVK automatically since nvidia-drm.modeset=1 is set and the GPU is active (driving HDMI). The `gamemoderun` command was failing initially because GameMode was not pre-installed — it was layered via rpm-ostree (see below).

### Gaming Setup ✅
- Steam installed with Proton Experimental as default compatibility tool
- GE-Proton installed via **ProtonPlus** (pre-installed on Bazzite; ProtonUp-Qt was NOT installed)
- **GameMode installed via `rpm-ostree install gamemode`** — it was NOT pre-installed on this Bazzite image despite documentation suggesting otherwise
- MangoHud pre-installed and configured at `~/.config/MangoHud/MangoHud.conf`:
  - F12: toggle overlay on/off
  - F11: toggle performance logging (saves CSV to /tmp/MangoHud/)
  - Shows: FPS, GPU/CPU stats+temps, VRAM, RAM, frame timing
- Steam shader pre-caching enabled (both toggles ON in Settings → Downloads)
- Downloads during gameplay disabled
- External 1.8TB SSD set as Steam library location (ownership fixed with `chown lch:lch`)
- Steam configured: GPU accelerated rendering ON, hardware video decoding ON

### Performance Config ✅
- **ZRAM swap**: Active with `vm.swappiness=180` — this is the **Bazzite default optimized for ZRAM, do NOT lower it**. We tested lowering to 10 and reverted because ZRAM-backed swap needs high swappiness to function properly.
- **GameMode advanced config**: `/etc/gamemode.ini` deployed — GPU powermizer mode 1, reaper freq 5s, custom governor script hooks
- **NVIDIA shader cache**: 4GB limit set in `/etc/environment` via `__GL_SHADER_DISK_CACHE_SIZE=4294967296`
- **I/O scheduler**: `mq-deadline` set for external SSD via udev rule at `/etc/udev/rules.d/60-ioschedulers.rules`
- **Network tuning**: TCP Fast Open + no slow start after idle via `/etc/sysctl.d/99-gaming-network.conf`
- System fully updated (`rpm-ostree upgrade` + `flatpak update`)

### Services Optimization ✅
Disabled all unnecessary services to reduce attack surface and resource usage:
- avahi-daemon.service + avahi-daemon.socket — mDNS/Bonjour
- ModemManager.service — no modem on this machine
- All virt* services/sockets — libvirt/KVM virtualization daemons
- vboxservice.service — VirtualBox guest additions
- vmtoolsd.service, vgauthd.service — VMware tools
- sssd.service, sssd-kcm.socket — System Security Services Daemon
- iscsi-onboot.service, iscsi-starter.service, iscsid.socket, iscsiuio.socket — iSCSI storage
- mdmonitor.service — MD RAID monitoring (no RAID on this system)
- raid-check.timer — Weekly RAID check (no RAID)
- qemu-guest-agent.service — QEMU agent (bare metal, not a VM)

### Security Hardening ✅
- **SSH**: Disabled (`sudo systemctl disable --now sshd`)
- **Firewall**: firewalld set to DROP zone (all incoming blocked except dhcpv6-client)
- **Firewall logging**: `log-denied=all` set permanently
- **CUPS**: Disabled (`sudo systemctl disable --now cups`) — no printing needed
- **DNS-over-TLS**: Enabled via systemd-resolved (Cloudflare 1.1.1.1 + Quad9 9.9.9.9) at `/etc/systemd/resolved.conf.d/dns-over-tls.conf`
- **Public WiFi toggle script**: Installed at `/usr/local/bin/public-wifi-mode`
  - `sudo public-wifi-mode on` — DROP zone (public WiFi)
  - `sudo public-wifi-mode off` — HOME zone (trusted network)
- KDE Connect and Bluetooth: still enabled but blocked by firewall DROP zone
- **KDE Security menu**: 6-item shortcut menu in KDE application launcher (scans, quarantine, firewall, USB, logs)

### ClamAV ✅
Layered packages: `clamav`, `clamav-freshclam`, `msmtp`
- **Quick scan**: daily at noon — `/home/lch`, `/tmp` — email alert on threats only
- **Deep scan**: weekly Friday 11PM — `/home/lch`, `/tmp`, `/var` — email alert always
- **Quarantine**: `~/security/quarantine/`
- **Logs**: `/var/log/clamav-scans/` with 60-day rotation via `/etc/logrotate.d/clamav-scans`
- **Email alerts**: via msmtp + Gmail app password (`~/.msmtprc` chmod 600)
- **Signature updates**: freshclam every 4 hours (`/etc/freshclam.conf`)
- **Script**: `/usr/local/bin/clamav-scan.sh {quick|deep}` — colored terminal UI, status file, desktop notifications
- **Alert script**: `/usr/local/bin/clamav-alert.sh` — sends email with threat details

### USBGuard ✅
Layered package: `usbguard`
- **Status**: Active, policy-mode block
- **Rules**: `/etc/usbguard/rules.conf` — 12 devices whitelisted
- **Whitelisted**: USB root hubs, Lite-On WiFi/BT, Chicony webcam, SanDisk Extreme SSD, 2× ASolid flash drives, 8BitDo controller (active+idle+port2), Logitech mouse, VOOPOO
- **Setup script**: `usbguard-setup.sh` — interactive two-round setup (connect all devices, then whitelist)

### LUKS ✅
- KDF is already **Argon2id** — no upgrade needed (verified with `luks-upgrade.sh`)
- Header backed up to `~/security/luks-backup/` and `/mnt/backup/luks-header-backup/`
- Emergency restore: `sudo cryptsetup luksHeaderRestore /dev/sda3 --header-backup-file luks-header.bak`

### Browser Hardening ✅
Using **Brave** (com.brave.Browser) — built-in ad/tracker blocking, fingerprint protection, HTTPS upgrades. No additional hardening needed (arkenfox was for Firefox).

### Backup System ✅
Custom flat backup to BazziteBackup flash drive (sdc3):
- **backup.sh**: backs up all configs, scripts, user data, game saves, flatpak data, project files to `/mnt/backup/latest/`
- **restore.sh**: interactive step-by-step restore with confirmation prompts and manual steps
- **backup-official-guide.md**: full guide with 5 restore scenarios including LUKS emergency
- Flash drive layout: sdc1/sdc2 = Bazzite installer (bootable), sdc3 = BazziteBackup

### Claude Code Setup ✅
- Version 2.1.76 at `~/.local/bin/claude`
- Settings at `~/.claude/settings.json`
- Sandbox enabled (bubblewrap)
- Launch from project directories, never from `$HOME`

### Layered Packages (rpm-ostree)
- `clamav` — antivirus scanner
- `clamav-freshclam` — signature updater
- `gamemode` — CPU/GPU optimization during gaming
- `msmtp` — SMTP client for email alerts
- `usbguard` — USB device authorization

---

## REMAINING WORK — TO DO IN FUTURE CHATS

### 1. Notification System Overhaul
Current ClamAV alerts are basic. Upgrade to:
- Fancy terminal output with progress bars and color-coded threat levels
- HTML emails with formatted threat reports
- KDE system tray icon showing scan status

### 2. ScopeBuddy Configuration
Pre-installed advanced game launch manager. Config at `~/.config/scopebuddy/`. Use `scb -- %command%` in launch options. Note: gamescope has beta NVIDIA support — may need `SCB_NOSCOPE=1` if issues arise.
Docs: https://docs.bazzite.gg/Advanced/scopebuddy/

### 3. Proton Environment Variables
Test per-game (do NOT use PRIME offload vars — those crash games):
- `PROTON_ENABLE_WAYLAND=1` — native Wayland rendering in Proton 10+
- `PROTON_USE_NTSYNC=1` — improved synchronization primitives

### 4. AI/Coding Setup (Deferred)
**Ollama with CUDA** — GTX 1060 6GB VRAM can run:
- ✅ 7B parameter models (Llama 3.2, Mistral 7B, Qwen2.5-Coder 7B)
- ⚠️ 13B models will be slow (heavy CPU offloading)
- ❌ 70B+ models won't run well

**VS Code** — Install via Flatpak: `flatpak install flathub com.visualstudio.code`
Connect to local Ollama via Continue extension.

### 5. System Monitoring Tools
| Tool | Method | Purpose |
|------|--------|---------|
| Mission Center | Flatpak | GUI system monitor (Task Manager equivalent) |
| btop | `ujust bazzite-cli` | Terminal system monitor |
| nvtop | rpm-ostree or Flatpak | Dual-GPU terminal monitor |
| smartmontools | rpm-ostree | SSD health monitoring (SMART) |
| lm-sensors | Check if pre-installed | Hardware temperature readings |

**Disk health** — After installing smartmontools:
- Internal: `sudo smartctl -a /dev/sda`
- External: `sudo smartctl -a -d sat /dev/sdb`

---

## Game Compatibility Notes

| Game | Status | Notes |
|------|--------|-------|
| Elden Ring | ✅ Works | Medium/Low settings on GTX 1060 |
| Skyrim SE | ✅ Works | |
| Fallout 4 | ✅ Works | |
| Fallout: New Vegas | ✅ Works | |
| Fallout 76 | ⚠️ Works | Can be finicky, check ProtonDB |
| Hogwarts Legacy | ✅ Works | Medium/Low settings on GTX 1060 |
| Valheim | ✅ Confirmed | Tested and working |
| Fable Anniversary | ✅ Confirmed | Tested and working |
| No Man's Sky | ✅ Works | |
| Outer Wilds | ✅ Works | |
| Red Dead Redemption 2 | ✅ Works | Medium/Low settings on GTX 1060 |
| Stray | ✅ Works | |
| Palworld | ✅ Works | |
| Path of Exile 1 & 2 | ✅ Works | PoE2 works out of box with Proton |
| Overwatch | ✅ Works | Use Proton Experimental |
| Marvel Rivals | ⚠️ Works | Needs `SteamDeck=1`, unofficial/ban risk |
| GTA V/Enhanced (Story) | ✅ Works | Story mode only |
| GTA V/Enhanced (Online) | ❌ Broken | BattlEye not enabled for Linux by Rockstar |
| skate. | ❌ Likely broken | EA anti-cheat |
| Disney Dreamlight Valley | ✅ Works | |
| Palia | ✅ Works | |
| Supermarket Together | ✅ Works | |
| Fishing Planet | ✅ Works | |
| Session: Skate Sim | ✅ Works | |
| Strategic War in Europe | ✅ Works | |
| RuneScape | ✅ Works | |
| IdleOn | ✅ Works | |
| VRoid Studio | ✅ Works | |

---

## Where Custom Files Survive Bazzite Updates

| Path | Survives | Our files there |
|------|----------|-----------------|
| `/etc/systemd/system/` | ✅ | clamav-quick/deep .timer + .service |
| `/etc/sysctl.d/` | ✅ | 99-gaming-network.conf |
| `/etc/udev/rules.d/` | ✅ | 60-ioschedulers.rules |
| `/etc/systemd/resolved.conf.d/` | ✅ | dns-over-tls.conf |
| `/etc/usbguard/` | ✅ | rules.conf |
| `/etc/firewalld/` | ✅ | Custom zone configs |
| `/etc/logrotate.d/` | ✅ | clamav-scans |
| `/usr/local/bin/` | ✅ | clamav-scan.sh, clamav-alert.sh, public-wifi-mode |
| `~/.config/MangoHud/` | ✅ | MangoHud.conf |
| `~/.config/scopebuddy/` | ✅ | Future ScopeBuddy configs |
| `~/.claude/` | ✅ | Claude Code settings |
| `/usr/` (except /usr/local/) | ❌ | Immutable — don't put files here |

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Check GPU mode | `supergfxctl -g` |
| Check NVIDIA status | `nvidia-smi` |
| Check GPU rendering | `glxinfo \| grep "OpenGL renderer"` |
| Check GameMode | `gamemoded --status` |
| Update system | `rpm-ostree upgrade && flatpak update` |
| Check open ports | `sudo ss -tlnp` |
| Check firewall | `sudo firewall-cmd --list-all` |
| Check DNS | `resolvectl status` |
| Check SELinux | `getenforce` |
| Public WiFi mode | `sudo public-wifi-mode on/off` |
| Run ClamAV quick scan | `sudo clamav-scan.sh quick` |
| Run ClamAV deep scan | `sudo clamav-scan.sh deep` |
| Check ClamAV timers | `systemctl list-timers clamav-*` |
| Check USBGuard status | `sudo usbguard list-rules` |
| Kill stuck Proton | `ujust fix-proton-hang` |
| View boot logs | `ujust logs-this-boot` |
| Rollback system | `rpm-ostree rollback` |
| List layered packages | `rpm-ostree status` |
