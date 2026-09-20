"""Acceptance cases: partial pay, credit, idempotency, reversal, isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from shared import fixtures

pytestmark = [pytest.mark.module]


def test_partial_payment_reduces_outstanding(client, baseline):
    """A1: charge 100000, pay 40000 → charge balance 60000."""
    charge_id = baseline["tuition_charge_id"]
    res = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 40000,
                "method": "upi",
                "reference": "UPI-1",
                "allocations": [{"charge_id": charge_id, "amount_paise": 40000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "pay-partial-1"},
    )
    assert res.status_code == 201, res.content
    body = res.json()
    assert body["balance"]["paid_paise"] == 40000
    from modules.fees.models import Charge

    assert Charge.objects.get(id=charge_id).balance_paise == 60000


def test_credit_after_partial(client, baseline):
    """A2: after partial, credit 10000 → charge balance 50000."""
    charge_id = baseline["tuition_charge_id"]
    client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 40000,
                "method": "cash",
                "allocations": [{"charge_id": charge_id, "amount_paise": 40000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "pay-for-credit"},
    )
    res = client.post(
        "/api/v1/concessions",
        data=json.dumps(
            {
                "charge_id": charge_id,
                "amount_paise": 10000,
                "reason": "Approved hardship concession",
                "source_key": "concession:tuition:s1:v1",
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 201, res.content
    from modules.fees.models import Charge

    assert Charge.objects.get(id=charge_id).balance_paise == 50000


def test_duplicate_idempotency_key(client, baseline):
    """A3: retry same key returns same receipt; balance unchanged."""
    charge_id = baseline["tuition_charge_id"]
    payload = {
        "student_id": str(fixtures.STUDENT_S1),
        "amount_paise": 40000,
        "method": "upi",
        "allocations": [{"charge_id": charge_id, "amount_paise": 40000}],
    }
    first = client.post(
        "/api/v1/payments",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Idempotency-Key": "dup-key-1"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/payments",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Idempotency-Key": "dup-key-1"},
    )
    assert second.status_code == 200
    assert first.json()["payment"]["number"] == second.json()["payment"]["number"]
    assert (
        first.json()["balance"]["outstanding_paise"]
        == second.json()["balance"]["outstanding_paise"]
    )


def test_idempotency_payload_conflict(client, baseline):
    """A4: same key different payload → 409."""
    charge_id = baseline["tuition_charge_id"]
    client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 10000,
                "method": "cash",
                "allocations": [{"charge_id": charge_id, "amount_paise": 10000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "conflict-key"},
    )
    res = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 20000,
                "method": "cash",
                "allocations": [{"charge_id": charge_id, "amount_paise": 20000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "conflict-key"},
    )
    assert res.status_code == 409
    assert res.json()["message_key"] == "fees.error.idempotency_payload_conflict"


def test_reversal_restores_balance(client, baseline):
    """A6: reverse payment restores charge balance."""
    charge_id = baseline["tuition_charge_id"]
    pay = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 40000,
                "method": "bank",
                "allocations": [{"charge_id": charge_id, "amount_paise": 40000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "rev-pay"},
    ).json()
    res = client.post(
        f"/api/v1/payments/{pay['payment']['id']}/reversals",
        data=json.dumps(
            {
                "reason": "posted to wrong student",
                "expected_version": pay["payment"]["version"],
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 200, res.content
    from modules.fees.models import Charge

    assert Charge.objects.get(id=charge_id).balance_paise == 100000


def test_overpayment_tracked_as_credit(client, baseline):
    """A7: payment exceeding allocation creates overpayment credit."""
    charge_id = baseline["tuition_charge_id"]
    res = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 50000,
                "method": "upi",
                "allocations": [{"charge_id": charge_id, "amount_paise": 40000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "overpay-1"},
    )
    assert res.status_code == 201
    assert res.json()["balance"]["credit_available_paise"] == 10000


def test_unrelated_guardian_denied(client, baseline, as_persona):
    """A8: G2 cannot read S1 statement."""
    as_persona(fixtures.GUARDIAN_G2)
    res = client.get(f"/api/v1/students/{fixtures.STUDENT_S1}/fee-statement")
    assert res.status_code == 404


def test_bus_source_key_conflict(client, baseline):
    """A9: same bus source_key different amount → 409."""
    head = baseline["fee_heads"]["bus"]
    res = client.post(
        "/api/v1/charges",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "fee_head_id": head,
                "amount_paise": 31000,
                "due_date": "2026-06-15",
                "source_key": "bus:route-a:2026-06:s1",
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 409
    assert res.json()["message_key"] == "fees.error.source_key_conflict"


def test_opening_totals_match_import(client, baseline):
    """A10: opening balance charge appears in statement totals."""
    res = client.get(f"/api/v1/students/{fixtures.STUDENT_S1}/fee-statement")
    assert res.status_code == 200
    assert res.json()["balance"]["charged_paise"] == 155000


def test_no_float_in_amounts(client, baseline):
    """A11: all amounts remain integers."""
    charge_id = baseline["tuition_charge_id"]
    res = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 33333,
                "method": "cash",
                "allocations": [{"charge_id": charge_id, "amount_paise": 33333}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "int-only"},
    )
    body = res.json()
    assert isinstance(body["payment"]["amount_paise"], int)
    assert isinstance(body["balance"]["outstanding_paise"], int)


def test_foreign_school_404(client, baseline):
    """A12: School B student id → 404."""
    res = client.get(f"/api/v1/students/{fixtures.STUDENT_S1_SCHOOL_B}/fee-statement")
    assert res.status_code == 404


def test_stale_reversal_version(client, baseline):
    """A13: stale expected_version → 409."""
    charge_id = baseline["tuition_charge_id"]
    pay = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 1000,
                "method": "cash",
                "allocations": [{"charge_id": charge_id, "amount_paise": 1000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "stale-ver"},
    ).json()
    res = client.post(
        f"/api/v1/payments/{pay['payment']['id']}/reversals",
        data=json.dumps({"reason": "fix", "expected_version": 99}),
        content_type="application/json",
    )
    assert res.status_code == 409


def test_stale_2fa_on_reversal(client, baseline, settings):
    """A14: reversal without 2FA → 401."""
    from contracts.identity import AuthLevel
    from shared.http.context import DevPersona

    charge_id = baseline["tuition_charge_id"]
    pay = client.post(
        "/api/v1/payments",
        data=json.dumps(
            {
                "student_id": str(fixtures.STUDENT_S1),
                "amount_paise": 2000,
                "method": "cash",
                "allocations": [{"charge_id": charge_id, "amount_paise": 2000}],
            }
        ),
        content_type="application/json",
        headers={"Idempotency-Key": "stale-2fa-pay"},
    ).json()
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.PASSWORD,
    )
    res = client.post(
        f"/api/v1/payments/{pay['payment']['id']}/reversals",
        data=json.dumps(
            {"reason": "needs 2fa", "expected_version": pay["payment"]["version"]}
        ),
        content_type="application/json",
    )
    assert res.status_code == 401


def test_concurrent_allocations_safe(baseline, clock):
    """A5: a second allocation cannot overspend the remaining charge balance."""
    from contracts.errors import StateConflict
    from contracts.identity import AuthLevel, RequestContext
    from modules.fees.api import deps
    from modules.fees.models import Charge

    charge_id = baseline["tuition_charge_id"]
    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        request_id="alloc-1",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=datetime(2026, 6, 20, 9, 30, tzinfo=UTC),
    )
    deps.payment_service().create(
        ctx,
        student_id=fixtures.STUDENT_S1,
        amount_paise=60000,
        method="cash",
        reference=None,
        allocations=[{"charge_id": charge_id, "amount_paise": 60000}],
        idempotency_key="pre-concurrent",
    )
    assert Charge.objects.get(id=charge_id).balance_paise == 40000

    deps.payment_service().create(
        RequestContext(
            actor_id=fixtures.PRINCIPAL_P1,
            school_id=fixtures.SCHOOL_A,
            request_id="alloc-2",
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=datetime(2026, 6, 20, 9, 30, tzinfo=UTC),
        ),
        student_id=fixtures.STUDENT_S1,
        amount_paise=40000,
        method="upi",
        reference=None,
        allocations=[{"charge_id": charge_id, "amount_paise": 40000}],
        idempotency_key="conc-a",
    )
    assert Charge.objects.get(id=charge_id).balance_paise == 0

    with pytest.raises(StateConflict) as exc:
        deps.payment_service().create(
            RequestContext(
                actor_id=fixtures.PRINCIPAL_P1,
                school_id=fixtures.SCHOOL_A,
                request_id="alloc-3",
                auth_level=AuthLevel.TWO_FACTOR,
                auth_time=datetime(2026, 6, 20, 9, 30, tzinfo=UTC),
            ),
            student_id=fixtures.STUDENT_S1,
            amount_paise=40000,
            method="upi",
            reference=None,
            allocations=[{"charge_id": charge_id, "amount_paise": 40000}],
            idempotency_key="conc-b",
        )
    assert exc.value.message_key == "fees.error.allocation_exceeds_available"


def test_guardian_can_read_own_child(client, baseline, as_persona):
    """G1 can read S1 statement."""
    as_persona(fixtures.GUARDIAN_G1)
    res = client.get(f"/api/v1/students/{fixtures.STUDENT_S1}/fee-statement")
    assert res.status_code == 200
