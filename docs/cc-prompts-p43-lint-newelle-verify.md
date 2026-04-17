# P43 — Lint Cleanup, Newelle Sync & Operational Verification
## CC Prompts 93–100

> Historical artifact: this prompt pack refers to a legacy client path that is no longer active runtime guidance.

**Starting state:** P42 complete. 1,872 tests (0 failures). 82 MCP tools, 22 timers.
30 ruff errors remaining. Commit `cf9e7db`.

**Goal:** Clean lint to zero, sync all legacy-client docs with the 82-tool reality,
verify the 30 tools wired in P42 actually work end-to-end, and fix remaining hygiene
items (pre-commit hook, architecture diagram).

**Design principle:** No new features. This is about making the existing 82 tools
fully discoverable and operational through the legacy client path, and cleaning up the last
technical debt before the next feature phase.

---

## cc-prompt-93 — Ruff Lint Zero

```
/feature-dev

## Task: P43 Ruff Lint Cleanup — Target Zero

There are 30 ruff errors remaining. Fix all of them.

```bash
ruff check ai/ tests/ 2>&1
```

Common patterns from OpenCode sessions:
- Unused imports (F401)
- Undefined names (F821) — usually from lazy imports not wired correctly
- Redefined unused variables (F841)
- Star imports (F403/F405)
- Missing type annotations on arguments that ruff now requires

### Rules:
- Fix each error in-place. If an unused import is genuinely needed (side effect),
  add `# noqa: F401` with a comment explaining why
- If an undefined name is a genuine bug (function called but never defined),
  add a stub that raises NotImplementedError with a TODO comment
- Do NOT add new functionality — only fix lint

### Verify:
```bash
ruff check ai/ tests/
# Expected: 0 errors
python -m pytest tests/ -x --tb=short -q
# Expected: 1872 passed
```

**Do NOT**: Refactor code. Do not rename functions. Do not change logic. Do not
touch `configs/` or `docs/`. Only fix lint violations.

**Done when**: `ruff check ai/ tests/` returns zero errors. All tests still pass.
```

---

## cc-prompt-94 — Pre-commit Hook Fix

```
/feature-dev

## Task: P43 Fix Pre-commit Ruff Hook

Check if the pre-commit hook is working:

```bash
cat .git/hooks/pre-commit 2>/dev/null
ls -la .git/hooks/pre-commit 2>/dev/null
```

If broken or missing, reinstall from `scripts/pre-commit-hook.sh`:

```bash
cat scripts/pre-commit-hook.sh
```

The hook should:
1. Run `ruff check` on staged `.py` files only (not the entire repo)
2. Exit non-zero if any errors found
3. Be executable (`chmod +x`)

If `scripts/pre-commit-hook.sh` exists and is correct:
```bash
cp scripts/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

If it doesn't exist or is broken, create/fix it:
```bash
#!/usr/bin/env bash
set -euo pipefail

STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
if [ -n "$STAGED" ]; then
    source .venv/bin/activate 2>/dev/null || true
    echo "$STAGED" | xargs ruff check --force-exclude
fi
```

### Verify:
```bash
# Test the hook with a dummy change
echo "# test" >> ai/__init__.py
git add ai/__init__.py
git commit --dry-run 2>&1 | head -5
git checkout -- ai/__init__.py
```

**Do NOT**: Modify any Python source files. Do not change ruff configuration.
Do not add additional pre-commit checks (bandit, mypy, etc. — scope creep).

**Done when**: `.git/hooks/pre-commit` exists, is executable, and runs `ruff check`
on staged Python files.
```

---

## cc-prompt-95 — Newelle System Prompt Sync

```
/feature-dev

## Task: P43 Newelle System Prompt — Sync with 82 Tools

The Newelle system prompt at `docs/newelle-system-prompt.md` references 48 tools.
The system now has 82 tools. Newelle can't effectively use tools it doesn't know about.

### Step 1: Get the current tool manifest

```bash
# Get actual tool list from allowlist
python -c "
import yaml
with open('configs/mcp-bridge-allowlist.yaml') as f:
    data = yaml.safe_load(f)
for name in sorted(data.get('tools', {}).keys()):
    tool = data['tools'][name]
    desc = tool.get('description', 'No description')[:60]
    print(f'{name}: {desc}')
