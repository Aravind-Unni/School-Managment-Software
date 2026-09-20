"""Corrections, summaries, reconciliation and baseline seed outcomes."""

from __future__ import annotations

import pytest

from modules.attendance.models import AttendanceAmendment, AttendanceEntry, AttendanceSession
from modules.attendance.seeds import seed_baseline
from shared import fixtures
from shared.harness.models import HarnessAuditRecord, HarnessOutboxEvent

pytestmark = pytest.mark.module

DATE = fixtures.TERM_SAMPLE_DATE.isoformat()


def _mark_all(api, session_body, status="present"):
    entries = [
        {"enrolment_id": row["enrolment_id"], "status": status}
        for row in session_body["roster_snapshot"]
    ]
    return api.put(
        f"/attendance/sessions/{session_body['id']}",
        {"expected_version": session_body["version"], "entries": entries},
    ).json()


def test_baseline_summary_counts(api, clock):
    """After seed: S1/S2 eligible=2 marked=1; S3 eligible=1."""
    seed_baseline()
    for student, expect in (
        (
            fixtures.STUDENT_S1,
            {"eligible": 2, "marked": 1, "present": 1, "absent": 0, "unmarked": 1},
        ),
        (
            fixtures.STUDENT_S2,
            {"eligible": 2, "marked": 1, "present": 0, "absent": 1, "unmarked": 1},
        ),
        (
            fixtures.STUDENT_S3,
            {"eligible": 1, "marked": 1, "present": 1, "absent": 0, "unmarked": 0},
        ),
    ):
        response = api.get(f"/attendance/summary?student_id={student}&from={DATE}&to={DATE}")
        assert response.status_code == 200, response.content
        body = response.json()
        for key, value in expect.items():
            assert body[key] == value, (student, key, body)
        assert body["percentage"] is None
        assert body["unit"] == "period"


def test_correction_emits_event(api, p1_id):
    """Correction of a submitted entry emits attendance.corrected and keeps history."""
    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    saved = _mark_all(api, created)
    submitted = api.client.post(
        f"/api/v1/attendance/sessions/{saved['id']}/submit",
        data={"expected_version": saved["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="correct-setup",
    ).json()
    entry = next(e for e in submitted["entries"] if e["student_id"] == str(fixtures.STUDENT_S1))
    response = api.post(
        f"/attendance/entries/{entry['id']}/corrections",
        {
            "status": "absent",
            "reason": "marked in error",
            "expected_version": entry["version"],
        },
    )
    assert response.status_code == 200, response.content
    assert response.json()["entry"]["status"] == "absent"
    assert AttendanceAmendment.objects.filter(entry_id=entry["id"]).count() == 1
    assert HarnessOutboxEvent.objects.filter(event_type="attendance.corrected").count() == 1


def test_reconciliation_preserves_history(api, p1_id, timetable, as_persona):
    """Cancel after submit; reconcile keeps entries and records audit."""
    from modules.attendance.api import deps

    created = api.post("/attendance/sessions", {"timetable_session_id": str(p1_id)}).json()
    saved = _mark_all(api, created)
    submitted = api.client.post(
        f"/api/v1/attendance/sessions/{saved['id']}/submit",
        data={"expected_version": saved["version"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="reconcile-setup",
    ).json()
    entry_count_before = AttendanceEntry.objects.filter(session_id=submitted["id"]).count()
    timetable.cancel_session(p1_id)
    from datetime import UTC, datetime

    from contracts.identity import AuthLevel, RequestContext

    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        request_id="reconcile-test",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=datetime(2026, 7, 15, 4, 30, tzinfo=UTC),
    )
    refreshed = deps.reconcile_service().reconcile_after_cancellation(
        ctx, session_id=submitted["id"], reason="period cancelled after submission"
    )
    assert refreshed.entries.count() == entry_count_before
    assert refreshed.reconciliation_reason.startswith("period cancelled")
    assert AttendanceSession.objects.filter(id=submitted["id"]).exists()
    assert HarnessAuditRecord.objects.filter(action="attendance.session_reconciled").exists()


def test_holiday_adds_no_eligibility(api):
    """Holiday date contributes zero eligible periods."""
    seed_baseline()
    holiday = "2026-07-16"
    response = api.get(
        f"/attendance/summary?student_id={fixtures.STUDENT_S1}&from={holiday}&to={holiday}"
    )
    assert response.status_code == 200
    assert response.json()["eligible"] == 0
