"""Overdue queue with overdue_detected events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from contracts.errors import ValidationFailed
from contracts.events import EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor

from ..models import Copy, Loan
from .authority import AuthorityGate


@dataclass(frozen=True, slots=True)
class OverdueService:
    """List overdue open loans as of a school civil date."""

    gate: AuthorityGate
    platform: object
    clock: object

    def list_overdues(
        self,
        context: RequestContext,
        *,
        as_of: date,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """Return overdue open loans; emit overdue_detected when first seen."""
        self.gate.require_action(context, "library.read_overdues")
        size = clamp_page_size(page_size)
        queryset = Loan.objects.filter(
            school_id=context.school_id,
            returned_at__isnull=True,
            due_date__lt=as_of,
        ).order_by("due_date", "id")
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_due = date.fromisoformat(str(position["due_date"]))
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            queryset = queryset.filter(
                Q(due_date__gt=after_due) | Q(due_date=after_due, id__gt=after_id)
            )

        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor(
                {"due_date": last.due_date.isoformat(), "id": str(last.id)}
            )
            rows = rows[:size]

        now = self.clock.now()
        items = []
        with transaction.atomic():
            for loan in rows:
                copy = Copy.objects.filter(id=loan.copy_id).first()
                accession = copy.accession_no if copy else ""
                display = self._borrower_name(context, loan.borrower_person_id)
                items.append(
                    {
                        "loan_id": str(loan.id),
                        "copy_id": str(loan.copy_id),
                        "accession_no": accession,
                        "borrower_person_id": str(loan.borrower_person_id),
                        "borrower_display_name": display,
                        "due_date": loan.due_date.isoformat(),
                        "as_of": as_of.isoformat(),
                    }
                )
                if loan.overdue_event_emitted_as_of != as_of:
                    locked = Loan.objects.select_for_update().filter(id=loan.id).first()
                    if locked is not None and locked.overdue_event_emitted_as_of != as_of:
                        locked.overdue_event_emitted_as_of = as_of
                        locked.save(update_fields=["overdue_event_emitted_as_of"])
                        self.platform.append_event(
                            EventEnvelope(
                                event_id=uuid.uuid4(),
                                school_id=context.school_id,
                                event_type="library.overdue_detected",
                                occurred_at=now,
                                aggregate_id=loan.id,
                                aggregate_version=loan.version,
                                payload={
                                    "loan_id": str(loan.id),
                                    "as_of": as_of.isoformat(),
                                },
                                correlation_id=context.request_id,
                            )
                        )

        page = Page(items=tuple(items), next_cursor=next_cursor)
        return page.to_wire()

    def _borrower_name(self, context: RequestContext, person_id: UUID) -> str:
        """Resolve display name via Registry; fall back to id string."""
        try:
            student = self.gate.registry.get_student(context, person_id)
            return student.display_name
        except Exception:
            return str(person_id)