"
```

### Step 2: Read current system prompt

```bash
cat docs/newelle-system-prompt.md
```

### Step 3: Update the system prompt

Update the **tool routing table** in `docs/newelle-system-prompt.md` to include
ALL 82 tools, organized by namespace. The routing table is the compact reference
Newelle uses to pick the right tool.

For each new namespace that didn't exist before (check for these):
- `intel.*` — threat intelligence scraping tools
- `memory.*` — memory/session search
- `collab.*` — collaboration tools
- `workflow.*` — workflow automation tools
- `code.impact_analysis`, `code.dependency_graph`, `code.find_callers`,
  `code.suggest_tests`, `code.complexity_report`, `code.class_hierarchy`
- `system.alert_history`, `system.rules`, `system.dep_audit`
- `system.budget_status`, `system.metrics_summary`, `system.provider_status`,
  `system.weekly_insights`
- `system.create_tool`, `system.list_dynamic_tools`
- `knowledge.task_patterns`, `knowledge.session_history`
- `agents.timer_health` (if present)

Add a routing entry for each new tool. Follow the existing compact format:
```
| "search my session history" | memory.search |
| "what tools are available" | system.list_dynamic_tools |
```

### Step 4: Update tool count references

Replace all instances of "48" with "82" in the system prompt.
Update the MCP endpoint reference if needed (should still be `localhost:8766/mcp`).

### Verify:
```bash
# Check word count is reasonable (should be under 4000 words for context window)
wc -w docs/newelle-system-prompt.md
# Check no broken markdown
python -c "
with open('docs/newelle-system-prompt.md') as f:
    content = f.read()
print(f'Length: {len(content)} chars')
print(f'Tool mentions: {content.count(\".\")}')" 
```

**Do NOT**: Change the system prompt structure (sections, rules, anti-loop guards).
Do not modify the NATIVE FILE TOOLS section. Do not change the model switching guidance.
Only add new tools to the routing table and update counts.

**Done when**: `docs/newelle-system-prompt.md` references all 82 tools in the routing
table. Tool count is updated. File is valid markdown.
```

---

## cc-prompt-96 — Newelle Skills Bundles Sync

```
/feature-dev

## Task: P43 Newelle Skills Bundles — Add Missing Namespaces

The skill bundles in `docs/newelle-skills/` teach Newelle how to use tools in
each namespace. Currently there are 5 bundles:

```bash
ls docs/newelle-skills/
```

These were written for the original 48 tools. If new namespaces were added
(intel.*, memory.*, collab.*, workflow.*, or significant new code.* tools),
they need skill bundles.

### Step 1: Inventory existing bundles vs namespaces

```bash
# What bundles exist
ls docs/newelle-skills/

# What namespaces exist in the allowlist
python -c "
import yaml
with open('configs/mcp-bridge-allowlist.yaml') as f:
    data = yaml.safe_load(f)
namespaces = set()
for name in data.get('tools', {}).keys():
    ns = name.split('.')[0]
    namespaces.add(ns)
print('Namespaces:', sorted(namespaces))
"
```

### Step 2: Create missing skill bundles

For each namespace that doesn't have a skill bundle, create one in
`docs/newelle-skills/` following the existing pattern. Each bundle should include:
- Namespace description (1-2 sentences)
- Tool reference table (tool name, args, what it returns)
- Example natural language → tool mappings
- Common workflows combining tools in this namespace

Match the style and length of existing bundles (check `docs/newelle-skills/bazzite-system.md`
as the reference).

### Step 3: Update existing bundles

For bundles that already exist but are missing new tools (e.g., if `bazzite-system.md`
doesn't include `system.budget_status` or `system.metrics_summary`), add the missing
tools to the reference table.

### Verify:
```bash
# Every namespace should have a bundle
python -c "
import yaml, os
with open('configs/mcp-bridge-allowlist.yaml') as f:
    data = yaml.safe_load(f)
namespaces = set(n.split('.')[0] for n in data.get('tools', {}).keys())
bundles = set(f.replace('.md','').replace('bazzite-','') for f in os.listdir('docs/newelle-skills/') if f.endswith('.md'))
print('Namespaces:', sorted(namespaces))
print('Bundles:', sorted(bundles))
missing = namespaces - bundles - {'health'}  # health is built-in
if missing:
    print(f'MISSING bundles: {missing}')
else:
    print('All namespaces covered')
"
```

**Do NOT**: Modify the Newelle system prompt (that's prompt 95). Do not change
tool implementations. Do not add tools to the allowlist.

**Done when**: Every tool namespace has a corresponding skill bundle. Existing
bundles include all current tools. No namespace is undocumented.
```

---

## cc-prompt-97 — Morning Briefing Prompt Update

