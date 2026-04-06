# P29–P33 OpenCode Autonomous Playbook
<!-- Agent: OpenCode (z.ai GLM models) | TUI mode only -->
<!-- Starting state: P28 complete, ~1650 tests, 57 MCP tools, 19 timers, 13 LanceDB tables -->
<!-- OC prompt numbering: OC-31 through OC-60 -->
<!-- Implementation order: Prereq (tool filtering) → P32 → P29 → P31 → P30 → P33 -->

---

## How to Use This Document

Same execution pattern as the P24–P28 playbook. Paste numbered OC-XX prompts
into OpenCode TUI one at a time, review output, then proceed.

**Implementation order is NOT numerical by phase name.** Research confirms the
optimal sequence is: **P32 → P29 → P31 → P30 → P33**, because testing intelligence
gives immediate payoff, the code graph is foundational for everything after it,
and the plugin factory should be last since it expands the attack surface.

A **prerequisite step** (MCP tool filtering) must be completed before any new
tools are added. At 57 tools heading toward 75+, LLM tool selection accuracy
degrades significantly without server-side filtering.

**New dependencies to install before starting (user does this manually):**
```bash
cd ~/projects/bazzite-laptop && source .venv/bin/activate
uv pip install grimp==3.14 radon==6.0.1 pydriller==2.9 \
  pytest-testmon==2.2.0 pytest-xdist==3.8.0 pytest-timeout \
  pytest-rerunfailures mutmut==3.5.0 hypothesis \
  watchdog pluggy filelock
```

**Same OpenCode constraints as P24–P28 playbook:**
- 5-space indentation bug → verify with `ruff check` after every edit
- Use `.venv/bin/python`, never system Python 3.14
- TUI only, no /feature-dev or /code-review plugins
- Manual `/save-handoff` after each phase

---

## Target State After P33

| Metric | P28 (start) | P33 (target) |
|--------|-------------|--------------|
| MCP tools | 57 | ~68 (+11) |
| Timers | 19 | 20 (+1: code-index.timer) |
| LanceDB tables | 13 | 22 (+9) |
| Tests | ~1650 | ~1800+ |
| New modules | — | ai/code_intel/, ai/testing/, ai/collab/, ai/workflows/, ai/tools/ |

---

## Prerequisite — MCP Tool Filtering Middleware

**Goal:** Prevent tool selection degradation as tool count grows past 60. Add a
server-side filter that exposes only 10–15 relevant tools per request based on
namespace tags and semantic matching.

### OC-31 — Pre-flight and design review

```
Read HANDOFF.md in the project root. Run pre-flight verification:

git status && git log --oneline -3
source .venv/bin/activate
python -m pytest tests/ -x -q 2>&1 | tail -5
ruff check ai/ tests/ 2>&1 | tail -3
grep -c "name:" configs/mcp-bridge-allowlist.yaml

Then read these files to understand the current tool dispatch:
- ai/mcp_bridge/server.py — how tools are registered and dispatched
- ai/mcp_bridge/tools.py — the tool dispatch handlers
- configs/mcp-bridge-allowlist.yaml — all tool definitions

Report: Current tool count, how tools are exposed to clients,
and whether there's any existing namespace filtering.

Do NOT modify any files.
```

### OC-32 — Create ai/mcp_bridge/tool_filter.py

```
Create ai/mcp_bridge/tool_filter.py that implements server-side tool filtering.

1. Define TOOL_GROUPS — a dict mapping group names to namespace prefixes:
   {
       "security": ["security.", "agents.security"],
       "system": ["system.", "agents.timer", "agents.performance"],
       "knowledge": ["knowledge.", "code.", "agents.knowledge", "agents.code"],
       "logs": ["logs."],
       "gaming": ["gaming."],
       "memory": ["memory."],
       "metrics": ["system.metrics", "system.provider", "system.budget",
                    "system.weekly", "system.pipeline"],
       "all": []  # empty = no filtering, expose everything
   }

2. Class ToolFilter:
   - __init__(self, allowlist_path="configs/mcp-bridge-allowlist.yaml"):
     Loads the allowlist, builds a name→tool mapping, builds a LanceDB table
     "tool_metadata" with tool name, description, namespace, tags, and
     a vector embedding of the description for semantic search.
   - filter_by_namespace(self, namespaces: list[str]) -> list[str]:
     Returns tool names matching any of the given namespace prefixes.
   - filter_by_query(self, query: str, top_k: int = 15) -> list[str]:
     Embeds the query, searches tool_metadata by cosine similarity,
     returns top_k most relevant tool names.
   - get_context_tools(self, user_message: str, task_type: str = None) -> list[str]:
     Combines: always include "health" + core system tools (disk, memory, uptime),
     then add namespace-matched tools based on keywords in user_message,
     then fill remaining slots (up to 15 total) via semantic search.
     Returns list of tool names to expose for this request.
   - get_all_tools(self) -> list[str]:
     Returns all tool names (bypass filtering, for admin/debug use).

3. Module-level singleton: get_filter() -> ToolFilter

CRITICAL RULES:
- Do NOT import ai.router
- Use the existing embedding function from ai/rag/embedder.py for tool vectors
- Handle missing LanceDB table gracefully (create on first call)
- The filter is advisory — tools are still registered on the server, but the
  filter determines which ones are included in tool schemas sent to clients
- Keep a CORE_TOOLS set that is ALWAYS included: ["health", "system.disk_usage",
  "system.memory_usage", "system.service_status", "system.mcp_manifest"]

Do NOT modify any other files. Only create ai/mcp_bridge/tool_filter.py.
Done when: ruff check passes on the new file.
```

### OC-33 — Tests, integrate into server, commit

```
1. Create tests/test_tool_filter.py:
   - test_filter_by_namespace: Filter "security" → returns only security.* tools
   - test_filter_by_query: Query "check CVE" → returns security tools ranked high
   - test_core_tools_always_included: Any filter result includes CORE_TOOLS
   - test_max_tools_limit: get_context_tools never returns more than 15 tools
   - test_get_all_tools: Returns complete list without filtering
   - test_empty_query: Empty string → returns core tools only

2. In ai/mcp_bridge/server.py — add a MINIMAL integration point:
   - Import get_filter from ai.mcp_bridge.tool_filter
   - Add a utility method that other handlers can call to get filtered tool list
   - Do NOT restructure the server. The filter is available but not enforced
     on every request yet — that comes later as clients adopt it.
   - Add a note in the server docstring about the filter capability

3. Run full test suite:
   python -m pytest tests/ -x -q 2>&1 | tail -10
   ruff check ai/ tests/

4. Commit:
   git add ai/mcp_bridge/tool_filter.py tests/test_tool_filter.py ai/mcp_bridge/server.py
   git commit -m "feat(prereq): MCP tool filtering middleware

   - ai/mcp_bridge/tool_filter.py: namespace + semantic tool filtering
   - LanceDB tool_metadata table for semantic tool search
   - Core tools always included (health, disk, memory, services, manifest)
   - Max 15 tools per context window
   - tests/test_tool_filter.py: 6 test cases"
   git push origin main

5. /save-handoff --tool opencode --summary "Prereq complete: MCP tool filter middleware (14 LanceDB tables)" --done "Tool Filtering"
```

---

## Phase 32 — Testing Intelligence

