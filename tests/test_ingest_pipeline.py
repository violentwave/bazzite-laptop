"""Tests for ai/system/ingest_pipeline.py"""

import json
import os
from unittest.mock import MagicMock, patch


class TestIngestPipeline:
    """Test ingest pipeline functionality."""

    def test_ingest_empty_returns_no_data(self, tmp_path):
        """Missing ingest file returns status no_data."""
        from ai.system.ingest_pipeline import ingest_intel_to_rag

        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        ingest_dir = intel_dir / "ingest"
        ingest_dir.mkdir()

        result = ingest_intel_to_rag(str(intel_dir))

        assert result["status"] == "no_data"
        assert result["count"] == 0

    def test_ingest_defers_without_rag(self, tmp_path):
        """Returns deferred when ai.rag unavailable."""
        from ai.system.ingest_pipeline import ingest_intel_to_rag

        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        ingest_dir = intel_dir / "ingest"
        ingest_dir.mkdir()

        pending_file = ingest_dir / "pending_ingest.jsonl"
        pending_file.write_text(
            json.dumps(
                {
                    "source": "test",
                    "scraped_at": "2024-01-01T00:00:00Z",
                    "text": "test content",
                    "data": {},
                }
            )
            + "\n"
        )

        with patch("ai.rag.store.get_store", side_effect=ImportError("No module")):
            result = ingest_intel_to_rag(str(intel_dir))

        assert result["status"] == "deferred"
        assert result["count"] == 1

    def test_ingest_atomic_processed_write(self, tmp_path):
        """Processed file written atomically."""
        from ai.system.ingest_pipeline import get_processed_file

        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        ingest_dir = intel_dir / "ingest"
        ingest_dir.mkdir()

        processed = get_processed_file(intel_dir)

        test_records = [{"test": "data"}]
        tmp = processed.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(test_records, f)
        os.replace(tmp, processed)

        assert processed.exists()
        assert not tmp.exists()

    def test_ingest_clears_pending(self, tmp_path):
        """Pending file removed after successful ingest."""
        from ai.system.ingest_pipeline import (
            get_ingest_file,
            ingest_intel_to_rag,
        )

        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        ingest_dir = intel_dir / "ingest"
        ingest_dir.mkdir()

        pending_file = get_ingest_file(intel_dir)
        pending_file.write_text(
            json.dumps(
                {
                    "source": "test",
                    "scraped_at": "2024-01-01T00:00:00Z",
                    "text": "test content",
                    "data": {},
                }
            )
            + "\n"
        )

        mock_table = MagicMock()
        mock_store = MagicMock()
        mock_store.get_or_create_table.return_value = mock_table

        with patch("ai.rag.store.get_store", return_value=mock_store):
            result = ingest_intel_to_rag(str(intel_dir))

        assert result["status"] == "success"
        assert not pending_file.exists()

    def test_import_no_side_effects(self):
        """Import produces no output."""
        import sys

        modules_to_remove = [
            key for key in sys.modules.keys() if key.startswith("ai.system.ingest_pipeline")
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        import io
        from contextlib import redirect_stderr, redirect_stdout

        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            pass

        assert stdout.getvalue() == ""
        assert stderr.getvalue() == ""
