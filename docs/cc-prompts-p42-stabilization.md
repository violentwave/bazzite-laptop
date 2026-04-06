# P42 — Stabilization & Verification Pass
## CC Prompts 86–92

**Context:** P19–P41 were executed (P24–P40 via OpenCode, P41 via CC). The project
docs (AGENT.md, CHANGELOG.md, USER-GUIDE.md) are frozen at P18 state (48 tools,
15 timers, ~1,611 tests). Actual state per memory: 82 MCP tools (dynamic), 22 timers,
~2,071 tests, 23 LanceDB tables, commit `debc0a3`.

OpenCode quality gap precedent (P14–P15) means P24–P40 modules likely have YAML
registrations not wired into dispatch, indentation bugs, or broken imports.

**Goal:** Zero failing tests, full doc reconciliation, verified tool wiring, clean git.

---

## cc-prompt-86 — Health Check & Full Inventory

```
/feature-dev

## Task: P42 Health Check & Full Inventory

Read HANDOFF.md first.

Then run a comprehensive health check and produce an inventory report. Do these in order:

1. **Git status**: `git status`, `git log --oneline -5`
2. **Test suite**: `source .venv/bin/activate && python -m pytest tests/ -v --tb=short 2>&1 | tail -80`
3. **Lint**: `ruff check ai/ tests/ 2>&1 | tail -30`
4. **Tool inventory**:
   - Count entries in `configs/mcp-bridge-allowlist.yaml`: `grep -c '^  [a-z]' configs/mcp-bridge-allowlist.yaml`
   - Count dispatch handlers in `ai/mcp_bridge/tools.py`: `grep -c 'def _handle_' ai/mcp_bridge/tools.py`
   - Count `@mcp.tool` decorators in `ai/mcp_bridge/server.py`: `grep -c '@mcp.tool' ai/mcp_bridge/server.py`
5. **Timer inventory**: `ls systemd/*.timer | wc -l` and `systemctl --user list-timers --all 2>/dev/null | grep bazzite`
6. **LanceDB tables**: `python -c "import lancedb; db = lancedb.connect('$HOME/security/vector-db'); print(sorted(db.table_names()))"`
7. **New modules check** — verify these P24–P41 files exist and import cleanly:
   ```bash
   for mod in ai.metrics ai.alerts ai.learning.handoff_parser ai.system.depaudit \
              ai.intel_scraper ai.system.dep_scanner ai.system.test_analyzer \
              ai.system.perf_profiler ai.system.mcp_generator ai.system.ingest_pipeline; do
     python -c "import $mod" 2>&1 && echo "OK: $mod" || echo "FAIL: $mod"
   done
   ```
8. **Pre-commit hook**: `cat .git/hooks/pre-commit 2>/dev/null | head -5` — check if broken

Produce a summary table at the end:
| Metric | Expected (memory) | Actual |
|--------|-------------------|--------|
| Tests passing | ~2071 | ? |
| Tests failing | 0 | ? |
| Allowlist entries | 82 | ? |
| Dispatch handlers | ? | ? |
| Timer files | 22 | ? |
| LanceDB tables | 23 | ? |
| Ruff errors | 0 | ? |
| New module imports | all OK | ? |

**Do NOT**: Fix anything. This is read-only reconnaissance. Do not edit any files,
do not run deploy, do not modify tests. Just report what you find.

**Done when**: Summary table is complete with all actuals filled in. Paste the
full terminal output.
```

---

## cc-prompt-87 — OpenCode Quality Audit (Wiring Verification)

```
/feature-dev

## Task: P42 OpenCode Wiring Verification

Phases P24–P40 were implemented by OpenCode (non-Claude agent). Historical precedent
shows OpenCode frequently registers tools in the YAML allowlist but doesn't wire them
into the dispatch handler, or uses 5-space indentation instead of 4-space.

### Step 1: Allowlist vs Dispatch cross-reference

Extract every tool name from `configs/mcp-bridge-allowlist.yaml` and check that each
has a corresponding dispatch path in `ai/mcp_bridge/tools.py`:

```bash
# Get all tool names from allowlist
grep -E '^\s+[a-z]+\.[a-z_]+:' configs/mcp-bridge-allowlist.yaml | \
  sed 's/://;s/^ *//' | sort > /tmp/allowlist-tools.txt

# Get all handled tool names from dispatch
grep -oP '(?<=")\w+\.\w+(?=")' ai/mcp_bridge/tools.py | sort > /tmp/dispatch-tools.txt

