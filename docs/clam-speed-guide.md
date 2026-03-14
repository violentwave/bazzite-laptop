# Turbocharging ClamAV scans with clamd on Bazzite

**Switching from clamscan to clamd + clamdscan can cut your 75-minute scan to under 10 minutes.** The daemon loads virus signatures into memory once and scans files in parallel across multiple threads, eliminating the massive startup penalty and single-threaded bottleneck that make standalone clamscan so slow. On a gaming laptop with 16GB RAM and ZRAM, the best approach is running clamd on-demand via a systemd timer — start the daemon, scan, stop it — rather than leaving it resident 24/7. This guide covers the full setup on Bazzite 43 with rpm-ostree layered packages.

## Why clamd delivers 5–20× faster scans

Every time clamscan runs, it creates a new engine instance, reads ~110MB of signature files from disk, compiles them into ~1.1GB of in-memory pattern structures, scans files single-threaded, then throws everything away. Your 75-minute scan includes **30–90 seconds just loading signatures** before a single file is checked.

clamd flips this model. The daemon loads signatures once at startup and keeps them resident. The lightweight `clamdscan` client connects via Unix socket, passes file descriptors, and gets results back instantly. A benchmark of 10,000 files on ClamAV 1.0.7 showed clamscan taking **3 minutes 5 seconds** versus clamdscan at **9 seconds** — a 20× improvement. The Archivematica project documented a single 1MB file scanning in 2 seconds via clamdscan versus 1 minute 20 seconds with clamscan.

The second key advantage is **`--multiscan` mode**. clamd distributes directory contents across its thread pool (configurable via `MaxThreads`, default 10). On a modern multi-core gaming laptop, this parallelism is transformative. For your ~76,000 files across 9.2GB, realistic expectations with `clamdscan --fdpass --multiscan` are **5–15 minutes** — comfortably under your 20-minute goal and likely under 10 minutes on a fast NVMe drive.

## Installing and configuring clamd on Bazzite

Fedora splits ClamAV across several packages. The daemon lives in its own **`clamd`** package, separate from the base `clamav` package that provides clamscan and clamdscan. Install all three required packages:

```bash
rpm-ostree install clamav clamd clamav-update
systemctl reboot
```

After reboot, the configuration file lives at **`/etc/clamd.d/scan.conf`** — not `/etc/clamd.conf` as upstream documentation suggests. Fedora uses a template-based approach where the systemd service `clamd@scan` reads `/etc/clamd.d/scan.conf`. Both `/etc` and `/var` are writable and persistent on Bazzite, so your configuration survives reboots and image updates.

The essential edits to `/etc/clamd.d/scan.conf`:

```ini
# Comment out or delete the "Example" line near the top — clamd refuses to start with it present
# Example

# Uncomment the socket path (commented out by default)
LocalSocket /run/clamd.scan/clamd.sock

# Fedora runs clamd as the "clamscan" user (not "clamav" like Debian)
User clamscan

# Memory optimization: prevent 2× RAM spike during signature reloads
ConcurrentDatabaseReload no

# Clean exit on out-of-memory instead of crash
ExitOnOOM yes

# Thread count for --multiscan (default 10, tune to your CPU core count)
MaxThreads 8
```

Similarly, edit `/etc/freshclam.conf` — comment out the `Example` line, then add the critical line that tells freshclam to notify clamd after signature updates:

```ini
NotifyClamd /etc/clamd.d/scan.conf
```

One Fedora-specific requirement: **enable the SELinux boolean** for antivirus scanning, or clamd will get permission denials:

```bash
sudo setsebool -P antivirus_can_scan_system 1
```

## The on-demand daemon approach saves 1.1GB of RAM

clamd consumes approximately **1.0–1.3GB of resident memory** with current official signatures (~8.7 million signatures). With `ConcurrentDatabaseReload yes` (the default), this spikes to **~2.2GB during signature reloads** as clamd hot-swaps the old and new databases. Setting `ConcurrentDatabaseReload no` caps peak usage at ~1.1GB but blocks scanning for 30–60 seconds during reloads.

On a 16GB gaming laptop with ZRAM at vm.swappiness=180, dedicating ~7% of physical RAM to a permanently running clamd is feasible but wasteful during gaming sessions. The smarter approach: **start clamd only when scanning, then stop it**. clamd does not support true systemd socket activation, but a wrapper script with `--ping` and `--wait` (introduced in ClamAV 0.103.0) handles this cleanly.

Create the scan script at `/usr/local/bin/clamav-scan.sh`:

