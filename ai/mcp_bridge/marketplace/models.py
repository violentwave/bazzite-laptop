"""Pydantic models for MCP Tool Marketplace.

P103: MCP Tool Marketplace + Tool Pack Import/Export

Provides models for tool pack manifests, validation states, and governance metadata.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PackState(StrEnum):
    """Lifecycle states for a tool pack."""

    STAGED = "staged"  # Imported but not validated
    VALIDATED = "validated"  # Validation passed, ready for install
    INSTALLED = "installed"  # Installed and active
    DISABLED = "disabled"  # Disabled but preserved
    REMOVED = "removed"  # Removed (audit trail only)


class RiskTier(StrEnum):
    """Risk tiers for tool packs."""

    LOW = "low"  # Read-only tools, no sensitive access
    MEDIUM = "medium"  # Standard tools with controlled mutations
    HIGH = "high"  # Tools with destructive capabilities
    CRITICAL = "critical"  # Tools with system-level access


class ToolPackFile(BaseModel):
    """A file within a tool pack.

    Attributes:
        path: Relative path within pack
        checksum: SHA-256 hash of file content
        size_bytes: File size in bytes
    """

    path: str
    checksum: str
    size_bytes: int


class ToolDefinition(BaseModel):
    """Definition of a tool within a pack.

    Attributes:
        name: Tool name (e.g., "custom.my_tool")
        description: Tool description
        handler_module: Python module path
        handler_function: Function name within module
        args: Argument definitions
        annotations: MCP annotations (readOnly, destructive, etc.)
    """

    name: str
    description: str
    handler_module: str
    handler_function: str
    args: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v or "." not in v:
            raise ValueError(f"Tool name must be namespaced: {v}")
        if len(v) > 128:
            raise ValueError(f"Tool name too long: {v}")
        return v


class PackManifest(BaseModel):
    """Manifest for a tool pack.

    This is the primary metadata file for a tool pack, containing
    identification, versioning, compatibility, and tool definitions.

    Attributes:
        pack_id: Unique pack identifier (e.g., "org.example.tools")
        name: Human-readable pack name
        version: Semantic version (e.g., "1.2.3")
        description: Pack description
        author: Author/organization
        source: Source URL or origin
        risk_tier: Risk assessment level
        compatibility: Compatibility constraints
        tools: Tool definitions included in pack
        files: List of files with checksums
        required_permissions: Required capabilities
        created_at: Creation timestamp
        updated_at: Last update timestamp
        migration_notes: Notes for migration from previous versions
        governance_metadata: Additional governance metadata
    """

    pack_id: str = Field(..., description="Unique pack identifier")
    name: str = Field(..., description="Human-readable pack name")
    version: str = Field(..., description="Semantic version")
    description: str = Field(default="", description="Pack description")
    author: str = Field(default="", description="Author/organization")
    source: str = Field(default="", description="Source URL or origin")
    risk_tier: RiskTier = Field(default=RiskTier.MEDIUM)
    compatibility: dict[str, Any] = Field(
        default_factory=lambda: {
            "min_bridge_version": "1.0.0",
            "max_bridge_version": None,
            "requires": [],
            "conflicts": [],
        }
    )
    tools: list[ToolDefinition] = Field(default_factory=list)
    files: list[ToolPackFile] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    migration_notes: str = Field(default="")
    governance_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("pack_id")
    @classmethod
    def validate_pack_id(cls, v: str) -> str:
        """Validate pack ID format."""
        if not v:
            raise ValueError("pack_id is required")
        if len(v) > 128:
            raise ValueError(f"pack_id too long: {v}")
        # Must contain at least one dot for namespacing
        if "." not in v:
            raise ValueError(f"pack_id must be namespaced (e.g., 'org.example.tools'): {v}")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format (simplified)."""
        if not v:
            raise ValueError("version is required")
        parts = v.split(".")
        if len(parts) < 2 or len(parts) > 4:
            raise ValueError(f"Invalid version format (expected X.Y.Z): {v}")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Invalid version format (expected X.Y.Z): {v}")
        return v

    def compute_content_hash(self) -> str:
        """Compute a hash of the manifest content for integrity.

        Returns:
            SHA-256 hash of canonical JSON representation
        """
        # Create canonical representation (sorted keys, no extra whitespace)
        canonical = json.dumps(
            self.model_dump(exclude={"created_at", "updated_at"}),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


class ToolPack(BaseModel):
    """A complete tool pack with metadata and state.

    This represents a tool pack at various stages of its lifecycle:
    staged (imported), validated (ready), installed (active), etc.

    Attributes:
        manifest: Pack manifest with tool definitions
        state: Current lifecycle state
        state_reason: Reason for current state (e.g., validation error)
        staged_at: When pack was imported/staged
        validated_at: When validation passed
        installed_at: When installed to registry
        removed_at: When removed (audit trail)
        staging_path: Path where pack is staged
        install_path: Path where pack is installed
        validation_errors: List of validation errors
        audit_log: List of state transitions for audit trail
        pack_hash: Hash of manifest for integrity verification
    """

    manifest: PackManifest
    state: PackState = PackState.STAGED
    state_reason: str = ""
    staged_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: datetime | None = None
    installed_at: datetime | None = None
    removed_at: datetime | None = None
    staging_path: str = ""
    install_path: str = ""
    validation_errors: list[str] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    pack_hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        """Compute pack hash after initialization."""
        if not self.pack_hash:
            self.pack_hash = self.manifest.compute_content_hash()

    def add_audit_entry(self, action: str, details: str | None = None) -> None:
        """Add an entry to the audit log.

        Args:
            action: Action performed
            details: Optional details
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "state": self.state.value,
        }
        if details:
            entry["details"] = details
        self.audit_log.append(entry)

    def transition_to(self, new_state: PackState, reason: str = "") -> None:
        """Transition pack to a new state.

        Args:
            new_state: Target state
            reason: Reason for transition
        """
        old_state = self.state
        self.state = new_state
        self.state_reason = reason

        # Update timestamps
        now = datetime.utcnow()
        if new_state == PackState.VALIDATED:
            self.validated_at = now
        elif new_state == PackState.INSTALLED:
            self.installed_at = now
        elif new_state == PackState.REMOVED:
            self.removed_at = now

        self.add_audit_entry(
            action="state_transition",
            details=f"{old_state.value} -> {new_state.value}: {reason}",
        )

    def to_summary(self) -> dict[str, Any]:
        """Get a summary representation of the pack.

        Returns:
            Dict with key pack information
        """
        return {
            "pack_id": self.manifest.pack_id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "risk_tier": self.manifest.risk_tier.value,
            "tool_count": len(self.manifest.tools),
            "staged_at": self.staged_at.isoformat(),
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
        }


class ValidationResult(BaseModel):
    """Result of pack validation.

    Attributes:
        valid: Whether pack passed validation
        errors: List of validation errors
        warnings: List of validation warnings
        risk_assessment: Risk assessment details
        compatibility_check: Compatibility results
    """

    valid: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    compatibility_check: dict[str, Any] = Field(default_factory=dict)

    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "risk_assessment": self.risk_assessment,
            "compatibility_check": self.compatibility_check,
        }


class PackInstallResult(BaseModel):
    """Result of pack installation.

    Attributes:
        success: Whether installation succeeded
        pack_id: Installed pack ID
        tools_installed: List of tool names installed
        tools_skipped: List of tool names skipped (already existed)
        errors: List of installation errors
        governance_flags: Governance policy implications
    """

    success: bool = False
    pack_id: str = ""
    tools_installed: list[str] = Field(default_factory=list)
    tools_skipped: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    governance_flags: list[dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "pack_id": self.pack_id,
            "tools_installed": self.tools_installed,
            "tools_skipped": self.tools_skipped,
            "error_count": len(self.errors),
            "errors": self.errors,
            "governance_flags": self.governance_flags,
        }


class PackExportRequest(BaseModel):
    """Request to export tools to a pack.

    Attributes:
        pack_id: Target pack ID
        name: Pack name
        version: Pack version
        description: Pack description
        author: Pack author
        tool_selection: Tools to include
        include_source_files: Whether to include handler source files
        output_path: Optional output path override
    """

    pack_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    tool_selection: list[str] = Field(default_factory=list)
    include_source_files: bool = True
    output_path: str = ""


class PackListFilter(BaseModel):
    """Filter criteria for listing packs.

    Attributes:
        state_filter: Filter by pack state
        risk_tier_filter: Filter by risk tier
        search_query: Search in pack name/description
        include_removed: Include removed packs in results
    """

    state_filter: PackState | None = None
    risk_tier_filter: RiskTier | None = None
    search_query: str = ""
    include_removed: bool = False


class MarketplaceStats(BaseModel):
    """Statistics for the tool marketplace.

    Attributes:
        total_packs: Total number of packs
        staged_count: Number of staged packs
        validated_count: Number of validated packs
        installed_count: Number of installed packs
        disabled_count: Number of disabled packs
        tool_count: Total tools across all installed packs
        storage_used_bytes: Total storage used
    """

    total_packs: int = 0
    staged_count: int = 0
    validated_count: int = 0
    installed_count: int = 0
    disabled_count: int = 0
    tool_count: int = 0
    storage_used_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_packs": self.total_packs,
            "by_state": {
                "staged": self.staged_count,
                "validated": self.validated_count,
                "installed": self.installed_count,
                "disabled": self.disabled_count,
            },
            "total_tools": self.tool_count,
            "storage_used_mb": round(self.storage_used_bytes / (1024 * 1024), 2),
        }