```
/feature-dev

## Task: P43 Morning Briefing — Expand to Use New Tools

The morning briefing at `docs/morning-briefing-prompt.md` calls 7 tools.
With 82 tools now available, the briefing should cover more ground.

### Current 7 tools:
1. security.status
2. security.last_scan
3. security.health_snapshot
4. security.threat_summary
5. logs.anomalies
6. system.release_watch
7. system.fedora_updates

### Add these (if they exist and are relevant to a daily briefing):
- `system.budget_status` — token budget remaining for the day
- `system.metrics_summary` — system metrics overview
- `system.provider_status` — LLM provider health
- `agents.timer_health` — are all timers firing correctly?
- `system.dep_audit` — any new dependency vulnerabilities?
- `system.pipeline_status` — log pipeline health (already existed but not in briefing)
- `system.cache_stats` — cache hit rates

### Rules:
- Keep the batch call pattern (all tools called in one batch, not sequentially)
- Cap at 12 tools max — Newelle has a 7-call anti-loop limit, so the briefing
  prompt must explicitly say "call ALL of these in a single batch"
- Add new sections to the output format: BUDGET, PROVIDERS, DEPENDENCIES
- Keep the "If everything is clean, say so in one sentence" rule

### Verify:
```bash
# Check the prompt is valid
cat docs/morning-briefing-prompt.md
wc -w docs/morning-briefing-prompt.md
```

**Do NOT**: Change the existing 7 tool calls — only add new ones. Do not modify
the output format for existing sections. Do not exceed 12 total tool calls.

**Done when**: `docs/morning-briefing-prompt.md` calls up to 12 tools with the
additional sections. Format is clean markdown.
```

---

## cc-prompt-98 — End-to-End Tool Smoke Test

```
/feature-dev

## Task: P43 Smoke Test — Verify 30 Newly-Wired Tools

In P42, 30 orphaned tools were wired into dispatch. Verify they actually work
by calling each one through the MCP bridge's Python dispatch path.

### Create a test script:

Create `scripts/smoke-test-tools.py` that:

1. Imports the tool dispatch function from `ai/mcp_bridge/tools.py`
2. Calls each of the 30 tools wired in P42 with minimal valid arguments
3. Checks that each returns a non-error response (not a traceback, not "unknown tool")
4. Reports pass/fail for each tool

```python
#!/usr/bin/env python3
"""Smoke test for P42-wired tools."""
import asyncio
import json
import sys

# Tools wired in P42 (from the cc-prompt-89 summary)
NEW_TOOLS = [
    ("system.alert_history", {}),
    ("system.rules", {}),
    ("system.dep_audit", {}),
    ("system.budget_status", {}),
    ("system.metrics_summary", {}),
    ("system.provider_status", {}),
    ("system.weekly_insights", {}),
    ("system.create_tool", {"name": "test_tool", "description": "test"}),
    ("system.list_dynamic_tools", {}),
    ("knowledge.task_patterns", {"query": "test"}),
    ("knowledge.session_history", {}),
    ("memory.search", {"query": "test"}),
    ("code.impact_analysis", {"file": "ai/config.py"}),
    ("code.dependency_graph", {}),
    ("code.find_callers", {"function": "route_query"}),
    ("code.suggest_tests", {"file": "ai/config.py"}),
    ("code.complexity_report", {}),
    ("code.class_hierarchy", {}),
    # Add remaining tools from the P42 wiring list...
]

async def smoke_test():
    from ai.mcp_bridge.tools import execute_tool
    
    passed = 0
    failed = 0
    errors = []
    
    for tool_name, args in NEW_TOOLS:
        try:
            result = await execute_tool(tool_name, args)
            data = json.loads(result) if isinstance(result, str) else result
            if isinstance(data, dict) and "error" in data:
                errors.append(f"FAIL: {tool_name} → {data['error'][:80]}")
                failed += 1
            else:
                print(f"  OK: {tool_name}")
                passed += 1
        except Exception as e:
            errors.append(f"FAIL: {tool_name} → {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Passed: {passed}/{len(NEW_TOOLS)}")
    print(f"Failed: {failed}/{len(NEW_TOOLS)}")
    for err in errors:
        print(f"  {err}")
    
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    asyncio.run(smoke_test())
```

### Complete the NEW_TOOLS list

Read `ai/mcp_bridge/tools.py` to find all 30 tools wired in P42 and add them
to the list above. Use the dispatch handler to determine what arguments each
tool expects.

### Run it:
```bash
source .venv/bin/activate
python scripts/smoke-test-tools.py
```

### For tools that fail:
- If it's a missing module → note it (don't fix — that's a separate prompt)
- If it's a bad argument → fix the test script's args
- If it's a genuine dispatch bug → fix the dispatch in `ai/mcp_bridge/tools.py`

**Do NOT**: Fix bugs in the tool implementations themselves (e.g., if a tool's
business logic crashes). Only fix dispatch wiring issues. The goal is to verify
the wiring layer, not the business logic.

**Done when**: Smoke test script exists at `scripts/smoke-test-tools.py`. It reports
pass/fail for all 30 tools. If any fail, document the specific error for each.
```

---

