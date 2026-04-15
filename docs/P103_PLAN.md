# P103 — MCP Tool Marketplace + Tool Pack Import/Export

**Status**: Complete  
**Date**: 2026-04-15  
**Dependencies**: P101 (Tool Governance), P102 (Dynamic Tool Discovery)  
**Risk Tier**: High  
**Backend**: opencode  

---

## Objective

Implement a local, security-gated MCP Tool Marketplace layer for exporting, importing, validating, signing/checksumming, listing, and installing tool packs. This provides a controlled mechanism for managing tool collections without creating a public marketplace or bypassing P101 governance/P102 dynamic discovery safety models.

---

## Background

### Current State (Pre-P103)
- **151 MCP tools** managed through allowlist YAML
- **P101**: Tool Governance with lifecycle states, risk tiers, and security scoring
- **P102**: Dynamic Tool Discovery with runtime registration and hot-reload
- Tools added individually through manual allowlist updates or dynamic registration
- No systematic way to package, share, or version groups of tools

### Pain Points
1. **No Portability**: Tools cannot be easily exported/imported between environments
2. **No Versioning**: No way to version and track tool collections
3. **Manual Process**: Adding multiple related tools requires manual allowlist editing
4. **No Staging**: No safe staging area for testing tool packs before installation
5. **Limited Validation**: No comprehensive validation before tool activation

### Strategic Value
- **Operational Portability**: Move tool packs between development, staging, and production
- **Version Control**: Track tool pack versions and changes
- **Safety**: Comprehensive validation before installation
- **Auditability**: Complete audit trail for pack lifecycle
- **Governance Integration**: Risk tier enforcement and approval workflows

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   MCP Tool Marketplace (P103)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Import/   │  │   Pack      │  │   Pack    │   Pack      │  │
│  │   Export    │──│   Store     │──│   Validator│  Installer  │  │
│  │             │  │             │  │             │             │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┴─────────────┘  │
│         │                │                                       │
│         ▼                ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Storage Layer                            │  │
│  │  ├─ ~/security/mcp-tool-packs/staging/  (import/validate)  │  │
│  │  ├─ ~/security/mcp-tool-packs/installed/ (active packs)    │  │
│  │  └─ index.json (pack registry with audit trail)            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                 MCP Tool Handlers (6 tools)                 │  │
│  │  tool.pack_validate │ tool.pack_export │ tool.pack_import   │  │
│  │  tool.pack_list     │ tool.pack_install│ tool.pack_remove   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Integration with P101/P102 Systems                  │
├─────────────────────────────────────────────────────────────────┤
│  P101 Governance      → Risk tier enforcement, approval workflow │
│  P102 Dynamic Registry → Tool registration, allowlist updates    │
│  Allowlist YAML        → Tool definitions with marketplace metadata│
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation

### New Files Created

```
ai/mcp_bridge/marketplace/
├── __init__.py                  # Module exports
├── models.py                    # Pydantic models (ToolPack, PackManifest, etc.)
├── pack_validator.py            # Validation without code execution
├── pack_store.py                # Storage management
├── import_export.py             # Import/export functionality
└── installer.py                 # Installation with P102 integration

ai/mcp_bridge/tool_marketplace_handlers.py  # MCP tool handlers (6 tools)

tests/test_p103_tool_marketplace.py         # Comprehensive tests

docs/P103_PLAN.md                          # This document
```

### Key Components

#### 1. Tool Pack Model (`models.py`)

A tool pack consists of:
- **pack_id**: Unique identifier (e.g., "org.example.tools")
- **name**: Human-readable name
- **version**: Semantic version
- **description**: Pack description
- **author**: Author/organization
- **risk_tier**: LOW, MEDIUM, HIGH, CRITICAL
- **tools**: List of ToolDefinition objects
- **files**: Source files with checksums
- **required_permissions**: Required capabilities
- **compatibility**: Version constraints
- **governance_metadata**: Policy metadata

