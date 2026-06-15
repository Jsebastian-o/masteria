import pytest
from app.schemas import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.prompts.loader import render_estimation_prompt


@pytest.fixture
def base_request():
    return EstimationRequest(
        description="Build a mobile app for tracking daily water intake with reminders and statistics.",
        project_type=ProjectType.MOBILE_APP,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )


def test_user_description_sent_unchanged(base_request):
    _, user = render_estimation_prompt(base_request)
    assert base_request.description in user


def test_output_format_included_in_user_message(base_request):
    _, user = render_estimation_prompt(base_request)
    assert base_request.output_format.value in user


def test_narrative_format_excludes_table_instructions(base_request):
    narrative_request = base_request.model_copy(update={"output_format": OutputFormat.NARRATIVE})
    system, _ = render_estimation_prompt(narrative_request)
    assert "Phase | Tasks | Effort" not in system


def test_summary_detail_level_excludes_phase_breakdown(base_request):
    summary_request = base_request.model_copy(update={"detail_level": DetailLevel.SUMMARY})
    system, _ = render_estimation_prompt(summary_request)
    assert "Break the project into main phases" not in system
    assert "Do not break down individual tasks" in system