# Find orphans (in allowlist but not dispatched)
comm -23 /tmp/allowlist-tools.txt /tmp/dispatch-tools.txt
```

Report any orphaned tools — these are tools registered but not callable.

### Step 2: Indentation check

```bash
# Find 5-space indentation (OpenCode signature bug)
grep -n '     [^ ]' ai/mcp_bridge/tools.py | head -20
grep -rn '     [^ ]' ai/system/*.py ai/alerts/*.py ai/learning/*.py ai/metrics.py 2>/dev/null | head -20
```

### Step 3: Import chain validation

For every new module added in P24–P41, verify it doesn't accidentally:
- Import `ai.router` from inside `ai/mcp_bridge/` (forbidden)
- Use `shell=True` anywhere
- Import from system Python 3.14 packages

```bash
grep -rn 'from ai.router\|import ai.router' ai/mcp_bridge/ 2>/dev/null
grep -rn 'shell=True' ai/ --include='*.py' 2>/dev/null
grep -rn 'python3.14\|/usr/lib/python3.14' ai/ 2>/dev/null
```

### Step 4: Annotation coverage

Check that all tools in the allowlist have MCP annotations (readOnly/destructive hints):

```bash
python -c "
import yaml
with open('configs/mcp-bridge-allowlist.yaml') as f:
    data = yaml.safe_load(f)
tools = data.get('tools', {})
missing = [t for t, v in tools.items() if not isinstance(v, dict) or 'annotations' not in str(v)]
print(f'Tools missing annotations: {len(missing)}')
for t in missing[:10]:
    print(f'  - {t}')
"
```

**Do NOT**: Fix anything yet. This is audit-only. Report all findings clearly so the
next prompt can address them surgically.

**Done when**: You've reported: (a) orphaned tools list, (b) indentation violations,
(c) forbidden import violations, (d) annotation gaps. Paste full output.
```

---

## cc-prompt-88 — Fix Failing Tests & Hanging Tests

```
/feature-dev

## Task: P42 Fix Test Failures

Based on the inventory from cc-prompt-86, fix all failing and hanging tests.

### Hanging tests (live API calls without mocks)

Common pattern: tests that call real APIs (Gemini embed, VT, OTX) hang or fail
when API keys aren't available or rate limits hit. Fix by adding proper mocks:

```python
@pytest.fixture(autouse=True)
def mock_api_calls(monkeypatch):
    """Prevent live API calls in tests."""
    # Pattern: monkeypatch the HTTP client, not the business logic
```

Known hanging test: `test_log_intel_anomalies` — find it, add a timeout or mock.

### LanceDB test failures

If tests fail on LanceDB operations, check:
- Table schema changes between P18 and P41 (new columns added?)
- Tests using hardcoded column counts or schema assertions
- Embedding dimension mismatches (768 vs 1024)

### Pre-commit ruff hook

If `scripts/pre-commit-hook.sh` or `.git/hooks/pre-commit` is broken:
- Check the shebang line
- Verify it calls `ruff check` on staged files only
- Fix and test with: `echo "test" | git stash && git stash pop`

### Rules
- Every test fix must use `unittest.mock` or `monkeypatch` — never make tests
  depend on live API availability
- Add `@pytest.mark.timeout(30)` to any test that could hang
- Run the full suite after fixes: `python -m pytest tests/ -v --tb=short`

**Do NOT**: Add new features. Do not modify production code in `ai/` unless a test
reveals a genuine bug. Do not delete tests — fix them or mark them with
`@pytest.mark.skip(reason="...")` with a clear reason.

**Done when**: `python -m pytest tests/ -v` shows 0 failures, 0 errors. No tests
skipped without a documented reason. Paste the final test summary line.
```

---

## cc-prompt-89 — Fix Orphaned Tool Wiring

```
/feature-dev

## Task: P42 Wire Orphaned Tools

Based on the audit from cc-prompt-87, wire any orphaned tools (in allowlist but
not dispatched) into `ai/mcp_bridge/tools.py`.

For each orphaned tool:

1. Read its definition in `configs/mcp-bridge-allowlist.yaml` to understand:
   - Source type (python, command, json_file, file_tail)
   - Arguments and types
   - Description

2. Add a dispatch handler in `ai/mcp_bridge/tools.py` following the existing pattern:
   ```python
   elif tool_name == "namespace.tool_name":
       return await _handle_tool_name(arguments)
   ```

3. Implement `_handle_tool_name()` following existing patterns for that source type.

4. Add MCP tool annotations in `_ANNOTATIONS` dict in `ai/mcp_bridge/server.py`
   if missing.

### Also fix:
- Any 5-space indentation → convert to 4-space
- Any forbidden `ai.router` imports in `ai/mcp_bridge/`

### Verify:
```bash
# After wiring, verify tool count matches
python -c "
from ai.mcp_bridge.server import mcp
# Count registered tools
print(f'Registered tools: {len(mcp._tools) if hasattr(mcp, \"_tools\") else \"unknown\"}')"

# Run MCP-related tests
python -m pytest tests/ -v -k "mcp" --tb=short
```

**Do NOT**: Add new tools not in the allowlist. Do not modify `ai/router.py`.
Do not change tool names or argument schemas. Do not touch `configs/litellm-config.yaml`.

**Done when**: `comm -23 /tmp/allowlist-tools.txt /tmp/dispatch-tools.txt` returns
empty (zero orphaned tools). All MCP tests pass. `ruff check ai/mcp_bridge/` clean.
```

---

## cc-prompt-90 — Docs Reconciliation (AGENT.md + CHANGELOG.md)

```
/feature-dev

## Task: P42 Docs Reconciliation

The project docs are frozen at P18 state. Update them to reflect reality (post-P41).

### 1. AGENT.md updates

Read the actual codebase to determine current counts, then update AGENT.md:

**Header & Architecture section:**
- Update tool count in ASCII diagram and all references (48 → actual)
- Update timer count (15 → actual)
- Update test count (~1611 → actual)
- Update "Last updated" date to 2026-04-06

**MCP Tools section:**
- Run: `python -c "import yaml; d=yaml.safe_load(open('configs/mcp-bridge-allowlist.yaml')); [print(t) for t in sorted(d.get('tools',{}).keys())]"`
- Add ALL new tools to the appropriate namespace tables (system.*, security.*, knowledge.*, etc.)
- Create new namespace sections if needed (e.g., if P24–P40 added new namespaces)
- Update the `health` endpoint tool count

**Systemd Timers section:**
- `ls systemd/*.timer` to get the full list
- Add any new timers with schedule and purpose

**Key Paths section:**
- Add new modules: `ai/metrics.py`, `ai/alerts/`, `ai/learning/`, `ai/intel_scraper.py`,
  `ai/system/dep_scanner.py`, `ai/system/test_analyzer.py`, `ai/system/perf_profiler.py`,
  `ai/system/mcp_generator.py`, `ai/system/ingest_pipeline.py`
- Update allowlist entry count
- Update test count

**Known Active Issues:**
- Keep existing issues that are still open
- Add: "17 Dependabot PRs open and unmerged"
- Add: "Hanging test: test_log_intel_anomalies" (if not fixed in prompt 88)
- Remove any issues that were resolved in P19–P41

### 2. CHANGELOG.md updates

Add entries for P19 through P41 at the TOP of the file (before Phase 18).
For each phase, document:
- Phase name and date (2026-04-03 through 2026-04-06)
- Key deliverables (new files, new tools, new timers)
- Tool/timer/test count changes

Use `git log --oneline --since="2026-04-03"` to reconstruct what changed.
Group by phase where possible. If phase boundaries are unclear, use a single
"Phases P19–P41" bulk entry.

### 3. USER-GUIDE.md updates

Update the MCP Tools Reference table (Section 13) to include all new tools.
Update test count in Section 13.
Update timer count references.

### Verification:
```bash
# Counts in AGENT.md should match reality
grep -c 'tool count\|tools:' docs/AGENT.md
ruff check docs/ 2>/dev/null || true
```

**Do NOT**: Change architecture decisions, modify Critical Rules, or alter the
provider chain configuration. Do not update `verified-deps.md` (that's a separate task).
Do not modify any Python code.

**Done when**: AGENT.md tool/timer/test counts match actual codebase. CHANGELOG.md
has entries for P19–P41. USER-GUIDE.md tool table is current. `git diff --stat`
shows only docs/ files changed.
```

---

## cc-prompt-91 — Dependabot PR Triage

```
/feature-dev

## Task: P42 Dependabot Triage

There are 17 open Dependabot PRs. Triage them.

### Step 1: List all open PRs

```bash
# If gh CLI is available:
gh pr list --state open --label dependencies 2>/dev/null || \
  echo "gh CLI not available — check GitHub web UI"
```

If `gh` isn't available, read `requirements-ai.txt` and cross-reference with
`docs/verified-deps.md` to identify which packages have known updates pending.

Known pending updates (from memory): cryptography, filelock, pillow, protobuf, requests.

### Step 2: Categorize each PR

For each PR, categorize as:
- **SAFE TO MERGE**: Patch version bumps (x.y.Z) for non-breaking deps
- **REVIEW NEEDED**: Minor version bumps (x.Y.0) — check changelog for breaking changes
- **DEFER**: Major version bumps (X.0.0) — needs testing
- **CLOSE**: Updates for packages we don't directly use (transitive deps)

### Step 3: Update verified-deps.md

For any packages we decide to update, note the new target version in
`docs/verified-deps.md` with today's date.

### Step 4: Merge safe PRs (if gh CLI available)

```bash
# Only merge SAFE TO MERGE category
gh pr merge <number> --squash
```

### Verify after merges:
```bash
uv pip install -r requirements-ai.txt
python -m pytest tests/ -v --tb=short -x  # Stop on first failure
```

**Do NOT**: Merge major version bumps without testing. Do not modify `requirements.txt`
(that's the system snapshot, not our install file). Do not add new packages.

**Done when**: All PRs are categorized. Safe PRs are merged (or documented for manual
merge). `verified-deps.md` is updated. Tests still pass after any merges.
```

---

## cc-prompt-92 — Final Verification & Code Review

```
/code-review

## Task: P42 Final Verification

Review all changes made in cc-prompts 87–91. Verify:

1. **Zero test failures**: `python -m pytest tests/ -v --tb=short`
2. **Clean lint**: `ruff check ai/ tests/`
3. **No security issues**: `bandit -r ai/ -c pyproject.toml`
4. **Git is clean**: `git status` — all changes committed
5. **Docs are consistent**:
   - Tool count in AGENT.md matches allowlist entries
   - Timer count in AGENT.md matches systemd/*.timer files
   - Test count in AGENT.md is within ±10 of actual
   - CHANGELOG.md has P19–P41 entries
6. **Services work**:
   ```bash
   curl -s http://127.0.0.1:8766/health | python -m json.tool
   curl -s http://127.0.0.1:8767/v1/models | python -m json.tool
   ```

If everything passes, commit with:
```bash
git add -A
git commit -m "P42: stabilization pass — fix test failures, wire orphaned tools, reconcile docs

- Fixed N failing tests (mocked live API calls)
- Wired N orphaned MCP tools from allowlist
- Fixed N indentation issues from OpenCode sessions
- Updated AGENT.md: tool/timer/test counts current
- Added CHANGELOG entries for P19–P41
- Updated USER-GUIDE.md tool reference
- Triaged N Dependabot PRs"
```

**Done when**: All 6 checks pass. Single commit on main. `git log --oneline -1`
shows the P42 commit.
```

---

## Execution Order

| # | Prompt | Prereqs | Est. Time |
|---|--------|---------|-----------|
| 86 | Health Check | none | 3 min |
| 87 | Wiring Audit | 86 results | 5 min |
| 88 | Fix Tests | 86 results | 15 min |
| 89 | Wire Orphans | 87 results | 10 min |
| 90 | Docs Reconcile | 86+87+88+89 done | 15 min |
| 91 | Dependabot | 88 done (tests pass) | 10 min |
| 92 | Final Review | all above | 5 min |

**Total estimate:** ~60 min of CC time.

**Workflow:** Paste each prompt into CC one at a time. Paste terminal output back
here after each. I'll analyze results and adjust subsequent prompts if needed.

---

## Notes on AGENT.md / CLAUDE.md Updates

The CLAUDE.md file (which CC reads at session start) references AGENT.md as the
source of truth. So AGENT.md is the primary target — prompt 90 handles this.

Key discrepancies to fix in AGENT.md:
- **Line 77**: "48 + health" → actual count
- **Line 79**: "48 entries" → actual count
- **Line 81**: "All 48 tools" → actual count
- **Line 204**: "Timers (15)" → actual count
- **Line 259**: "Tool dispatch handlers for all 48 tools" → actual count
- **Line 266**: "48 tool definitions" → actual count
- **Line 273**: "15 timers" → actual count
- **Line 274**: "~1611 pytest tests" → actual count
- **Line 305**: "~1611 tests" → actual count
- **Line 369**: "48 tools" → actual count

The CHANGELOG.md has ZERO entries for P19–P41 — that's 23 phases of work unrecorded.
Prompt 90 will reconstruct from git log.

Memory update needed after P42 completes to reflect new baseline counts.