**Goal:** Smart test selection, parallel execution, flaky detection, mutation testing,
and test-to-code traceability.

**Starting state:** 57 tools, 19 timers, 14 LanceDB tables
**Final state:** 57 tools (unchanged — pytest plugins, no MCP tools), 19 timers, 15 LanceDB tables (+1: test_mappings)

### OC-34 — Install and configure pytest plugins

```
Read HANDOFF.md. Verify new dependencies are installed:

source .venv/bin/activate
python -c "import pytest_testmon; print('testmon OK')"
python -c "import xdist; print('xdist OK')"
python -c "import hypothesis; print('hypothesis OK')"

If any import fails, report which package is missing. Do NOT install packages
yourself (user will install via uv).

Then configure pytest plugins in pyproject.toml. Add/update the [tool.pytest.ini_options] section:

[tool.pytest.ini_options]
timeout = 60
timeout_method = "thread"
markers = [
    "quarantined: flaky test excluded from main suite",
    "slow: test takes >10s",
    "requires_embedding: needs real embedding provider",
    "requires_writable_db: needs writable LanceDB",
]

Do NOT modify any Python source files. Only pyproject.toml.
Done when: pyproject.toml has the new pytest config, ruff check passes.
```

### OC-35 — Create ai/testing/test_intelligence.py

```
Create the directory ai/testing/ with __init__.py and test_intelligence.py.

ai/testing/test_intelligence.py implements:

1. Import: ast, json, os, sqlite3, hashlib, logging, pathlib, datetime (UTC)
2. Import: coverage (if available, for reading .coverage SQLite)

3. Class TestIntelligence:
   - __init__(self, project_root=None):
     Sets project root. Initializes SQLite DB at
     ~/.config/bazzite-ai/test-stability.db for result tracking.
     Creates tables: test_results(test_id, timestamp, passed, duration, worker),
     test_quarantine(test_id, reason, quarantined_at, consecutive_passes).
   - record_result(self, test_id, passed, duration, worker="main"):
     Inserts a row into test_results. Called from pytest hook.
   - get_flaky_tests(self, min_runs=5, min_pass_rate=0.1, max_pass_rate=0.99):
     Returns tests that pass intermittently based on history.
   - quarantine_test(self, test_id, reason="auto-detected flaky"):
     Adds to test_quarantine table.
   - check_unquarantine(self, consecutive_passes_needed=10):
     Finds quarantined tests with N consecutive recent passes, removes from quarantine.
   - get_affected_tests(self, changed_files: list[str]) -> list[str]:
     Reads .testmondata SQLite (if exists) to find tests affected by the given files.
     Fallback: uses import-graph heuristic (test files importing changed modules).
   - get_coverage_map(self) -> dict:
     Reads .coverage SQLite with dynamic contexts to build
     {source_file: [test_functions]} mapping. Returns empty dict if no data.
   - get_test_stats(self) -> dict:
     Returns summary: total tests, quarantined count, flaky count,
     avg duration, slowest 10 tests.

4. Module-level singleton: get_test_intel() -> TestIntelligence

CRITICAL RULES:
- Do NOT import ai.router
- SQLite DB at ~/.config/bazzite-ai/ (mkdir -p if not exists)
- Use sqlite3 context managers for all DB operations
- Handle missing .testmondata and .coverage gracefully (return empty results)
- All timestamps UTC

Do NOT modify any other files.
Done when: ai/testing/test_intelligence.py passes ruff check.
```

### OC-36 — Create pytest plugin hook and conftest integration

```
Create ai/testing/pytest_plugin.py — a pytest plugin that records test results
to the stability database.

1. Import: pytest, ai.testing.test_intelligence

2. Implement pytest_runtest_makereport hook:
   @pytest.hookimpl(hookwrapper=True)
   def pytest_runtest_makereport(item, call):
       outcome = yield
       report = outcome.get_result()
       if report.when == "call":
           test_id = f"{item.module.__name__}::{item.name}"
           intel = get_test_intel()
           intel.record_result(
               test_id=test_id,
               passed=report.passed,
               duration=report.duration,
               worker=os.environ.get("PYTEST_XDIST_WORKER", "main")
           )

3. Register the plugin in conftest.py at project root (if it exists) or
   create a minimal one. Add:
   pytest_plugins = ["ai.testing.pytest_plugin"]

   OR if conftest.py already exists, add the import at the end.

4. Create scripts/test-smart.sh — convenience wrapper:
   #!/bin/bash
   set -euo pipefail
   cd ~/projects/bazzite-laptop
   source .venv/bin/activate
   MODE="${1:-smart}"
   case "$MODE" in
     smart)   python -m pytest --testmon -m "not quarantined" "$@" ;;
     full)    python -m pytest -n 4 --timeout=60 -m "not quarantined" "$@" ;;
     flaky)   python -m pytest -m "quarantined" --reruns 3 --reruns-delay 1 "$@" ;;
     *)       echo "Usage: test-smart.sh [smart|full|flaky]"; exit 1 ;;
   esac
   chmod +x scripts/test-smart.sh

CRITICAL RULES:
- The pytest plugin must handle ImportError gracefully (if ai.testing
  is not importable, skip recording silently)
- Do NOT modify existing test files
- Do NOT break the existing test suite — verify with a quick run
- Do NOT use testmon and xdist together (known compatibility issue)

Done when:
- ruff check passes
- python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5 shows all passing
- scripts/test-smart.sh exists and is executable
```

### OC-37 — Create tests and LanceDB test_mappings table

```
1. Create tests/test_testing_intelligence.py:
   - test_record_and_query_result: Record 5 results, verify get_test_stats counts
   - test_flaky_detection: Record alternating pass/fail for one test,
     verify get_flaky_tests returns it
   - test_quarantine_lifecycle: Quarantine a test, verify it's quarantined,
     record 10 passes, verify check_unquarantine removes it
   - test_affected_tests_fallback: No .testmondata → fallback to import heuristic
   - test_coverage_map_empty: No .coverage file → returns empty dict
   - test_stats_format: Verify get_test_stats returns expected keys

2. Create ai/testing/traceability.py — populates LanceDB test_mappings table:
   - LanceDB table: "test_mappings"
   - Schema:
     test_id (str), test_file (str), test_function (str),
     source_files (str, JSON list), source_functions (str, JSON list),
     coverage_pct (float), last_run (str, ISO8601), last_duration (float),
     status (str: "pass"|"fail"|"skip"|"flaky"|"quarantined"),
     pass_rate (float), run_count (int),
     vector (list[float32, 768])
   - Class TestTraceability:
     - __init__(self, db_path=None): connects to LanceDB
     - populate_from_coverage(self): reads .coverage SQLite, populates table
     - query_tests_for_source(self, source_path: str) -> list[dict]:
       Returns tests covering the given source file
     - query_risky_tests(self, min_coverage=0.5, max_pass_rate=0.95) -> list[dict]:
       Returns tests that cover significant code but are unreliable
     - update_stats(self, test_id, passed, duration):
       Updates pass_rate and run_count for a test

CRITICAL RULES:
- Do NOT import ai.router
- Use existing embedder for the vector column
- Handle missing .coverage gracefully
- Use merge_insert for upserts if LanceDB version supports it,
  otherwise delete + add pattern

Done when: tests pass, ruff clean, ai/testing/traceability.py exists.
```

