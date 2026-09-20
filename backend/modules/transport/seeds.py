"""Baseline seed for M08: Bus A, S1 opted in from 2026-06-01, S2 out."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .api import deps
from .models import AdjustmentRequest, BillingRequest, Bus, Participation

FROZEN_INSTANT = datetime(2026, 6, 15, 9, 30, tzinfo=UTC)
FEE_PLAN_ID = UUID("b8e2c1a0-4f3d-5e6a-9b0c-1d2e3f4a5b6c")
PARTICIPATION_FROM = date(2026, 6, 1)


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline: S1 in, S2 out, labelled Bus A.

    Does not raise Fees charges — acceptance tests exercise billing runs.
    """
    school = school_id or fixtures.SCHOOL_A
    AdjustmentRequest.objects.filter(school_id=school).delete()
    BillingRequest.objects.filter(school_id=school).delete()
    Participation.objects.filter(school_id=school).delete()
    Bus.objects.filter(school_id=school).delete()

    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    bus = deps.bus_service().create(ctx, label="Bus A", active=True)
    participation = deps.participation_service().create(
        ctx,
        student_id=fixtures.STUDENT_S1,
        from_date=PARTICIPATION_FROM,
        fee_plan_id=FEE_PLAN_ID,
        bus_id=UUID(bus["id"]),
    )
    return {
        "school_id": str(school),
        "bus_id": bus["id"],
        "participation_id": participation["id"],
        "fee_plan_id": str(FEE_PLAN_ID),
        "student_s1": str(fixtures.STUDENT_S1),
        "student_s2": str(fixtures.STUDENT_S2),
        "billing_period": "2026-06",
        "as_of": "2026-06-15",
    }


def empty(*, school_id: UUID | None = None) -> dict[str, object]:
    """No-op empty scenario."""
    return {"school_id": str(school_id or fixtures.SCHOOL_A)}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
