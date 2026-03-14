# Services Optimization — COMPLETED
## All services below were disabled on 2026-03-14

> **NOTE**: This document is now a REFERENCE showing what was disabled and why. All services listed below have been successfully disabled.

### Services Safe to Disable (performance + security)
These are enabled but not needed on a gaming laptop without VMs or modems:

| Service | Why disable | Command |
|---------|-------------|---------|
| avahi-daemon | mDNS/network broadcasting — attack surface, not needed | `sudo systemctl disable --now avahi-daemon.service avahi-daemon.socket` |
| ModemManager | Cellular modem management — no modem present | `sudo systemctl disable --now ModemManager.service` |
| virtqemud + all virt* | Libvirt/VM services — ~30 sockets, not using VMs | `for s in $(systemctl list-unit-files 'virt*' --state=enabled --no-pager \| awk '{print $1}'); do sudo systemctl disable --now "$s"; done` |
| vboxservice | VirtualBox guest additions — not a VM guest | `sudo systemctl disable --now vboxservice.service` |
| vmtoolsd + vgauthd | VMware guest tools — not a VM guest | `sudo systemctl disable --now vmtoolsd.service vgauthd.service` |
| sssd + sssd-kcm | System security services daemon — enterprise auth, not needed | `sudo systemctl disable --now sssd.service sssd-kcm.socket` |
| iscsi* | iSCSI network storage — not using | `sudo systemctl disable --now iscsi-onboot.service iscsi-starter.service iscsid.socket iscsiuio.socket` |
| mdmonitor | Software RAID monitoring — no RAID | `sudo systemctl disable --now mdmonitor.service` |
| raid-check.timer | RAID health check — no RAID | `sudo systemctl disable --now raid-check.timer` |
| qemu-guest-agent | QEMU guest service — not a VM guest | `sudo systemctl disable --now qemu-guest-agent.service` |

**Estimated impact**: Fewer background processes, reduced RAM usage (~50-100MB), smaller attack surface, faster boot.

### Services to KEEP (important for this system)
| Service | Why keep |
|---------|----------|
| supergfxd | GPU switching — critical |
| nvidia-powerd + nvidia-* | GPU power management |
| thermald | Thermal management — important for laptop |
| tuned + tuned-ppd | Performance profiles |
| firewalld | Firewall — critical |
| systemd-resolved | DNS-over-TLS |
| smartd | Disk health monitoring (already pre-installed!) |
| lm_sensors | Temperature monitoring |
| bluetooth | Currently blocked by firewall, keep for future use |
| NetworkManager | Network management — critical |
| fstrim.timer | SSD maintenance |

### External SSD Optimization (minor)
Current mount: `relatime` — consider adding `noatime` via fstab or udisks2 rule to reduce unnecessary writes.

### Browser Note
Using Brave (Flatpak) — already has built-in ad blocking, HTTPS upgrading, and fingerprinting protection. arkenfox user.js hardening from the guide applies to Firefox only and is NOT needed if sticking with Brave.
