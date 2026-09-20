"""Submit, concurrency, stale versions and idempotency."""

from __future__ import annotations

import pytest
from shared import fixtures
from shared.harness.models import HarnessOutboxEvent

pytestmark = pytest.mark.module


def _open_and_mark(api, p1_id):
    """Create P1 draft and mark every pupil present."""
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    entries = [
        {"enrolment_id": row["enrolment_id"], "status": "present"}
        for row in created["roster_snapshot"]
    ]
    saved = api.put(
        f"/attendance/sessions/{created['id']}",
        {"expected_version": created["version"], "entries": entries},
    ).json()
    return saved


def test_submit_requires_idempotency_key(api, p1_id):
    """Submit without Idempotency-Key is 422."""
    saved = _open_and_mark(api, p1_id)
    response = api.post(
        f"/attendance/sessions/{saved['id']}/submit",
        {"expected_version": saved["version"]},
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "attendance.error.idempotency_key_required"


def test_incomplete_roster_rejected(api, p1_id):
    """Submit with unmarked pupils is 422."""
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    response = api.client.post(
        f"/api/v1/attendance/sessions/{created['id']}/submit",
        data={"expected_version": created["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="incomplete-1",
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "attendance.error.incomplete_roster"


def test_submit_emits_one_event_on_retry(api, p1_id):
    """Same Idempotency-Key twice yields one attendance.submitted event."""
    saved = _open_and_mark(api, p1_id)
    first = api.client.post(
        f"/api/v1/attendance/sessions/{saved['id']}/submit",
        data={"expected_version": saved["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="submit-once",
    )
    second = api.client.post(
        f"/api/v1/attendance/sessions/{saved['id']}/submit",
        data={"expected_version": saved["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="submit-once",
    )
    assert first.status_code == 200, first.content
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    events = HarnessOutboxEvent.objects.filter(event_type="attendance.submitted")
    assert events.count() == 1


def test_stale_version_409(api, p1_id):
    """Wrong expected_version on save is 409."""
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    response = api.put(
        f"/attendance/sessions/{created['id']}",
        {
            "expected_version": created["version"] + 5,
            "entries": [
                {"enrolment_id": created["roster_snapshot"][0]["enrolment_id"], "status": "present"}
            ],
        },
    )
    assert response.status_code == 409


def test_roster_stale_on_version_bump(api, p1_id, timetable):
    """Timetable version bump between draft and save yields roster_stale."""
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    timetable.bump_timetable_version(1)
    entries = [
        {"enrolment_id": row["enrolment_id"], "status": "present"}
        for row in created["roster_snapshot"]
    ]
    response = api.put(
        f"/attendance/sessions/{created['id']}",
        {"expected_version": created["version"], "entries": entries},
    )
    assert response.status_code == 409
    assert response.json()["message_key"] == "attendance.error.roster_stale"


def test_concurrent_duplicate_submit_one_event(api, p1_id):
    """Two submits with different keys: one wins, one conflicts; one event."""
    saved = _open_and_mark(api, p1_id)
    first = api.client.post(
        f"/api/v1/attendance/sessions/{saved['id']}/submit",
        data={"expected_version": saved["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="key-a",
    )
    second = api.client.post(
        f"/api/v1/attendance/sessions/{saved['id']}/submit",
        data={"expected_version": saved["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="key-b",
    )
    assert first.status_code == 200
    assert second.status_code == 409
    assert HarnessOutboxEvent.objects.filter(event_type="attendance.submitted").count() == 1
