"""MCP Tool Marketplace module.

P103: MCP Tool Marketplace + Tool Pack Import/Export

Provides local tool pack management with validation, import/export,
and installation capabilities. Integrates with P101 Governance and
P102 Dynamic Tool Discovery.

Usage:
    from ai.mcp_bridge.marketplace import PackStore, PackValidator, PackInstaller

    # Stage a pack
    store = PackStore()
    pack = store.stage_pack(tool_pack, files)

    # Validate
    validator = PackValidator()
    result = validator.validate_pack(pack)

    # Install
    installer = PackInstaller()
    result = installer.install_pack(pack_id)
"""

from ai.mcp_bridge.marketplace.import_export import PackExporter, PackImporter
from ai.mcp_bridge.marketplace.installer import PackInstaller, PackInstallError
from ai.mcp_bridge.marketplace.models import (
    MarketplaceStats,
    PackExportRequest,
    PackInstallResult,
    PackListFilter,
    PackManifest,
    PackState,
    RiskTier,
    ToolDefinition,
    ToolPack,
    ToolPackFile,
    ValidationResult,
)
from ai.mcp_bridge.marketplace.pack_store import PackStore, PackStoreError
from ai.mcp_bridge.marketplace.pack_validator import PackValidationError, PackValidator

__all__ = [
    # Models
    "ToolPack",
    "PackManifest",
    "ToolDefinition",
    "ToolPackFile",
    "PackState",
    "RiskTier",
    "ValidationResult",
    "PackInstallResult",
    "PackExportRequest",
    "PackListFilter",
    "MarketplaceStats",
    # Core classes
    "PackStore",
    "PackValidator",
    "PackInstaller",
    "PackExporter",
    "PackImporter",
    # Exceptions
    "PackStoreError",
    "PackValidationError",
    "PackInstallError",
]