### OC-38 — Docs and commit P32

```
1. Update docs/AGENT.md:
   - Add note under Phase 32 about testing intelligence
   - LanceDB tables: add test_mappings (14 → 15 total so far)
   - Key Paths: add ai/testing/, scripts/test-smart.sh
   - Build & Test section: add smart test commands

2. Update docs/CHANGELOG.md: Phase 32 — Testing Intelligence section

3. Run full test suite:
   python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10
   ruff check ai/ tests/ scripts/

4. Commit:
   git add -A
   git commit -m "feat(P32): testing intelligence — selective execution, flaky detection, traceability

   - ai/testing/test_intelligence.py: TestIntelligence with stability tracking
   - ai/testing/pytest_plugin.py: auto-record test results via hook
   - ai/testing/traceability.py: LanceDB test_mappings table
   - scripts/test-smart.sh: smart/full/flaky test runner modes
   - pytest-testmon for selective runs, pytest-xdist for parallel
   - pyproject.toml: timeout, quarantine marker configuration
   - tests/test_testing_intelligence.py: 6 test cases"
   git push origin main

5. /save-handoff --tool opencode --summary "P32 complete: testing intelligence with testmon, xdist, flaky detection, test_mappings LanceDB table" --done "P32 Testing Intelligence"
```

---

## Phase 29 — Structural Code Intelligence

**Goal:** AST-based code analysis, dependency graphs, change impact analysis,
test-to-source mapping, and 6 new MCP tools.

**Starting state:** 57 tools, 19 timers, 15 LanceDB tables
**Final state:** 63 tools (+6), 20 timers (+1: code-index.timer), 19 LanceDB tables (+4)

### OC-39 — Pre-flight and Context7

```
Read HANDOFF.md. Pre-flight:
git log --oneline -3
python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5
ruff check ai/ tests/ 2>&1 | tail -3

Verify new deps:
python -c "import grimp; print('grimp', grimp.__version__)"
python -c "import radon; print('radon OK')"
python -c "import pydriller; print('pydriller OK')"

Use Context7 MCP to research:
1. grimp API: build_graph(), find_downstream_modules(), find_upstream_modules()
2. LanceDB: table creation with pa.schema(), merge_insert pattern
3. radon: cc_visit() for McCabe complexity

Do NOT modify any files.
```

### OC-40 — Create ai/code_intel/parser.py

```
Create ai/code_intel/ directory with __init__.py and parser.py.

ai/code_intel/parser.py implements the AST-based code parser:

1. Import: ast, hashlib, json, logging, pathlib, os

2. Dataclasses:
   - CodeNode: node_id (str), node_type (str: "module"|"class"|"function"|"method"),
     name (str), qualified_name (str), file_path (str), line_start (int),
     line_end (int), signature (str), docstring (str), complexity (int),
     file_hash (str)
   - Relationship: source_id (str), target_id (str), rel_type (str),
     file_path (str), line_number (int)

3. Class CodeParser:
   - __init__(self, project_root=None):
     Sets project root to ~/projects/bazzite-laptop/ai/ by default.
   - parse_file(self, file_path: str) -> tuple[list[CodeNode], list[Relationship]]:
     Uses ast.parse() to extract all functions, classes, methods.
     For each function/method, extract:
       - qualified_name: module:Class.method or module:function
       - signature from ast.arguments
       - docstring from ast.get_docstring()
       - complexity via radon.visitors.ComplexityVisitor if available
     For relationships: find ast.Call nodes, resolve to qualified names,
     create "calls" relationships. Find ast.Import/ImportFrom, create
     "imports" relationships.
     Returns (nodes, relationships).
   - parse_project(self) -> tuple[list[CodeNode], list[Relationship]]:
     Walks the project root, parses all .py files, returns combined lists.
     Skips __pycache__, .venv, node_modules, .git.
     Uses file SHA-256 hash for incremental detection.
   - get_file_hash(self, file_path: str) -> str:
     Returns SHA-256 hex digest of file contents.

4. Class ImportGraphBuilder:
   - __init__(self, project_root=None):
     Uses grimp to build import graph for the ai package.
   - build(self) -> dict:
     Returns {"modules": [...], "edges": [...], "circular": [...]}
     Uses grimp.build_graph("ai") if the package is importable,
     otherwise falls back to ast-based import extraction.
   - find_dependents(self, module: str, max_depth=3) -> list[str]:
     Returns modules that depend on the given module (downstream).
   - find_dependencies(self, module: str, max_depth=3) -> list[str]:
     Returns modules that the given module depends on (upstream).

CRITICAL RULES:
- Do NOT import ai.router
- Use radon only for complexity, not for other metrics
- Handle syntax errors gracefully (skip files that don't parse)
- grimp.build_graph() may fail if the package isn't properly installed —
  catch ImportError and fall back to AST-based import parsing
- Keep qualified names consistent: "ai.router:route_query"

Do NOT modify any other files.
Done when: ruff check passes.
```

### OC-41 — Create ai/code_intel/store.py (LanceDB tables)

```
Create ai/code_intel/store.py — manages 4 LanceDB tables for code intelligence.

1. Import: uuid, json, logging, lancedb, pyarrow, datetime (UTC)
2. Import from ai.rag.embedder: the embed function (check which one exists)
3. Import from ai.config: VECTOR_DB_PATH (or equivalent)

4. Tables and schemas:

   Table "code_nodes":
   - node_id: string (PK, qualified name)
   - node_type: string
   - name: string
   - qualified_name: string
   - file_path: string
   - line_start: int32
   - line_end: int32
   - signature: string
   - docstring: string
   - complexity: int32
   - file_hash: string
   - vector: list(float32, 768)

   Table "relationships":
   - source_id: string
   - target_id: string
   - rel_type: string ("calls"|"imports"|"inherits"|"overrides")
   - file_path: string
   - line_number: int32

   Table "import_graph":
   - source_module: string
   - target_module: string
   - import_type: string ("absolute"|"relative"|"from")
   - is_circular: bool

   Table "change_history":
   - commit_hash: string
   - file_path: string
   - functions_changed: string (JSON list)
   - co_changed_files: string (JSON list)
   - timestamp: string (ISO8601)
   - vector: list(float32, 768)

5. Class CodeIntelStore:
   - __init__(self, db_path=None): connects to LanceDB, creates tables if not exists
   - index_project(self, nodes, relationships):
     Clears and rebuilds code_nodes and relationships tables from parser output.
     Embeds each node's name+signature+docstring for the vector column.
   - update_incremental(self, changed_files: list[str], parser):
     Parses only changed files, deletes old entries by file_path, inserts new ones.
   - store_import_graph(self, graph_data: dict):
     Stores module-level import edges from ImportGraphBuilder.
   - mine_change_history(self, repo_path: str, max_commits=500):
     Uses PyDriller to extract commit history, identifies co-changed files,
     stores in change_history table. Embeds commit messages for semantic search.
   - query_dependents(self, node_id: str, max_depth=3) -> list[dict]:
     Traverses relationships table to find callers/importers.
   - query_impact(self, changed_files: list[str]) -> dict:
     Combines: static dependents from relationships, co-change from change_history,
     covering tests from test_mappings (P32). Returns union with confidence scores.
   - search_nodes(self, query: str, node_type=None, top_k=10) -> list[dict]:
     Semantic search over code_nodes, optionally filtered by node_type.

6. Module-level singleton: get_code_store() -> CodeIntelStore

CRITICAL RULES:
- Do NOT import ai.router
- Embedding calls should be wrapped in try/except
- Use batch embedding where possible (embed multiple descriptions at once)
- For relationships table, no vector column needed (structural queries only)
- Use table.delete("file_path = '...'") for incremental updates

Done when: ruff check passes.
```

