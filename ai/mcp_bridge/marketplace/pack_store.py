"""Tool Pack Storage Management for MCP Marketplace.

P103: MCP Tool Marketplace + Tool Pack Import/Export

Manages storage of tool packs including staging, installation, and retrieval.
Uses atomic file operations and maintains audit trails.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from ai.mcp_bridge.marketplace.models import (
    MarketplaceStats,
    PackListFilter,
    PackManifest,
    PackState,
    ToolPack,
)

logger = logging.getLogger("ai.mcp_bridge.marketplace.store")


class PackStoreError(Exception):
    """Exception raised for pack storage errors."""

    pass


class PackStore:
    """Storage manager for tool packs.

    Manages the lifecycle of tool packs from staging through installation,
    including atomic file operations and audit trail maintenance.

    Storage layout:
        <base_dir>/
            staging/          # Staged packs (imported but not validated)
                <pack_id>/
                    manifest.json
                    files/
            installed/        # Installed packs
                <pack_id>/
                    manifest.json
                    files/
            index.json        # Index of all packs
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        """Initialize pack store.

        Args:
            base_dir: Base directory for pack storage.
                     Defaults to ~/security/mcp-tool-packs
        """
        if base_dir is None:
            base_dir = Path.home() / "security" / "mcp-tool-packs"

        self.base_dir = Path(base_dir)
        self.staging_dir = self.base_dir / "staging"
        self.installed_dir = self.base_dir / "installed"
        self.index_file = self.base_dir / "index.json"

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(exist_ok=True)
        self.installed_dir.mkdir(exist_ok=True)

    def _atomic_write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file atomically.

        Args:
            path: Target file path
            data: Data to write
        """
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        temp_path.replace(path)

    def _load_index(self) -> dict[str, Any]:
        """Load pack index.

        Returns:
            Index dictionary
        """
        if not self.index_file.exists():
            return {"packs": {}, "version": "1.0"}

        try:
            with open(self.index_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load index, creating new: {e}")
            return {"packs": {}, "version": "1.0"}

    def _save_index(self, index: dict[str, Any]) -> None:
        """Save pack index atomically.

        Args:
            index: Index dictionary
        """
        self._atomic_write_json(self.index_file, index)

    def _get_pack_path(self, pack_id: str, state: PackState) -> Path:
        """Get storage path for a pack.

        Args:
            pack_id: Pack identifier
            state: Pack state

        Returns:
            Path to pack directory
        """
        if state in (PackState.STAGED, PackState.VALIDATED):
            return self.staging_dir / pack_id
        elif state in (PackState.INSTALLED, PackState.DISABLED):
            return self.installed_dir / pack_id
        else:
            # For removed packs, we don't need a path
            raise PackStoreError(f"Cannot get path for pack in state: {state}")

    def stage_pack(
        self,
        pack: ToolPack,
        files: dict[str, bytes] | None = None,
    ) -> ToolPack:
        """Stage a tool pack for validation.

        Args:
            pack: Tool pack to stage
            files: Optional dict of file paths to file contents

        Returns:
            Updated ToolPack with staging path set

        Raises:
            PackStoreError: If staging fails
        """
        pack_id = pack.manifest.pack_id

        # Check if pack already exists
        existing = self.get_pack(pack_id)
        if existing and existing.state != PackState.REMOVED:
            raise PackStoreError(
                f"Pack '{pack_id}' already exists in state: {existing.state.value}"
            )

        # Create staging directory
        staging_path = self.staging_dir / pack_id
        if staging_path.exists():
            shutil.rmtree(staging_path)
        staging_path.mkdir(parents=True)

        # Write manifest
        manifest_path = staging_path / "manifest.json"
        self._atomic_write_json(manifest_path, pack.manifest.model_dump())

        # Write files if provided
        if files:
            files_dir = staging_path / "files"
            files_dir.mkdir(exist_ok=True)
            for file_path, content in files.items():
                target = files_dir / file_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "wb") as f:
                    f.write(content)

        # Update pack
        pack.staging_path = str(staging_path)
        pack.state = PackState.STAGED
        pack.add_audit_entry("staged", f"Staged at {staging_path}")

        # Update index
        index = self._load_index()
        index["packs"][pack_id] = {
            "state": pack.state.value,
            "staged_at": pack.staged_at.isoformat(),
            "version": pack.manifest.version,
        }
        self._save_index(index)

        logger.info(f"Staged pack '{pack_id}' at {staging_path}")
        return pack

    def get_pack(self, pack_id: str) -> ToolPack | None:
        """Get a pack by ID.

        Args:
            pack_id: Pack identifier

        Returns:
            ToolPack if found, None otherwise
        """
        index = self._load_index()
        if pack_id not in index["packs"]:
            return None

        pack_info = index["packs"][pack_id]
        state = PackState(pack_info["state"])

        # Removed packs are not retrievable
        if state == PackState.REMOVED:
            return None

        try:
            pack_path = self._get_pack_path(pack_id, state)
            manifest_path = pack_path / "manifest.json"

            if not manifest_path.exists():
                logger.warning(f"Manifest missing for pack '{pack_id}'")
                return None

            with open(manifest_path) as f:
                manifest_data = json.load(f)

            manifest = PackManifest(**manifest_data)
            pack = ToolPack(
                manifest=manifest,
                state=state,
                staged_at=pack_info.get("staged_at", ""),
                staging_path=str(pack_path)
                if state in (PackState.STAGED, PackState.VALIDATED)
                else "",
                install_path=str(pack_path)
                if state in (PackState.INSTALLED, PackState.DISABLED)
                else "",
            )

            # Restore additional metadata
            if "installed_at" in pack_info:
                from datetime import datetime

                pack.installed_at = datetime.fromisoformat(pack_info["installed_at"])

            return pack

        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load pack '{pack_id}': {e}")
            return None

    def update_pack_state(
        self,
        pack_id: str,
        new_state: PackState,
        reason: str = "",
    ) -> ToolPack | None:
        """Update pack state.

        Args:
            pack_id: Pack identifier
            new_state: New state to transition to
            reason: Reason for state change

        Returns:
            Updated ToolPack if successful, None if pack not found
        """
        pack = self.get_pack(pack_id)
        if not pack:
            return None

        old_state = pack.state
        pack.transition_to(new_state, reason)

        # Handle physical moves between directories
        if old_state in (PackState.STAGED, PackState.VALIDATED) and new_state in (
            PackState.INSTALLED,
            PackState.DISABLED,
        ):
            # Move from staging to installed
            old_path = self.staging_dir / pack_id
            new_path = self.installed_dir / pack_id

            if old_path.exists():
                if new_path.exists():
                    shutil.rmtree(new_path)
                shutil.move(str(old_path), str(new_path))
                pack.install_path = str(new_path)
                pack.staging_path = ""

        # Update index
        index = self._load_index()
        if pack_id in index["packs"]:
            index["packs"][pack_id]["state"] = new_state.value
            if new_state == PackState.INSTALLED:
                from datetime import datetime

                index["packs"][pack_id]["installed_at"] = datetime.utcnow().isoformat()
            if new_state == PackState.REMOVED:
                index["packs"][pack_id]["removed"] = True

            self._save_index(index)

        # Save updated manifest with audit log
        if pack.install_path or pack.staging_path:
            manifest_path = Path(pack.install_path or pack.staging_path) / "manifest.json"
            if manifest_path.exists():
                # Update the stored manifest
                self._atomic_write_json(manifest_path, pack.manifest.model_dump())

        logger.info(f"Pack '{pack_id}' transitioned: {old_state.value} -> {new_state.value}")
        return pack

    def list_packs(self, filter_criteria: PackListFilter | None = None) -> list[ToolPack]:
        """List packs matching filter criteria.

        Args:
            filter_criteria: Optional filter criteria

        Returns:
            List of matching ToolPacks
        """
        filter_criteria = filter_criteria or PackListFilter()
        index = self._load_index()

        packs = []
        for pack_id, pack_info in index["packs"].items():
            # Skip removed unless requested
            state = PackState(pack_info["state"])
            if state == PackState.REMOVED and not filter_criteria.include_removed:
                continue

            # Apply state filter
            if filter_criteria.state_filter and state != filter_criteria.state_filter:
                continue

            # Load pack for further filtering
            pack = self.get_pack(pack_id)
            if not pack:
                continue

            # Apply risk tier filter
            if filter_criteria.risk_tier_filter:
                if pack.manifest.risk_tier != filter_criteria.risk_tier_filter:
                    continue

            # Apply search query
            if filter_criteria.search_query:
                query = filter_criteria.search_query.lower()
                searchable = f"{pack.manifest.name} {pack.manifest.description}".lower()
                if query not in searchable:
                    continue

            packs.append(pack)

        return packs

    def remove_pack(self, pack_id: str, preserve_audit: bool = True) -> bool:
        """Remove a pack.

        Args:
            pack_id: Pack identifier
            preserve_audit: Whether to preserve audit trail in index

        Returns:
            True if removed, False if not found
        """
        pack = self.get_pack(pack_id)
        if not pack:
            return False

        # Remove physical directories
        paths_to_remove = []
        if pack.staging_path:
            paths_to_remove.append(Path(pack.staging_path))
        if pack.install_path:
            paths_to_remove.append(Path(pack.install_path))

        for path in paths_to_remove:
            if path.exists():
                shutil.rmtree(path)

        # Update index
        index = self._load_index()
        if pack_id in index["packs"]:
            if preserve_audit:
                # Mark as removed but keep entry for audit
                from datetime import datetime

                index["packs"][pack_id]["state"] = PackState.REMOVED.value
                index["packs"][pack_id]["removed_at"] = datetime.utcnow().isoformat()
            else:
                # Completely remove
                del index["packs"][pack_id]

            self._save_index(index)

        logger.info(f"Removed pack '{pack_id}' (preserve_audit={preserve_audit})")
        return True

    def get_pack_files(self, pack_id: str) -> dict[str, Path]:
        """Get paths to all files in a pack.

        Args:
            pack_id: Pack identifier

        Returns:
            Dict mapping relative paths to absolute paths
        """
        pack = self.get_pack(pack_id)
        if not pack:
            return {}

        pack_path = Path(pack.install_path or pack.staging_path)
        files_dir = pack_path / "files"

        if not files_dir.exists():
            return {}

        files = {}
        for file_path in files_dir.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(files_dir))
                files[rel_path] = file_path

        return files

    def read_pack_file(self, pack_id: str, file_path: str) -> bytes | None:
        """Read a file from a pack.

        Args:
            pack_id: Pack identifier
            file_path: Relative path within pack files

        Returns:
            File contents or None if not found
        """
        files = self.get_pack_files(pack_id)
        if file_path not in files:
            return None

        try:
            with open(files[file_path], "rb") as f:
                return f.read()
        except OSError as e:
            logger.error(f"Failed to read file '{file_path}' from pack '{pack_id}': {e}")
            return None

    def get_stats(self) -> MarketplaceStats:
        """Get marketplace statistics.

        Returns:
            MarketplaceStats with current statistics
        """
        index = self._load_index()
        stats = MarketplaceStats()

        total_size = 0
        tool_count = 0

        for pack_id, pack_info in index["packs"].items():
            state = PackState(pack_info["state"])

            stats.total_packs += 1

            if state == PackState.STAGED:
                stats.staged_count += 1
            elif state == PackState.VALIDATED:
                stats.validated_count += 1
            elif state == PackState.INSTALLED:
                stats.installed_count += 1
                # Count tools
                pack = self.get_pack(pack_id)
                if pack:
                    tool_count += len(pack.manifest.tools)
            elif state == PackState.DISABLED:
                stats.disabled_count += 1

            # Calculate size
            try:
                pack_path = self._get_pack_path(pack_id, state)
                if pack_path.exists():
                    total_size += sum(f.stat().st_size for f in pack_path.rglob("*") if f.is_file())
            except PackStoreError:
                pass

        stats.tool_count = tool_count
        stats.storage_used_bytes = total_size

        return stats

    def export_pack(self, pack_id: str, output_dir: str | Path) -> Path | None:
        """Export a pack to a directory.

        Args:
            pack_id: Pack identifier
            output_dir: Output directory for export

        Returns:
            Path to exported pack directory or None if not found
        """
        pack = self.get_pack(pack_id)
        if not pack:
            return None

        output_path = Path(output_dir) / f"{pack_id}-{pack.manifest.version}"

        # Get source path
        source_path = Path(pack.install_path or pack.staging_path)
        if not source_path.exists():
            return None

        # Copy to output
        if output_path.exists():
            shutil.rmtree(output_path)
        shutil.copytree(source_path, output_path)

        logger.info(f"Exported pack '{pack_id}' to {output_path}")
        return output_path

    def cleanup_staging(self, max_age_hours: float = 24.0) -> int:
        """Clean up old staged packs.

        Args:
            max_age_hours: Maximum age in hours for staged packs

        Returns:
            Number of packs cleaned up
        """
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        index = self._load_index()
        cleaned = 0

        for pack_id, pack_info in list(index["packs"].items()):
            if pack_info.get("state") != PackState.STAGED.value:
                continue

            staged_at = datetime.fromisoformat(pack_info.get("staged_at", "1970-01-01"))
            if staged_at < cutoff:
                self.remove_pack(pack_id, preserve_audit=True)
                cleaned += 1

        logger.info(f"Cleaned up {cleaned} old staged packs")
        return cleaned
