"""Placing a pupil in a section enrols them in its compulsory subjects.

Without this a subject-filtered roster (the Maths attendance register, the
Maths mark sheet) is empty until someone enrols every pupil by hand.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def _student(api, admission_no: str) -> dict:
    response = api.post(
        "/students",
        {
            "admission_no": admission_no,
            "display_name": f"Pupil {admission_no}",
            "profile": {"date_of_birth": None, "preferred_language": "en"},
            "guardian_links": [],
            "external_ids": [],
            "duplicate_review": None,
        },
    )
    assert response.status_code == 201, response.content
    return response.json()


def _subject(api, code: str) -> dict:
    response = api.post("/subjects", {"code": code, "display_name": code.title()})
    assert response.status_code == 201, response.content
    return response.json()


def _offer(api, configured, section, subject, *, optional_group=None) -> dict:
    response = api.post(
        "/subject-offerings",
        {
            "year_id": configured["year"]["id"],
            "section_id": section["id"],
            "subject_id": subject["id"],
            "optional_group": optional_group,
        },
    )
    assert response.status_code == 201, response.content
    return response.json()


def _enrol(api, configured, student, section) -> dict:
    response = api.post(
        "/enrolments",
        {
            "student_id": student["id"],
            "year_id": configured["year"]["id"],
            "section_id": section["id"],
            "from_date": "2026-06-01",
            "to_date": None,
        },
    )
    assert response.status_code == 201, response.content
    return response.json()


def _open_offering_ids(student_id: str) -> set[str]:
    from modules.registry.models import SubjectEnrolment

    return {
        str(row.subject_offering_id)
        for row in SubjectEnrolment.objects.filter(
            enrolment__student_id=student_id, to_date__isnull=True
        )
    }


def test_enrolment_adds_every_compulsory_subject_but_not_electives(api, configured):
    section = configured["section"]
    maths = _offer(api, configured, section, _subject(api, "MATH"))
    english = _offer(api, configured, section, _subject(api, "ENG"))
    _offer(api, configured, section, _subject(api, "ART"), optional_group="elective")
    pupil = _student(api, "A-1")
    _enrol(api, configured, pupil, section)
    assert _open_offering_ids(pupil["id"]) == {maths["id"], english["id"]}


def test_a_subject_added_later_reaches_pupils_already_in_the_section(api, configured):
    section = configured["section"]
    pupil = _student(api, "A-2")
    _enrol(api, configured, pupil, section)
    science = _offer(api, configured, section, _subject(api, "SCI"))
    assert science["id"] in _open_offering_ids(pupil["id"])


def test_a_transfer_moves_subject_enrolments_to_the_new_section(api, configured):
    first = configured["section"]
    second = api.post(
        "/sections",
        {
            "year_id": configured["year"]["id"],
            "standard_id": configured["standard"]["id"],
            "name": "B",
        },
    ).json()
    maths = _subject(api, "MATH2")
    in_first = _offer(api, configured, first, maths)
    in_second = _offer(api, configured, second, maths)
    pupil = _student(api, "A-3")
    enrolment = _enrol(api, configured, pupil, first)
    moved = api.post(
        f"/enrolments/{enrolment['id']}/transfer",
        {
            "target_section_id": second["id"],
            "effective_date": "2026-08-01",
            "expected_version": enrolment["version"],
            "reason": "parent request",
        },
    )
    assert moved.status_code in (200, 201), moved.content
    open_ids = _open_offering_ids(pupil["id"])
    assert in_second["id"] in open_ids
    assert in_first["id"] not in open_ids
