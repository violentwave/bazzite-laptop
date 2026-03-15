# Bazzite Gaming Laptop: Optimization, Security & Automation Guide
## Acer Predator G3-571 — Project Reference Document

**System**: Acer Predator G3-571 | Bazzite 42/43 (KDE6/Wayland) | Username: lch
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

**Services to KEEP** (important for this system):

| Service | Why keep |
|---------|----------|
| supergfxd | GPU switching — critical |
| nvidia-powerd + nvidia-* | GPU power management |
| thermald | Thermal management — important for laptop |
| tuned + tuned-ppd | Performance profiles |
| firewalld | Firewall — critical |
| systemd-resolved | DNS-over-TLS |
| smartd | Disk health monitoring |
| lm_sensors | Temperature monitoring |
| bluetooth | Currently blocked by firewall, keep for future use |
| NetworkManager | Network management — critical |
| fstrim.timer | SSD maintenance |
| clamav-freshclam | Virus signature auto-updater |
| clamd@scan | ClamAV daemon — on-demand only (started/stopped per scan) |

> External SSD optimization note: current mount uses `relatime` — consider adding `noatime` via fstab or udisks2 rule to reduce unnecessary writes.

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
- **KDE Security menu**: ClamAV Deep Scan, ClamAV Quick Scan, Firewall, Firewall Status, KWalletManager, Scan Logs, Start Security Monitor, System Health Snapshot, Update Email Password, USB Devices, View Health Logs, View Quarantine
- ## Brave Browser — Flatseal Permission Hardening
**Status**: Completed
**Date**: 2026-03-14
**Tool**: Flatseal (com.github.tchx84.Flatseal)

Brave Flatpak ships with overly broad default permissions that flag it as
medium risk. The following changes were made in Flatseal to tighten the
sandbox without breaking normal browsing.

### Sockets
| Permission | Change | Notes |
|---|---|---|
| X11 windowing | Disabled | Running Wayland natively — X11 has no app isolation |
| Wayland windowing | Kept ON | Required — primary display server |
| Fallback to X11 | Kept OFF | Leave off — would undermine X11 removal |
| PulseAudio | Kept ON | Required for audio |
| Smart cards | Disabled | Not using a physical smart card or YubiKey |
| Printing (cups) | Disabled | Not printing from browser |

### Filesystem
| Permission | Change | Notes |
|---|---|---|
| filesystem=host | Kept OFF | Never needed |
| filesystem=host-etc | Kept OFF | Brave does not need system config access |
| filesystem=home | Kept OFF | Too broad |
| xdg-download | Kept ON | Required for downloads |
| xdg-desktop | Removed | Browser doesn't need Desktop folder access |
| xdg-run/pipewire-0 | Kept | Required for audio/video |
| xdg-run/dconf | Kept | Acceptable — KDE settings integration |
| ~/.local/share/icons:create | Removed | Not using PWAs |
| /run/.heim_org.h5l.kcm-socket | Removed | Kerberos auth socket — not needed |

### Devices
| Permission | Change | Notes |
|---|---|---|
| Bluetooth (org.bluez) | Disabled | Not using BT devices with browser |

### Share / Environment / Persistent
No changes — all settings in these sections were already appropriate.

### Result
Brave risk rating reduced from medium toward low. Residual medium
classification is inherent to Chromium-based Flatpak sandbox model
(Zypak) — not a config issue. On Bazzite with Wayland, enforcement
is solid.

### What still works after hardening
- All browsing, downloads, file uploads (via xdg portal picker)
- Audio and video in browser
- KDE integration
- GPU acceleration (GTX 1060)

### What no longer works (intentional)
- Drag-and-drop uploads from Desktop folder
- PWA icons (removed ~/.local/share/icons:create)
- Smart card auth
- Printing directly from browser
- Bluetooth device pairing through browser


