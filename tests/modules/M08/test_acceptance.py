"""Acceptance cases: billing once, timeout retry, overlap, proration, isolation."""

from __future__ import annotations

import json
from datetime import date

import pytest

from shared import fixtures

pytestmark = [pytest.mark.module]

FEE_PLAN_ID = "b8e2c1a0-4f3d-5e6a-9b0c-1d2e3f4a5b6c"
PERIOD = "2026-06"


def test_same_period_billed_once(client, baseline, fees):
    """Same participation/period posts one 50000 paise charge."""
    run = client.post(
        "/api/v1/bus-billing-runs",
        data=json.dumps({"period": PERIOD, "policy_version": 1}),
        content_type="application/json",
    )
    assert run.status_code == 202, run.content
    body = run.json()
    assert body["preview"]["eligible_count"] >= 1
    assert body["state"] == "succeeded"
    charges = fees.list_charges()
    assert len(charges) == 1
    assert charges[0].amount_paise == 50000
    assert charges[0].student_id == fixtures.STUDENT_S1
    # Second run is idempotent.
    again = client.post(
        "/api/v1/bus-billing-runs",
        data=json.dumps({"period": PERIOD, "policy_version": 1}),
        content_type="application/json",
    )
    assert again.status_code == 202
    assert len(fees.list_charges()) == 1


def test_timeout_after_commit_safe_and_retry_recovers(client, baseline, fees):
    """FeesCommitTimeout leaves requested without charge_id; retry links it."""
    participation_id = baseline["participation_id"]
    source_key = f"transport:{participation_id}:{PERIOD}:period"
    fees.arm_timeout_after_commit(source_key)
    run = client.post(
        "/api/v1/bus-billing-runs",
        data=json.dumps({"period": PERIOD, "policy_version": 1}),
        content_type="application/json",
    )
    assert run.status_code == 202, run.content
    assert len(fees.list_charges()) == 1
    from modules.transport.models import BillingRequest

    row = BillingRequest.objects.get(source_key=source_key)
    assert row.state == "requested"
    assert row.charge_id is None
    recon = client.get(f"/api/v1/bus-billing-reconciliation?period={PERIOD}")
    assert recon.status_code == 200
    kinds = {item["kind"] for item in recon.json()["items"]}
    assert "orphaned_link" in kinds
    retry = client.post(f"/api/v1/bus-billing-requests/{row.id}/retry")
    assert retry.status_code == 200, retry.content
    body = retry.json()
    assert body["state"] == "posted"
    assert body["charge_id"] == str(fees.list_charges()[0].id)
    assert len(fees.list_charges()) == 1


def test_overlap_rejected(client, baseline):
    """Second overlapping participation for S1 is 422."""
    res = client.post(
        "/api/v1/bus-participations",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "from_date": "2026-06-10",
                "fee_plan_id": FEE_PLAN_ID,
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 422
    assert res.json()["message_key"] == "transport.error.overlapping_participation"


def test_version_conflict_on_patch(client, baseline):
    """Stale expected_version returns 409."""
    pid = baseline["participation_id"]
    res = client.patch(
        f"/api/v1/bus-participations/{pid}",
        data=json.dumps({"expected_version": 99, "reason": "stale", "to_date": "2026-06-30"}),
        content_type="application/json",
    )
    assert res.status_code == 409
    assert res.json()["code"] == "version_conflict"


def test_unauthorized_read_denied(client, baseline, as_persona):
    """Unrelated guardian G2 cannot read S1 participation (404)."""
    as_persona(fixtures.GUARDIAN_G2)
    res = client.get(f"/api/v1/bus-participations/{baseline['participation_id']}")
    assert res.status_code == 404


def test_cross_school_participation_is_404(client, baseline):
    """Other-school participation id is 404, never 403."""
    from datetime import date
    from uuid import UUID

    from modules.transport.models import Participation

    foreign = Participation.objects.create(
        school_id=fixtures.SCHOOL_B,
        student_id=fixtures.STUDENT_S1_SCHOOL_B,
        from_date=date(2026, 6, 1),
        fee_plan_id=UUID(FEE_PLAN_ID),
        version=1,
    )
    res = client.get(f"/api/v1/bus-participations/{foreign.id}")
    assert res.status_code == 404


def test_partial_period_blocked_without_proration(client, baseline, fees):
    """Mid-month end date without proration policy blocks billing."""
    pid = baseline["participation_id"]
    patch = client.patch(
        f"/api/v1/bus-participations/{pid}",
        data=json.dumps(
            {
                "expected_version": 1,
                "reason": "left mid month",
                "to_date": "2026-06-15",
            }
        ),
        content_type="application/json",
    )
    assert patch.status_code == 200, patch.content
    run = client.post(
        "/api/v1/bus-billing-runs",
        data=json.dumps({"period": PERIOD, "policy_version": 1}),
        content_type="application/json",
    )
    assert run.status_code == 202
    assert run.json()["preview"]["blocked_count"] >= 1
    assert fees.list_charges() == []
    from modules.transport.models import BillingRequest

    row = BillingRequest.objects.get(participation_id=pid, period=PERIOD)
    assert row.state == "blocked"
    assert row.error_code == "transport.error.proration_policy_missing"


def test_s2_opted_out_no_charge(client, baseline, fees):
    """S2 has no participation; billing only charges S1."""
    client.post(
        "/api/v1/bus-billing-runs",
        data=json.dumps({"period": PERIOD, "policy_version": 1}),
        content_type="application/json",
    )
    charges = fees.list_charges()
    assert all(c.student_id != fixtures.STUDENT_S2 for c in charges)
    participants = client.get("/api/v1/bus-participants?date=2026-06-15")
    assert participants.status_code == 200
    ids = {row["student_id"] for row in participants.json()["items"]}
    assert str(fixtures.STUDENT_S1) in ids
    assert str(fixtures.STUDENT_S2) not in ids


def test_adjustment_credits_via_fees(client, baseline, fees):
    """AdjustmentRequest calls Fees.credit_charge against the posted charge."""
    client.post(
        "/api/v1/bus-billing-runs",
        data=json.dumps({"period": PERIOD, "policy_version": 1}),
        content_type="application/json",
    )
    charge = fees.list_charges()[0]
    res = client.post(
        "/api/v1/bus-adjustments",
        data=json.dumps(
            {
                "charge_id": str(charge.id),
                "amount_paise": 10000,
                "reason": "partial month refund after early exit",
                "source_key": f"transport-adj:{charge.id}:v1",
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 201, res.content
    assert res.json()["state"] == "posted"
    assert fees.get_by_source_key(charge.source_key).balance_paise == 40000


def test_audit_and_events_on_participation(client, baseline):
    """Participation create wrote audit + participation_changed outbox event."""
    from shared.harness.models import HarnessAuditRecord, HarnessOutboxEvent

    assert HarnessOutboxEvent.objects.filter(
        event_type="transport.participation_changed"
    ).exists()
    assert HarnessAuditRecord.objects.filter(action="transport.participation_created").exists()


def test_transport_port_get_participation(baseline):
    """TransportPort returns the seeded S1 participation on as_of."""
    from datetime import UTC, datetime

    from contracts.identity import AuthLevel, RequestContext
    from modules.transport.api import deps

    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        request_id="port-test",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
    )
    view = deps.transport_port().get_participation(ctx, fixtures.STUDENT_S1, date(2026, 6, 15))
    assert view.active is True
    assert str(view.fee_plan_id) == FEE_PLAN_ID
