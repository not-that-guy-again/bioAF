import pytest
from pydantic import ValidationError

from app.schemas.naming_profile import (
    NamingProfileCreate,
    NamingProfileTestRequest,
    SegmentDefinition,
)
from app.schemas.ingest import (
    BulkReassignRequest,
    IngestSimulateRequest,
)
from app.schemas.pipeline_trigger import (
    BudgetCheckResult,
    EventTriggerConfig,
    PipelineTriggerCreate,
    ScheduleTriggerConfig,
)


class TestSegmentDefinition:
    def test_valid_segment(self):
        seg = SegmentDefinition(position=0, field="date", format="YYYY-MM-DD", required=True)
        assert seg.field == "date"
        assert seg.position == 0

    def test_invalid_field_value(self):
        with pytest.raises(ValidationError):
            SegmentDefinition(position=0, field="invalid_field", required=True)

    def test_negative_position(self):
        with pytest.raises(ValidationError):
            SegmentDefinition(position=-1, field="date", required=True)


class TestNamingProfileCreate:
    def test_valid_profile(self):
        profile = NamingProfileCreate(
            name="Test Profile",
            segments=[SegmentDefinition(position=0, field="date", required=True)],
        )
        assert profile.name == "Test Profile"
        assert profile.delimiter == "_"
        assert profile.strip_extension is True

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            NamingProfileCreate(
                name="   ",
                segments=[SegmentDefinition(position=0, field="date", required=True)],
            )

    def test_empty_segments_rejected(self):
        with pytest.raises(ValidationError):
            NamingProfileCreate(name="Test", segments=[])

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            NamingProfileCreate(name="Test")  # type: ignore[call-arg]


class TestNamingProfileTestRequest:
    def test_valid_request(self):
        req = NamingProfileTestRequest(filenames=["test.fastq", "sample.bam"])
        assert len(req.filenames) == 2

    def test_empty_filenames_rejected(self):
        with pytest.raises(ValidationError):
            NamingProfileTestRequest(filenames=[])


class TestIngestSimulateRequest:
    def test_valid_request(self):
        req = IngestSimulateRequest(filename="test.fastq", file_size_bytes=1024)
        assert req.filename == "test.fastq"

    def test_empty_filename_rejected(self):
        with pytest.raises(ValidationError):
            IngestSimulateRequest(filename="   ")


class TestBulkReassignRequest:
    def test_valid_request(self):
        req = BulkReassignRequest(file_ids=[1, 2, 3], target_project_id=1)
        assert len(req.file_ids) == 3

    def test_empty_file_ids_rejected(self):
        with pytest.raises(ValidationError):
            BulkReassignRequest(file_ids=[])


class TestEventTriggerConfig:
    def test_valid_config(self):
        cfg = EventTriggerConfig(file_types=["fastq"], batching_window_minutes=15)
        assert cfg.batching_window_minutes == 15

    def test_empty_file_types_rejected(self):
        with pytest.raises(ValidationError):
            EventTriggerConfig(file_types=[])

    def test_negative_window_rejected(self):
        with pytest.raises(ValidationError):
            EventTriggerConfig(file_types=["fastq"], batching_window_minutes=-1)


class TestScheduleTriggerConfig:
    def test_valid_config(self):
        cfg = ScheduleTriggerConfig(
            cron_expression="0 6 * * 1-5",
            file_types=["fastq"],
        )
        assert cfg.timezone == "UTC"

    def test_invalid_cron_rejected(self):
        with pytest.raises(ValidationError):
            ScheduleTriggerConfig(cron_expression="bad", file_types=["fastq"])


class TestPipelineTriggerCreate:
    def test_event_driven_requires_event_config(self):
        with pytest.raises(ValidationError):
            PipelineTriggerCreate(
                pipeline_id=1,
                trigger_mode="event_driven",
                event_config=None,
            )

    def test_scheduled_requires_schedule_config(self):
        with pytest.raises(ValidationError):
            PipelineTriggerCreate(
                pipeline_id=1,
                trigger_mode="scheduled",
                schedule_config=None,
            )

    def test_manual_needs_no_config(self):
        trigger = PipelineTriggerCreate(pipeline_id=1, trigger_mode="manual")
        assert trigger.trigger_mode == "manual"

    def test_event_driven_with_config(self):
        trigger = PipelineTriggerCreate(
            pipeline_id=1,
            trigger_mode="event_driven",
            event_config=EventTriggerConfig(file_types=["fastq"]),
        )
        assert trigger.event_config is not None


class TestBudgetCheckResult:
    def test_valid_result(self):
        result = BudgetCheckResult(
            estimated_cost=5.0,
            confidence_interval_pct=15.0,
            current_month_spend=100.0,
            queued_running_cost=10.0,
            projected_total=115.0,
            monthly_budget=500.0,
            decision="within_budget",
        )
        assert result.decision == "within_budget"

    def test_invalid_decision_rejected(self):
        with pytest.raises(ValidationError):
            BudgetCheckResult(
                estimated_cost=5.0,
                confidence_interval_pct=15.0,
                current_month_spend=100.0,
                queued_running_cost=10.0,
                projected_total=115.0,
                monthly_budget=500.0,
                decision="invalid",
            )