### OC-42 — Create MCP tools and indexing timer

```
Register 6 new MCP tools and create an indexing timer.

1. In configs/mcp-bridge-allowlist.yaml, add:
   - code.impact_analysis: python, args: changed_files (string, comma-separated),
     include_tests (bool, default true), max_depth (int, default 3). readOnly.
   - code.dependency_graph: python, args: module (string, required),
     direction (string: "up"|"down"|"both", default "both"). readOnly.
   - code.find_callers: python, args: function_name (string, required),
     include_indirect (bool, default true). readOnly.
   - code.suggest_tests: python, args: changed_files (string, comma-separated). readOnly.
   - code.complexity_report: python, args: target (string, optional),
     threshold (int, default 10). readOnly.
   - code.class_hierarchy: python, args: class_name (string, required). readOnly.

2. In ai/mcp_bridge/server.py:
   - Tool count: 57 → 63 (6 new tools)
   - Add handlers for each tool that call CodeIntelStore methods
   - Import from ai.code_intel.store, NOT from ai.router
   - Wrap each handler in try/except

3. Create scripts/index-code.py:
   #!/usr/bin/env python3
   """Rebuild the code intelligence index."""
   import sys
   sys.path.insert(0, "/home/lch/projects/bazzite-laptop")
   from ai.code_intel.parser import CodeParser, ImportGraphBuilder
   from ai.code_intel.store import get_code_store
   parser = CodeParser()
   nodes, rels = parser.parse_project()
   store = get_code_store()
   store.index_project(nodes, rels)
   graph = ImportGraphBuilder()
   store.store_import_graph(graph.build())
   store.mine_change_history("/home/lch/projects/bazzite-laptop")
   print(f"Indexed {len(nodes)} nodes, {len(rels)} relationships")
   chmod +x

4. Create systemd/code-index.service and systemd/code-index.timer:
   Timer: Daily 06:00 (before morning briefing)
   Service: runs .venv/bin/python scripts/index-code.py

Phase B (manual):
  sudo cp systemd/code-index.{service,timer} /etc/systemd/system/
  sudo restorecon -v /etc/systemd/system/code-index.*
  sudo systemctl daemon-reload && sudo systemctl enable --now code-index.timer

Done when:
- ruff check passes
- grep -c "name:" configs/mcp-bridge-allowlist.yaml shows 63
```

### OC-43 — Tests for code intelligence

```
Create tests/test_code_intel.py:

1. test_parse_file_extracts_functions: Parse a known Python file,
   verify functions and classes are extracted with correct qualified names.
2. test_parse_file_extracts_calls: Parse a file with function calls,
   verify "calls" relationships are created.
3. test_file_hash_changes: Modify a temp file, verify hash changes.
4. test_import_graph_no_circular: Build graph for a clean package,
   verify no circular imports reported.
5. test_index_project_to_lancedb: Index a temp project directory,
   verify code_nodes table has entries.
6. test_incremental_update: Index, modify one file, incremental update,
   verify only that file's entries changed.
7. test_query_dependents: Store known relationships, query dependents,
   verify correct results.
8. test_query_impact_combined: Store relationships + change_history + test_mappings,
   verify impact analysis combines all three signals.
9. test_search_nodes_semantic: Index nodes with embeddings, search by query,
   verify ranked results. Mock embedder.
10. test_complexity_report: Parse a file with known complexity,
    verify radon scores match.

Use tmp_path for isolated LanceDB and temp Python files.
Mock the embedding function for unit tests.

Done when: tests pass and ruff check clean.
```

### OC-44 — Docs, full suite, commit P29

```
1. Update docs/AGENT.md:
   - MCP Tools: 57 → 63, add all 6 new code.* tools to the code.* section
   - code.* section grows from 2 tools to 8
   - Timers: 19 → 20, add code-index.timer
   - LanceDB tables: add code_nodes, relationships, import_graph, change_history
   - Key Paths: add ai/code_intel/, scripts/index-code.py

2. Update docs/CHANGELOG.md: Phase 29 — Structural Code Intelligence

3. Run full suite:
   python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10
   ruff check ai/ tests/ scripts/

4. Commit:
   git add -A
   git commit -m "feat(P29): structural code intelligence — AST, grimp, impact analysis

   - ai/code_intel/parser.py: AST-based parser + grimp import graph
   - ai/code_intel/store.py: 4 LanceDB tables for code knowledge graph
   - 6 new MCP tools: impact_analysis, dependency_graph, find_callers,
     suggest_tests, complexity_report, class_hierarchy (57 → 63)
   - code-index.timer: daily code re-indexing (19 → 20 timers)
   - PyDriller co-change mining for historical analysis
   - tests/test_code_intel.py: 10 test cases"
   git push origin main

5. /save-handoff --tool opencode --summary "P29 complete: code intel with 6 new tools (63 total), code-index timer (20 timers), 4 new LanceDB tables (19 total)" --done "P29 Code Intelligence"
```

---

## Phase 31 — Agent Collaboration & Task Routing

**Goal:** Structured task queuing between CC/OpenCode, agent-strengths routing,
shared real-time context, and cross-agent learning.

**Starting state:** 63 tools, 20 timers, 19 LanceDB tables
**Final state:** 66 tools (+3), 20 timers (unchanged), 21 LanceDB tables (+2)

### OC-45 — Pre-flight and design

```
Read HANDOFF.md. Pre-flight:
git log --oneline -3
python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5

Read existing agent collaboration infrastructure:
- .opencode/AGENTS.md — OpenCode instructions
- HANDOFF.md format — current handoff structure
- ai/learning/task_logger.py — existing task pattern logging (P22)

Report: What does the current handoff system look like? What task metadata
does task_logger.py capture? What's missing for structured collaboration?

Do NOT modify any files.
```

### OC-46 — Create ai/collab/task_queue.py

