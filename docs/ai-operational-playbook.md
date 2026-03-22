# Bazzite AI Operational Playbook

This playbook is for humans and AI assistants (Perplexity, Claude, Newelle)
working on the **bazzite-laptop** project. It summarizes how to operate and
modify the system safely.

---

## 1. Core paths and locations

- Security dir (canonical root): `~/security/`
- Status JSON (tray + MCP read this): `~/security/.status`
- LanceDB root: `~/security/vector-db/`
  - Health: `health_records.lance`
  - Scans: `scan_records.lance`
  - Log intel: `security_logs.lance`
  - Threat intel: `threat_intel.lance`
- Ingest state file: `~/security/vector-db/.ingest-state.json`
- Health logs: `/var/log/system-health/`
  - Latest symlink: `/var/log/system-health/health-latest.log`
- ClamAV logs: `/var/log/clamav-scans/`
- Systemd units (system): `/etc/systemd/system/*.service`, `*.timer`
- Project root (code): `~/projects/bazzite-laptop/`

These locations are **contractual**. Do not move them without updating
scripts, `ai/config.py`, tray code, and docs together.

---

## 2. Safe day‑to‑day commands

From `~/projects/bazzite-laptop`:

- Show relevant timers and next runs:
  - `systemctl list-timers --all | grep -E "clamav|system-health|rag-embed"`
- Force a health snapshot:
  - `sudo /usr/local/bin/system-health-snapshot.sh --quiet`
- Run a ClamAV quick scan:
  - `sudo /usr/local/bin/clamav-scan.sh quick`
- Run a ClamAV deep scan:
  - `sudo /usr/local/bin/clamav-scan.sh deep`
- Re‑ingest logs into LanceDB:
  - `source .venv/bin/activate && python3 -m ai.log_intel --all && deactivate`

Check status JSON at any time:

- `cat ~/security/.status`

---

## 3. Systemd + SELinux rules

All system services/timers for this project:

- Live under `/etc/systemd/system/`
- Must be owned by `root:root`
- Must have SELinux type `systemd_unit_file_t`

### Installing or updating a unit from the repo

From project root:

```bash
# Example for system-health
sudo install -m 644 systemd/system-health.service /etc/systemd/system/system-health.service
sudo install -m 644 systemd/system-health.timer   /etc/systemd/system/system-health.timer

# Fix SELinux context
sudo restorecon -v /etc/systemd/system/system-health.service /etc/systemd/system/system-health.timer

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable --now system-health.timer
Apply the same pattern for:

clamav-quick.service / .timer

clamav-deep.service / .timer

clamav-healthcheck.service / .timer

rag-embed.service / .timer

Never “fix” issues by disabling SELinux; always correct ownership and labels.

4. Timers: quick diagnostics
To verify everything is healthy:

bash
systemctl list-timers --all --no-pager | grep -E "clamav|system-health|rag-embed"
If a timer shows - - - for NEXT/LAST:

Confirm the service exists and is readable:

bash
sudo systemctl cat system-health.service
Repair and reload:

bash
sudo chown root:root /etc/systemd/system/system-health.*
sudo restorecon -v /etc/systemd/system/system-health.*
sudo systemctl daemon-reload
sudo systemctl enable --now system-health.timer
Repeat for any other affected units.

5. LanceDB & ingest sanity checks
Check table row counts:

bash
source .venv/bin/activate
python3 -c "
import lancedb
db = lancedb.connect('/home/lch/security/vector-db')
for name in db.table_names():
    t = db.open_table(name)
    print(f'{name}: {t.count_rows()} rows')
"
deactivate
If health_records is unexpectedly tiny while there are many health logs in
/var/log/system-health/:

Inspect .ingest-state.json and ai/log_intel/ingest.py before deleting or
resetting anything.

Prefer targeted fixes (e.g. removing just last_health_file /
last_health_ingest) and document the steps in docs/pending-review.md.

6. Status JSON contract (~/security/.status)
This file is shared by:

clamav-scan.sh (security scan state)

system-health-snapshot.sh (health snapshot state)

Tray UI + MCP tools (read‑only consumers)

Key expectations:

JSON keys such as state, message, result, threat_count,
health_status, health_issues, etc., must be preserved.

Writes must remain atomic using the existing Python mkstemp/rename
pattern in the scripts.

File path must remain ~/security/.status unless all dependent code and
docs are updated together.

Do not introduce a second status file; extend this one instead.

7. Changelog and documentation rules
All non‑trivial changes (code, units, scripts, configs, behavior) must be
recorded by appending to docs/pending-review.md:

Date + short title

What changed (files, services, commands)

Why (bug, feature, hardening)

Follow‑ups or migration steps

Never rewrite or truncate pending-review.md.

Cross‑reference significant roadmap‑level changes in:

phases_3-5-overview.md

project-instructions-updated.md

8. AI collaborator expectations
Before editing code or system config, assistants should:

Read:

project-onboarding.md

project-instructions-updated.md

newelle-integration.md

Skim:

docs/pending-review.md (latest sessions)

This playbook

After making changes, assistants must:

Ensure tests or smoke checks run where applicable.

Append a new entry to docs/pending-review.md.

Prefer small, reversible changes and avoid “big bang” refactors.