### ClamAV ✅
Layered packages: `clamav`, `clamav-freshclam`, `clamd`, `msmtp`
- **Scanner**: clamdscan (daemon mode via clamd@scan, not standalone clamscan)
- **On-demand pattern**: start clamd@scan → clamdscan --fdpass --multiscan → stop clamd@scan (reclaims ~1.1GB RAM)
- **Scan time**: ~20 minutes (down from 75 min with standalone clamscan), 8 threads via MaxThreads in /etc/clamd.d/scan.conf
- **Config**: /etc/clamd.d/scan.conf — ExcludePath directives (replaces --exclude-dir which clamdscan ignores)
- **Socket**: /run/clamd.scan/clamd.sock
- **Quick scan**: daily at noon — `/home/lch`, `/tmp`
- **Deep scan**: weekly Friday 11PM — `/home/lch`, `/tmp`, `/var`
- **Test scan**: EICAR detection test — full pipeline validation in ~30-60 seconds
- **Quarantine**: `~/security/quarantine/` — files locked with chmod 000 + chattr +i, directory root:lch 750
- **Quarantine release**: `/usr/local/bin/quarantine-release.sh` (--list, --interactive, direct release)
- **SHA256 hash logging**: `~/security/quarantine-hashes.log` with VirusTotal links for every quarantined file
- **Logs**: `/var/log/clamav-scans/` with 60-day rotation via `/etc/logrotate.d/clamav-scans`
- **clamd logs**: `/var/log/clamav-scans/clamd.log`
- **Signature updates**: freshclam daemon (clamav-freshclam.service) — automatic, continuous updates
- **SELinux boolean**: `antivirus_can_scan_system = on`
- **Email alerts**: HTML emails via msmtp + Gmail app password, sent after EVERY scan (quick, deep, test)
  - Config: /home/lch/.msmtprc (absolute path required — script runs as root via sudo)
  - 3 templates: clean (green banner), threats (red with detail table), error (amber)
  - Healthcheck failures also trigger email
- **Script**: `/usr/local/bin/clamav-scan.sh {quick|deep|test}` — colored terminal UI, status file, desktop notifications
- **Alert script**: `/usr/local/bin/clamav-alert.sh` — sends HTML email with threat details
- **Signal handling**: Scan script traps INT/TERM — stops clamd, resets tray status to idle on interrupt

### Notification System ✅
- **System tray app**: ~/security/bazzite-security-tray.py (Python + GObject + AppIndicator3)
- **Custom icons**: 7 SVG shield icons at ~/security/icons/hicolor/scalable/status/ with freedesktop index.theme (viewBox 48x48)
  - Shape-differentiated badges for colorblind accessibility: filled circle (healthy), hollow ring (scanning), checkmark (complete), triangle (warning), X mark (error/threats), EKG pulse (health warning), outline-only (blink frame)
- **9-state icon machine**:
  - healthy_idle (green, filled circle badge)
  - scan_running (teal blink, ring badge)
  - scan_complete (blue blink 30s, checkmark badge)
  - warning (yellow, triangle badge)
  - scan_failed (red, X badge)
  - scan_aborted (red blink, X badge)
  - threats_found (red blink, X badge)
  - health_warning (green shield + amber EKG pulse badge, steady — shows when ClamAV idle but health has warnings)
  - unknown (yellow, triangle badge)
- **Blink**: GLib.timeout_add toggles between colored icon and blank shield
- **Autostart**: ~/.config/autostart/bazzite-security-tray.desktop (X-GNOME-Autostart-Delay=5)
- **Resilience**: SIGHUP ignored (survives terminal closure), PR_SET_NAME prevents pkill clamscan from killing tray
- **Status**: Polls ~/security/.status (JSON) every 3 seconds, atomic writes from scan/health scripts (read-modify-write pattern)
- **Menu**: Quick/deep/test scan, health snapshot, health submenu (status + issue count), test suite, quarantine view/release, logs, quit

### Healthcheck System ✅
- **Script**: `/usr/local/bin/clamav-healthcheck.sh` — 10+ automated checks
- **Timer**: clamav-healthcheck.timer — Wednesdays 2:00 PM
- **Checks**: binaries, signatures, timers, quarantine, logs, msmtp, disk space, clamd service
- **Email**: Sends alert on failure
- **Scan email integration**: Health summary appended to every ClamAV scan email

### Security Test Suite ✅
- **Script**: `/usr/local/bin/bazzite-security-test.sh` — 15-test diagnostic
- **5 phases**: prerequisites, infrastructure, scanning (EICAR), notifications, tray/menu
- **EICAR test**: Creates standard test virus, validates full detection → quarantine → lockdown pipeline
- **Report**: Generates ~/security/test-report-*.log
- **Safety**: Backs up/restores .status file, full cleanup on exit via trap
- **Access**: Available from tray menu "Run Test Suite"

### Integration Test Suite ✅
- **Script**: `/usr/local/bin/integration-test.sh` — 26 automated checks
- **Covers**: lock files, .desktop icon paths, path traversal prevention, firewall zones, SELinux, USBGuard, ClamAV signatures, msmtp binary
- **Access**: Run manually via `sudo integration-test.sh`