```
Create ai/collab/ directory with __init__.py and task_queue.py.

ai/collab/task_queue.py — SQLite-backed task queue for agent coordination:

1. Import: sqlite3, uuid, json, logging, datetime (UTC), pathlib, enum

2. TaskStatus enum: PENDING, CLAIMED, IN_PROGRESS, DONE, FAILED
3. TaskType enum: IMPLEMENT_FEATURE, IMPLEMENT_MCP_TOOL, REFACTOR_MODULE,
   WRITE_TESTS, FIX_BUG, AUDIT_CODE, REVIEW_PR, UPDATE_DOCS, SECURITY_AUDIT

4. AGENT_ROUTING — static dict mapping TaskType → preferred agent:
   {
       IMPLEMENT_FEATURE: "claude_code",
       IMPLEMENT_MCP_TOOL: "claude_code",
       REFACTOR_MODULE: "claude_code",
       WRITE_TESTS: "claude_code",
       FIX_BUG: "opencode",
       AUDIT_CODE: "opencode",
       REVIEW_PR: "opencode",
       UPDATE_DOCS: "opencode",
       SECURITY_AUDIT: "opencode",
   }

5. Class TaskQueue:
   - __init__(self, db_path=None):
     SQLite at ~/.config/bazzite-ai/task-queue.db (WAL mode).
     Creates tables: tasks, task_results, task_dependencies.
   - add_task(self, title, task_type, description="", priority=3,
     agent_affinity=None, dependencies=None, parent_id=None, metadata=None) -> str:
     Creates task. If agent_affinity is None, uses AGENT_ROUTING.
     Returns task_id (UUID).
   - claim_task(self, agent_name, task_types=None) -> dict | None:
     Atomically claims the highest-priority pending task that matches
     agent_name's routing. Sets status to CLAIMED. Returns task dict.
   - start_task(self, task_id, agent_name):
     Sets status to IN_PROGRESS. Records start time.
   - complete_task(self, task_id, result="", files_touched=None):
     Sets status to DONE. Records result and files. Updates task_results.
   - fail_task(self, task_id, error=""):
     Sets status to FAILED. Records error.
   - get_ready_tasks(self, agent_name=None) -> list[dict]:
     Returns tasks whose dependencies are all DONE, filtered by agent routing.
     Uses simple SQL join on task_dependencies.
   - decompose_task(self, parent_id, subtasks: list[dict]):
     Creates subtasks with parent_id and inter-dependencies.
   - get_queue_status(self) -> dict:
     Returns counts by status and agent.

6. Module-level: get_queue() -> TaskQueue

CRITICAL RULES:
- SQLite WAL mode for concurrent reads
- All operations atomic (use transactions)
- Do NOT import ai.router
- Do NOT create a daemon — the queue is passive, polled by agents
- Priority 1 = highest, 5 = lowest

Done when: ruff check passes.
```

### OC-47 — Create shared context and knowledge base

```
1. Create ai/collab/shared_context.py:

   Class SharedContext:
   - __init__(self, db_path=None): connects to LanceDB
   - LanceDB table "shared_context":
     context_id (str), context_type (str: "decision"|"finding"|"blocker"|
     "active_edit"|"pattern"|"warning"), agent (str), content (str),
     files_involved (str, JSON list), priority (int), created_at (str),
     expires_at (str, optional), vector (list[float32, 768])
   - add_context(self, context_type, content, agent, files=None, priority=3, ttl_hours=None):
     Stores context entry. Embeds content for semantic search.
   - query_relevant(self, query: str, context_type=None, top_k=5) -> list[dict]:
     Semantic search with optional type filter.
   - get_active_edits(self, agent=None) -> list[dict]:
     Returns active_edit entries, optionally filtered by agent.
   - cleanup_expired(self):
     Deletes entries past their expires_at.

2. Create ai/collab/knowledge_base.py:

   Class AgentKnowledge:
   - __init__(self, db_path=None): connects to LanceDB
   - LanceDB table "agent_knowledge":
     knowledge_id (str), knowledge_type (str: "pattern"|"quirk"|"solution"|
     "convention"|"api_usage"), title (str), content (str),
     source_agent (str), tags (str, JSON list), confidence (float),
     use_count (int), version (int), created_at (str), updated_at (str),
     related_files (str, JSON list), vector (list[float32, 768])
   - store_knowledge(self, knowledge_type, title, content, source_agent,
     tags=None, related_files=None, confidence=0.8):
     Stores knowledge entry with embedding.
   - query_knowledge(self, query: str, knowledge_type=None, top_k=5) -> list[dict]:
     Semantic search. Increments use_count on returned entries.
   - decay_confidence(self, days_unused=30, decay_rate=0.05):
     Reduces confidence of entries unused for N days.
   - get_stale(self, min_age_days=60, max_confidence=0.3) -> list[dict]:
     Returns low-confidence old entries for review/deletion.

CRITICAL RULES:
- Do NOT import ai.router
- Use existing embedder for vector columns
- Atomic writes for JSON state files
- Handle embedding failures gracefully (log, skip vector)

Done when: both files pass ruff check.
```

### OC-48 — MCP tools and file claim system

```
1. Add 3 MCP tools to configs/mcp-bridge-allowlist.yaml:
   - collab.queue_status: returns task queue summary. readOnly.
   - collab.add_task: args: title (str), task_type (str), description (str),
     priority (int). Returns task_id.
   - collab.search_knowledge: args: query (str, max 500), top_k (int, default 5).
     readOnly.

2. In ai/mcp_bridge/server.py:
   - Tool count: 63 → 66
   - Add handlers for all 3 tools
   - Import from ai.collab, NOT from ai.router

3. Create ai/collab/file_claims.py:
   Simple file-claim system using filelock + JSON:
   - claim_file(agent, filepath) -> bool: Claims file if unclaimed
   - release_file(agent, filepath): Releases claim
   - get_claims() -> dict: Returns {filepath: agent} mapping
   - Claims stored in ~/.config/bazzite-ai/.file-claims.json
   - Uses filelock for thread/process safety
   - Auto-expire claims after 2 hours

Done when:
- ruff check passes
- grep -c "name:" configs/mcp-bridge-allowlist.yaml shows 66
```

### OC-49 — Tests, docs, commit P31

```
1. Create tests/test_collab.py:
   - test_add_and_claim_task: Add task, claim by correct agent, verify
   - test_routing_table: Add IMPLEMENT_FEATURE, verify routed to claude_code
   - test_dependency_ordering: Add tasks with deps, verify get_ready_tasks
     only returns tasks whose deps are DONE
   - test_shared_context_store_and_query: Store context, query semantically
   - test_knowledge_store_and_decay: Store knowledge, simulate age,
     verify confidence decay
   - test_file_claims: Claim file, verify claimed, release, verify released
   - test_queue_status_format: Verify get_queue_status returns expected keys

2. Update docs/AGENT.md: tools 63 → 66, add collab.* section (3 tools),
   add ai/collab/ to Key Paths, add shared_context and agent_knowledge
   LanceDB tables (19 → 21)

3. Update docs/CHANGELOG.md: Phase 31

4. Full test suite + commit:
   python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10
   ruff check ai/ tests/
   git add -A
   git commit -m "feat(P31): agent collaboration — task queue, routing, shared context

   - ai/collab/task_queue.py: SQLite task queue with agent routing
   - ai/collab/shared_context.py: LanceDB shared context for decisions/findings
   - ai/collab/knowledge_base.py: cross-agent learning with confidence decay
   - ai/collab/file_claims.py: file-level claim system with auto-expiry
   - 3 MCP tools: collab.queue_status, collab.add_task, collab.search_knowledge
   - tests/test_collab.py: 7 test cases"
   git push origin main

5. /save-handoff --tool opencode --summary "P31 complete: agent collab with 3 new tools (66 total), task queue, shared context, knowledge base (21 LanceDB tables)" --done "P31 Agent Collaboration"
```

---

## Phase 30 — Workflow Engine & Skill Expansion

**Goal:** Multi-tool composition, natural language workflow definitions, event-driven
triggers, and dynamic skill loading.

**Starting state:** 66 tools, 20 timers, 21 LanceDB tables
**Final state:** 68 tools (+2), 20 timers (unchanged), 22 LanceDB tables (+1)

### OC-50 — Pre-flight

