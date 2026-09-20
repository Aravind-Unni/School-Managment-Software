"""In-process LibraryPort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.library import AvailabilityView, OpenLoanView
from contracts.values import school_date

from ..models import Copy, CopyState, Loan, Title
from .authority import AuthorityGate


@dataclass(frozen=True, slots=True)
class LibraryService:
    """Concrete LibraryPort for in-process consumers."""

    gate: AuthorityGate
    clock: object

    def get_open_loans(
        self,
        context: RequestContext,
        person_id: UUID,
    ) -> list[OpenLoanView]:
        """Return open loans for person_id in the actor school."""
        self.gate.require_borrower_visibility(context, person_id)
        civil = school_date(self.clock.now())
        rows = Loan.objects.filter(
            school_id=context.school_id,
            borrower_person_id=person_id,
            returned_at__isnull=True,
        ).order_by("due_date", "id")
        return [
            OpenLoanView(
                loan_id=row.id,
                copy_id=row.copy_id,
                due_date=row.due_date,
                overdue=row.due_date < civil,
            )
            for row in rows
        ]

    def get_availability(
        self,
        context: RequestContext,
        title_id: UUID,
    ) -> AvailabilityView:
        """Return available and total (non-withdrawn) copy counts."""
        self.gate.require_catalogue_read(context)
        title = Title.objects.filter(id=title_id, school_id=context.school_id).first()
        if title is None:
            raise ObjectInaccessible("error.object_inaccessible")
        copies = Copy.objects.filter(school_id=context.school_id, title_id=title_id)
        total = copies.exclude(state=CopyState.WITHDRAWN).count()
        available = copies.filter(state=CopyState.AVAILABLE).count()
        return AvailabilityView(available=available, total=total)
