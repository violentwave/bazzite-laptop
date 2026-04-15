"""Tests for P103 MCP Tool Marketplace.

Tests for tool pack validation, storage, import/export, and installation.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from ai.mcp_bridge.marketplace import (
    PackImporter,
    PackInstaller,
    PackStore,
    PackValidator,
)
from ai.mcp_bridge.marketplace.models import (
    MarketplaceStats,
    PackExportRequest,
    PackManifest,
    PackState,
    RiskTier,
    ToolDefinition,
    ToolPack,
    ToolPackFile,
    ValidationResult,
)
from ai.mcp_bridge.marketplace.pack_store import PackStoreError


class TestPackModels:
    """Tests for marketplace models."""

    def test_pack_manifest_creation(self) -> None:
        """Test PackManifest creation and validation."""
        manifest = PackManifest(
            pack_id="test.example.tools",
            name="Example Tools",
            version="1.0.0",
            description="A pack of example tools",
            author="Test Author",
            risk_tier=RiskTier.LOW,
        )

        assert manifest.pack_id == "test.example.tools"
        assert manifest.name == "Example Tools"
        assert manifest.version == "1.0.0"
        assert manifest.risk_tier == RiskTier.LOW

    def test_pack_manifest_validation(self) -> None:
        """Test PackManifest validation."""
        # Valid pack_id with dot
        manifest = PackManifest(
            pack_id="valid.pack.id",
            name="Valid Pack",
            version="1.0.0",
        )
        assert manifest.pack_id == "valid.pack.id"

        # Invalid pack_id without dot
        with pytest.raises(ValueError, match="namespaced"):
            PackManifest(
                pack_id="invalidpackid",
                name="Invalid Pack",
                version="1.0.0",
            )

    def test_tool_definition_creation(self) -> None:
        """Test ToolDefinition creation."""
        tool = ToolDefinition(
            name="test.my_tool",
            description="A test tool",
            handler_module="ai.test.handlers",
            handler_function="my_tool_handler",
            args={
                "param1": {"type": "string", "required": True},
            },
            annotations={"readOnly": True},
        )

        assert tool.name == "test.my_tool"
        assert tool.annotations.get("readOnly") is True

    def test_tool_pack_lifecycle(self) -> None:
        """Test ToolPack state transitions."""
        manifest = PackManifest(
            pack_id="test.lifecycle",
            name="Lifecycle Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)

        assert pack.state == PackState.STAGED
        assert len(pack.audit_log) == 0

        pack.transition_to(PackState.VALIDATED, "Test validation")
        assert pack.state == PackState.VALIDATED
        assert pack.validated_at is not None
        assert len(pack.audit_log) == 1

        pack.transition_to(PackState.INSTALLED, "Test installation")
        assert pack.state == PackState.INSTALLED
        assert pack.installed_at is not None
        assert len(pack.audit_log) == 2

    def test_pack_summary(self) -> None:
        """Test ToolPack summary generation."""
        manifest = PackManifest(
            pack_id="test.summary",
            name="Summary Test",
            version="2.0.0",
            risk_tier=RiskTier.MEDIUM,
            tools=[
                ToolDefinition(
                    name="test.tool1",
                    description="Tool 1",
                    handler_module="ai.test",
                    handler_function="tool1",
                ),
                ToolDefinition(
                    name="test.tool2",
                    description="Tool 2",
                    handler_module="ai.test",
                    handler_function="tool2",
                ),
            ],
        )
        pack = ToolPack(manifest=manifest)

        summary = pack.to_summary()
        assert summary["pack_id"] == "test.summary"
        assert summary["version"] == "2.0.0"
        assert summary["risk_tier"] == "medium"
        assert summary["tool_count"] == 2


class TestPackValidator:
    """Tests for PackValidator."""

    @pytest.fixture
    def validator(self) -> PackValidator:
        return PackValidator()

    def test_validate_valid_pack(self, validator: PackValidator) -> None:
        """Test validation of a valid pack."""
        manifest = PackManifest(
            pack_id="test.valid.pack",
            name="Valid Pack",
            version="1.0.0",
            description="A valid test pack with sufficient description",
            author="Test Author",
            risk_tier=RiskTier.LOW,
            tools=[
                ToolDefinition(
                    name="custom.valid_tool",
                    description="A valid tool",
                    handler_module="ai.custom.handlers",
                    handler_function="valid_handler",
                    args={
                        "input": {"type": "string", "required": True},
                    },
                    annotations={"readOnly": True},
                ),
            ],
        )
        ToolPack(manifest=manifest)

        result = validator.validate_quick(manifest)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_reserved_prefix(self, validator: PackValidator) -> None:
        """Test validation catches reserved prefixes."""
        manifest = PackManifest(
            pack_id="test.reserved",
            name="Reserved Test",
            version="1.0.0",
            tools=[
                ToolDefinition(
                    name="system.invalid_tool",  # Reserved prefix
                    description="Invalid tool",
                    handler_module="ai.test",
                    handler_function="handler",
                ),
            ],
        )

        result = validator.validate_quick(manifest)

        assert result.valid is False
        assert any("reserved prefix" in e.lower() for e in result.errors)

    def test_validate_conflicting_annotations(self, validator: PackValidator) -> None:
        """Test validation catches conflicting annotations."""
        manifest = PackManifest(
            pack_id="test.conflict",
            name="Conflict Test",
            version="1.0.0",
            tools=[
                ToolDefinition(
                    name="custom.conflict_tool",
                    description="Conflicting tool",
                    handler_module="ai.test",
                    handler_function="handler",
                    annotations={
                        "readOnly": True,
                        "destructive": True,  # Conflict!
                    },
                ),
            ],
        )

        result = validator.validate_quick(manifest)

        assert result.valid is False
        assert any("conflicting" in e.lower() for e in result.errors)

    def test_validate_risk_tier_constraints(self, validator: PackValidator) -> None:
        """Test risk tier constraint validation."""
        # LOW tier with destructive tool should fail
        manifest = PackManifest(
            pack_id="test.risk",
            name="Risk Test",
            version="1.0.0",
            risk_tier=RiskTier.LOW,
            tools=[
                ToolDefinition(
                    name="custom.destructive_tool",
                    description="Destructive tool",
                    handler_module="ai.test",
                    handler_function="handler",
                    annotations={"destructive": True},
                ),
            ],
        )

        result = validator.validate_quick(manifest)

        assert result.valid is False
        assert any("destructive" in e.lower() for e in result.errors)

    def test_risk_assessment(self, validator: PackValidator) -> None:
        """Test risk assessment generation."""
        manifest = PackManifest(
            pack_id="test.assess",
            name="Assessment Test",
            version="1.0.0",
            risk_tier=RiskTier.HIGH,
            required_permissions=["shell_execution", "file_write"],
            tools=[
                ToolDefinition(
                    name="custom.destructive_tool",
                    description="Destructive tool",
                    handler_module="ai.test",
                    handler_function="handler",
                    annotations={"destructive": True},
                ),
            ],
        )
        pack = ToolPack(manifest=manifest)

        result = validator.validate_pack(pack, check_file_integrity=False)

        assert "risk_assessment" in result.to_dict()
        assessment = result.risk_assessment
        assert "score" in assessment
        assert "factors" in assessment
        assert assessment["factors"]["destructive_tools"] == 1


class TestPackStore:
    """Tests for PackStore."""

    @pytest.fixture
    def temp_store(self) -> PackStore:
        """Create a temporary pack store."""
        temp_dir = tempfile.mkdtemp()
        store = PackStore(base_dir=temp_dir)
        yield store
        shutil.rmtree(temp_dir)

    def test_stage_and_get_pack(self, temp_store: PackStore) -> None:
        """Test staging and retrieving a pack."""
        manifest = PackManifest(
            pack_id="test.stage",
            name="Stage Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)

        staged = temp_store.stage_pack(pack)

        assert staged.state == PackState.STAGED
        assert staged.staging_path != ""

        # Retrieve
        retrieved = temp_store.get_pack("test.stage")
        assert retrieved is not None
        assert retrieved.manifest.pack_id == "test.stage"

    def test_duplicate_stage_fails(self, temp_store: PackStore) -> None:
        """Test that staging duplicate pack_id fails."""
        manifest = PackManifest(
            pack_id="test.duplicate",
            name="Duplicate Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)

        temp_store.stage_pack(pack)

        with pytest.raises(PackStoreError):
            temp_store.stage_pack(pack)

    def test_update_pack_state(self, temp_store: PackStore) -> None:
        """Test pack state transitions."""
        manifest = PackManifest(
            pack_id="test.state",
            name="State Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)
        temp_store.stage_pack(pack)

        updated = temp_store.update_pack_state(
            "test.state",
            PackState.VALIDATED,
            "Test validation",
        )

        assert updated is not None
        assert updated.state == PackState.VALIDATED

        retrieved = temp_store.get_pack("test.state")
        assert retrieved.state == PackState.VALIDATED

    def test_list_packs(self, temp_store: PackStore) -> None:
        """Test listing packs."""
        # Create multiple packs
        for i in range(3):
            manifest = PackManifest(
                pack_id=f"test.list.{i}",
                name=f"List Test {i}",
                version="1.0.0",
            )
            pack = ToolPack(manifest=manifest)
            temp_store.stage_pack(pack)

        packs = temp_store.list_packs()

        assert len(packs) == 3

    def test_remove_pack(self, temp_store: PackStore) -> None:
        """Test pack removal."""
        manifest = PackManifest(
            pack_id="test.remove",
            name="Remove Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)
        temp_store.stage_pack(pack)

        result = temp_store.remove_pack("test.remove")

        assert result is True
        assert temp_store.get_pack("test.remove") is None

    def test_store_files(self, temp_store: PackStore) -> None:
        """Test storing files with a pack."""
        manifest = PackManifest(
            pack_id="test.files",
            name="Files Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)

        files = {
            "handler.py": b"def handler(): pass",
            "README.md": b"# Test Pack",
        }

        temp_store.stage_pack(pack, files)

        # Read back
        content = temp_store.read_pack_file("test.files", "handler.py")
        assert content == b"def handler(): pass"


class TestPackImporterExporter:
    """Tests for PackImporter and PackExporter."""

    @pytest.fixture
    def temp_store(self) -> PackStore:
        """Create a temporary pack store."""
        temp_dir = tempfile.mkdtemp()
        store = PackStore(base_dir=temp_dir)
        yield store
        shutil.rmtree(temp_dir)

    def test_export_request_creation(self) -> None:
        """Test PackExportRequest creation."""
        request = PackExportRequest(
            pack_id="test.export",
            name="Export Test",
            version="1.0.0",
            tool_selection=["tool1", "tool2"],
        )

        assert request.pack_id == "test.export"
        assert len(request.tool_selection) == 2

    def test_import_from_directory(self, temp_store: PackStore) -> None:
        """Test importing from directory."""
        # Create a temporary pack directory
        temp_dir = Path(tempfile.mkdtemp())
        manifest = {
            "pack_id": "test.import.dir",
            "name": "Import Test",
            "version": "1.0.0",
            "tools": [
                {
                    "name": "custom.imported_tool",
                    "description": "Imported tool",
                    "handler_module": "ai.test",
                    "handler_function": "handler",
                },
            ],
        }

        # Write manifest
        manifest_path = temp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        importer = PackImporter(store=temp_store)
        pack = importer.import_from_directory(temp_dir)

        assert pack.manifest.pack_id == "test.import.dir"
        assert len(pack.manifest.tools) == 1

        shutil.rmtree(temp_dir)

    def test_import_from_manifest(self, temp_store: PackStore) -> None:
        """Test importing from manifest data."""
        manifest_data = {
            "pack_id": "test.import.manifest",
            "name": "Manifest Import",
            "version": "2.0.0",
            "description": "Test pack for manifest import validation",
            "tools": [
                {
                    "name": "test.tool_one",
                    "description": "A test tool for import validation",
                    "handler_module": "test_handlers",
                    "handler_function": "handle_tool_one",
                    "args": {},
                    "annotations": {"readOnly": True},
                }
            ],
            "risk_tier": "low",
        }

        importer = PackImporter(store=temp_store)
        pack = importer.import_from_manifest(manifest_data)

        assert pack.manifest.pack_id == "test.import.manifest"
        assert pack.manifest.version == "2.0.0"


class TestPackInstaller:
    """Tests for PackInstaller."""

    @pytest.fixture
    def temp_store(self) -> PackStore:
        """Create a temporary pack store."""
        temp_dir = tempfile.mkdtemp()
        store = PackStore(base_dir=temp_dir)
        yield store
        shutil.rmtree(temp_dir)

    def test_check_prerequisites_not_found(self, temp_store: PackStore) -> None:
        """Test prerequisite check for non-existent pack."""
        installer = PackInstaller(store=temp_store)

        result = installer.check_install_prerequisites("nonexistent.pack")

        assert result["can_install"] is False
        assert "not found" in result["error"].lower()

    def test_check_prerequisites_not_validated(self, temp_store: PackStore) -> None:
        """Test prerequisite check for non-validated pack."""
        manifest = PackManifest(
            pack_id="test.prereq",
            name="Prereq Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)
        temp_store.stage_pack(pack)

        installer = PackInstaller(store=temp_store)
        result = installer.check_install_prerequisites("test.prereq")

        # Should not be installable (needs validation)
        assert result["can_install"] is False

    def test_approval_required_for_high_risk(self, temp_store: PackStore) -> None:
        """Test that high-risk packs require approval."""
        manifest = PackManifest(
            pack_id="test.highrisk",
            name="High Risk Test",
            version="1.0.0",
            risk_tier=RiskTier.HIGH,
        )
        pack = ToolPack(manifest=manifest)
        temp_store.stage_pack(pack)
        temp_store.update_pack_state("test.highrisk", PackState.VALIDATED)

        installer = PackInstaller(store=temp_store, require_approval=True)
        result = installer.check_install_prerequisites("test.highrisk")

        assert result["checks"]["requires_approval"] is True


class TestMarketplaceIntegration:
    """Integration tests for the full marketplace flow."""

    @pytest.fixture
    def temp_store(self) -> PackStore:
        """Create a temporary pack store."""
        temp_dir = tempfile.mkdtemp()
        store = PackStore(base_dir=temp_dir)
        yield store
        shutil.rmtree(temp_dir)

    def test_full_pack_lifecycle(self, temp_store: PackStore) -> None:
        """Test complete pack lifecycle: create -> validate -> stage -> install."""
        # 1. Create a pack
        manifest = PackManifest(
            pack_id="test.lifecycle.full",
            name="Full Lifecycle Test",
            version="1.0.0",
            description="A pack for testing the full lifecycle",
            author="Test Suite",
            risk_tier=RiskTier.LOW,
            tools=[
                ToolDefinition(
                    name="custom.test_tool",
                    description="A test tool",
                    handler_module="ai.test.handlers",
                    handler_function="test_handler",
                    args={
                        "input": {"type": "string", "required": True},
                    },
                    annotations={"readOnly": True},
                ),
            ],
        )
        pack = ToolPack(manifest=manifest)

        # 2. Validate
        validator = PackValidator()
        result = validator.validate_quick(manifest)
        assert result.valid is True

        # 3. Stage
        staged = temp_store.stage_pack(pack)
        assert staged.state == PackState.STAGED

        # 4. Mark as validated
        temp_store.update_pack_state(
            "test.lifecycle.full",
            PackState.VALIDATED,
            "Validation passed",
        )

        # 5. Check can install
        installer = PackInstaller(store=temp_store)
        prereqs = installer.check_install_prerequisites("test.lifecycle.full")
        assert prereqs["can_install"] is True

        # 6. List packs
        packs = temp_store.list_packs()
        assert len(packs) == 1
        assert packs[0].manifest.pack_id == "test.lifecycle.full"

        # 7. Get stats
        stats = temp_store.get_stats()
        assert stats.total_packs == 1

    def test_validation_result_to_dict(self) -> None:
        """Test ValidationResult dictionary conversion."""
        result = ValidationResult(valid=True)
        result.add_warning("Test warning")

        data = result.to_dict()

        assert data["valid"] is True
        assert data["warning_count"] == 1
        assert len(data["warnings"]) == 1

    def test_marketplace_stats_to_dict(self) -> None:
        """Test MarketplaceStats dictionary conversion."""
        stats = MarketplaceStats(
            total_packs=10,
            staged_count=3,
            validated_count=2,
            installed_count=5,
            tool_count=25,
            storage_used_bytes=1024 * 1024 * 10,  # 10 MB
        )

        data = stats.to_dict()

        assert data["total_packs"] == 10
        assert data["by_state"]["staged"] == 3
        assert data["storage_used_mb"] == 10.0


class TestToolMarketplaceHandlers:
    """Tests for MCP tool handlers."""

    @pytest.mark.asyncio
    async def test_handle_tool_pack_list_empty(self) -> None:
        """Test pack list handler with no packs."""
        from ai.mcp_bridge.tool_marketplace_handlers import handle_tool_pack_list

        result = await handle_tool_pack_list({})
        data = json.loads(result)

        assert data["success"] is True
        assert data["pack_count"] == 0

    @pytest.mark.asyncio
    async def test_handle_tool_pack_validate_no_args(self) -> None:
        """Test pack validate handler with no arguments."""
        from ai.mcp_bridge.tool_marketplace_handlers import handle_tool_pack_validate

        result = await handle_tool_pack_validate({})
        data = json.loads(result)

        assert data["success"] is False
        assert "pack_id" in data["error"].lower() or "manifest" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_tool_pack_export_no_args(self) -> None:
        """Test pack export handler with no arguments."""
        from ai.mcp_bridge.tool_marketplace_handlers import handle_tool_pack_export

        result = await handle_tool_pack_export({})
        data = json.loads(result)

        assert data["success"] is False
        assert "pack_id" in data["error"].lower() or "required" in data["error"].lower()


class TestPackIntegrity:
    """Tests for pack integrity checking."""

    def test_manifest_hash_computation(self) -> None:
        """Test manifest hash computation."""
        manifest = PackManifest(
            pack_id="test.hash",
            name="Hash Test",
            version="1.0.0",
        )

        hash1 = manifest.compute_content_hash()
        hash2 = manifest.compute_content_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_pack_hash_on_init(self) -> None:
        """Test that pack hash is computed on initialization."""
        manifest = PackManifest(
            pack_id="test.packhash",
            name="Pack Hash Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)

        assert pack.pack_hash != ""
        assert len(pack.pack_hash) == 64

    def test_tool_pack_file_creation(self) -> None:
        """Test ToolPackFile creation."""
        file_info = ToolPackFile(
            path="handler.py",
            checksum="abc123" * 10 + "abcd",  # 64 chars
            size_bytes=1024,
        )

        assert file_info.path == "handler.py"
        assert len(file_info.checksum) == 64
        assert file_info.size_bytes == 1024


class TestRiskTiers:
    """Tests for risk tier handling."""

    def test_risk_tier_values(self) -> None:
        """Test risk tier enum values."""
        assert RiskTier.LOW.value == "low"
        assert RiskTier.MEDIUM.value == "medium"
        assert RiskTier.HIGH.value == "high"
        assert RiskTier.CRITICAL.value == "critical"

    def test_risk_tier_from_string(self) -> None:
        """Test creating risk tier from string."""
        assert RiskTier("low") == RiskTier.LOW
        assert RiskTier("high") == RiskTier.HIGH


class TestPackStates:
    """Tests for pack state handling."""

    def test_pack_state_values(self) -> None:
        """Test pack state enum values."""
        assert PackState.STAGED.value == "staged"
        assert PackState.VALIDATED.value == "validated"
        assert PackState.INSTALLED.value == "installed"
        assert PackState.DISABLED.value == "disabled"
        assert PackState.REMOVED.value == "removed"

    def test_pack_state_transitions(self) -> None:
        """Test valid pack state transitions."""
        manifest = PackManifest(
            pack_id="test.transitions",
            name="Transition Test",
            version="1.0.0",
        )
        pack = ToolPack(manifest=manifest)

        assert pack.state == PackState.STAGED

        pack.transition_to(PackState.VALIDATED)
        assert pack.state == PackState.VALIDATED

        pack.transition_to(PackState.INSTALLED)
        assert pack.state == PackState.INSTALLED

        pack.transition_to(PackState.DISABLED)
        assert pack.state == PackState.DISABLED

        pack.transition_to(PackState.REMOVED)
        assert pack.state == PackState.REMOVED
