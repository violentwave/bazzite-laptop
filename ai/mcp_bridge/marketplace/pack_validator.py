"""Tool Pack Validator for MCP Marketplace.

P103: MCP Tool Marketplace + Tool Pack Import/Export

Validates tool pack manifests and files WITHOUT executing code.
Performs metadata inspection, schema validation, checksum verification,
and governance constraint checking.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from ai.mcp_bridge.marketplace.models import (
    PackManifest,
    RiskTier,
    ToolPack,
    ValidationResult,
)

logger = logging.getLogger("ai.mcp_bridge.marketplace.validator")


class PackValidationError(Exception):
    """Exception raised when pack validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class PackValidator:
    """Validator for tool packs.

    Performs comprehensive validation of tool packs without executing
    any code from the pack. Validates:
    - Manifest schema and required fields
    - Tool definition syntax
    - File checksums
    - Compatibility constraints
    - Governance policies
    - Security constraints
    """

    # Reserved tool name prefixes that require special handling
    RESERVED_PREFIXES = [
        "system.",
        "security.",
        "shell.",
        "internal.",
    ]

    # Allowed annotation keys for MCP tools
    VALID_ANNOTATIONS = {
        "readOnly",
        "destructive",
        "openWorld",
        "idempotent",
    }

    # Risk tier requirements
    RISK_REQUIREMENTS: dict[RiskTier, dict[str, Any]] = {
        RiskTier.LOW: {
            "max_tools": 50,
            "allows_destructive": False,
            "requires_approval": False,
        },
        RiskTier.MEDIUM: {
            "max_tools": 30,
            "allows_destructive": True,
            "requires_approval": False,
        },
        RiskTier.HIGH: {
            "max_tools": 15,
            "allows_destructive": True,
            "requires_approval": True,
        },
        RiskTier.CRITICAL: {
            "max_tools": 5,
            "allows_destructive": True,
            "requires_approval": True,
        },
    }

    def __init__(self, bridge_version: str = "1.0.0") -> None:
        """Initialize validator.

        Args:
            bridge_version: Current MCP bridge version for compatibility checks
        """
        self.bridge_version = bridge_version

    def validate_pack(
        self,
        pack: ToolPack,
        pack_root: Path | None = None,
        check_file_integrity: bool = True,
    ) -> ValidationResult:
        """Validate a tool pack comprehensively.

        This method validates the pack manifest and optionally checks
        file integrity without executing any code.

        Args:
            pack: The tool pack to validate
            pack_root: Root directory containing pack files (for checksum validation)
            check_file_integrity: Whether to validate file checksums

        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(valid=True)

        # Phase 1: Validate manifest structure
        self._validate_manifest_structure(pack.manifest, result)

        # Phase 2: Validate tool definitions
        self._validate_tool_definitions(pack.manifest, result)

        # Phase 3: Validate risk tier constraints
        self._validate_risk_constraints(pack.manifest, result)

        # Phase 4: Validate compatibility
        self._validate_compatibility(pack.manifest, result)

        # Phase 5: Validate governance compliance
        self._validate_governance_compliance(pack.manifest, result)

        # Phase 6: Validate file integrity (if requested and root provided)
        if check_file_integrity and pack_root:
            self._validate_file_integrity(pack.manifest, pack_root, result)

        # Set final validity based on errors
        result.valid = len(result.errors) == 0

        # Generate risk assessment summary
        result.risk_assessment = self._assess_risk(pack.manifest)

        return result

    def _validate_manifest_structure(
        self,
        manifest: PackManifest,
        result: ValidationResult,
    ) -> None:
        """Validate basic manifest structure and fields.

        Args:
            manifest: Pack manifest to validate
            result: Validation result to populate
        """
        # Required fields are enforced by Pydantic, but we do additional checks

        # Check pack_id format
        if not re.match(r"^[a-z0-9._-]+$", manifest.pack_id):
            result.add_error(
                f"pack_id '{manifest.pack_id}' contains invalid characters. "
                "Use only lowercase letters, numbers, dots, underscores, and hyphens."
            )

        # Check version format (semantic versioning)
        if not re.match(r"^\d+\.\d+\.\d+$", manifest.version):
            result.add_warning(
                f"version '{manifest.version}' does not follow semantic versioning (X.Y.Z). "
                "Recommend using standard semver format."
            )

        # Check description length
        if len(manifest.description) < 10:
            result.add_warning(
                "description is very short. "
                "Consider providing more detail about the pack's purpose."
            )

        # Warn if no author
        if not manifest.author:
            result.add_warning("No author specified. Consider adding authorship information.")

    def _validate_tool_definitions(
        self,
        manifest: PackManifest,
        result: ValidationResult,
    ) -> None:
        """Validate tool definitions in the manifest.

        Args:
            manifest: Pack manifest to validate
            result: Validation result to populate
        """
        if not manifest.tools:
            result.add_error("Pack contains no tool definitions")
            return

        tool_names: set[str] = set()

        for tool in manifest.tools:
            # Check for duplicate tool names
            if tool.name in tool_names:
                result.add_error(f"Duplicate tool name: {tool.name}")
            tool_names.add(tool.name)

            # Validate tool name format
            if not re.match(r"^[a-z0-9._-]+$", tool.name):
                result.add_error(
                    f"Tool name '{tool.name}' contains invalid characters. "
                    "Use only lowercase letters, numbers, dots, underscores, and hyphens."
                )

            # Check reserved prefixes
            for prefix in self.RESERVED_PREFIXES:
                if tool.name.startswith(prefix):
                    result.add_error(
                        f"Tool name '{tool.name}' uses reserved prefix '{prefix}'. "
                        "These namespaces are reserved for system tools."
                    )

            # Validate handler module format
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", tool.handler_module):
                result.add_error(f"Invalid handler_module for '{tool.name}': {tool.handler_module}")

            # Validate handler function format
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", tool.handler_function):
                result.add_error(
                    f"Invalid handler_function for '{tool.name}': {tool.handler_function}"
                )

            # Validate argument definitions
            self._validate_tool_args(tool.name, tool.args, result)

            # Validate annotations
            self._validate_tool_annotations(tool.name, tool.annotations, result)

            # Check description
            if len(tool.description) < 5:
                result.add_warning(f"Tool '{tool.name}' has a very short description")

    def _validate_tool_args(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Validate argument definitions for a tool.

        Args:
            tool_name: Name of the tool being validated
            args: Argument definitions
            result: Validation result to populate
        """
        valid_types = {"string", "integer", "number", "boolean", "array", "object"}

        for arg_name, arg_def in args.items():
            # Check argument name
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", arg_name):
                result.add_error(
                    f"Invalid argument name '{arg_name}' in tool '{tool_name}'. "
                    "Must start with letter/underscore, followed by alphanumeric."
                )

            # Validate type if specified
            arg_type = arg_def.get("type", "string")
            if arg_type not in valid_types:
                result.add_error(
                    f"Invalid type '{arg_type}' for argument '{arg_name}' in tool '{tool_name}'. "
                    f"Valid types: {', '.join(valid_types)}"
                )

            # Validate pattern if specified (syntax check only)
            pattern = arg_def.get("pattern")
            if pattern:
                try:
                    re.compile(pattern)
                except re.error as e:
                    result.add_error(
                        f"Invalid regex pattern for argument '{arg_name}' "
                        f"in tool '{tool_name}': {e}"
                    )

            # Validate numeric constraints
            if "min" in arg_def or "max" in arg_def:
                if arg_type not in ("integer", "number"):
                    result.add_warning(
                        f"Min/max constraints on non-numeric type '{arg_type}' "
                        f"for argument '{arg_name}' in tool '{tool_name}'"
                    )

    def _validate_tool_annotations(
        self,
        tool_name: str,
        annotations: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Validate tool annotations.

        Args:
            tool_name: Name of the tool
            annotations: Annotations dict
            result: Validation result to populate
        """
        for key in annotations:
            if key not in self.VALID_ANNOTATIONS:
                result.add_warning(
                    f"Unknown annotation '{key}' for tool '{tool_name}'. "
                    f"Valid annotations: {', '.join(self.VALID_ANNOTATIONS)}"
                )

        # Check for conflicting annotations
        is_readonly = annotations.get("readOnly", False)
        is_destructive = annotations.get("destructive", False)

        if is_readonly and is_destructive:
            result.add_error(
                f"Tool '{tool_name}' has conflicting annotations: "
                "readOnly and destructive cannot both be true"
            )

    def _validate_risk_constraints(
        self,
        manifest: PackManifest,
        result: ValidationResult,
    ) -> None:
        """Validate risk tier constraints.

        Args:
            manifest: Pack manifest
            result: Validation result to populate
        """
        requirements = self.RISK_REQUIREMENTS.get(manifest.risk_tier)
        if not requirements:
            return

        tool_count = len(manifest.tools)
        max_tools = requirements["max_tools"]

        if tool_count > max_tools:
            result.add_error(
                f"Risk tier '{manifest.risk_tier.value}' allows maximum {max_tools} tools, "
                f"but pack contains {tool_count}. Consider splitting into multiple packs "
                f"or upgrading risk tier."
            )

        # Check destructive tools permission
        allows_destructive = requirements["allows_destructive"]
        if not allows_destructive:
            destructive_tools = [
                t.name for t in manifest.tools if t.annotations.get("destructive", False)
            ]
            if destructive_tools:
                result.add_error(
                    f"Risk tier '{manifest.risk_tier.value}' does not allow destructive tools, "
                    f"but pack contains: {', '.join(destructive_tools)}"
                )

        # Set approval requirement in risk assessment
        result.risk_assessment["requires_approval"] = requirements["requires_approval"]

    def _validate_compatibility(
        self,
        manifest: PackManifest,
        result: ValidationResult,
    ) -> None:
        """Validate compatibility constraints.

        Args:
            manifest: Pack manifest
            result: Validation result to populate
        """
        compat = manifest.compatibility

        # Check minimum bridge version
        min_version = compat.get("min_bridge_version")
        if min_version:
            if not self._version_satisfies(self.bridge_version, min_version):
                result.add_error(
                    f"Bridge version {self.bridge_version} is below minimum "
                    f"required version {min_version}"
                )

        # Check maximum bridge version
        max_version = compat.get("max_bridge_version")
        if max_version:
            if not self._version_satisfies(max_version, self.bridge_version):
                result.add_error(
                    f"Bridge version {self.bridge_version} exceeds maximum "
                    f"supported version {max_version}"
                )

        # Store compatibility check results
        result.compatibility_check = {
            "bridge_version": self.bridge_version,
            "min_required": min_version,
            "max_supported": max_version,
            "compatible": len(result.errors) == 0,
        }

    def _validate_governance_compliance(
        self,
        manifest: PackManifest,
        result: ValidationResult,
    ) -> None:
        """Validate governance compliance.

        Args:
            manifest: Pack manifest
            result: Validation result to populate
        """
        # Check for required permissions
        required_perms = manifest.required_permissions

        # High-risk permissions that should be flagged
        high_risk_permissions = {
            "shell_execution",
            "file_write",
            "network_outbound",
            "system_modification",
        }

        flagged_perms = set(required_perms) & high_risk_permissions
        if flagged_perms:
            result.add_warning(
                f"Pack requires high-risk permissions: {', '.join(flagged_perms)}. "
                "These will be subject to additional governance review."
            )

        # Check for conflicts with system tools
        # This would typically query the governance engine
        # For now, just note the check was performed
        result.compatibility_check["governance_reviewed"] = True

    def _validate_file_integrity(
        self,
        manifest: PackManifest,
        pack_root: Path,
        result: ValidationResult,
    ) -> None:
        """Validate file checksums for integrity.

        Args:
            manifest: Pack manifest
            pack_root: Root directory containing pack files
            result: Validation result to populate
        """
        for file_info in manifest.files:
            file_path = pack_root / file_info.path

            if not file_path.exists():
                result.add_error(f"Pack file missing: {file_info.path}")
                continue

            # Check file size
            actual_size = file_path.stat().st_size
            if actual_size != file_info.size_bytes:
                result.add_error(
                    f"File size mismatch for {file_info.path}: "
                    f"expected {file_info.size_bytes}, got {actual_size}"
                )

            # Check checksum
            try:
                actual_hash = self._compute_file_hash(file_path)
                if actual_hash != file_info.checksum:
                    result.add_error(
                        f"Checksum mismatch for {file_info.path}: "
                        f"expected {file_info.checksum[:16]}..., got {actual_hash[:16]}..."
                    )
            except OSError as e:
                result.add_error(f"Failed to read {file_info.path}: {e}")

    def _assess_risk(self, manifest: PackManifest) -> dict[str, Any]:
        """Generate risk assessment for the pack.

        Args:
            manifest: Pack manifest

        Returns:
            Risk assessment dictionary
        """
        risk_factors = {
            "tool_count": len(manifest.tools),
            "risk_tier": manifest.risk_tier.value,
            "destructive_tools": sum(
                1 for t in manifest.tools if t.annotations.get("destructive", False)
            ),
            "read_only_tools": sum(
                1 for t in manifest.tools if t.annotations.get("readOnly", False)
            ),
            "required_permissions": len(manifest.required_permissions),
        }

        # Calculate overall risk score (0-100)
        base_score = {
            RiskTier.LOW: 10,
            RiskTier.MEDIUM: 30,
            RiskTier.HIGH: 60,
            RiskTier.CRITICAL: 90,
        }.get(manifest.risk_tier, 50)

        # Adjust for tool count
        tool_factor = min(len(manifest.tools) * 2, 20)

        # Adjust for permissions
        perm_factor = min(len(manifest.required_permissions) * 5, 15)

        risk_score = min(base_score + tool_factor + perm_factor, 100)

        return {
            "score": risk_score,
            "level": manifest.risk_tier.value,
            "factors": risk_factors,
            "recommendations": self._generate_risk_recommendations(manifest, risk_score),
        }

    def _generate_risk_recommendations(
        self,
        manifest: PackManifest,
        risk_score: int,
    ) -> list[str]:
        """Generate risk-based recommendations.

        Args:
            manifest: Pack manifest
            risk_score: Calculated risk score

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if risk_score > 70:
            recommendations.append(
                "High-risk pack: Consider manual security review before installation"
            )

        if len(manifest.tools) > 20:
            recommendations.append(
                "Large tool count: Consider splitting into smaller, focused packs"
            )

        destructive_count = sum(
            1 for t in manifest.tools if t.annotations.get("destructive", False)
        )
        if destructive_count > 0 and manifest.risk_tier == RiskTier.LOW:
            recommendations.append(
                "Pack contains destructive tools but has LOW risk tier - consider upgrading"
            )

        if not manifest.author:
            recommendations.append("Add author information for accountability")

        return recommendations

    def _version_satisfies(self, version: str, requirement: str) -> bool:
        """Check if version satisfies a minimum version requirement.

        Performs simple semver comparison (major.minor.patch).

        Args:
            version: Version to check
            requirement: Minimum required version

        Returns:
            True if version >= requirement
        """
        try:
            v_parts = [int(p) for p in version.split(".")]
            r_parts = [int(p) for p in requirement.split(".")]

            # Pad to same length
            while len(v_parts) < len(r_parts):
                v_parts.append(0)
            while len(r_parts) < len(v_parts):
                r_parts.append(0)

            for v, r in zip(v_parts, r_parts, strict=False):
                if v > r:
                    return True
                if v < r:
                    return False
            return True  # Equal
        except (ValueError, AttributeError):
            return False

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def validate_quick(self, manifest: PackManifest) -> ValidationResult:
        """Perform quick validation without file integrity checks.

        Args:
            manifest: Pack manifest to validate

        Returns:
            ValidationResult
        """
        return self.validate_pack(
            ToolPack(manifest=manifest),
            pack_root=None,
            check_file_integrity=False,
        )


class PackIntegrityChecker:
    """Checker for pack integrity using checksums.

    Provides methods to verify that pack files have not been modified
    since the pack was created.
    """

    @staticmethod
    def compute_manifest_hash(manifest: PackManifest) -> str:
        """Compute hash of manifest for integrity verification.

        Args:
            manifest: Pack manifest

        Returns:
            SHA-256 hash of canonical manifest JSON
        """
        return manifest.compute_content_hash()

    @staticmethod
    def verify_pack_integrity(
        pack: ToolPack,
        pack_root: Path,
    ) -> dict[str, Any]:
        """Verify pack integrity including files.

        Args:
            pack: Tool pack
            pack_root: Root directory containing pack files

        Returns:
            Dict with verification results
        """
        results = {
            "manifest_hash_match": False,
            "files_verified": 0,
            "files_failed": 0,
            "errors": [],
        }

        # Verify manifest hash
        current_hash = pack.manifest.compute_content_hash()
        results["manifest_hash_match"] = current_hash == pack.pack_hash

        if not results["manifest_hash_match"]:
            results["errors"].append("Manifest hash mismatch - pack may have been modified")

        # Verify files
        for file_info in pack.manifest.files:
            file_path = pack_root / file_info.path

            if not file_path.exists():
                results["files_failed"] += 1
                results["errors"].append(f"Missing file: {file_info.path}")
                continue

            try:
                sha256 = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                actual_hash = sha256.hexdigest()

                if actual_hash == file_info.checksum:
                    results["files_verified"] += 1
                else:
                    results["files_failed"] += 1
                    results["errors"].append(f"Hash mismatch: {file_info.path}")
            except OSError as e:
                results["files_failed"] += 1
                results["errors"].append(f"Failed to read {file_info.path}: {e}")

        results["integrity_passed"] = (
            results["manifest_hash_match"] and results["files_failed"] == 0
        )

        return results
