"""Baseline seed for M07: tuition charge, opening balance, bus charge for S1."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .api import deps
from .models import FeeHead

FROZEN_INSTANT = datetime(2026, 6, 20, 9, 30, tzinfo=UTC)

HEAD_TUITION = UUID("f1111111-1111-1111-1111-111111111111")
HEAD_BUS = UUID("f2222222-2222-2222-2222-222222222222")
HEAD_OPENING = UUID("f3333333-3333-3333-3333-333333333333")


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline charges for School A student S1.

    Does not post payments — acceptance tests exercise partial payment and credit.
    """
    school = school_id or fixtures.SCHOOL_A
    from .models import (
        Allocation,
        Charge,
        Credit,
        FeePlan,
        Payment,
        PaymentIdempotency,
        ReceiptSequence,
        RefundRecord,
        Reversal,
    )

    Reversal.objects.filter(school_id=school).delete()
    RefundRecord.objects.filter(school_id=school).delete()
    PaymentIdempotency.objects.filter(school_id=school).delete()
    Allocation.objects.filter(school_id=school).delete()
    Payment.objects.filter(school_id=school).delete()
    Credit.objects.filter(school_id=school).delete()
    Charge.objects.filter(school_id=school).delete()
    FeePlan.objects.filter(school_id=school).delete()
    FeeHead.objects.filter(school_id=school).delete()
    ReceiptSequence.objects.filter(school_id=school).delete()

    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    plan = deps.plan_service().create_plan(
        ctx,
        fee_heads=[
            {"code": "tuition", "label_key": "fees.head.tuition"},
            {"code": "bus", "label_key": "fees.head.bus"},
            {"code": "opening_balance", "label_key": "fees.head.opening_balance"},
        ],
        applicability={"standards": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]},
        schedule=[
            {
                "fee_head_code": "tuition",
                "amount_paise": 100000,
                "due_date": "2026-06-01",
            },
            {
                "fee_head_code": "bus",
                "amount_paise": 30000,
                "due_date": "2026-06-15",
            },
            {
                "fee_head_code": "opening_balance",
                "amount_paise": 25000,
                "due_date": "2026-04-01",
            },
        ],
        version=1,
    )
    # Re-key heads to stable IDs used in fixtures when possible
    for code, fixed_id in (
        ("tuition", HEAD_TUITION),
        ("bus", HEAD_BUS),
        ("opening_balance", HEAD_OPENING),
    ):
        head = FeeHead.objects.get(school_id=school, code=code)
        if head.id != fixed_id:
            # Keep generated ids; map by code in return value
            pass

    heads = {h["code"]: h["id"] for h in plan["fee_heads"]}
    tuition, _ = deps.charge_service().raise_charge(
        ctx,
        source_key="plan:v1:tuition:s1",
        student_id=fixtures.STUDENT_S1,
        fee_head_id=UUID(heads["tuition"]),
        amount_paise=100000,
        due_date=date(2026, 6, 1),
        description_key="fees.charge.tuition",
    )
    opening, _ = deps.charge_service().raise_charge(
        ctx,
        source_key=f"opening:{fixtures.STUDENT_S1}",
        student_id=fixtures.STUDENT_S1,
        fee_head_id=UUID(heads["opening_balance"]),
        amount_paise=25000,
        due_date=date(2026, 4, 1),
        description_key="fees.charge.opening_balance",
    )
    bus, _ = deps.charge_service().raise_charge(
        ctx,
        source_key="bus:route-a:2026-06:s1",
        student_id=fixtures.STUDENT_S1,
        fee_head_id=UUID(heads["bus"]),
        amount_paise=30000,
        due_date=date(2026, 6, 15),
        description_key="fees.charge.bus",
    )
    return {
        "school_id": str(school),
        "plan_id": plan["id"],
        "fee_heads": heads,
        "tuition_charge_id": str(tuition.id),
        "opening_charge_id": str(opening.id),
        "bus_charge_id": str(bus.id),
        "tuition_amount_paise": 100000,
        "opening_amount_paise": 25000,
    }


def empty(*, school_id: UUID | None = None) -> dict[str, object]:
    """No-op empty scenario."""
    return {"school_id": str(school_id or fixtures.SCHOOL_A)}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