```
Read HANDOFF.md. Pre-flight:
git log --oneline -3
python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5

Verify deps:
python -c "import watchdog; print('watchdog OK')"
python -c "import pluggy; print('pluggy OK')"
python -c "import filelock; print('filelock OK')"

Read ai/mcp_bridge/server.py to understand how tools are currently dispatched
and how the LLM proxy calls tools.

Do NOT modify files.
```

### OC-51 — Create ai/workflows/runner.py (ReAct loop)

```
Create ai/workflows/ directory with __init__.py and runner.py.

ai/workflows/runner.py — lightweight ReAct-style tool chaining:

1. Import: json, logging, asyncio, time, datetime (UTC)
2. Import from ai.router: route_query (this module CAN import router since
   it's NOT in mcp_bridge — it's a separate orchestration layer)
3. Import from ai.mcp_bridge.tools: execute_tool (if this function exists,
   check the file first)

4. Class WorkflowRunner:
   - __init__(self, max_iterations=10, timeout_seconds=120):
     Sets iteration and timeout limits.
   - async run(self, user_message: str, tools: list[dict] = None,
     task_type: str = "fast") -> dict:
     The ReAct loop:
     a. Send user_message + tool definitions to LLM via route_query/route_chat
     b. If response contains tool_calls:
        - Execute each tool call via execute_tool
        - Append tool results as role:"tool" messages
        - Re-call the LLM with updated messages
     c. If response has no tool_calls → return final text response
     d. Enforce max_iterations and timeout
     e. Return {"response": str, "tools_called": list, "iterations": int}

   - async run_plan(self, plan: list[dict]) -> dict:
     Executes a pre-defined plan (list of steps with tool, args, depends_on).
     Steps without dependencies run first. Steps with depends_on wait for
     those steps to complete. Results from prior steps available as $step_id.
     Returns {"steps": {step_id: result}, "status": "complete"|"partial"|"failed"}

   - _handle_error(self, step, error, strategy="skip"):
     strategy "retry": exponential backoff, max 3 attempts
     strategy "skip": log error, continue with error context
     strategy "abort": raise, let caller handle

5. Standalone function:
   async def execute_workflow(user_message, task_type="fast") -> dict:
     runner = WorkflowRunner()
     return await runner.run(user_message, task_type=task_type)

CRITICAL RULES:
- This module lives OUTSIDE ai/mcp_bridge/ so it CAN import ai.router
- Set parallel_tool_calls=False for safety across all providers
- Wrap all LLM calls in try/except with provider fallback
- Log every tool call and result for debugging
- Enforce hard timeout of 120 seconds total
- Do NOT create any daemon or background process

Done when: ruff check passes.
```

### OC-52 — Create ai/workflows/definitions.py and event triggers

```
1. Create ai/workflows/definitions.py:

   Class WorkflowStore:
   - __init__(self, db_path=None): connects to LanceDB
   - LanceDB table "workflows":
     workflow_id (str), name (str), description (str), schedule (str, cron),
     steps (str, JSON list of step dicts), trigger_type (str: "manual"|"schedule"|
     "file_change"|"event"), trigger_config (str, JSON),
     enabled (bool), created_at (str), last_run (str),
     vector (list[float32, 768])
   - save_workflow(self, name, description, steps, schedule=None,
     trigger_type="manual", trigger_config=None) -> str:
     Validates steps (each has id, tool, args), stores with embedding.
   - get_workflow(self, workflow_id) -> dict | None
   - list_workflows(self, enabled_only=True) -> list[dict]
   - search_workflows(self, query: str, top_k=5) -> list[dict]:
     Semantic search by description.
   - disable_workflow(self, workflow_id)
   - enable_workflow(self, workflow_id)

2. Create ai/workflows/triggers.py:

   Class FileWatcher:
   - __init__(self, paths: list[str], callback):
     Uses watchdog.observers.Observer with inotify backend.
     Watches specified paths for modifications.
   - start(self): Starts observer in background thread.
   - stop(self): Stops observer.

   Class EventBus:
   - __init__(self):
     Simple asyncio.Queue-based event bus.
   - subscribe(self, event_type: str, handler: callable)
   - publish(self, event_type: str, data: dict)
   - start(self): Runs event loop consumer in background.
   - stop(self)

   Note: The event bus is NOT a daemon. It runs within the MCP bridge
   process when explicitly started, or within workflow scripts.

CRITICAL RULES:
- Do NOT create systemd services for the event bus
- watchdog observers must be stoppable (clean shutdown)
- Store workflow definitions in LanceDB, not YAML files
- Validate step tool names against the allowlist before saving
- Maximum 20 steps per workflow

Done when: ruff check passes on both files.
```

### OC-53 — MCP tools for workflows

```
1. Add 2 MCP tools to configs/mcp-bridge-allowlist.yaml:
   - workflow.run: args: workflow_id (str, required) OR steps (str, JSON).
     Executes a saved workflow or ad-hoc steps. NOT readOnly.
   - workflow.list: returns available workflows. readOnly.

2. In ai/mcp_bridge/server.py:
   - Tool count: 66 → 68
   - Add handlers:
     workflow.list → WorkflowStore().list_workflows()
     workflow.run → loads workflow, calls WorkflowRunner.run_plan()
   - Wrap workflow.run in try/except with timeout

3. In ai/mcp_bridge/tools.py:
   - Add dispatch entries if using registry

CRITICAL RULES:
- workflow.run MUST enforce the 120-second timeout
- Do NOT import ai.router in mcp_bridge (workflow.run should call
  the runner module which in turn calls the router — indirect path)
- Actually, since mcp_bridge cannot import ai.router, workflow.run
  should spawn the workflow as a subprocess or use a different approach.
  ALTERNATIVE: workflow.run writes the request to a queue file and
  returns "workflow queued", then a separate process handles execution.
  USE THIS APPROACH — it respects the ai.router import boundary.

Done when:
- ruff check passes
- grep -c "name:" configs/mcp-bridge-allowlist.yaml shows 68
```

### OC-54 — Dynamic skill loading

```
Create ai/workflows/skills.py — pluggy-based dynamic skill system:

1. Import: pluggy, importlib.util, pathlib, logging

2. Define hook specification:
   class SkillHookSpec:
       @hookspec
       def register_tools(self, mcp_server): pass
       @hookspec
       def get_skill_info(self) -> dict: pass

3. Class SkillManager:
   - __init__(self, skills_dir=None):
     Default: ~/projects/bazzite-laptop/ai/skills/
     Creates pluggy PluginManager.
   - discover_skills(self) -> list[str]:
     Scans skills_dir for .py files with register_tools function.
   - load_skill(self, skill_path: str, mcp_server=None):
     Uses importlib to load skill module, registers via pluggy.
     If mcp_server provided, calls skill.register_tools(mcp_server).
   - load_all(self, mcp_server=None):
     Discovers and loads all skills.
   - unload_skill(self, skill_name: str):
     Unregisters from pluggy, removes tools from mcp_server.
   - list_loaded(self) -> list[dict]:
     Returns loaded skill info.

4. Create ai/skills/ directory with __init__.py and one example skill:

   ai/skills/git_tools.py:
   """Git workflow skill — provides repository analysis tools."""
   import subprocess, json
   def register_tools(mcp_server):
       # Only register if mcp_server supports add_tool
       pass  # Placeholder — actual tool registration in future prompts
   def get_skill_info():
       return {"name": "git_tools", "version": "1.0",
               "description": "Git workflow analysis tools",
               "tools": ["git.branch_summary", "git.commit_analysis"]}

CRITICAL RULES:
- Skills MUST NOT import ai.router
- Skills are loaded lazily — only when explicitly requested
- Validate skill code before loading (check for forbidden imports)
- Skills directory is NOT in mcp_bridge, so they CAN use ai.router
  if needed — but the loading mechanism is in mcp_bridge, so be careful
- Actually: SkillManager should live in ai/workflows/, not mcp_bridge

Done when: ruff check passes.
```