```bash
#!/bin/bash
SCAN_TARGETS="/home/lch /tmp"
LOG_FILE="/var/log/clamav/scheduled-scan.log"
QUARANTINE_DIR="/home/lch/.quarantine"

mkdir -p "$QUARANTINE_DIR"

# Start clamd (takes 20-60 seconds to load signatures)
systemctl start clamd@scan

# Wait up to 120 seconds for clamd to be ready (ping every 2 seconds)
clamdscan --ping 60:2 --wait
if [ $? -eq 21 ]; then
    echo "$(date): clamd failed to start within timeout" >> "$LOG_FILE"
    systemctl stop clamd@scan
    exit 2
fi

# Run the scan with parallel threads and fd-passing
clamdscan --fdpass --multiscan --infected \
    --move="$QUARANTINE_DIR" \
    --log="$LOG_FILE" \
    $SCAN_TARGETS
SCAN_EXIT=$?

# Stop clamd to reclaim ~1.1GB RAM
systemctl stop clamd@scan

exit $SCAN_EXIT
```

The corresponding systemd service and timer:

```ini
# /etc/systemd/system/clamav-scan.service
[Unit]
Description=Scheduled ClamAV scan

[Service]
Type=oneshot
ExecStart=/usr/local/bin/clamav-scan.sh
Nice=19
IOSchedulingClass=idle
```

```ini
# /etc/systemd/system/clamav-scan.timer
[Unit]
Description=Weekly ClamAV scan

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with `sudo systemctl enable --now clamav-scan.timer`. The daemon starts, scans in parallel, and shuts down — your gaming sessions never compete with clamd for memory.

## clamdscan command differences that matter

clamdscan accepts many of the same flags as clamscan but silently ignores several important ones. The critical difference: **`--exclude-dir` is ignored by clamdscan**. Exclusions must be configured server-side in `/etc/clamd.d/scan.conf` using `ExcludePath` with POSIX extended regex:

```ini
ExcludePath ^/proc/
ExcludePath ^/sys/
ExcludePath ^/dev/
ExcludePath ^/run/
```

The flags that do work with clamdscan include **`--move`** (quarantine), **`--infected`** (only print infected files), **`--log`** (write results to file), **`--multiscan`** (parallel scanning), and **`--fdpass`** (pass file descriptors over the Unix socket). Exit codes match clamscan: **0** for clean, **1** for infections found, **2** for errors, plus **21** for ping/wait timeout.

Always use `--fdpass` for local scanning. It passes open file descriptors through the Unix socket via SCM_RIGHTS, which is faster than streaming file contents and solves permission mismatches between your user and the `clamscan` daemon user. Without `--fdpass`, clamdscan would need to stream entire file contents over the socket, or clamd would need read access to all your files.

## On-access scanning is a non-starter for gaming

clamonacc uses the Linux fanotify kernel interface to intercept every file open and read event. It has **well-documented, severe performance problems on active systems**. A GitHub issue against ClamAV states bluntly: "clamonacc is impractical to use on more active systems. With on-access prevention it may even DoS a system quickly." The tool has no client-side caching, so it re-scans files on every access. Gaming involves massive I/O — loading textures, shader caches, Wine/Proton prefixes with thousands of files — and clamonacc would intercept all of it, causing stuttering and frame drops.

Even in notify-only mode (no blocking), the overhead of sending every file-open event to clamd for scanning creates CPU spikes and I/O contention. Users with Ryzen 3900x systems reported significant problems. **Skip clamonacc entirely** on a gaming system. Scheduled scans via the systemd timer approach above provide good security coverage without runtime cost.

Bazzite's immutable root filesystem actually reduces the attack surface that on-access scanning would protect — `/usr`, `/bin`, and system directories can't be modified at runtime. The mutable paths that matter (`/home`, `/tmp`, `/var`) are well served by periodic scheduled scans.

## How freshclam keeps clamd's signatures current

freshclam and clamd interact through two complementary mechanisms. The **`NotifyClamd`** directive in `freshclam.conf` tells freshclam to send a `RELOAD` command to clamd's socket immediately after downloading new signatures. This must be explicitly configured — it is disabled by default. As a fallback, clamd's **`SelfCheck`** setting (default: 600 seconds) periodically checks whether signature files have changed on disk and triggers an automatic reload if they have.

For the on-demand approach, this interaction is mostly irrelevant — clamd loads the latest signatures from disk each time it starts, so it always picks up whatever freshclam has downloaded. Keep `clamav-freshclam.service` enabled to update signatures automatically (it runs as a lightweight daemon checking for updates periodically), and clamd will always have fresh signatures whenever it starts for a scan.

## Conclusion

The path from 75-minute clamscan runs to sub-10-minute scans requires exactly three changes: install the `clamd` package, configure `/etc/clamd.d/scan.conf` with the socket and thread settings, and switch your scan command to `clamdscan --fdpass --multiscan`. The on-demand systemd approach — starting clamd before scans and stopping it afterward — is the right architecture for a gaming laptop, avoiding the permanent **~1.1GB memory cost** while still capturing the full speed benefit of daemon-mode scanning. The `--ping` and `--wait` flags make this pattern reliable and production-ready. Skip clamonacc entirely; scheduled scans of `/home` and `/tmp` provide strong coverage for a desktop system with an immutable root filesystem.