```python
class ToolPack(BaseModel):
    manifest: PackManifest
    state: PackState  # STAGED, VALIDATED, INSTALLED, DISABLED, REMOVED
    validation_errors: list[str]
    audit_log: list[dict]  # Complete lifecycle audit trail
    pack_hash: str  # Integrity checksum
```

#### 2. Pack Validator (`pack_validator.py`)

Validates packs **WITHOUT executing any code**:

```python
class PackValidator:
    def validate_pack(self, pack: ToolPack, ...) -> ValidationResult:
        # 1. Manifest structure validation
        # 2. Tool definition syntax checking
        # 3. Risk tier constraint validation
        # 4. Compatibility checking
        # 5. Governance compliance
        # 6. File integrity (checksums)
```

**Validation checks**:
- Required fields present
- Tool name format (no reserved prefixes like "system.", "security.")
- Conflicting annotations (readOnly + destructive)
- Risk tier tool count limits
- Semantic versioning
- Regex pattern syntax
- File checksums

#### 3. Pack Store (`pack_store.py`)

Manages pack storage with atomic operations:

```python
class PackStore:
    def stage_pack(self, pack: ToolPack, files: dict) -> ToolPack
    def get_pack(self, pack_id: str) -> ToolPack | None
    def update_pack_state(self, pack_id: str, state: PackState)
    def list_packs(self, filter: PackListFilter) -> list[ToolPack]
    def remove_pack(self, pack_id: str)
```

**Storage layout**:
```
~/security/mcp-tool-packs/
├── staging/
│   └── <pack_id>/
│       ├── manifest.json
│       └── files/
├── installed/
│   └── <pack_id>/
│       ├── manifest.json
│       └── files/
└── index.json
```

#### 4. Import/Export (`import_export.py`)

**PackExporter**: Creates portable packs from dynamic registry tools
**PackImporter**: Imports packs from directories or manifest data

```python
# Export existing tools
exporter = PackExporter()
request = PackExportRequest(
    pack_id="org.example.tools",
    name="Example Tools",
    tool_selection=["custom.tool1", "custom.tool2"],
)
pack = exporter.export_tools(request)

# Import from directory
importer = PackImporter()
pack = importer.import_from_directory("/path/to/pack")
```

#### 5. Installer (`installer.py`)

Integrates with P102 Dynamic Registry:

```python
class PackInstaller:
    def check_install_prerequisites(self, pack_id: str) -> dict
    def request_approval(self, pack_id: str) -> dict  # For HIGH/CRITICAL
    def approve_pack(self, pack_id: str) -> dict
    def install_pack(self, pack_id: str, ...) -> PackInstallResult
    def remove_pack(self, pack_id: str) -> dict
    def disable_pack(self, pack_id: str) -> dict
```

**Installation flow**:
1. Check prerequisites (validated, not already installed)
2. Verify approval for high-risk packs
3. Register tools with P102 Dynamic Registry
4. Update allowlist YAML atomically
5. Update pack state to INSTALLED
6. Maintain audit trail

**Rollback on failure**: Unregisters any successfully installed tools

---

## MCP Tools Added (6 tools)

| Tool | Read-Only | Destructive | Description |
|------|-----------|-------------|-------------|
| `tool.pack_validate` | Yes | No | Validate pack manifest and files |
| `tool.pack_export` | No | No | Export tools to portable pack |
| `tool.pack_import` | No | No | Import pack to staging area |
| `tool.pack_list` | Yes | No | List packs with filtering |
| `tool.pack_install` | No | No | Install validated pack |
| `tool.pack_remove` | No | Yes | Remove or disable pack |

### Usage Examples

```bash
# Validate a pack before import
tool.pack_validate manifest={"pack_id": "test.tools", ...}

# Export existing tools
tool.pack_export pack_id="org.example.tools" name="Example Tools" \
    tools=["custom.tool1", "custom.tool2"]

# Import a pack
tool.pack_import source_path="/path/to/pack"

# List all packs
tool.pack_list state_filter="validated"

# Install a pack (may require approval for high-risk)
tool.pack_install pack_id="org.example.tools"

# Remove a pack
tool.pack_remove pack_id="org.example.tools" reason="No longer needed"
```

---

## Security Model

