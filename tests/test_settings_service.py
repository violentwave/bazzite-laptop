from __future__ import annotations

from pathlib import Path

import ai.settings_service as settings_service


def _write_keys_file(path: Path, entries: dict[str, str]) -> None:
    lines = [f'{k}="{v}"' for k, v in entries.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_setup_settings_pin_emits_audit_entry(tmp_path, monkeypatch):
    pin_manager = settings_service.PINManager(tmp_path / "settings.db")
    audit_logger = settings_service.AuditLogger(tmp_path / "settings-audit.jsonl")

    monkeypatch.setattr(settings_service, "_pin_manager", pin_manager)
    monkeypatch.setattr(settings_service, "_audit_logger", audit_logger)

    result = settings_service.setup_settings_pin("1234")
    assert result["success"] is True

    entries = audit_logger.get_recent(limit=10)
    assert any(
        e["action"] == settings_service.AuditAction.SETUP.value and e["success"] for e in entries
    )


def test_unlock_settings_invalid_then_lockout_is_structured(tmp_path, monkeypatch):
    pin_manager = settings_service.PINManager(tmp_path / "settings.db")
    pin_manager.setup_pin("1234")
    audit_logger = settings_service.AuditLogger(tmp_path / "settings-audit.jsonl")

    monkeypatch.setattr(settings_service, "_pin_manager", pin_manager)
    monkeypatch.setattr(settings_service, "_audit_logger", audit_logger)

    first = settings_service.unlock_settings("9999")
    second = settings_service.unlock_settings("9999")
    third = settings_service.unlock_settings("9999")

    assert first["success"] is False and first["error_code"] == "pin_invalid"
    assert second["success"] is False and second["error_code"] == "pin_invalid"
    assert third["success"] is False and third["error_code"] == "pin_locked"
    assert third["lockout"]["is_locked"] is True

    entries = audit_logger.get_recent(limit=20)
    assert any(
        e["action"] == settings_service.AuditAction.UNLOCK.value and not e["success"]
        for e in entries
    )
    assert any(e["action"] == settings_service.AuditAction.LOCKOUT.value for e in entries)


def test_unlock_settings_requires_initialized_pin(tmp_path, monkeypatch):
    pin_manager = settings_service.PINManager(tmp_path / "settings.db")
    audit_logger = settings_service.AuditLogger(tmp_path / "settings-audit.jsonl")

    monkeypatch.setattr(settings_service, "_pin_manager", pin_manager)
    monkeypatch.setattr(settings_service, "_audit_logger", audit_logger)

    result = settings_service.unlock_settings("1234")
    assert result["success"] is False
    assert result["error_code"] == "pin_not_initialized"


def test_secrets_service_returns_precise_results_and_audits(tmp_path):
    db_path = tmp_path / "settings.db"
    audit_path = tmp_path / "settings-audit.jsonl"
    keys_path = tmp_path / "keys.env"

    pin_manager = settings_service.PINManager(db_path)
    audit_logger = settings_service.AuditLogger(audit_path)
    service = settings_service.SecretsService(
        keys_env=keys_path,
        pin_manager=pin_manager,
        audit_logger=audit_logger,
    )

    _write_keys_file(keys_path, {"GROQ_API_KEY": "initial-value"})

    not_initialized = service.reveal_secret_result("GROQ_API_KEY", "1234")
    assert not_initialized["success"] is False
    assert not_initialized["error_code"] == "pin_not_initialized"

    pin_manager.setup_pin("1234")

    replace_result = service.set_secret_result("GROQ_API_KEY", "updated-value", "1234")
    add_result = service.set_secret_result("P91_TEST_KEY", "new-value", "1234")
    reveal_result = service.reveal_secret_result("GROQ_API_KEY", "1234")
    delete_result = service.delete_secret_result("P91_TEST_KEY", "1234")

    assert replace_result["success"] is True and replace_result["action"] == "replace"
    assert add_result["success"] is True and add_result["action"] == "add"
    assert reveal_result["success"] is True
    assert reveal_result["entry"].name == "GROQ_API_KEY"
    assert delete_result["success"] is True and delete_result["action"] == "delete"

    invalid_pin = service.delete_secret_result("GROQ_API_KEY", "0000")
    assert invalid_pin["success"] is False
    assert invalid_pin["error_code"] == "pin_invalid"

    entries = audit_logger.get_recent(limit=50)
    actions = {entry["action"] for entry in entries}
    assert settings_service.AuditAction.REVEAL.value in actions
    assert settings_service.AuditAction.REPLACE.value in actions
    assert settings_service.AuditAction.ADD.value in actions
    assert settings_service.AuditAction.DELETE.value in actions