### OC-55 — Tests, docs, commit P30

```
1. Create tests/test_workflows.py:
   - test_workflow_runner_single_step: Run a workflow with one mock tool call
   - test_workflow_runner_max_iterations: Verify loop stops at max_iterations
   - test_workflow_store_save_and_list: Save workflow, list it back
   - test_workflow_search_semantic: Save workflows, search by description
   - test_plan_execution_with_dependencies: Plan with 3 steps, middle depends
     on first, verify execution order
   - test_event_bus_pub_sub: Publish event, verify subscriber receives it
   - test_skill_discovery: Create temp skill files, verify discover_skills finds them

2. Update docs/AGENT.md: tools 66 → 68, add workflow.* section,
   add ai/workflows/, ai/skills/ to Key Paths, add workflows LanceDB table

3. Update CHANGELOG.md: Phase 30

4. Full suite + commit:
   python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10
   ruff check ai/ tests/
   git add -A
   git commit -m "feat(P30): workflow engine — ReAct loop, event triggers, dynamic skills

   - ai/workflows/runner.py: multi-tool composition with plan-then-execute
   - ai/workflows/definitions.py: LanceDB workflow store
   - ai/workflows/triggers.py: watchdog file watcher + asyncio event bus
   - ai/workflows/skills.py: pluggy-based dynamic skill loading
   - workflow.run + workflow.list MCP tools (66 → 68)
   - tests/test_workflows.py: 7 test cases"
   git push origin main

5. /save-handoff --tool opencode --summary "P30 complete: workflow engine with 2 tools (68 total), event triggers, dynamic skills, 22 LanceDB tables" --done "P30 Workflow Engine"
```

---

## Phase 33 — Plugin Factory & Dynamic Tool Builder

**Goal:** Dynamic MCP tool creation at runtime, tool persistence across restarts,
safety validation, and composite tool patterns.

**Starting state:** 68 tools, 20 timers, 22 LanceDB tables
**Final state:** 70 tools (+2 meta-tools), 20 timers (unchanged), 23 LanceDB tables (+1)

### OC-56 — Pre-flight

```
Read HANDOFF.md. Pre-flight:
git log --oneline -5
python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5
ruff check ai/ tests/ 2>&1 | tail -3

Read FastMCP documentation via Context7 MCP:
1. mcp.add_tool() — runtime registration API
2. mcp.remove_tool() — runtime removal
3. notifications/tools/list_changed

Do NOT modify files.
```

### OC-57 — Create ai/tools/builder.py

```
Create ai/tools/ directory with __init__.py and builder.py.

ai/tools/builder.py — safe dynamic tool creation:

1. Import: ast, json, inspect, logging, uuid, lancedb, pyarrow, datetime (UTC)
2. Import from ai.config: VECTOR_DB_PATH
3. Import from ai.rag.embedder: embed function

4. FORBIDDEN_PATTERNS — AST node types/names to block:
   - ast.Import/ImportFrom of: os, subprocess, sys, shutil, socket, http,
     urllib, pathlib.Path.unlink, pathlib.Path.rmdir
   - ast.Call to: exec, eval, compile, __import__, open (write mode),
     os.system, os.popen, subprocess.run, subprocess.Popen
   - ast.Attribute access to: __builtins__, __class__, __subclasses__

5. SAFE_BUILTINS — restricted builtins dict:
   Only: str, int, float, bool, list, dict, tuple, set, len, range,
   enumerate, zip, map, filter, sorted, reversed, min, max, sum, abs,
   round, isinstance, issubclass, hasattr, getattr, json, print, type

6. Class SafetyValidator(ast.NodeVisitor):
   - visit_Import(self, node): Block if any module in FORBIDDEN list
   - visit_ImportFrom(self, node): Block if module in FORBIDDEN list
   - visit_Call(self, node): Block if function name in FORBIDDEN list
   - visit_Attribute(self, node): Block dunder access
   - validate(self, code: str) -> tuple[bool, list[str]]:
     Parses code, visits AST, returns (is_safe, violations)

7. Class ToolBuilder:
   - __init__(self, db_path=None):
     Connects to LanceDB. Creates "persisted_tools" table if not exists.
     Schema: tool_id (str), name (str), description (str),
     parameters (str, JSON Schema), code (str), version (int),
     created_at (str), created_by (str), is_active (bool),
     code_hash (str, SHA-256), vector (list[float32, 768])
   - create_tool(self, name, description, handler_code, parameters=None,
     created_by="system") -> dict:
     a. Validate code via SafetyValidator — reject if unsafe
     b. Execute code in restricted namespace with SAFE_BUILTINS
     c. Find the function object via inspect.isfunction
     d. Store in persisted_tools table
     e. Return {"status": "created", "tool_name": name, "version": 1}
     Does NOT register with MCP server — that's done by the caller.
   - register_tool(self, name, mcp_server):
     Loads tool from persisted_tools, registers with mcp_server.add_tool()
   - load_all_persisted(self, mcp_server):
     On server startup, reloads all active persisted tools.
   - update_tool(self, name, handler_code, description=None):
     Validates, increments version, updates in LanceDB.
   - deactivate_tool(self, name):
     Sets is_active=False, removes from MCP server.
   - list_dynamic_tools(self) -> list[dict]:
     Returns all persisted tools with metadata.

8. Module-level: get_builder() -> ToolBuilder

CRITICAL RULES:
- NEVER execute code that fails SafetyValidator
- NEVER allow imports of os, subprocess, sys, shutil in dynamic tools
- ALWAYS use restricted builtins namespace
- Code hash prevents duplicate registrations
- Version tracking enables rollback
- Dynamic tools are ALWAYS read-only by default
- Do NOT import ai.router

Done when: ruff check passes.
```

### OC-58 — Create meta-tools and composite tool patterns