### Systemd Service Hardening ✅
All ClamAV and health systemd services include security directives:
- `NoNewPrivileges=yes` — prevents privilege escalation via setuid binaries
- `ProtectSystem=strict` — entire filesystem read-only except API filesystems
- `ProtectHome=read-only` — home directories read-only
- `PrivateTmp=yes` — private /tmp namespace
- `ReadWritePaths=` — explicit write whitelist (e.g., `/var/log/clamav-scans /home/lch/security`)
- Applied to: clamav-quick.service, clamav-deep.service, clamav-healthcheck.service, system-health.service

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
- **deploy.sh**: syncs repo files (scripts, systemd units, configs, desktop files, tray app) to their system locations — `sudo ./scripts/deploy.sh [--dry-run]`
- **backup-official-guide.md**: full guide with 5 restore scenarios including LUKS emergency
- Flash drive layout: sdc1/sdc2 = Bazzite installer (bootable), sdc3 = BazziteBackup

### GitHub ✅
- **Private repo**: github.com:violentwave/bazzite-laptop.git
- All project files, scripts, configs, docs, and history tracked in git
- Additional off-site backup for the project (supplements flash drive backup)

### Bitwarden ✅
- Password manager for secure credential storage

### System Monitoring Tools ✅
- Mission Center: Flatpak (GUI system monitor)
- btop: pre-installed (terminal system monitor)
- nvtop: pre-installed (GPU terminal monitor)
- smartmontools: pre-installed (SMART disk health)
- lm-sensors: pre-installed (hardware temperatures)
- system-health-snapshot.sh: custom health monitoring — SMART delta tracking,
  GPU/CPU thermals, storage alerts, service checks, email alerts, tray integration
- system-health-test.sh: 16-test validation suite
- Daily 8AM timer (system-health.timer) with persistent catch-up

### Claude Code Setup ✅
- At `~/.local/bin/claude`
- Settings at `~/.claude/settings.json`
- Sandbox enabled (bubblewrap)
- Launch from project directories, never from `$HOME`

### Layered Packages (rpm-ostree)
- `clamd` — ClamAV scanning daemon (on-demand, not persistent)
- `clamav` — antivirus scanner
- `clamav-freshclam` — signature updater
- `gamemode` — CPU/GPU optimization during gaming
- `msmtp` — SMTP client for email alerts
- `usbguard` — USB device authorization

---

## REMAINING WORK — TO DO IN FUTURE CHATS

### 1. ScopeBuddy Configuration
Pre-installed advanced game launch manager. Config at `~/.config/scopebuddy/`. Use `scb -- %command%` in launch options. Note: gamescope has beta NVIDIA support — may need `SCB_NOSCOPE=1` if issues arise.
Docs: https://docs.bazzite.gg/Advanced/scopebuddy/

### 2. Proton Environment Variables
Test per-game (do NOT use PRIME offload vars — those crash games):
- `PROTON_ENABLE_WAYLAND=1` — native Wayland rendering in Proton 10+
- `PROTON_USE_NTSYNC=1` — improved synchronization primitives

### 3. AI/Coding Setup (Deferred)
**Ollama with CUDA** — GTX 1060 6GB VRAM can run:
- ✅ 7B parameter models (Llama 3.2, Mistral 7B, Qwen2.5-Coder 7B)
- ⚠️ 13B models will be slow (heavy CPU offloading)
- ❌ 70B+ models won't run well

**VS Code** — Install via Flatpak: `flatpak install flathub com.visualstudio.code`
Connect to local Ollama via Continue extension.

### 4. Downloads Folder Watcher
inotify-based auto-scan of ~/Downloads for new files — quarantine anything suspicious automatically.

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
| `/etc/logrotate.d/` | ✅ | clamav-scans, system-health |
| `/usr/local/bin/` | ✅ | clamav-scan.sh, clamav-alert.sh, clamav-healthcheck.sh, quarantine-release.sh, bazzite-security-test.sh, public-wifi-mode, system-health-snapshot.sh, system-health-test.sh, start-security-tray.sh, integration-test.sh |
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
| Run test suite | `sudo bazzite-security-test.sh` |
| Run test scan | `sudo clamav-scan.sh test` |
| Run healthcheck | `sudo clamav-healthcheck.sh` |
| Quarantine list | `sudo quarantine-release.sh --list` |
| Release quarantine | `sudo quarantine-release.sh --interactive` |
| Start tray icon | `start-security-tray.sh` |
| Integration tests | `sudo integration-test.sh` |
| Check freshclam | `systemctl status clamav-freshclam.service` |
| Check clamd | `systemctl status clamd@scan` |
| Health snapshot | `sudo system-health-snapshot.sh` |
| Health + email | `sudo system-health-snapshot.sh --email` |
| SMART self-test | `sudo system-health-snapshot.sh --selftest` |
| Health test suite | `sudo system-health-test.sh` |
| View health log | `less /var/log/system-health/health-latest.log` |
