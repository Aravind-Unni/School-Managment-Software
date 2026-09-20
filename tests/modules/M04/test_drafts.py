"""Step 1: periods, draft create/save, authorisation and roster rules."""

from __future__ import annotations

import uuid

import pytest
from shared import fixtures

pytestmark = pytest.mark.module

DATE = fixtures.TERM_SAMPLE_DATE.isoformat()


def test_list_periods_for_t1(api, p1_id):
    """T1 sees P1 (maths) among authorised periods."""
    response = api.get(f"/attendance/periods?date={DATE}")
    assert response.status_code == 200, response.content
    body = response.json()
    ids = {item["timetable_session_id"] for item in body["items"]}
    assert str(p1_id) in ids
    assert all(item["submission_state"] == "unopened" for item in body["items"])


def test_t1_cannot_open_p2(api, p2_id, as_persona):
    """Assigned maths teacher cannot mark English P2."""
    as_persona(fixtures.TEACHER_T1)
    response = api.post("/attendance/sessions", {"timetable_session_id": str(p2_id)})
    assert response.status_code == 403


def test_t3_can_open_substituted_p2(api, p2_id, as_persona):
    """Dated substitute T3 may open P2."""
    as_persona(fixtures.TEACHER_T3)
    response = api.post("/attendance/sessions", {"timetable_session_id": str(p2_id)})
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["state"] == "draft"
    enrolments = {row["student_id"] for row in body["roster_snapshot"]}
    assert str(fixtures.STUDENT_S1) in enrolments
    assert str(fixtures.STUDENT_S2) in enrolments
    assert str(fixtures.STUDENT_S3) not in enrolments


def test_unknown_session_404(api):
    """Unknown timetable_session_id is 404."""
    response = api.post("/attendance/sessions", {"timetable_session_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_idempotent_create(api, p1_id):
    """Repeated create returns the same session id."""
    body = {"timetable_session_id": str(p1_id)}
    first = api.post("/attendance/sessions", body)
    second = api.post("/attendance/sessions", body)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_entries_start_unmarked(api, p1_id):
    """No untouched entry becomes present."""
    response = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)})
    body = response.json()
    assert all(e["status"] == "unmarked" for e in body["entries"])


def test_enrolment_not_on_roster_rejected(api, p2_id, as_persona):
    """Saving S3 onto English P2 is 422."""
    as_persona(fixtures.TEACHER_T3)
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p2_id)}).json()
    foreign_enrolment = fixtures.fixture_uuid(
        f"enrolment.{fixtures.STUDENT_S3}.{fixtures.CLASS_C1}"
    )
    response = api.put(
        f"/attendance/sessions/{created['id']}",
        {
            "expected_version": created["version"],
            "entries": [{"enrolment_id": str(foreign_enrolment), "status": "present"}],
        },
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "attendance.error.enrolment_not_on_roster"


def test_save_marks(api, p1_id):
    """Teacher can save present/absent on the draft."""
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    entries = [
        {"enrolment_id": row["enrolment_id"], "status": "present"}
        for row in created["roster_snapshot"]
    ]
    response = api.put(
        f"/attendance/sessions/{created['id']}",
        {"expected_version": created["version"], "entries": entries},
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["version"] == created["version"] + 1
    assert all(e["status"] == "present" for e in body["entries"])
