"""Tool Pack Import/Export for MCP Marketplace.

P103: MCP Tool Marketplace + Tool Pack Import/Export

Handles exporting tool definitions from the dynamic registry and
importing tool packs from external sources. Creates portable,
checksummed tool packs that can be shared and installed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ai.mcp_bridge.dynamic_registry import get_registry
from ai.mcp_bridge.marketplace.models import (
    PackExportRequest,
    PackManifest,
    PackState,
    RiskTier,
    ToolDefinition,
    ToolPack,
    ToolPackFile,
)
from ai.mcp_bridge.marketplace.pack_store import PackStore
from ai.mcp_bridge.marketplace.pack_validator import PackValidator

logger = logging.getLogger("ai.mcp_bridge.marketplace.import_export")


class ImportExportError(Exception):
    """Exception raised for import/export errors."""

    pass


class PackExporter:
    """Exporter for tool packs.

    Creates portable tool packs from dynamically registered tools,
    including manifest generation, checksums, and file packaging.
    """

    def __init__(self, store: PackStore | None = None) -> None:
        """Initialize exporter.

        Args:
            store: Optional pack store for staging exported packs
        """
        self.store = store or PackStore()
        self.registry = get_registry()

    def export_tools(
        self,
        request: PackExportRequest,
    ) -> ToolPack:
        """Export selected tools to a pack.

        Args:
            request: Export request with tool selection and metadata

        Returns:
            ToolPack with manifest and staged files

        Raises:
            ImportExportError: If export fails
        """
        # Get tools from registry
        selected_tools = []
        for tool_name in request.tool_selection:
            tool = self.registry.get_tool(tool_name)
            if not tool:
                raise ImportExportError(f"Tool not found in registry: {tool_name}")
            selected_tools.append(tool)

        if not selected_tools:
            raise ImportExportError("No tools selected for export")

        # Build tool definitions
        tool_definitions = []
        for tool in selected_tools:
            tool_def = ToolDefinition(
                name=tool.name,
                description=tool.definition.get("description", ""),
                handler_module=tool.definition.get("module", ""),
                handler_function=tool.definition.get("function", ""),
                args=tool.definition.get("args", {}),
                annotations=tool.definition.get("annotations", {}),
            )
            tool_definitions.append(tool_def)

        # Determine risk tier based on tools
        risk_tier = self._determine_risk_tier(selected_tools)

        # Build manifest
        manifest = PackManifest(
            pack_id=request.pack_id,
            name=request.name,
            version=request.version,
            description=request.description,
            author=request.author,
            source="local_export",
            risk_tier=risk_tier,
            tools=tool_definitions,
        )

        # Create pack
        pack = ToolPack(manifest=manifest)

        # Collect files if requested
        files: dict[str, bytes] = {}
        if request.include_source_files:
            files = self._collect_source_files(selected_tools)
            # Compute file checksums
            manifest.files = self._compute_file_checksums(files)

        # Stage pack
        staged_pack = self.store.stage_pack(pack, files)

        logger.info(
            f"Exported {len(tool_definitions)} tools to pack '{request.pack_id}' v{request.version}"
        )

        return staged_pack

    def _determine_risk_tier(
        self,
        tools: list[Any],
    ) -> RiskTier:
        """Determine risk tier for a set of tools.

        Args:
            tools: List of tools to assess

        Returns:
            Highest applicable risk tier
        """
        has_destructive = any(
            t.definition.get("annotations", {}).get("destructive", False) for t in tools
        )
        has_system_access = any(t.name.startswith(("system.", "security.")) for t in tools)

        if has_system_access and has_destructive:
            return RiskTier.CRITICAL
        elif has_system_access or has_destructive:
            return RiskTier.HIGH
        elif len(tools) > 10:
            return RiskTier.MEDIUM
        else:
            return RiskTier.LOW

    def _collect_source_files(
        self,
        tools: list[Any],
    ) -> dict[str, bytes]:
        """Collect source files for tools.

        Args:
            tools: List of tools

        Returns:
            Dict mapping relative paths to file contents
        """
        files: dict[str, bytes] = {}

        for tool in tools:
            module_path = tool.definition.get("module", "").replace(".", "/")
            if not module_path:
                continue

            # Look for Python file
            py_file = Path(f"ai/{module_path}.py")
            if py_file.exists():
                try:
                    content = py_file.read_bytes()
                    files[f"src/{module_path}.py"] = content
                except OSError as e:
                    logger.warning(f"Failed to read source file for {tool.name}: {e}")

        return files

    def _compute_file_checksums(
        self,
        files: dict[str, bytes],
    ) -> list[ToolPackFile]:
        """Compute checksums for files.

        Args:
            files: Dict of file paths to contents

        Returns:
            List of ToolPackFile with checksums
        """
        pack_files = []
        for file_path, content in files.items():
            checksum = hashlib.sha256(content).hexdigest()
            pack_files.append(
                ToolPackFile(
                    path=file_path,
                    checksum=checksum,
                    size_bytes=len(content),
                )
            )
        return pack_files

    def export_to_allowlist_patch(
        self,
        pack_id: str,
    ) -> dict[str, Any]:
        """Generate an allowlist patch from an exported pack.

        Args:
            pack_id: Pack ID to export

        Returns:
            Allowlist patch dictionary
        """
        pack = self.store.get_pack(pack_id)
        if not pack:
            raise ImportExportError(f"Pack not found: {pack_id}")

        tools = {}
        for tool_def in pack.manifest.tools:
            tool_entry = {
                "description": tool_def.description,
                "source": "python",
                "module": tool_def.handler_module,
                "function": tool_def.handler_function,
            }
            if tool_def.args:
                tool_entry["args"] = tool_def.args
            if tool_def.annotations:
                tool_entry["annotations"] = tool_def.annotations

            tools[tool_def.name] = tool_entry

        return {"tools": tools}


class PackImporter:
    """Importer for tool packs.

    Handles importing tool packs from external sources, validating them,
    and staging them for installation.
    """

    def __init__(self, store: PackStore | None = None) -> None:
        """Initialize importer.

        Args:
            store: Optional pack store for staging imported packs
        """
        self.store = store or PackStore()
        self.validator = PackValidator()

    def import_from_directory(
        self,
        pack_dir: str | Path,
        skip_validation: bool = False,
    ) -> ToolPack:
        """Import a pack from a directory.

        Args:
            pack_dir: Directory containing pack files
            skip_validation: Skip validation (not recommended)

        Returns:
            Imported and staged ToolPack

        Raises:
            ImportExportError: If import fails
        """
        pack_path = Path(pack_dir)

        if not pack_path.exists():
            raise ImportExportError(f"Pack directory not found: {pack_dir}")

        # Load manifest
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.exists():
            raise ImportExportError(f"Manifest not found in {pack_dir}")

        try:
            with open(manifest_path) as f:
                manifest_data = json.load(f)
            manifest = PackManifest(**manifest_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ImportExportError(f"Failed to parse manifest: {e}") from e

        # Create pack
        pack = ToolPack(manifest=manifest)

        # Collect files
        files_dir = pack_path / "files"
        files: dict[str, bytes] = {}
        if files_dir.exists():
            for file_path in files_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(files_dir))
                    files[rel_path] = file_path.read_bytes()

        # Validate before staging
        if not skip_validation:
            validation_result = self.validator.validate_pack(pack, pack_path)
            if not validation_result.valid:
                error_msg = "; ".join(validation_result.errors[:5])
                raise ImportExportError(f"Pack validation failed: {error_msg}")

        # Stage pack
        staged_pack = self.store.stage_pack(pack, files)

        # If validation passed, mark as validated
        if not skip_validation:
            staged_pack.transition_to(PackState.VALIDATED, "Auto-validated on import")
            self.store.update_pack_state(
                pack.manifest.pack_id, PackState.VALIDATED, "Auto-validated on import"
            )

        logger.info(
            f"Imported pack '{manifest.pack_id}' v{manifest.version} "
            f"with {len(manifest.tools)} tools"
        )

        return staged_pack

    def import_from_manifest(
        self,
        manifest_data: dict[str, Any],
        files: dict[str, bytes] | None = None,
        skip_validation: bool = False,
    ) -> ToolPack:
        """Import a pack from manifest data.

        Args:
            manifest_data: Manifest dictionary
            files: Optional dict of file contents
            skip_validation: Skip validation (not recommended)

        Returns:
            Imported and staged ToolPack
        """
        try:
            manifest = PackManifest(**manifest_data)
        except ValueError as e:
            raise ImportExportError(f"Invalid manifest: {e}") from e

        # Create pack
        pack = ToolPack(manifest=manifest)

        # Validate
        if not skip_validation:
            validation_result = self.validator.validate_quick(manifest)
            if not validation_result.valid:
                error_msg = "; ".join(validation_result.errors[:5])
                raise ImportExportError(f"Pack validation failed: {error_msg}")

        # Stage
        staged_pack = self.store.stage_pack(pack, files or {})

        if not skip_validation:
            staged_pack.transition_to(PackState.VALIDATED, "Auto-validated on import")
            self.store.update_pack_state(
                pack.manifest.pack_id, PackState.VALIDATED, "Auto-validated on import"
            )

        logger.info(f"Imported pack '{manifest.pack_id}' from manifest data")

        return staged_pack

    def create_bundle(
        self,
        pack_id: str,
        output_path: str | Path,
    ) -> Path:
        """Create a portable bundle from a staged pack.

        Args:
            pack_id: Pack to bundle
            output_path: Output file path (.zip)

        Returns:
            Path to created bundle
        """
        pack = self.store.get_pack(pack_id)
        if not pack:
            raise ImportExportError(f"Pack not found: {pack_id}")

        source_path = Path(pack.staging_path or pack.install_path)
        if not source_path.exists():
            raise ImportExportError(f"Pack files not found for: {pack_id}")

        output_file = Path(output_path)
        if output_file.suffix != ".zip":
            output_file = output_file.with_suffix(".zip")

        # Create zip archive
        shutil.make_archive(
            str(output_file.with_suffix("")),
            "zip",
            root_dir=source_path,
        )

        logger.info(f"Created bundle for pack '{pack_id}': {output_file}")
        return output_file

    def extract_bundle(
        self,
        bundle_path: str | Path,
        temp: bool = True,
    ) -> Path:
        """Extract a bundle to a directory.

        Args:
            bundle_path: Path to bundle file
            temp: Whether to extract to temp directory

        Returns:
            Path to extracted directory
        """
        bundle_file = Path(bundle_path)
        if not bundle_file.exists():
            raise ImportExportError(f"Bundle not found: {bundle_path}")

        if temp:
            extract_dir = Path(tempfile.mkdtemp(prefix="mcp_pack_"))
        else:
            extract_dir = Path(bundle_file.stem)

        shutil.unpack_archive(bundle_file, extract_dir)

        logger.info(f"Extracted bundle to: {extract_dir}")
        return extract_dir


class PackMigrationHelper:
    """Helper for migrating between pack versions.

    Provides utilities for analyzing differences between pack versions
    and generating migration guides.
    """

    @staticmethod
    def compare_packs(
        old_pack: ToolPack,
        new_pack: ToolPack,
    ) -> dict[str, Any]:
        """Compare two versions of a pack.

        Args:
            old_pack: Original pack
            new_pack: New pack version

        Returns:
            Comparison results
        """
        old_tools = {t.name: t for t in old_pack.manifest.tools}
        new_tools = {t.name: t for t in new_pack.manifest.tools}

        added = set(new_tools.keys()) - set(old_tools.keys())
        removed = set(old_tools.keys()) - set(new_tools.keys())
        common = set(old_tools.keys()) & set(new_tools.keys())

        modified = []
        for tool_name in common:
            old_def = old_tools[tool_name]
            new_def = new_tools[tool_name]
            if old_def != new_def:
                modified.append(tool_name)

        return {
            "added_tools": list(added),
            "removed_tools": list(removed),
            "modified_tools": modified,
            "old_version": old_pack.manifest.version,
            "new_version": new_pack.manifest.version,
            "breaking_changes": len(removed) > 0 or len(modified) > 0,
        }

    @staticmethod
    def generate_migration_guide(
        comparison: dict[str, Any],
    ) -> str:
        """Generate a migration guide from comparison results.

        Args:
            comparison: Comparison results from compare_packs

        Returns:
            Migration guide text
        """
        lines = [
            f"# Migration Guide: v{comparison['old_version']} -> v{comparison['new_version']}",
            "",
        ]

        if comparison["breaking_changes"]:
            lines.append("## Breaking Changes")
            lines.append("")

        if comparison["removed_tools"]:
            lines.append("### Removed Tools")
            for tool in comparison["removed_tools"]:
                lines.append(f"- `{tool}`")
            lines.append("")

        if comparison["modified_tools"]:
            lines.append("### Modified Tools")
            for tool in comparison["modified_tools"]:
                lines.append(f"- `{tool}`")
            lines.append("")

        if comparison["added_tools"]:
            lines.append("## New Tools")
            for tool in comparison["added_tools"]:
                lines.append(f"- `{tool}`")
            lines.append("")

        return "\n".join(lines)
