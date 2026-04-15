"""MCP Tool handlers for Tool Marketplace (P103).

Exposes tool.pack_validate, tool.pack_export, tool.pack_import,
tool.pack_list, tool.pack_install, and tool.pack_remove for
tool pack management.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai.mcp_bridge.marketplace import (
    PackExporter,
    PackImporter,
    PackInstaller,
    PackListFilter,
    PackStore,
    PackValidator,
)
from ai.mcp_bridge.marketplace.models import (
    PackExportRequest,
    PackState,
    RiskTier,
)

logger = logging.getLogger("ai.mcp_bridge.tool_marketplace_handlers")

# Shared instances (lazy initialized)
_store: PackStore | None = None
_validator: PackValidator | None = None
_installer: PackInstaller | None = None
_exporter: PackExporter | None = None
_importer: PackImporter | None = None


def _get_store() -> PackStore:
    """Get shared pack store instance."""
    global _store
    if _store is None:
        _store = PackStore()
    return _store


def _get_validator() -> PackValidator:
    """Get shared pack validator instance."""
    global _validator
    if _validator is None:
        _validator = PackValidator()
    return _validator


def _get_installer() -> PackInstaller:
    """Get shared pack installer instance."""
    global _installer
    if _installer is None:
        _installer = PackInstaller()
    return _installer


def _get_exporter() -> PackExporter:
    """Get shared pack exporter instance."""
    global _exporter
    if _exporter is None:
        _exporter = PackExporter()
    return _exporter


def _get_importer() -> PackImporter:
    """Get shared pack importer instance."""
    global _importer
    if _importer is None:
        _importer = PackImporter()
    return _importer


async def handle_tool_pack_validate(args: dict) -> str:
    """Validate a tool pack manifest and files without installing.

    Performs comprehensive validation of a staged or to-be-imported pack,
    checking manifest structure, tool definitions, risk constraints,
    compatibility, and governance compliance WITHOUT executing any code.

    Args:
        pack_id: Pack ID to validate (if already staged)
        manifest: Optional manifest data to validate before staging
        pack_path: Optional path to pack directory

    Returns:
        JSON with validation results
    """
    pack_id = args.get("pack_id", "")
    manifest_data = args.get("manifest")
    pack_path = args.get("pack_path")

    validator = _get_validator()
    store = _get_store()

    try:
        # Case 1: Validate existing staged pack
        if pack_id:
            pack = store.get_pack(pack_id)
            if not pack:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Pack '{pack_id}' not found",
                    }
                )

            result = validator.validate_pack(
                pack,
                pack_root=Path(pack.staging_path) if pack.staging_path else None,
                check_file_integrity=True,
            )

            # Update pack state based on validation
            if result.valid:
                store.update_pack_state(
                    pack_id,
                    PackState.VALIDATED,
                    "Validation passed",
                )
            else:
                pack.validation_errors = result.errors

            return json.dumps(
                {
                    "success": True,
                    "pack_id": pack_id,
                    "valid": result.valid,
                    "validation": result.to_dict(),
                },
                indent=2,
            )

        # Case 2: Validate manifest only
        if manifest_data:
            from ai.mcp_bridge.marketplace.models import PackManifest

            try:
                manifest = PackManifest(**manifest_data)
            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid manifest: {e}",
                    }
                )

            result = validator.validate_quick(manifest)

            return json.dumps(
                {
                    "success": True,
                    "valid": result.valid,
                    "validation": result.to_dict(),
                },
                indent=2,
            )

        # Case 3: Validate pack at path
        if pack_path:
            path = Path(pack_path)
            if not path.exists():
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Pack path not found: {pack_path}",
                    }
                )

            importer = _get_importer()
            try:
                # Import first (validates during import)
                pack = importer.import_from_directory(
                    path,
                    skip_validation=False,
                )

                return json.dumps(
                    {
                        "success": True,
                        "pack_id": pack.manifest.pack_id,
                        "valid": True,
                        "message": "Pack imported and validated successfully",
                    },
                    indent=2,
                )

            except Exception as e:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Validation failed: {e}",
                    }
                )

        return json.dumps(
            {
                "success": False,
                "error": "Must provide pack_id, manifest, or pack_path",
            }
        )

    except Exception as e:
        logger.error(f"Pack validation failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_pack_export(args: dict) -> str:
    """Export selected dynamic tools into a portable local pack.

    Creates a tool pack from currently registered dynamic tools, including
    manifest generation, checksums, and optional source file inclusion.

    Args:
        pack_id: Target pack ID (e.g., "org.example.tools")
        name: Human-readable pack name
        version: Pack version (default: "1.0.0")
        description: Pack description
        author: Pack author
        tools: List of tool names to include
        include_source: Include handler source files (default: true)

    Returns:
        JSON with export results
    """
    pack_id = args.get("pack_id", "")
    name = args.get("name", "")
    version = args.get("version", "1.0.0")
    description = args.get("description", "")
    author = args.get("author", "")
    tools = args.get("tools", [])
    include_source = args.get("include_source", True)

    if not pack_id:
        return json.dumps(
            {
                "success": False,
                "error": "pack_id is required",
            }
        )

    if not name:
        return json.dumps(
            {
                "success": False,
                "error": "name is required",
            }
        )

    if not tools:
        return json.dumps(
            {
                "success": False,
                "error": "tools list is required",
            }
        )

    try:
        request = PackExportRequest(
            pack_id=pack_id,
            name=name,
            version=version,
            description=description,
            author=author,
            tool_selection=tools,
            include_source_files=include_source,
        )

        exporter = _get_exporter()
        pack = exporter.export_tools(request)

        return json.dumps(
            {
                "success": True,
                "pack_id": pack.manifest.pack_id,
                "name": pack.manifest.name,
                "version": pack.manifest.version,
                "tool_count": len(pack.manifest.tools),
                "risk_tier": pack.manifest.risk_tier.value,
                "staged_at": pack.staged_at.isoformat(),
                "staging_path": pack.staging_path,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Pack export failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_pack_import(args: dict) -> str:
    """Import a local pack into a staging area after validation.

    Imports a tool pack from a directory or manifest data, validates it,
    and stages it for installation. Does not install or execute any code.

    Args:
        source_path: Path to pack directory
        manifest: Optional manifest data (JSON object)
        skip_validation: Skip validation (not recommended)

    Returns:
        JSON with import results
    """
    source_path = args.get("source_path", "")
    manifest_data = args.get("manifest")
    skip_validation = args.get("skip_validation", False)

    try:
        importer = _get_importer()

        if source_path:
            pack = importer.import_from_directory(
                source_path,
                skip_validation=skip_validation,
            )
        elif manifest_data:
            pack = importer.import_from_manifest(
                manifest_data,
                skip_validation=skip_validation,
            )
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": "Must provide source_path or manifest",
                }
            )

        return json.dumps(
            {
                "success": True,
                "pack_id": pack.manifest.pack_id,
                "name": pack.manifest.name,
                "version": pack.manifest.version,
                "state": pack.state.value,
                "tool_count": len(pack.manifest.tools),
                "risk_tier": pack.manifest.risk_tier.value,
                "staged_at": pack.staged_at.isoformat(),
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Pack import failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_pack_list(args: dict) -> str:
    """List staged/installed packs and validation state.

    Lists all tool packs in the marketplace with optional filtering
    by state, risk tier, or search query.

    Args:
        state_filter: Filter by state (staged, validated, installed, disabled)
        risk_tier: Filter by risk tier (low, medium, high, critical)
        search: Search in pack name/description
        include_removed: Include removed packs (default: false)
        include_details: Include full details (default: false)

    Returns:
        JSON with pack list
    """
    state_filter = args.get("state_filter")
    risk_tier = args.get("risk_tier")
    search = args.get("search", "")
    include_removed = args.get("include_removed", False)
    include_details = args.get("include_details", False)

    try:
        store = _get_store()

        # Build filter
        filter_criteria = PackListFilter(
            state_filter=PackState(state_filter) if state_filter else None,
            risk_tier_filter=RiskTier(risk_tier) if risk_tier else None,
            search_query=search,
            include_removed=include_removed,
        )

        packs = store.list_packs(filter_criteria)
        stats = store.get_stats()

        if include_details:
            pack_list = []
            for pack in packs:
                info = pack.to_summary()
                info["tools"] = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "annotations": t.annotations,
                    }
                    for t in pack.manifest.tools
                ]
                info["audit_log"] = pack.audit_log[-5:]  # Last 5 entries
                pack_list.append(info)
        else:
            pack_list = [p.to_summary() for p in packs]

        return json.dumps(
            {
                "success": True,
                "stats": stats.to_dict(),
                "pack_count": len(packs),
                "packs": pack_list,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Pack list failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_pack_install(args: dict) -> str:
    """Install a validated pack into the dynamic registry.

    Installs a validated tool pack, registering its tools with the
    P102 Dynamic Tool Registry and updating the allowlist. May require
    approval for high-risk packs.

    Args:
        pack_id: Pack ID to install
        force: Force installation even with warnings
        dry_run: Preview changes without installing
        request_approval: Request approval for high-risk packs

    Returns:
        JSON with installation results
    """
    pack_id = args.get("pack_id", "")
    force = args.get("force", False)
    dry_run = args.get("dry_run", False)
    request_approval = args.get("request_approval", False)

    if not pack_id:
        return json.dumps(
            {
                "success": False,
                "error": "pack_id is required",
            }
        )

    try:
        installer = _get_installer()

        # Check prerequisites first
        prereqs = installer.check_install_prerequisites(pack_id)

        if not prereqs["can_install"]:
            # Check if approval is needed
            if prereqs["checks"].get("requires_approval") and request_approval:
                approval_result = installer.request_approval(pack_id)
                return json.dumps(
                    {
                        "success": False,
                        "error": "Approval required for high-risk pack",
                        "approval_requested": True,
                        "governance_flags": approval_result.get("governance_flags", []),
                    },
                    indent=2,
                )

            return json.dumps(
                {
                    "success": False,
                    "error": f"Cannot install: {prereqs.get('error', 'Unknown error')}",
                    "checks": prereqs.get("checks", {}),
                },
                indent=2,
            )

        # Perform installation
        result = installer.install_pack(
            pack_id,
            force=force,
            dry_run=dry_run,
        )

        return json.dumps(
            {
                "success": result.success,
                "pack_id": pack_id,
                "dry_run": dry_run,
                "tools_installed": result.tools_installed,
                "tools_skipped": result.tools_skipped,
                "error_count": len(result.errors),
                "errors": result.errors,
                "governance_flags": result.governance_flags,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Pack installation failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


async def handle_tool_pack_remove(args: dict) -> str:
    """Remove or disable an installed pack safely.

    Removes an installed pack, unregistering its tools and optionally
    preserving audit history. Can also disable packs instead of removing.

    Args:
        pack_id: Pack ID to remove
        disable_only: Disable instead of remove (default: false)
        preserve_allowlist: Keep allowlist entries (default: false)
        preserve_audit: Preserve audit trail (default: true)
        reason: Reason for removal

    Returns:
        JSON with removal results
    """
    pack_id = args.get("pack_id", "")
    disable_only = args.get("disable_only", False)
    preserve_allowlist = args.get("preserve_allowlist", False)
    preserve_audit = args.get("preserve_audit", True)
    reason = args.get("reason", "")

    if not pack_id:
        return json.dumps(
            {
                "success": False,
                "error": "pack_id is required",
            }
        )

    try:
        installer = _get_installer()

        if disable_only:
            result = installer.disable_pack(pack_id, reason)
        else:
            result = installer.remove_pack(
                pack_id,
                preserve_allowlist=preserve_allowlist,
                preserve_audit=preserve_audit,
            )

        return json.dumps(
            {
                "success": result.get("success", False),
                "pack_id": pack_id,
                "action": "disabled" if disable_only else "removed",
                **result,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Pack removal failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )


# Export handlers for registration
TOOL_HANDLERS = {
    "tool.pack_validate": handle_tool_pack_validate,
    "tool.pack_export": handle_tool_pack_export,
    "tool.pack_import": handle_tool_pack_import,
    "tool.pack_list": handle_tool_pack_list,
    "tool.pack_install": handle_tool_pack_install,
    "tool.pack_remove": handle_tool_pack_remove,
}
