"""Baseline seed for M04: submit P1 (S1 present, S2 absent, S3 present); leave P2 unmarked."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures
from shared.fakes.timetable import session_id_for

from .api import deps

SCENARIO_DATE = fixtures.TERM_SAMPLE_DATE
FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load the contracted baseline scenario into the attendance database.

    Assumes FakeTimetable + M04 FakeRegistry overlays are bound. Creates and
    submits P1 as T1; leaves P2 unopened.
    """
    school = school_id or fixtures.SCHOOL_A
    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    p1 = session_id_for(
        school_id=school,
        section_id=fixtures.CLASS_C1,
        on=SCENARIO_DATE,
        slot_code="P1",
    )
    drafts = deps.draft_service()
    submit = deps.submit_service()
    session = drafts.create_or_get(ctx, timetable_session_id=p1)
    # Map students to enrolments from snapshot.
    by_student = {row["student_id"]: row["enrolment_id"] for row in session["roster_snapshot"]}
    entries = [
        {
            "enrolment_id": UUID(by_student[str(fixtures.STUDENT_S1)]),
            "status": "present",
        },
        {
            "enrolment_id": UUID(by_student[str(fixtures.STUDENT_S2)]),
            "status": "absent",
        },
        {
            "enrolment_id": UUID(by_student[str(fixtures.STUDENT_S3)]),
            "status": "present",
        },
    ]
    saved = drafts.save_entries(
        ctx,
        session_id=UUID(session["id"]),
        expected_version=session["version"],
        entries=entries,
    )
    submitted = submit.submit(
        ctx,
        session_id=UUID(saved["id"]),
        expected_version=saved["version"],
        idempotency_key="seed-baseline-p1",
    )
    return {
        "scenario": "baseline",
        "p1_session_id": submitted["id"],
        "p1_timetable_session_id": str(p1),
        "date": SCENARIO_DATE.isoformat(),
        "sessions": 1,
        "entries": 3,
    }


def empty(*, school_id=None) -> dict[str, int]:
    """No-op empty scenario for harness completeness."""
    return {"sessions": 0, "entries": 0}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