## cc-prompt-99 — Architecture Diagram Update

```
/feature-dev

## Task: P43 Architecture Diagram — Update to Current State

The architecture diagram at `docs/architecture.mmd` (Mermaid) shows P7 numbers
(43 tools, 12 timers). Update it to reflect current state.

### Read current diagram:
```bash
cat docs/architecture.mmd
```

### Update these elements:
- MCP Bridge box: "48 tools" → "82 tools"
- Timer count in System Layer
- Add new module boxes if significant new subsystems were added (intel_scraper,
  dep_scanner, test_analyzer, perf_profiler, mcp_generator, alerts)
- Update subtitle/header with current phase number

### Re-render SVG:
```bash
# If mmdc (mermaid-cli) is available:
npx -y @mermaid-js/mermaid-cli mmdc -i docs/architecture.mmd -o docs/architecture.svg -b transparent 2>/dev/null
# If not, just update the .mmd and note SVG needs manual re-render
```

**Do NOT**: Restructure the diagram layout. Do not add Docker, Qdrant, or any
deferred architecture. Only update counts and add boxes for modules that exist.

**Done when**: `docs/architecture.mmd` has correct tool/timer counts. SVG is
regenerated (or noted as needing manual re-render).
```

---

## cc-prompt-100 — Final Commit & Code Review

```
/code-review

## Task: P43 Final Verification & Commit

Review all P43 changes:

### Verify checklist:
1. `ruff check ai/ tests/` → 0 errors
2. `python -m pytest tests/ -v --tb=short -q` → 1872+ passed, 0 failed
3. `.git/hooks/pre-commit` exists and is executable
4. `docs/newelle-system-prompt.md` references 82 tools
5. `docs/newelle-skills/` covers all namespaces
6. `docs/morning-briefing-prompt.md` calls up to 12 tools
7. `scripts/smoke-test-tools.py` exists and documents tool health
8. `docs/architecture.mmd` has current counts
9. `git status` — only expected files changed

### Deploy check (if services are running):
```bash
bash scripts/deploy-services.sh 2>/dev/null || true
systemctl --user restart bazzite-llm-proxy.service bazzite-mcp-bridge.service 2>/dev/null || true
curl -s http://127.0.0.1:8766/health | python -m json.tool 2>/dev/null || echo "Services not running (expected in sandbox)"
```

### Commit:
```bash
git add -A
git commit -m "P43: lint zero, Newelle sync, operational verification

- Ruff errors: 30 → 0
- Pre-commit hook: fixed/reinstalled
- Newelle system prompt: synced with 82 tools
- Newelle skills: new bundles for missing namespaces
- Morning briefing: expanded to ~12 tools
- Smoke test: scripts/smoke-test-tools.py for 30 P42-wired tools
- Architecture diagram: updated counts"
```

### Summary report:
Print a final status table:
| Metric | Before P43 | After P43 |
|--------|-----------|-----------|
| Ruff errors | 30 | 0 |
| Tests | 1872 | ? |
| Pre-commit hook | broken/unclear | working |
| Newelle tools documented | 48 | 82 |
| Skill bundles | 5 | ? |
| Morning briefing tools | 7 | ? |

**Done when**: Single commit on main. All checklist items pass.
```

---

## Execution Order

| # | Prompt | Prereqs | Est. Time |
|---|--------|---------|-----------|
| 93 | Ruff Lint Zero | none | 10 min |
| 94 | Pre-commit Hook | 93 (lint clean) | 3 min |
| 95 | Newelle System Prompt | none | 15 min |
| 96 | Newelle Skills Bundles | 95 (know the tools) | 10 min |
| 97 | Morning Briefing | 95 (know the tools) | 5 min |
| 98 | Smoke Test | none | 15 min |
| 99 | Architecture Diagram | none | 5 min |
| 100 | Final Commit | all above | 5 min |

**Total estimate:** ~70 min of CC time.

Prompts 93–94 can run independently from 95–97. Prompt 98 can run anytime.
Prompt 100 must be last.

---

## What Comes After P43

Once P43 is done, the system will be:
- **Lint clean** (0 ruff errors, pre-commit enforced)
- **Fully documented** (82 tools in all Newelle docs, current architecture diagram)
- **Operationally verified** (30 newly-wired tools smoke tested)
- **Newelle-ready** (system prompt + skills + briefing all synced)

At that point, the next phase (P44+) can focus on **new capabilities**:
- Input validation / AIDefence layer (P19 from original roadmap — verify if done)
- Semantic caching (P23 from original roadmap — verify if done)
- Token budget enforcement (P23 from original roadmap)
- Code pattern knowledge base (P21 — curated patterns for multi-language RAG)
- Reflection loops for task learning improvement
- Or whatever direction you want to take it
