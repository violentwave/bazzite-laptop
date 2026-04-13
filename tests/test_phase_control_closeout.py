"""Tests for P76 closeout ingestion system."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from ai.phase_control.closeout import (
    CloseoutIngestionEngine,
    CloseoutReport,
    CoverageMetrics,
    IngestionResult,
    IngestionStatus,
    RetryConfig,
)
from ai.phase_control.closeout_targets import (
    HandoffIngestionTarget,
    NotionMemoryIngestionTarget,
    RepoDocsIngestionTarget,
    TaskPatternIngestionTarget,
    ValidationCoverageIngestionTarget,
)
from ai.phase_control.models import PhaseRow, PhaseStatus


class TestIngestionResult:
    """Test IngestionResult dataclass."""

    def test_to_dict(self):
        result = IngestionResult(
            target="test_target",
            status=IngestionStatus.SUCCESS,
            items_processed=5,
            items_skipped=1,
            error_message=None,
            retry_count=0,
            duration_seconds=1.5,
            metadata={"key": "value"},
        )
        d = result.to_dict()
        assert d["target"] == "test_target"
        assert d["status"] == "success"
        assert d["items_processed"] == 5
        assert d["metadata"] == {"key": "value"}


class TestCoverageMetrics:
    """Test CoverageMetrics dataclass."""

    def test_coverage_percentage_all_true(self):
        coverage = CoverageMetrics(
            notion_status_normalized=True,
            commit_sha_present=True,
            finished_at_present=True,
            validation_summary_present=True,
            plan_doc_exists=True,
            completion_report_exists=True,
            artifact_register_updated=True,
            repo_docs_ingested=True,
            handoff_ingested=True,
            phase_summary_in_memory=True,
            task_patterns_logged=True,
            validation_commands_run=True,
            test_outputs_captured=True,
            failures_recorded=True,
            retry_state_visible=True,
        )
        assert coverage.coverage_percentage == 100.0

    def test_coverage_percentage_partial(self):
        # 7 out of 15 fields True = 46.67%
        coverage = CoverageMetrics(
            notion_status_normalized=True,
            commit_sha_present=True,
            finished_at_present=True,
            validation_summary_present=True,
            plan_doc_exists=True,
            completion_report_exists=True,
            artifact_register_updated=True,
            repo_docs_ingested=False,
            handoff_ingested=False,
            phase_summary_in_memory=False,
            task_patterns_logged=False,
            validation_commands_run=False,
            test_outputs_captured=False,
            failures_recorded=False,
            retry_state_visible=False,
        )
        assert coverage.coverage_percentage == (7 / 15) * 100

    def test_to_dict_structure(self):
        coverage = CoverageMetrics()
        d = coverage.to_dict()
        assert "metadata_coverage" in d
        assert "artifact_coverage" in d
        assert "ingestion_coverage" in d
        assert "validation_coverage" in d
        assert "failure_visibility" in d


class TestCloseoutReport:
    """Test CloseoutReport dataclass."""

    def test_to_dict(self):
        report = CloseoutReport(
            phase_number=76,
            run_id="test-run-123",
            started_at=datetime.now(UTC),
            ingestion_results=[
                IngestionResult(target="test", status=IngestionStatus.SUCCESS),
            ],
            coverage=CoverageMetrics(),
            overall_status=IngestionStatus.SUCCESS,
        )
        d = report.to_dict()
        assert d["phase_number"] == 76
        assert d["run_id"] == "test-run-123"
        assert d["overall_status"] == "success"
        assert "ingestion_results" in d
        assert "coverage" in d


class TestRetryConfig:
    """Test RetryConfig calculations."""

    def test_calculate_delay_exponential(self):
        config = RetryConfig(base_delay_seconds=1.0, exponential_base=2.0)
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0

    def test_calculate_delay_max_cap(self):
        config = RetryConfig(
            base_delay_seconds=1.0,
            exponential_base=10.0,
            max_delay_seconds=50.0,
        )
        assert config.calculate_delay(3) == 50.0  # Would be 1000 without cap


class TestCloseoutIngestionEngine:
    """Test CloseoutIngestionEngine."""

    def test_init(self, tmp_path):
        engine = CloseoutIngestionEngine(repo_path=str(tmp_path))
        assert engine.repo_path == tmp_path
        assert engine._targets == []

    def test_register_target(self, tmp_path):
        engine = CloseoutIngestionEngine(repo_path=str(tmp_path))
        mock_target = MagicMock()
        mock_target.name = "test_target"
        engine.register_target(mock_target)
        assert len(engine._targets) == 1

    def test_run_closeout_no_targets(self, tmp_path):
        engine = CloseoutIngestionEngine(repo_path=str(tmp_path))
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        report = engine.run_closeout(phase, run_id="test-123", dry_run=True)
        assert report.phase_number == 76
        assert report.run_id == "test-123"
        assert report.overall_status == IngestionStatus.SUCCESS

    def test_run_closeout_with_mock_target(self, tmp_path):
        engine = CloseoutIngestionEngine(repo_path=str(tmp_path))
        mock_target = MagicMock()
        mock_target.name = "test_target"
        mock_target.ingest.return_value = IngestionResult(
            target="test_target",
            status=IngestionStatus.SUCCESS,
            items_processed=1,
        )
        engine.register_target(mock_target)

        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        report = engine.run_closeout(phase, run_id="test-123")
        assert len(report.ingestion_results) == 1
        assert report.ingestion_results[0].status == IngestionStatus.SUCCESS

    def test_run_closeout_with_failed_target(self, tmp_path):
        engine = CloseoutIngestionEngine(repo_path=str(tmp_path))
        mock_target = MagicMock()
        mock_target.name = "failing_target"
        mock_target.ingest.return_value = IngestionResult(
            target="failing_target",
            status=IngestionStatus.FAILED,
            error_message="Test error",
        )
        engine.register_target(mock_target)

        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        report = engine.run_closeout(phase, run_id="test-123")
        assert report.overall_status == IngestionStatus.PARTIAL
        assert len(report.dead_letter_entries) == 1

    def test_calculate_coverage(self, tmp_path):
        engine = CloseoutIngestionEngine(repo_path=str(tmp_path))

        # Create test files
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs/P76_PLAN.md").write_text("# Plan")
        (tmp_path / "docs/P76_COMPLETION_REPORT.md").write_text("# Report")
        (tmp_path / "docs/PHASE_ARTIFACT_REGISTER.md").write_text("P76 content")

        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
            validation_summary={"test": "data"},
            validation_commands=["pytest"],
        )

        results = [
            IngestionResult(target="repo_docs", status=IngestionStatus.SUCCESS),
            IngestionResult(target="handoff", status=IngestionStatus.SUCCESS),
        ]

        coverage = engine._calculate_coverage(phase, results)

        assert coverage.notion_status_normalized is True
        assert coverage.plan_doc_exists is True
        assert coverage.completion_report_exists is True
        assert coverage.artifact_register_updated is True
        assert coverage.repo_docs_ingested is True
        assert coverage.handoff_ingested is True
        assert coverage.validation_commands_run is True
        assert coverage.test_outputs_captured is True

    def test_dead_letter_operations(self, tmp_path):
        # Use a unique dead letter path to avoid conflicts with other tests
        dead_letter_path = tmp_path / ".closeout-dead-letter.jsonl"
        engine = CloseoutIngestionEngine(
            repo_path=str(tmp_path),
            dead_letter_path=dead_letter_path,
        )

        # Use unique phase number
        test_phase = 9999

        # Write a dead letter entry manually
        engine._write_dead_letter(
            test_phase,
            "test_target",
            IngestionResult(
                target="test_target",
                status=IngestionStatus.FAILED,
                error_message="Test error",
            ),
        )

        # Now should have one entry
        entries = engine.get_dead_letter_entries(phase_number=test_phase)
        assert len(entries) == 1
        assert entries[0]["phase_number"] == test_phase
        assert entries[0]["target"] == "test_target"

        # Clear by phase
        cleared = engine.clear_dead_letter(phase_number=test_phase)
        assert cleared == 1

        # Verify cleared
        entries = engine.get_dead_letter_entries(phase_number=test_phase)
        assert entries == []

        # Write a dead letter entry manually
        engine._write_dead_letter(
            76,
            "test_target",
            IngestionResult(
                target="test_target",
                status=IngestionStatus.FAILED,
                error_message="Test error",
            ),
        )

        # Now should have one entry
        entries = engine.get_dead_letter_entries()
        assert len(entries) == 1
        assert entries[0]["phase_number"] == 76
        assert entries[0]["target"] == "test_target"

        # Clear by phase
        cleared = engine.clear_dead_letter(phase_number=76)
        assert cleared == 1

        # Verify cleared
        entries = engine.get_dead_letter_entries()
        assert entries == []


class TestRepoDocsIngestionTarget:
    """Test RepoDocsIngestionTarget."""

    def test_ingest_no_docs(self, tmp_path):
        target = RepoDocsIngestionTarget()
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_skipped == 0

    def test_ingest_dry_run(self, tmp_path):
        target = RepoDocsIngestionTarget()
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs/P76_PLAN.md").write_text("# Plan")

        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_processed == 1
        assert result.metadata.get("note") == "Dry run - not actually ingested"


class TestNotionMemoryIngestionTarget:
    """Test NotionMemoryIngestionTarget."""

    def test_ingest_dry_run(self, tmp_path):
        target = NotionMemoryIngestionTarget()
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
            summary="Test summary",
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_processed == 1
        assert "summary_keys" in result.metadata


class TestTaskPatternIngestionTarget:
    """Test TaskPatternIngestionTarget."""

    def test_ingest_not_done_status(self, tmp_path):
        target = TaskPatternIngestionTarget()
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.IN_PROGRESS,
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_skipped == 1

    def test_ingest_done_status_dry_run(self, tmp_path):
        target = TaskPatternIngestionTarget()
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
            execution_prompt="Test execution",
            summary="Test summary",
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_processed == 1


class TestHandoffIngestionTarget:
    """Test HandoffIngestionTarget."""

    def test_ingest_no_handoff(self, tmp_path):
        target = HandoffIngestionTarget()
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.metadata.get("note") == "No HANDOFF.md found"

    def test_ingest_with_handoff(self, tmp_path):
        target = HandoffIngestionTarget()
        (tmp_path / "HANDOFF.md").write_text("""
# Handoff

### 2024-01-01T00:00:00Z — test-agent
[Test summary]

- [x] Completed task
- [ ] Open task
""")

        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_processed == 1


class TestValidationCoverageIngestionTarget:
    """Test ValidationCoverageIngestionTarget."""

    def test_ingest_dry_run(self, tmp_path):
        target = ValidationCoverageIngestionTarget()
        phase = PhaseRow(
            phase_name="Test Phase",
            phase_number=76,
            status=PhaseStatus.DONE,
            validation_commands=["pytest", "ruff check"],
            validation_summary={"passed": True},
        )
        result = target.ingest(phase, str(tmp_path), dry_run=True)
        assert result.status == IngestionStatus.SUCCESS
        assert result.items_processed == 1
        assert result.metadata.get("command_count") == 2
