"""Tests for run-phase-control backend selection defaults."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai.phase_control.notion_sync import InMemoryPhaseSync


def _load_script_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "run-phase-control.py"
    spec = importlib.util.spec_from_file_location("run_phase_control", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_sync_backend_uses_database_id():
    """Backend builds with provided database_id without calling load_keys."""
    module = _load_script_module()
    args = SimpleNamespace(in_memory=False, database_id="db-1", seed_json=Path("/tmp/missing"))

    with patch.object(module, "NotionPhaseSync", return_value="notion-sync") as notion_cls:
        sync = module._build_sync_backend(args)

    assert sync == "notion-sync"
    notion_cls.assert_called_once_with(database_id="db-1")


def test_build_sync_backend_in_memory_requires_explicit_flag():
    module = _load_script_module()
    args = SimpleNamespace(in_memory=True, database_id="", seed_json=Path("/tmp/missing"))

    sync = module._build_sync_backend(args)
    assert isinstance(sync, InMemoryPhaseSync)


def test_main_smoke_test_uses_notion_backend_probe(capsys):
    module = _load_script_module()

    class _FakeSync:
        def smoke_test(self):
            return {"config_loaded": True, "query_ok": True, "row_count": 1}

    with (
        patch.object(module, "_build_sync_backend", return_value=_FakeSync()),
        patch.object(module, "load_keys"),
        patch("sys.argv", ["run-phase-control", "--smoke-test", "--database-id", "db-1"]),
    ):
        rc = module.main()

    output = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert output["status"] == "ok"
    assert output["mode"] == "notion"
    assert output["query_ok"] is True


def test_main_once_surfaces_runtime_error_as_operator_json(capsys):
    module = _load_script_module()

    class _BoomRunner:
        def run_once(self):
            raise RuntimeError("Notion database 'db-1' could not be queried")

    with (
        patch.object(module, "_build_sync_backend", return_value=object()),
        patch.object(module, "PhaseControlRunner", return_value=_BoomRunner()),
        patch.object(module, "load_keys"),
        patch("sys.argv", ["run-phase-control", "--once", "--database-id", "db-1"]),
    ):
        rc = module.main()

    output = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert output["status"] == "error"
    assert "could not be queried" in output["error"]
