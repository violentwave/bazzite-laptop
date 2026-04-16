"""Unit tests for ai/provider_registry.py ProviderRegistry."""

import pytest

from ai.provider_registry import (
    ModelCatalogEntry,
    ProviderRegistry,
    _safe_provider_id,
    _validate_no_secrets,
)
from ai.provider_service import KNOWN_PROVIDERS


class TestSafeProviderId:
    def test_valid_ids(self):
        assert _safe_provider_id("custom") == "custom"
        assert _safe_provider_id("my-provider") == "my-provider"
        assert _safe_provider_id("provider_123") == "provider_123"

    def test_invalid_id_starts_with_number(self):
        with pytest.raises(ValueError, match="Invalid provider_id"):
            _safe_provider_id("123provider")

    def test_invalid_id_uppercase(self):
        with pytest.raises(ValueError, match="Invalid provider_id"):
            _safe_provider_id("Provider")

    def test_invalid_id_special_chars(self):
        with pytest.raises(ValueError, match="Invalid provider_id"):
            _safe_provider_id("provider@123")


class TestValidateNoSecrets:
    def test_rejects_openai_key(self):
        with pytest.raises(ValueError, match="Potential secret"):
            _validate_no_secrets("sk-abcdefghijklmnopqrst")

    def test_rejects_anthropic_key(self):
        with pytest.raises(ValueError, match="Potential secret"):
            _validate_no_secrets("sk-ant-abcdefghijklmnopqrstuvwx")

    def test_accepts_safe_value(self):
        _validate_no_secrets("MY_API_KEY_NAME")


class TestModelCatalogEntry:
    def test_basic_fields(self):
        entry = ModelCatalogEntry(
            id="gpt-4",
            name="GPT-4",
            task_types=["reason"],
        )
        assert entry.id == "gpt-4"
        assert entry.name == "GPT-4"
        assert entry.task_types == ["reason"]


class TestProviderRegistry:
    @pytest.fixture
    def temp_registry(self, tmp_path):
        registry = ProviderRegistry(registry_path=tmp_path / "registry.json")
        yield registry
        registry._cache.clear()
        registry._loaded = False

    def test_list_empty(self, temp_registry):
        providers = temp_registry.list_providers()
        assert providers == []

    def test_create_and_list(self, temp_registry):
        record = temp_registry.create_provider(
            provider_id="custom-provider",
            display_name="Custom Provider",
            provider_type="openai_compatible",
            base_url="https://api.custom.com/v1",
            credential_ref="CUSTOM_API_KEY",
            models=[{"id": "model-1", "name": "Model 1", "task_types": ["fast"]}],
        )
        assert record.provider_id == "custom-provider"

        providers = temp_registry.list_providers()
        assert len(providers) == 1
        assert providers[0].provider_id == "custom-provider"

    def test_create_validates_provider_type(self, temp_registry):
        with pytest.raises(ValueError, match="Invalid provider_type"):
            temp_registry.create_provider(
                provider_id="test",
                display_name="Test",
                provider_type="invalid_type",
            )

    def test_create_requires_base_url_for_custom(self, temp_registry):
        with pytest.raises(ValueError, match="base_url required"):
            temp_registry.create_provider(
                provider_id="test",
                display_name="Test",
                provider_type="openai_compatible",
            )

    def test_update_provider(self, temp_registry):
        temp_registry.create_provider(
            provider_id="test",
            display_name="Test",
            provider_type="gemini",
            models=[{"id": "m1", "name": "Model 1", "task_types": ["fast"]}],
        )

        record = temp_registry.update_provider(
            provider_id="test",
            display_name="Updated Test",
        )
        assert record.display_name == "Updated Test"

    def test_disable_provider(self, temp_registry):
        temp_registry.create_provider(
            provider_id="test",
            display_name="Test",
            provider_type="gemini",
        )

        record = temp_registry.disable_provider("test")
        assert record.enabled is False

        providers = temp_registry.list_providers(include_disabled=False)
        assert providers == []

    def test_enable_provider(self, temp_registry):
        temp_registry.create_provider(
            provider_id="test",
            display_name="Test",
            provider_type="gemini",
        )
        temp_registry.disable_provider("test")

        record = temp_registry.enable_provider("test")
        assert record.enabled is True

    def test_get_provider(self, temp_registry):
        temp_registry.create_provider(
            provider_id="test",
            display_name="Test",
            provider_type="gemini",
        )

        record = temp_registry.get_provider("test")
        assert record is not None
        assert record.display_name == "Test"

    def test_get_nonexistent(self, temp_registry):
        record = temp_registry.get_provider("nonexistent")
        assert record is None

    def test_duplicate_create_fails(self, temp_registry):
        temp_registry.create_provider(
            provider_id="test",
            display_name="Test",
            provider_type="gemini",
        )

        with pytest.raises(ValueError, match="already exists"):
            temp_registry.create_provider(
                provider_id="test",
                display_name="Test 2",
                provider_type="gemini",
            )

    def test_merge_with_builtin(self, temp_registry):
        temp_registry.create_provider(
            provider_id="custom-provider",
            display_name="Custom Provider",
            provider_type="openai_compatible",
            base_url="https://api.custom.com/v1",
            credential_ref="CUSTOM_KEY",
            models=[{"id": "custom-model", "name": "Custom", "task_types": ["fast"]}],
        )

        merged = temp_registry.merge_with_builtin(KNOWN_PROVIDERS)

        provider_ids = [p.provider_id for p in merged]
        assert "custom-provider" in provider_ids
        assert "gemini" in provider_ids
        assert "groq" in provider_ids


class TestValidation:
    def test_validate_valid_config(self):
        registry = ProviderRegistry()
        errors = registry.validate_config(
            {
                "provider_id": "test",
                "provider_type": "gemini",
                "models": [{"id": "m1", "name": "M1", "task_types": ["fast"]}],
            }
        )
        assert errors == []

    def test_validate_missing_model(self):
        registry = ProviderRegistry()
        errors = registry.validate_config(
            {
                "provider_id": "test",
                "provider_type": "gemini",
                "models": [],
            }
        )
        assert len(errors) > 0


class TestDeterministicGeneration:
    def test_routing_stable_across_calls(self, tmp_path):
        registry1 = ProviderRegistry(registry_path=tmp_path / "r1.json")
        registry1.create_provider(
            provider_id="custom",
            display_name="Custom",
            provider_type="openai_compatible",
            base_url="https://api.custom.com",
            models=[{"id": "m1", "name": "M1", "task_types": ["fast"]}],
        )

        routing1 = registry1.generate_routing_config(KNOWN_PROVIDERS)

        registry2 = ProviderRegistry(registry_path=tmp_path / "r2.json")
        registry2.create_provider(
            provider_id="custom",
            display_name="Custom",
            provider_type="openai_compatible",
            base_url="https://api.custom.com",
            models=[{"id": "m1", "name": "M1", "task_types": ["fast"]}],
        )

        routing2 = registry2.generate_routing_config(KNOWN_PROVIDERS)

        assert routing1 == routing2
