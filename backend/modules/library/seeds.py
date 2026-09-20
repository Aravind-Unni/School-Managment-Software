"""Baseline seed for M09: one copy, policy limits, S1/S2 borrowers available."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .api import deps
from .models import Copy, CopyAdjustment, LibraryPolicy, Loan, LoanIdempotency, Renewal, Title

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline: one available copy; no open loans.

    Due-date scenarios are exercised by acceptance tests against this copy.
    """
    school = school_id or fixtures.SCHOOL_A
    LoanIdempotency.objects.filter(school_id=school).delete()
    Renewal.objects.filter(school_id=school).delete()
    CopyAdjustment.objects.filter(school_id=school).delete()
    Loan.objects.filter(school_id=school).delete()
    Copy.objects.filter(school_id=school).delete()
    Title.objects.filter(school_id=school).delete()
    LibraryPolicy.objects.filter(school_id=school).delete()

    LibraryPolicy.objects.create(
        school_id=school,
        max_active_loans_per_borrower=3,
        max_renewals_per_loan=2,
    )

    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    title = deps.catalogue_service().create_title(
        ctx,
        name="കേരള ചരിത്രം",
        author="Synthetic Author",
        language="ml",
        isbn="978-0-000000-01-1",
    )
    copy = deps.catalogue_service().create_copy(
        ctx,
        title_id=UUID(title["id"]),
        accession_no="ACC-1001",
    )
    return {
        "school_id": str(school),
        "title_id": title["id"],
        "copy_id": copy["id"],
        "accession_no": "ACC-1001",
        "student_s1": str(fixtures.STUDENT_S1),
        "student_s2": str(fixtures.STUDENT_S2),
        "future_due_date": "2026-10-01",
        "overdue_due_date": "2026-09-01",
        "as_of_before_overdue": "2026-09-01",
        "as_of_overdue": "2026-09-02",
    }


def empty(*, school_id: UUID | None = None) -> dict[str, object]:
    """No-op empty scenario."""
    return {"school_id": str(school_id or fixtures.SCHOOL_A)}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
