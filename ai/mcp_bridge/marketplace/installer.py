"""Tool Pack Installer for MCP Marketplace.

P103: MCP Tool Marketplace + Tool Pack Import/Export

Handles installation of validated tool packs into the dynamic registry,
including governance policy checks, allowlist updates, and audit trail
maintenance. Integrates with P102 Dynamic Tool Discovery.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from ai.config import CONFIGS_DIR
from ai.mcp_bridge.dynamic_registry import get_registry
from ai.mcp_bridge.governance import ToolGovernanceEngine
from ai.mcp_bridge.marketplace.models import (
    PackInstallResult,
    PackManifest,
    PackState,
    RiskTier,
    ToolPack,
)
from ai.mcp_bridge.marketplace.pack_store import PackStore
from ai.mcp_bridge.marketplace.pack_validator import PackValidator

logger = logging.getLogger("ai.mcp_bridge.marketplace.installer")


class PackInstallError(Exception):
    """Exception raised for pack installation errors."""

    pass


class PackInstaller:
    """Installer for tool packs.

    Installs validated tool packs into the dynamic registry, integrating
    with P102 Dynamic Tool Discovery and P101 Governance systems.

    Features:
    - Governance policy enforcement
    - Risk tier-based approval requirements
    - Allowlist integration
    - Audit trail maintenance
    - Safe rollback on failure
    """

    # Risk tiers requiring explicit approval
    APPROVAL_REQUIRED_TIERS = {RiskTier.HIGH, RiskTier.CRITICAL}

    def __init__(
        self,
        store: PackStore | None = None,
        require_approval: bool = True,
    ) -> None:
        """Initialize installer.

        Args:
            store: Optional pack store
            require_approval: Whether to require approval for high-risk packs
        """
        self.store = store or PackStore()
        self.registry = get_registry()
        self.governance = ToolGovernanceEngine()
        self.validator = PackValidator()
        self.require_approval = require_approval

        # Track pending approvals
        self._pending_approvals: set[str] = set()

    def check_install_prerequisites(
        self,
        pack_id: str,
    ) -> dict[str, Any]:
        """Check prerequisites for installation.

        Args:
            pack_id: Pack to check

        Returns:
            Dict with prerequisite check results
        """
        pack = self.store.get_pack(pack_id)

        if not pack:
            return {
                "can_install": False,
                "error": f"Pack '{pack_id}' not found",
            }

        checks = {
            "pack_exists": True,
            "is_validated": pack.state == PackState.VALIDATED,
            "is_installed": pack.state == PackState.INSTALLED,
            "is_disabled": pack.state == PackState.DISABLED,
            "risk_tier": pack.manifest.risk_tier.value,
            "requires_approval": pack.manifest.risk_tier in self.APPROVAL_REQUIRED_TIERS,
            "has_approval": pack_id in self._pending_approvals,
        }

        # Determine if can install
        can_install = checks["is_validated"] or checks["is_disabled"]

        if checks["requires_approval"] and self.require_approval:
            can_install = can_install and checks["has_approval"]

        if checks["is_installed"]:
            can_install = False

        return {
            "can_install": can_install,
            "checks": checks,
            "pack_summary": pack.to_summary(),
        }

    def request_approval(self, pack_id: str, approver: str = "") -> dict[str, Any]:
        """Request approval for a high-risk pack.

        Args:
            pack_id: Pack to approve
            approver: Approver identifier

        Returns:
            Approval request result
        """
        pack = self.store.get_pack(pack_id)
        if not pack:
            return {"success": False, "error": f"Pack '{pack_id}' not found"}

        if pack.manifest.risk_tier not in self.APPROVAL_REQUIRED_TIERS:
            return {
                "success": False,
                "error": f"Pack '{pack_id}' does not require approval "
                f"(risk tier: {pack.manifest.risk_tier.value})",
            }

        self._pending_approvals.add(pack_id)

        # Add audit entry
        pack.add_audit_entry(
            action="approval_requested",
            details=f"Requested by {approver or 'system'}",
        )

        return {
            "success": True,
            "pack_id": pack_id,
            "requires_approval": True,
            "risk_tier": pack.manifest.risk_tier.value,
            "governance_flags": self._generate_governance_flags(pack),
        }

    def approve_pack(self, pack_id: str, approver: str = "") -> dict[str, Any]:
        """Approve a pack for installation.

        Args:
            pack_id: Pack to approve
            approver: Approver identifier

        Returns:
            Approval result
        """
        if pack_id not in self._pending_approvals:
            return {
                "success": False,
                "error": f"No pending approval request for '{pack_id}'",
            }

        pack = self.store.get_pack(pack_id)
        if not pack:
            return {"success": False, "error": f"Pack '{pack_id}' not found"}

        self._pending_approvals.discard(pack_id)

        # Add audit entry
        pack.add_audit_entry(
            action="approved",
            details=f"Approved by {approver or 'system'}",
        )

        return {
            "success": True,
            "pack_id": pack_id,
            "approver": approver,
            "can_install": True,
        }

    def install_pack(
        self,
        pack_id: str,
        force: bool = False,
        dry_run: bool = False,
    ) -> PackInstallResult:
        """Install a validated pack.

        Args:
            pack_id: Pack to install
            force: Force installation even if validation warnings exist
            dry_run: Preview changes without installing

        Returns:
            PackInstallResult with installation details
        """
        result = PackInstallResult(pack_id=pack_id)

        # Get pack
        pack = self.store.get_pack(pack_id)
        if not pack:
            result.errors.append(f"Pack '{pack_id}' not found")
            return result

        # Check prerequisites
        prereqs = self.check_install_prerequisites(pack_id)
        if not prereqs["can_install"] and not force:
            result.errors.append(f"Cannot install: {prereqs['checks']}")
            return result

        # Re-validate if needed
        if pack.state not in (PackState.VALIDATED, PackState.DISABLED):
            if not force:
                result.errors.append(f"Pack must be validated (current: {pack.state.value})")
                return result

        # Generate governance flags
        result.governance_flags = self._generate_governance_flags(pack)

        # Collect tools to install
        tools_to_install = []
        for tool_def in pack.manifest.tools:
            # Check if tool already exists
            existing = self.registry.get_tool(tool_def.name)
            if existing:
                result.tools_skipped.append(tool_def.name)
                continue
            tools_to_install.append(tool_def)

        if dry_run:
            result.success = True
            result.tools_installed = [t.name for t in tools_to_install]
            return result

        # Install tools
        for tool_def in tools_to_install:
            try:
                # Build tool definition for registry
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

                # Register with P102 registry
                success = self.registry.register_tool(
                    name=tool_def.name,
                    definition=tool_entry,
                    source=f"marketplace:{pack_id}",
                )

                if success:
                    result.tools_installed.append(tool_def.name)
                else:
                    result.errors.append(f"Failed to register tool: {tool_def.name}")

            except Exception as e:
                logger.error(f"Failed to install tool {tool_def.name}: {e}")
                result.errors.append(f"Installation error for {tool_def.name}: {e}")

        # Update allowlist with installed tools
        if result.tools_installed:
            self._update_allowlist(pack.manifest, result.tools_installed)

        # Update pack state
        if result.tools_installed or not result.errors:
            self.store.update_pack_state(
                pack_id,
                PackState.INSTALLED,
                f"Installed {len(result.tools_installed)} tools",
            )
            result.success = True
        else:
            # Rollback on complete failure
            self._rollback_installation(pack_id, result.tools_installed)

        return result

    def _update_allowlist(
        self,
        manifest: PackManifest,
        installed_tools: list[str],
    ) -> None:
        """Update the allowlist with installed tools.

        Args:
            manifest: Pack manifest
            installed_tools: List of tool names that were installed
        """
        allowlist_path = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"

        try:
            # Load existing allowlist
            with open(allowlist_path) as f:
                data = yaml.safe_load(f) or {}

            tools = data.get("tools", {})

            # Add new tools
            for tool_def in manifest.tools:
                if tool_def.name not in installed_tools:
                    continue

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

                # Mark as from marketplace
                tool_entry["marketpack"] = {
                    "pack_id": manifest.pack_id,
                    "version": manifest.version,
                }

                tools[tool_def.name] = tool_entry

            # Write updated allowlist
            data["tools"] = tools

            # Atomic write
            temp_path = allowlist_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=True)
            temp_path.replace(allowlist_path)

            logger.info(
                f"Updated allowlist with {len(installed_tools)} tools from {manifest.pack_id}"
            )

        except Exception as e:
            logger.error(f"Failed to update allowlist: {e}")
            raise PackInstallError(f"Allowlist update failed: {e}") from e

    def _rollback_installation(
        self,
        pack_id: str,
        installed_tools: list[str],
    ) -> None:
        """Rollback a failed installation.

        Args:
            pack_id: Pack being installed
            installed_tools: Tools that were successfully installed
        """
        logger.warning(f"Rolling back installation of pack '{pack_id}'")

        for tool_name in installed_tools:
            try:
                self.registry.unregister_tool(tool_name)
                logger.info(f"Rolled back tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to rollback tool {tool_name}: {e}")

    def _generate_governance_flags(
        self,
        pack: ToolPack,
    ) -> list[dict[str, Any]]:
        """Generate governance flags for a pack.

        Args:
            pack: Tool pack

        Returns:
            List of governance flag dictionaries
        """
        flags = []

        # Risk tier flag
        if pack.manifest.risk_tier in (RiskTier.HIGH, RiskTier.CRITICAL):
            flags.append(
                {
                    "type": "high_risk",
                    "severity": pack.manifest.risk_tier.value,
                    "message": f"High-risk pack ({pack.manifest.risk_tier.value}) "
                    "requires additional scrutiny",
                }
            )

        # Check for destructive tools
        destructive_tools = [
            t.name for t in pack.manifest.tools if t.annotations.get("destructive", False)
        ]
        if destructive_tools:
            flags.append(
                {
                    "type": "destructive_tools",
                    "tools": destructive_tools,
                    "message": f"Pack contains {len(destructive_tools)} destructive tools",
                }
            )

        # Check for system namespace tools
        system_tools = [
            t.name for t in pack.manifest.tools if t.name.startswith(("system.", "security."))
        ]
        if system_tools:
            flags.append(
                {
                    "type": "system_namespace",
                    "tools": system_tools,
                    "message": f"Pack modifies {len(system_tools)} system namespace tools",
                }
            )

        # Required permissions
        if pack.manifest.required_permissions:
            flags.append(
                {
                    "type": "elevated_permissions",
                    "permissions": pack.manifest.required_permissions,
                    "message": f"Requires {len(pack.manifest.required_permissions)} "
                    "elevated permissions",
                }
            )

        return flags

    def remove_pack(
        self,
        pack_id: str,
        preserve_allowlist: bool = False,
        preserve_audit: bool = True,
    ) -> dict[str, Any]:
        """Remove an installed pack.

        Args:
            pack_id: Pack to remove
            preserve_allowlist: Whether to keep allowlist entries
            preserve_audit: Whether to preserve audit trail

        Returns:
            Removal result
        """
        pack = self.store.get_pack(pack_id)
        if not pack:
            return {"success": False, "error": f"Pack '{pack_id}' not found"}

        if pack.state != PackState.INSTALLED:
            return {
                "success": False,
                "error": f"Pack is not installed (state: {pack.state.value})",
            }

        removed_tools = []
        errors = []

        # Unregister tools from registry
        for tool_def in pack.manifest.tools:
            tool = self.registry.get_tool(tool_def.name)
            if tool and tool.source == f"marketplace:{pack_id}":
                try:
                    self.registry.unregister_tool(tool_def.name)
                    removed_tools.append(tool_def.name)
                except Exception as e:
                    errors.append(f"Failed to unregister {tool_def.name}: {e}")

        # Remove from allowlist if requested
        if not preserve_allowlist:
            self._remove_from_allowlist(pack_id, pack.manifest.tools)

        # Update pack state
        self.store.update_pack_state(
            pack_id,
            PackState.REMOVED,
            f"Removed {len(removed_tools)} tools",
        )

        # Physical removal
        self.store.remove_pack(pack_id, preserve_audit=preserve_audit)

        return {
            "success": len(errors) == 0,
            "pack_id": pack_id,
            "tools_removed": removed_tools,
            "errors": errors,
        }

    def _remove_from_allowlist(
        self,
        pack_id: str,
        tools: list[Any],
    ) -> None:
        """Remove pack tools from allowlist.

        Args:
            pack_id: Pack ID
            tools: List of tool definitions
        """
        allowlist_path = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"

        try:
            with open(allowlist_path) as f:
                data = yaml.safe_load(f) or {}

            tools_data = data.get("tools", {})
            tool_names = {t.name for t in tools}

            # Remove tools from allowlist
            for tool_name in tool_names:
                if tool_name in tools_data:
                    tool_entry = tools_data[tool_name]
                    marketpack = tool_entry.get("marketpack", {})
                    if marketpack.get("pack_id") == pack_id:
                        del tools_data[tool_name]

            # Write updated allowlist
            data["tools"] = tools_data

            temp_path = allowlist_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=True)
            temp_path.replace(allowlist_path)

            logger.info(f"Removed tools from allowlist for pack '{pack_id}'")

        except Exception as e:
            logger.error(f"Failed to update allowlist: {e}")

    def disable_pack(self, pack_id: str, reason: str = "") -> dict[str, Any]:
        """Disable an installed pack without removing it.

        Args:
            pack_id: Pack to disable
            reason: Reason for disabling

        Returns:
            Disable result
        """
        pack = self.store.get_pack(pack_id)
        if not pack:
            return {"success": False, "error": f"Pack '{pack_id}' not found"}

        if pack.state != PackState.INSTALLED:
            return {
                "success": False,
                "error": f"Pack is not installed (state: {pack.state.value})",
            }

        # Disable tools in registry
        for tool_def in pack.manifest.tools:
            tool = self.registry.get_tool(tool_def.name)
            if tool and tool.source == f"marketplace:{pack_id}":
                # Tools remain in allowlist but are marked as disabled
                pass  # Registry doesn't support disable, would need custom handling

        # Update pack state
        self.store.update_pack_state(
            pack_id,
            PackState.DISABLED,
            reason or "Pack disabled by operator",
        )

        return {
            "success": True,
            "pack_id": pack_id,
            "state": PackState.DISABLED.value,
            "reason": reason,
        }

    def get_installation_summary(self) -> dict[str, Any]:
        """Get summary of all installations.

        Returns:
            Installation summary
        """
        packs = self.store.list_packs()

        installed = [p for p in packs if p.state == PackState.INSTALLED]
        disabled = [p for p in packs if p.state == PackState.DISABLED]

        total_tools = sum(len(p.manifest.tools) for p in installed)

        return {
            "installed_packs": len(installed),
            "disabled_packs": len(disabled),
            "total_tools": total_tools,
            "packs": [p.to_summary() for p in installed + disabled],
        }


# Convenience functions for module-level access


def install_pack(
    pack_id: str,
    force: bool = False,
    dry_run: bool = False,
) -> PackInstallResult:
    """Convenience function to install a pack.

    Args:
        pack_id: Pack to install
        force: Force installation
        dry_run: Preview changes

    Returns:
        PackInstallResult
    """
    installer = PackInstaller()
    return installer.install_pack(pack_id, force=force, dry_run=dry_run)


def remove_pack(
    pack_id: str,
    preserve_allowlist: bool = False,
) -> dict[str, Any]:
    """Convenience function to remove a pack.

    Args:
        pack_id: Pack to remove
        preserve_allowlist: Keep allowlist entries

    Returns:
        Removal result
    """
    installer = PackInstaller()
    return installer.remove_pack(pack_id, preserve_allowlist=preserve_allowlist)
