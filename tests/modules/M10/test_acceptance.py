"""Acceptance cases: candidates, preferences, export, isolation, rollback."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from shared import fixtures
from shared.harness.models import HarnessAuditRecord, HarnessOutboxEvent

pytestmark = [pytest.mark.module]


def test_duplicate_leaving_creates_one_candidate(client, baseline):
    """Redelivered leaving_event_id yields the same candidate."""
    from datetime import UTC, datetime

    from contracts.identity import AuthLevel, RequestContext
    from modules.alumni.api import deps
    from modules.alumni.models import AlumniCandidate

    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        request_id="dup-leave",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=datetime(2026, 9, 21, 4, 30, tzinfo=UTC),
    )
    first = deps.alumni_port().create_candidate(
        ctx,
        UUID(baseline["graduate_student_id"]),
        UUID(baseline["duplicate_leaving_event_id"]),
        "graduate",
    )
    second = deps.alumni_port().create_candidate(
        ctx,
        UUID(baseline["graduate_student_id"]),
        UUID(baseline["duplicate_leaving_event_id"]),
        "graduate",
    )
    assert first.id == second.id
    assert (
        AlumniCandidate.objects.filter(
            school_id=fixtures.SCHOOL_A,
            leaving_event_id=baseline["duplicate_leaving_event_id"],
        ).count()
        == 1
    )


def test_transfer_remains_pending_without_policy(client, baseline):
    """transfer_include_as_alumni null keeps transfer candidate pending."""
    from modules.alumni.models import AlumniCandidate, AlumniPolicy

    policy = AlumniPolicy.objects.get(school_id=fixtures.SCHOOL_A)
    assert policy.transfer_include_as_alumni is None
    row = AlumniCandidate.objects.get(id=baseline["transfer_candidate_id"])
    assert row.outcome == "transfer"
    assert row.state == "pending"
    listing = client.get("/api/v1/alumni/candidates")
    assert listing.status_code == 200
    ids = {item["id"] for item in listing.json()["items"]}
    assert baseline["transfer_candidate_id"] in ids


def test_approved_profile_has_no_grade_fields(client, baseline):
    """AlumniProfileDTO carries snapshot identity only — no marks/grades."""
    res = client.post(
        f"/api/v1/alumni/candidates/{baseline['graduate_candidate_id']}/approve",
        data=json.dumps(
            {
                "include": True,
                "reason": "graduated year 12",
                "contact_policy": {
                    "fields": {"email": "grad.s1@example.test", "phone": None},
                    "preferences": [
                        {"purpose": "alumni_notice", "channel": "email", "allowed": True}
                    ],
                },
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 200, res.content
    body = res.json()
    assert "marks" not in body
    assert "grades" not in body
    assert "transcript" not in body
    assert set(body["contact_fields"]) <= {"email", "phone", "postal_address"}
    assert body["last_standard"] == 12
    assert HarnessOutboxEvent.objects.filter(event_type="alumni.profile_approved").count() == 1


def test_unrelated_actor_denied(client, baseline, as_persona):
    """Scenario unrelated actor cannot list or read alumni."""
    as_persona(UUID(baseline["unrelated_actor_id"]))
    listing = client.get("/api/v1/alumni")
    assert listing.status_code == 403
    candidates = client.get("/api/v1/alumni/candidates")
    assert candidates.status_code == 403


def test_preference_withdrawal_excludes_selection(client, baseline):
    """allowed=false removes the profile from contact selection."""
    from modules.alumni.services.profiles import is_selectable_for_contact

    approved = client.post(
        f"/api/v1/alumni/candidates/{baseline['graduate_candidate_id']}/approve",
        data=json.dumps(
            {
                "include": True,
                "reason": "include graduate",
                "contact_policy": {
                    "preferences": [
                        {"purpose": "alumni_notice", "channel": "email", "allowed": True}
                    ]
                },
            }
        ),
        content_type="application/json",
    )
    assert approved.status_code == 200
    profile = approved.json()
    assert is_selectable_for_contact(
        UUID(profile["id"]), purpose="alumni_notice", channel="email"
    )
    patched = client.patch(
        f"/api/v1/alumni/{profile['id']}/contact",
        data=json.dumps(
            {
                "expected_version": profile["version"],
                "reason": "withdraw email notices",
                "preferences": [
                    {"purpose": "alumni_notice", "channel": "email", "allowed": False}
                ],
            }
        ),
        content_type="application/json",
    )
    assert patched.status_code == 200, patched.content
    assert not is_selectable_for_contact(
        UUID(profile["id"]), purpose="alumni_notice", channel="email"
    )
    assert (
        HarnessOutboxEvent.objects.filter(
            event_type="alumni.contact_preference_changed"
        ).count()
        == 1
    )


def test_export_field_not_granted_rejected(client, baseline):
    """Phone is not in fixture exportable_fields → 422."""
    res = client.post(
        "/api/v1/alumni/exports",
        data=json.dumps(
            {
                "filters": {"year": 2026, "outcome": "graduate"},
                "fields": ["display_name", "phone"],
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 422
    assert res.json()["message_key"] == "alumni.error.export_field_not_granted"


def test_export_granted_fields_accepted(client, baseline):
    """Granted field set returns 202 ExportJobDTO."""
    res = client.post(
        "/api/v1/alumni/exports",
        data=json.dumps(
            {
                "filters": {"year": 2026},
                "fields": ["display_name", "email"],
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 202, res.content
    body = res.json()
    assert body["state"] == "queued"
    assert "job_id" in body


def test_cross_school_profile_is_404(client, baseline):
    """Other-school profile id is 404."""
    from modules.alumni.models import AlumniProfile

    foreign = AlumniProfile.objects.create(
        school_id=fixtures.SCHOOL_B,
        student_id=fixtures.STUDENT_S1_SCHOOL_B,
        candidate_id=UUID("aaaaaaaa-bbbb-5ccc-8ddd-eeeeeeeeeeee"),
        last_standard=10,
        leaving_year=2025,
        outcome="graduate",
        snapshot_version=1,
        version=1,
        display_name="S1_B",
        admission_no="B-9",
    )
    res = client.patch(
        f"/api/v1/alumni/{foreign.id}/contact",
        data=json.dumps(
            {
                "expected_version": 1,
                "reason": "probe",
                "fields": {"email": "x@example.test"},
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 404


def test_stale_version_conflict(client, baseline):
    """Stale expected_version on contact patch is 409."""
    approved = client.post(
        f"/api/v1/alumni/candidates/{baseline['graduate_candidate_id']}/approve",
        data=json.dumps({"include": True, "reason": "ok"}),
        content_type="application/json",
    )
    assert approved.status_code == 200
    profile = approved.json()
    stale = client.patch(
        f"/api/v1/alumni/{profile['id']}/contact",
        data=json.dumps(
            {
                "expected_version": 99,
                "reason": "stale write",
                "fields": {"email": "a@example.test"},
            }
        ),
        content_type="application/json",
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "version_conflict"


def test_rollback_clears_audit_and_outbox(client, baseline):
    """Injected platform failure rolls back approve audit and outbox."""
    from shared.fakes.failures import InjectedFailure
    from shared.ports import runtime

    platform = runtime.get_registry().resolve("platform")
    platform._failures.fail(
        "platform.append_event",
        on_call=platform._failures.call_count("platform.append_event") + 1,
    )
    with pytest.raises(InjectedFailure):
        client.post(
            f"/api/v1/alumni/candidates/{baseline['graduate_candidate_id']}/approve",
            data=json.dumps({"include": True, "reason": "should roll back"}),
            content_type="application/json",
        )
    assert HarnessOutboxEvent.objects.filter(event_type="alumni.profile_approved").count() == 0
    assert HarnessAuditRecord.objects.filter(action="alumni.profile_approved").count() == 0
    from modules.alumni.models import AlumniCandidate

    assert AlumniCandidate.objects.get(id=baseline["graduate_candidate_id"]).state == "pending"


def test_explicit_include_transfer_still_allowed(client, baseline):
    """Reviewer may explicitly include a transfer; policy null only blocks auto."""
    res = client.post(
        f"/api/v1/alumni/candidates/{baseline['transfer_candidate_id']}/approve",
        data=json.dumps({"include": True, "reason": "board approved transfer alumni"}),
        content_type="application/json",
    )
    assert res.status_code == 200, res.content
    assert res.json()["outcome"] == "transfer"