```
1. Add 2 meta-tools to configs/mcp-bridge-allowlist.yaml:
   - system.create_tool: args: name (str), description (str),
     handler_code (str), parameters (str, JSON Schema, optional).
     NOT readOnly (creates a tool). destructiveHint=true.
   - system.list_dynamic_tools: returns persisted tools. readOnly.

2. In ai/mcp_bridge/server.py:
   - Tool count: 68 → 70
   - Handler for system.create_tool:
     from ai.tools.builder import get_builder
     builder = get_builder()
     result = builder.create_tool(name=args["name"], ...)
     if result["status"] == "created":
         builder.register_tool(args["name"], mcp_server_instance)
     return json.dumps(result)
   - Handler for system.list_dynamic_tools:
     return json.dumps(get_builder().list_dynamic_tools())
   - On server startup: call builder.load_all_persisted(mcp_server) to
     restore dynamic tools from previous sessions

3. Create ai/tools/composites.py — composite tool patterns:
   Class CompositeToolFactory:
   - create_composite(self, name, description, sub_tools: list[dict]) -> callable:
     Creates a function that calls multiple tools in sequence/parallel
     and aggregates results. Uses asyncio.gather for parallel.
     Each sub_tool dict: {"tool": "name", "args": {...}, "parallel": bool}
   - Example composite: full_security_check = composite of
     security.cve_check + security.threat_summary + logs.anomalies + agents.timer_health

CRITICAL RULES:
- system.create_tool is HIGH RISK — always validate via SafetyValidator
- On server startup, load persisted tools AFTER all static tools are registered
- Composite tools should have their own timeout (30s per sub-tool)
- Do NOT import ai.router in mcp_bridge files

Done when:
- ruff check passes
- grep -c "name:" configs/mcp-bridge-allowlist.yaml shows 70
```

### OC-59 — Tests for P33

```
Create tests/test_tool_builder.py:

1. test_safety_validator_blocks_os: Code with "import os" → rejected
2. test_safety_validator_blocks_subprocess: subprocess.run → rejected
3. test_safety_validator_blocks_eval: eval() call → rejected
4. test_safety_validator_allows_safe_code: Simple math function → passes
5. test_create_tool_and_persist: Create tool, verify in LanceDB
6. test_create_tool_rejects_unsafe: Unsafe code → raises ValueError
7. test_load_persisted_tools: Create, reload from DB, verify function works
8. test_deactivate_tool: Create, deactivate, verify is_active=False
9. test_version_increment: Update tool twice, verify version=3
10. test_composite_tool: Create composite of 2 mock tools, verify both called
11. test_safe_builtins_only: Dynamic code can use len, sorted, but NOT open

Done when: tests pass and ruff check clean.
```

### OC-60 — Final docs, full suite, commit P33

```
1. Update docs/AGENT.md comprehensively for P29-P33:
   - MCP Tools: final count 70 (was 57 at P28)
   - Update ALL tool section counts:
     system.* → 22 (was 19, added metrics_summary, provider_status, weekly_insights,
       create_tool, list_dynamic_tools) — wait, check actual count
     code.* → 8 (was 2, added 6 in P29)
     collab.* → 3 (new section)
     workflow.* → 2 (new section)
     memory.* → 1 (P25)
     security.* → 15 (added alert_summary in P27)
   - Timers: 20 (added code-index.timer in P29)
   - LanceDB tables: 23 total
     List all: documents, code_index, log_entries, code_patterns, task_patterns,
     semantic_cache, metrics, conversation_memory, system_insights,
     tool_metadata, test_mappings, code_nodes, relationships, import_graph,
     change_history, shared_context, agent_knowledge, workflows, persisted_tools
     (plus originals: security_logs, threat_intel, health_records, scan_records)
   - Key Paths: all new modules
   - health endpoint: tools: 70
   - Software NOT to Use: reconfirm deferred list

2. Update CHANGELOG.md: Phase 33 + full P29-P33 summary

3. Update USER-GUIDE.md: new tool sections, smart test commands, workflow usage

4. Run FULL verification:
   python -m pytest tests/ -v --timeout=60 2>&1 | tail -20
   ruff check ai/ tests/ scripts/
   bandit -r ai/ -c pyproject.toml 2>&1 | tail -5
   grep -c "name:" configs/mcp-bridge-allowlist.yaml

5. Commit:
   git add -A
   git commit -m "feat(P33): plugin factory — dynamic tool creation with safety validation

   - ai/tools/builder.py: SafetyValidator + ToolBuilder with LanceDB persistence
   - ai/tools/composites.py: composite tool patterns with parallel execution
   - system.create_tool + system.list_dynamic_tools MCP tools (68 → 70)
   - AST-based safety: blocks os, subprocess, eval, __import__
   - Restricted builtins namespace for dynamic code execution
   - tests/test_tool_builder.py: 11 test cases
   - docs: full P29-P33 update across AGENT.md, CHANGELOG.md, USER-GUIDE.md"
   git push origin main

6. /save-handoff --tool opencode --summary "P33 complete + full P29-P33 arc done. 70 MCP tools, 20 timers, 23 LanceDB tables. All tests passing." --done "P33 Plugin Factory" --done "P29-P33 Arc Complete"
```

---

## Phase Summary

| Order | Phase | Name | New Tools | New Timers | New Tables | Key Module |
|-------|-------|------|-----------|------------|------------|------------|
| 0 | Prereq | Tool Filtering | 0 | 0 | +1 | ai/mcp_bridge/tool_filter.py |
| 1 | P32 | Testing Intelligence | 0 | 0 | +1 | ai/testing/ |
| 2 | P29 | Code Intelligence | +6 | +1 | +4 | ai/code_intel/ |
| 3 | P31 | Agent Collaboration | +3 | 0 | +2 | ai/collab/ |
| 4 | P30 | Workflow Engine | +2 | 0 | +1 | ai/workflows/ |
| 5 | P33 | Plugin Factory | +2 | 0 | +1 | ai/tools/ |

### Final State After P33

| Metric | P28 (start) | P33 (target) |
|--------|-------------|--------------|
| MCP tools | 57 | 70 (+13) |
| Timers | 19 | 20 (+1) |
| LanceDB tables | 13 | 23 (+10) |
| Tests | ~1650 | ~1800+ |
| New modules | — | tool_filter, ai/testing, ai/code_intel, ai/collab, ai/workflows, ai/tools, ai/skills |

---

## Post-P33 Checklist (User Manual Steps)

1. **Deploy code-index timer** (only new timer):
   ```bash
   sudo cp systemd/code-index.{service,timer} /etc/systemd/system/
   sudo restorecon -v /etc/systemd/system/code-index.*
   sudo systemctl daemon-reload
   sudo systemctl enable --now code-index.timer
   ```

2. **Restart services**:
   ```bash
   systemctl --user restart llm-proxy mcp-bridge
   curl -s http://127.0.0.1:8766/mcp/health | jq .  # should show tools: 70
   ```

3. **Run initial code index**:
   ```bash
   source .venv/bin/activate
   python scripts/index-code.py
   ```

4. **Build testmon baseline**:
   ```bash
   python -m pytest --testmon tests/
   ```

5. **Update Newelle system prompt** — reference new tool namespaces

6. **Schedule CC audit** — review P29-P33 for import violations,
   SQL injection, missing try/except in handlers

---

## Troubleshooting

**grimp fails to build graph:** The `ai` package must be importable.
Ensure `.venv/bin/activate` is sourced and PYTHONPATH includes the project root.

**testmon + xdist conflict:** NEVER use `--testmon` with `-n`. Use testmon
for fast local runs, xdist for full parallel runs — never together.

**mutmut requires LibCST Rust build:** If wheels aren't available, install
Rust toolchain: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`

**Dynamic tool execution fails:** Check SafetyValidator — it blocks all
import/exec/eval patterns. If a legitimate import is needed, add it to the
SAFE_BUILTINS allowlist in builder.py.

**Too many LanceDB tables:** 23 tables is well within LanceDB's capacity.
If SSD space is a concern, extend lancedb-prune.py to cover all new tables
with appropriate retention policies.