### Risk Tiers

| Tier | Max Tools | Destructive | Requires Approval |
|------|-----------|-------------|-------------------|
| LOW | 50 | No | No |
| MEDIUM | 30 | Yes | No |
| HIGH | 15 | Yes | Yes |
| CRITICAL | 5 | Yes | Yes |

### Governance Integration

1. **Policy Enforcement**: Risk tier constraints enforced at validation
2. **Approval Workflow**: HIGH/CRITICAL packs require explicit approval
3. **Audit Trail**: All state transitions logged with timestamps
4. **Integrity**: SHA-256 checksums for all files and manifests
5. **Reserved Namespaces**: "system.*", "security.*" protected

---

## Integration Points

### P101 Governance Integration

- Risk tier mapping to governance policies
- Security score calculation
- Permission audit tracking
- Compliance reporting

### P102 Dynamic Registry Integration

- Tools registered via `DynamicToolRegistry.register_tool()`
- Source tracked as `"marketplace:{pack_id}"`
- Allowlist YAML updated atomically
- Hot-reload compatible

### Allowlist Integration

Tools installed from marketplace include metadata:
```yaml
custom.example_tool:
  description: "Example tool from marketplace"
  source: python
  module: ai.example.handlers
  function: example_handler
  marketpack:
    pack_id: org.example.tools
    version: 1.0.0
```

---

## Validation Requirements

### Code Quality
```bash
ruff check ai/mcp_bridge/marketplace/ ai/mcp_bridge/tool_marketplace_handlers.py
```

### Tests
```bash
python -m pytest tests/test_p103_tool_marketplace.py -v
```

### YAML Validation
```bash
python3 -c "import yaml; yaml.safe_load(open('configs/mcp-bridge-allowlist.yaml'))"
```

### Integration Tests
```bash
python -m pytest tests/test_p101* tests/test_p102_dynamic_tool_discovery.py -q --tb=short
```

---

## Deliverables

### Code
- [x] `ai/mcp_bridge/marketplace/` module (6 files, ~1800 lines)
- [x] `ai/mcp_bridge/tool_marketplace_handlers.py` (600 lines)
- [x] `tests/test_p103_tool_marketplace.py` (650+ lines)
- [x] 6 new MCP tools in `configs/mcp-bridge-allowlist.yaml`

### Features
- [x] Tool pack validation without code execution
- [x] Import/export with checksums
- [x] Staging area for safe testing
- [x] Risk tier-based approval workflow
- [x] Complete audit trail
- [x] P102 Dynamic Registry integration
- [x] Atomic allowlist updates

### Documentation
- [x] `docs/P103_PLAN.md` (this document)
- [x] Inline code documentation
- [x] Comprehensive test coverage

---

## Done Criteria

1. [x] **Validation**: Packs validated without code execution
2. [x] **Import/Export**: Tools can be exported and imported
3. [x] **Storage**: Staging and installed pack management
4. [x] **Installation**: Safe installation with P102 integration
5. [x] **Governance**: Risk tier enforcement and approval workflow
6. [x] **Audit**: Complete lifecycle audit trail
7. [x] **Tests**: 650+ lines of tests, all passing
8. [x] **Docs**: PLAN document and inline documentation
9. [x] **Integration**: Works with P101 Governance and P102 Dynamic Discovery

---

## Metrics

- **Files created**: 9
- **Lines of code**: ~2400
- **Tests written**: 30+ test cases
- **MCP tools added**: 6
- **Total tools**: 151 → 157

---

## Future Enhancements

### P103.1: Advanced Validation
- Handler existence verification
- Import dependency checking
- Schema evolution detection

### P103.2: Pack Bundles
- Multi-pack bundles
- Dependency resolution
- Atomic multi-pack installation

### P103.3: Pack Updates
- In-place pack updates
- Migration path generation
- Version compatibility checking

---

## References

- [P101 Tool Governance](./P101_COMPLETION_REPORT.md)
- [P102 Dynamic Tool Discovery](./P102_PLAN.md)
- [MCP Specification](https://modelcontextprotocol.io/)
