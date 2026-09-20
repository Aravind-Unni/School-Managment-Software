"""Baseline seed for M06: S1 mean 65% / attendance 80%; S2 missing; topic insufficient.

Seeds FakeAssessment and FakeAttendance, then rebuilds projections and evaluates
warning rules. Uses contracts/M06/fixtures/scenario.json IDs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from contracts.timetable import AttendanceSummaryDTO
from shared import fixtures
from shared.ports import runtime

from .models import (
    MetricDefinition,
    Observation,
    Resource,
    Visibility,
    WarningRule,
)
from .services import wire

FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

TERM_ID = UUID("f76bcdb0-b6b9-5a80-a449-a8a4e423716a")
METRIC_ID = UUID("383477d6-efd2-5325-bc3b-09fe52d9e273")
RULE_ATT = UUID("2f806647-5d30-55ab-9b1f-76436dfb78ff")
RULE_MISS = UUID("b8b7857b-1954-5e67-b9dc-eb7e104748e6")
RESOURCE_ID = UUID("6c9d4e47-7502-5649-a661-3a9b673a90da")
OBS_RESTRICTED = UUID("9c9c9c9c-9c9c-5c9c-9c9c-9c9c9c9c9c9c")


def _seed_upstream(school_id: UUID) -> None:
    """Install FakeAssessment / FakeAttendance baseline rows."""
    assessment = runtime.get_registry().resolve("assessment")
    attendance = runtime.get_registry().resolve("attendance")
    assessment.seed_published_results(
        student_id=fixtures.STUDENT_S1,
        school_id=school_id,
        term_id=TERM_ID,
        items=[
            {
                "result_id": str(UUID("11111111-1111-5111-8111-111111111111")),
                "revision_id": str(UUID("22222222-2222-5222-8222-222222222222")),
                "assessment_id": str(UUID("33333333-3333-5333-8333-333333333333")),
                "subject_id": str(fixtures.SUBJECT_MATHS),
                "status": "published",
                "score": "60.00",
                "max_score": "100.00",
                "grade": None,
                "policy_version": "illustrative-v0",
                "evidence_refs": [],
                "updated_at": FROZEN_INSTANT.isoformat(),
            },
            {
                "result_id": str(UUID("44444444-4444-5444-8444-444444444444")),
                "revision_id": str(UUID("55555555-5555-5555-8555-555555555555")),
                "assessment_id": str(UUID("66666666-6666-5666-8666-666666666666")),
                "subject_id": str(fixtures.SUBJECT_MATHS),
                "status": "published",
                "score": "70.00",
                "max_score": "100.00",
                "grade": None,
                "policy_version": "illustrative-v0",
                "evidence_refs": [],
                "updated_at": FROZEN_INSTANT.isoformat(),
            },
        ],
    )
    assessment.seed_published_results(
        student_id=fixtures.STUDENT_S2,
        school_id=school_id,
        term_id=TERM_ID,
        items=[],
    )
    attendance.seed_summary(
        AttendanceSummaryDTO(
            unit="period",
            student_id=fixtures.STUDENT_S1,
            from_date=fixtures.TERM_START,
            to_date=fixtures.TERM_SAMPLE_DATE,
            eligible=10,
            marked=10,
            present=8,
            absent=2,
            late=0,
            excused=0,
            unmarked=0,
            updated_at=FROZEN_INSTANT,
            subject_id=None,
            percentage="80.00",
            policy_version="period_present_over_eligible_v1",
        ),
        school_id=school_id,
    )
    attendance.seed_missing(student_id=fixtures.STUDENT_S2, school_id=school_id)


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline: definitions, rules, projections, S1 warning."""
    school = school_id or fixtures.SCHOOL_A
    _seed_upstream(school)
    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )

    MetricDefinition.objects.filter(school_id=school).delete()
    WarningRule.objects.filter(school_id=school).delete()
    Observation.objects.filter(school_id=school).delete()
    Resource.objects.filter(school_id=school).delete()

    MetricDefinition.objects.create(
        id=METRIC_ID,
        school_id=school,
        code="overall_mean",
        version=1,
        formula="simple_mean_v1",
        denominator="100",
    )
    WarningRule.objects.create(
        id=RULE_ATT,
        school_id=school,
        code="low_attendance",
        version=1,
        threshold="85.00",
        window="term",
        minimum_samples=5,
        exclusions=[],
    )
    WarningRule.objects.create(
        id=RULE_MISS,
        school_id=school,
        code="missing_work",
        version=1,
        threshold="1",
        window="term",
        minimum_samples=1,
        exclusions=[],
    )
    Resource.objects.create(
        id=RESOURCE_ID,
        school_id=school,
        topic="fractions_revision",
        level="class_6",
        url="https://example.invalid/resources/fractions",
    )
    Observation.objects.create(
        id=OBS_RESTRICTED,
        school_id=school,
        student_id=fixtures.STUDENT_S1,
        kind="behavior",
        body="Restricted staff note — must not appear in guardian export.",
        visibility=Visibility.RESTRICTED,
        created_at=FROZEN_INSTANT,
    )

    proj = wire.projection_service()
    warn = wire.warning_service()
    for student_id in (fixtures.STUDENT_S1, fixtures.STUDENT_S2):
        proj.rebuild_student(ctx, student_id)
        warn.evaluate_student(ctx, student_id)

    from .models import Projection
    from .models import Warning as WarningRow

    s1 = Projection.objects.get(student_id=fixtures.STUDENT_S1, window="term")
    mean = s1.metrics_json["overall_mean"]["value"]
    att = s1.metrics_json["attendance_percentage"]["value"]
    warning_count = WarningRow.objects.filter(
        student_id=fixtures.STUDENT_S1, state="open"
    ).count()
    return {
        "school_id": str(school),
        "s1_overall_mean": mean,
        "s1_attendance": att,
        "s1_open_warnings": warning_count,
    }


def empty(*, school_id=None) -> dict[str, int]:
    """No-op empty scenario for harness completeness."""
    return {"projections": 0, "warnings": 0}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
