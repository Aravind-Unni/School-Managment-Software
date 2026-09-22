"""Scheduled tests, term exams and the assessment calendar."""

from __future__ import annotations

import pytest

from shared import fixtures
from shared.fakes.registry import FIXTURE_TERM_ID

pytestmark = pytest.mark.module


def _schedule_exam(api, **overrides):
    body = {
        "term_id": str(FIXTURE_TERM_ID),
        "title": "Term 1 Examination",
        "section_ids": [str(fixtures.CLASS_C1)],
        "papers": [
            {"subject_id": str(fixtures.SUBJECT_MATHS), "date": "2026-09-21", "time": "09:30"},
        ],
    }
    body.update(overrides)
    return api.post("/exam-schedules", body)


def test_exam_creates_one_paper_per_class_and_repeating_skips(api):
    first = _schedule_exam(api)
    assert first.status_code == 200, first.content
    assert first.json()["created"] == 1
    again = _schedule_exam(api).json()
    assert again["created"] == 0
    assert again["already_scheduled"] == 1


def test_exam_needs_a_title(api):
    response = _schedule_exam(api, title="   ")
    assert response.status_code == 422, response.content


def test_family_sees_the_exam_on_the_calendar(api, as_persona):
    _schedule_exam(api)
    as_persona(fixtures.GUARDIAN_G1)
    response = api.get(
        f"/assessment-calendar?from=2026-09-01&to=2026-09-30&student_id={fixtures.STUDENT_S1}"
    )
    assert response.status_code == 200, response.content
    items = response.json()["items"]
    assert [(row["date"], row["time"], row["type"], row["title"]) for row in items] == [
        ("2026-09-21", "09:30", "exam", "Term 1 Examination")
    ]
    assert items[0]["subject_name"] == "Mathematics"


def test_another_family_cannot_read_the_calendar(api, as_persona):
    _schedule_exam(api)
    as_persona(fixtures.GUARDIAN_G2)
    response = api.get(
        f"/assessment-calendar?from=2026-09-01&to=2026-09-30&student_id={fixtures.STUDENT_S1}"
    )
    assert response.status_code == 404, response.content


def test_a_teachers_dated_test_has_its_title(api):
    response = api.post(
        "/assessments",
        {
            "year_id": "66632073-44d5-5c85-9583-95ee9424d514",
            "term_id": str(FIXTURE_TERM_ID),
            "section_id": str(fixtures.CLASS_C1),
            "subject_id": str(fixtures.SUBJECT_MATHS),
            "type": "written_test",
            "title": "Unit Test 2",
            "due_at": "2026-09-25T04:00:00Z",
            "policy_version": "school-v1",
            "max_score": "25.00",
            "components": [
                {"max_score": "25.00", "weight": "1.000", "topic": None, "question_type": None}
            ],
        },
    )
    assert response.status_code == 201, response.content
    assert response.json()["title"] == "Unit Test 2"
    items = api.get("/assessment-calendar?from=2026-09-25&to=2026-09-25").json()["items"]
    assert [(row["title"], row["time"]) for row in items] == [("Unit Test 2", "09:30")]


def test_a_pupil_does_not_see_a_test_in_a_subject_they_do_not_take(api, as_persona):
    """An elective the pupil dropped is somebody else's exam, not theirs.

    S2 is moved onto malayalam only, so the C1 maths exam stops being S2's
    business even though it is their class's exam.
    """
    from shared.fakes.registry import SUBJECT_ENROLMENTS
    from shared.ports import runtime

    registry = runtime.get_registry().resolve("registry")
    registry._enrolment_overlay = {
        **SUBJECT_ENROLMENTS,
        fixtures.STUDENT_S2: (fixtures.SUBJECT_MALAYALAM,),
    }
    _schedule_exam(api)

    as_persona(fixtures.GUARDIAN_G1)
    items = api.get(
        f"/assessment-calendar?from=2026-09-01&to=2026-09-30&student_id={fixtures.STUDENT_S2}"
    ).json()["items"]

    assert items == []


def test_the_calendar_says_which_tests_are_the_teachers_own(api):
    """T1 teaches C1 maths, so the C1 maths exam is marked as theirs."""
    _schedule_exam(api)

    items = api.get("/assessment-calendar?from=2026-09-01&to=2026-09-30").json()["items"]

    assert items
    assert all(row["mine"] is True for row in items)
