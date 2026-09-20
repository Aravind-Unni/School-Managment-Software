"""Acceptance cases: metrics, warnings, dedupe, visibility, rebuild."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from django.db import transaction

from shared import fixtures

pytestmark = [pytest.mark.module]


def test_hand_calculated_mean_and_attendance(client, baseline):
    """A1: S1 mean 65.00 and attendance 80.00."""
    assert baseline["s1_overall_mean"] == "65.00"
    assert baseline["s1_attendance"] == "80.00"
    res = client.get(
        "/api/v1/performance/dashboard",
        {
            "scope": "student",
            "window": "term",
            "student_id": str(fixtures.STUDENT_S1),
        },
    )
    assert res.status_code == 200
    body = res.json()
    by_code = {m["code"]: m for m in body["metrics"]}
    assert by_code["overall_mean"]["value"] == "65.00"
    assert by_code["attendance_percentage"]["value"] == "80.00"
    assert by_code["topic_weakness"]["status"] == "insufficient_data"


def test_s2_missing_inputs_labeled(client, baseline):
    """A2: S2 shows insufficient/incomplete, no invented values."""
    res = client.get(
        "/api/v1/performance/dashboard",
        {
            "scope": "student",
            "window": "term",
            "student_id": str(fixtures.STUDENT_S2),
        },
    )
    assert res.status_code == 200
    by_code = {m["code"]: m for m in res.json()["metrics"]}
    assert by_code["overall_mean"]["status"] == "insufficient_data"
    assert by_code["overall_mean"]["value"] is None
    assert by_code["attendance_percentage"]["status"] == "incomplete"
    assert by_code["attendance_percentage"]["value"] is None


def test_incompatible_policies_not_averaged(db, clock):
    """A4: mixed policy_version → incompatible status."""
    from modules.performance.services.metrics import simple_mean_percent

    value, status = simple_mean_percent(
        [("60.00", "100.00", "a"), ("70.00", "100.00", "b")]
    )
    assert value is None
    assert status == "incompatible"


def test_repeated_evaluate_no_duplicate_warning(client, baseline, clock):
    """A5: re-evaluate does not open a second warning."""
    from contracts.identity import AuthLevel, RequestContext
    from modules.performance.models import Warning
    from modules.performance.services import wire

    before = Warning.objects.filter(student_id=fixtures.STUDENT_S1, state="open").count()
    assert before == 1
    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        request_id="dedupe",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=clock.now(),
    )
    wire.warning_service().evaluate_student(ctx, fixtures.STUDENT_S1)
    after = Warning.objects.filter(student_id=fixtures.STUDENT_S1, state="open").count()
    assert after == 1


def test_dismiss_warning_traceable(client, baseline):
    """A6: dismiss retains reason and history."""
    from modules.performance.models import Warning, WarningHistory

    warning = Warning.objects.get(student_id=fixtures.STUDENT_S1, state="open")
    res = client.post(
        f"/api/v1/warnings/{warning.id}/dismiss",
        data=json.dumps({"reason": "parent conference planned", "expected_version": 1}),
        content_type="application/json",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["state"] == "dismissed"
    assert body["reason"] == "parent conference planned"
    assert WarningHistory.objects.filter(warning_id=warning.id, to_state="dismissed").exists()


def test_unrelated_guardian_denied(client, baseline, as_persona):
    """A7: G2 cannot see S1 dashboard."""
    as_persona(fixtures.GUARDIAN_G2)
    res = client.get(
        "/api/v1/performance/dashboard",
        {
            "scope": "child",
            "window": "term",
            "student_id": str(fixtures.STUDENT_S1),
        },
    )
    assert res.status_code == 404


def test_restricted_notes_absent_from_guardian_export(client, baseline, as_persona):
    """A8: G1 export omits restricted observations."""
    as_persona(fixtures.GUARDIAN_G1)
    res = client.get(
        "/api/v1/performance/export",
        {"student_id": str(fixtures.STUDENT_S1), "window": "term"},
    )
    assert res.status_code == 200
    observations = res.json()["observations"]
    assert all(o["visibility"] != "restricted" for o in observations)
    assert observations == []


def test_full_rebuild_matches_projections(client, baseline):
    """A9: rebuild keeps S1 mean 65 and attendance 80."""
    res = client.post("/api/v1/performance/rebuild", data=b"{}", content_type="application/json")
    assert res.status_code == 202
    dash = client.get(
        "/api/v1/performance/dashboard",
        {
            "scope": "student",
            "window": "term",
            "student_id": str(fixtures.STUDENT_S1),
        },
    ).json()
    by_code = {m["code"]: m for m in dash["metrics"]}
    assert by_code["overall_mean"]["value"] == "65.00"
    assert by_code["attendance_percentage"]["value"] == "80.00"


def test_stale_version_409(client, baseline):
    """A11: acknowledge with stale expected_version → 409."""
    from modules.performance.models import Warning

    warning = Warning.objects.get(student_id=fixtures.STUDENT_S1, state="open")
    res = client.post(
        f"/api/v1/warnings/{warning.id}/acknowledge",
        data=json.dumps({"reason": "seen", "expected_version": 99}),
        content_type="application/json",
    )
    assert res.status_code == 409


def test_foreign_school_404(client, baseline, as_persona):
    """A12: School B student id while actor is School A → 404."""
    res = client.get(
        "/api/v1/performance/dashboard",
        {
            "scope": "student",
            "window": "term",
            "student_id": str(fixtures.STUDENT_S1_SCHOOL_B),
        },
    )
    assert res.status_code == 404


def test_intervention_and_meeting_create(client, baseline):
    """Create intervention and meeting for S1."""
    res = client.post(
        "/api/v1/interventions",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "goal": "Fraction revision pack",
                "owner_id": str(fixtures.TEACHER_T1),
                "review_date": "2026-08-01",
                "resource_ids": ["6c9d4e47-7502-5649-a661-3a9b673a90da"],
                "visibility": "guardian_visible",
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 201
    meeting = client.post(
        "/api/v1/meetings",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "date": "2026-07-20",
                "participants": [str(fixtures.TEACHER_T1), str(fixtures.GUARDIAN_G1)],
                "notes": "Discuss attendance",
                "actions": ["daily check-in"],
                "visibility": "staff",
            }
        ),
        content_type="application/json",
    )
    assert meeting.status_code == 201


def test_audit_rolls_back_with_failed_write(client, baseline, clock):
    """Failed dismiss does not leave a partial audit when version conflicts."""
    from modules.performance.models import Warning
    from shared.ports import runtime

    platform = runtime.get_registry().resolve("platform")
    before = len(platform.audit_rows(school_id=fixtures.SCHOOL_A))
    warning = Warning.objects.get(student_id=fixtures.STUDENT_S1, state="open")
    res = client.post(
        f"/api/v1/warnings/{warning.id}/dismiss",
        data=json.dumps({"reason": "x", "expected_version": 999}),
        content_type="application/json",
    )
    assert res.status_code == 409
    after = len(platform.audit_rows(school_id=fixtures.SCHOOL_A))
    assert after == before


def test_simple_mean_math():
    """Pure mean: (60+70)/2 = 65."""
    from modules.performance.services.metrics import simple_mean_percent

    value, status = simple_mean_percent(
        [("60.00", "100.00", "illustrative-v0"), ("70.00", "100.00", "illustrative-v0")]
    )
    assert status == "ok"
    assert Decimal(value) == Decimal("65.00")
