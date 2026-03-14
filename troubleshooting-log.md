# Troubleshooting Log
## Problems Solved — Do Not Re-debug

### 1. supergfxctl "Dedicated" mode does not exist
**Problem**: `supergfxctl -m Dedicated` returns "Could not parse mode name"
**Root cause**: Acer Predator G3-571 only supports Integrated and Hybrid modes (no hardware MUX switch)
**Fix**: Stay in Hybrid mode (`supergfxctl -g` returns "Hybrid"). This is correct.
**Verify**: `supergfxctl -s` shows `[Integrated, Hybrid]`

### 2. HDMI output not working (external TV not detected)
**Problem**: `/sys/class/drm/card0-HDMI-A-1/status` showed "disconnected" with TV plugged in
**Root cause**: `nvidia-drm.modeset=1` was missing from kernel arguments. Required for NVIDIA to drive HDMI on Wayland.
**Fix**: `rpm-ostree kargs --append=nvidia-drm.modeset=1` then reboot
**Verify**: Both displays working after reboot. `cat /proc/cmdline` includes `nvidia-drm.modeset=1`

### 3. PRIME offload environment variables crash all games
**Problem**: Adding `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia` to launch options causes games to show "launching" then stop after ~60 seconds.
**Root cause**: Once nvidia-drm.modeset=1 was enabled and NVIDIA is driving the HDMI display, the PRIME offload GLX variable conflicts with Proton/DXVK's Vulkan rendering pipeline.
**Fix**: Do NOT use any PRIME offload variables. Games route to NVIDIA automatically via DXVK/Vulkan.
**Working launch option**: `gamemoderun mangohud %command%`
**Also crashes**: `__NV_PRIME_RENDER_OFFLOAD=1 __VK_LAYER_NV_optimus=NVIDIA_only VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json gamemoderun mangohud %command%`

### 4. `gamemoderun` command not found
**Problem**: `gamemoderun mangohud %command%` caused games to fail. `which gamemoderun` returned nothing.
**Root cause**: GameMode was NOT pre-installed on this Bazzite image despite documentation claiming it is.
**Fix**: `rpm-ostree install gamemode` then reboot
**Verify**: `which gamemoderun` returns `/usr/bin/gamemoderun`, `gamemoded --status` returns "inactive" (activates only during gameplay)

### 5. ProtonUp-Qt not installed
**Problem**: `flatpak run net.davidotek.pupgui2` returned "not installed"
**Root cause**: Bazzite ships ProtonPlus instead of ProtonUp-Qt on this image
**Fix**: Use ProtonPlus (already installed) to manage Proton versions. Installed GE-Proton from it.

### 6. External SSD not appearing as Steam library option
**Problem**: After plugging in 1.8TB external SSD, Steam wouldn't show it as an installable location
**Root cause**: Drive root owned by root:root, Steam couldn't write to it
**Fix**: `sudo chown lch:lch /run/media/lch/SteamLibrary/`
**Note**: The `lost+found` directory on the drive is normal ext4 — not malware.

### 7. vm.swappiness set to wrong value
**Problem**: We lowered swappiness from 180 to 10 for "gaming optimization"
**Root cause**: Bazzite uses ZRAM-backed swap which needs HIGH swappiness (180) to function. Low swappiness starves ZRAM.
**Fix**: `sudo rm /etc/sysctl.d/99-gaming.conf && sudo sysctl vm.swappiness=180`
**Rule**: NEVER lower vm.swappiness on Bazzite. 180 is correct for ZRAM.

### 8. nvidia-xconfig command not found
**Problem**: `sudo nvidia-xconfig --cool-bits=28` returned "command not found"
**Root cause**: nvidia-xconfig doesn't exist on Bazzite's immutable filesystem
**Fix**: Ignore — overclocking via xconfig is not applicable on Bazzite

### 9. ujust enable-gamemode / ujust configure-nvidia-optimus confusion
**Problem**: `ujust enable-gamemode` doesn't exist, `ujust configure-nvidia-optimus` just runs nvidia-smi
**Root cause**: These ujust commands don't do what their names suggest on this hardware
**Fix**: GameMode installed manually via rpm-ostree. GPU config handled by supergfxctl + nvidia-drm.modeset=1.

### 10. "No licenses" error when launching game from terminal
**Problem**: `steam steam://rungameid/351970` shows "no licenses" error
**Root cause**: Running steam:// URI while Steam is already open causes this. Not an actual license issue.
**Fix**: Ignore — only happens when trying to launch via terminal while Steam is running. Launch games normally through Steam UI.

### 11. freshclam "Permission denied" on log file
**Problem**: freshclam shows "ERROR: Failed to open log file /var/log/clamav-scans/freshclam.log: Permission denied"
**Root cause**: freshclam runs as clamupdate user, can't write to root-owned directory
**Fix**: `sudo chown clamupdate:clamupdate /var/log/clamav-scans/freshclam.log`
**Also**: enabled clamav-freshclam.service so daemon runs continuously — scan script detects it and skips manual freshclam

### 12. clamav-freshclam.service was disabled
**Problem**: freshclam daemon was never enabled, all manual freshclam calls failed
**Root cause**: rpm-ostree install of clamav-freshclam doesn't auto-enable the service
**Fix**: `sudo systemctl enable --now clamav-freshclam.service`
**Verify**: `systemctl is-active clamav-freshclam.service`

### 13. Email alerts not sending — "No recipient address found"
**Problem**: clamav-alert.sh couldn't parse email from ~/.msmtprc
**Root cause**: Script runs as root (via sudo), so ~ resolves to /root/ not /home/lch/
**Fix**: Changed all ~/.msmtprc references to /home/lch/.msmtprc and added --file=/home/lch/.msmtprc to msmtp command

### 14. Scan log content duplicated
**Problem**: Same scan results appeared twice in log files
**Root cause**: Both clamdscan --log flag AND script's own log writing output to same file
**Fix**: Removed --log flag from clamdscan, let script handle all log writing

### 15. clamdscan "Scanned: 0 files"
**Problem**: Results box showed 0 files scanned on clean scans
**Root cause**: clamdscan with --infected only outputs infected files, grep for OK/FOUND returns 0
**Fix**: Use `find "${SCAN_DIRS[@]}" -type f | wc -l` to count files independently

### 16. System tray icon killed by pkill clamscan
**Problem**: pkill clamscan also kills the tray app (substring match)
**Root cause**: "clamscan" is a substring of process args
**Fix**: Added PR_SET_NAME to rename tray process to "bazzite-security-tray"

### 17. System tray icon dies when terminal closes
**Problem**: Launching tray with `python3 ... &` means SIGHUP kills it
**Fix**: `signal.signal(signal.SIGHUP, signal.SIG_IGN)` in tray app + launch with `nohup ... & disown`

### 18. LibClamAV cli_realpath warnings spam
**Problem**: Hundreds of "LibClamAV Warning: cli_realpath: Invalid arguments" in scan logs
**Root cause**: Known ClamAV 1.4.x bug with clamdscan --fdpass and symlinks
**Fix**: Filter with `grep -v "LibClamAV Warning: cli_realpath"` in output capture
