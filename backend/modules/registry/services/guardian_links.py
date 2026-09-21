"""Guardian-to-student links with dated visibility.

Does not handle: granting access. Access decides whether a guardian may read; this
file only maintains the dated facts other modules and the port consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.identity import RequestContext
from contracts.scope import ScopeFacts

from ..models import Guardian, GuardianLink, Student
from .configuration import require_ordered_dates
from .effective import range_covers, ranges_overlap
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update


@dataclass(frozen=True, slots=True)
class GuardianLinkService:
    """Reads and writes guardian links for one school."""

    access: object
    clock: object

    def _authorise(self, context: RequestContext, action: str) -> None:
        """Ask Access whether this school-scoped action is permitted."""
        self.access.check(context, action, ScopeFacts(resource_school_id=context.school_id))

    def create_link(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        guardian_id: UUID,
        visibility: str,
        from_date: date,
        to_date: date | None,
    ) -> GuardianLink:
        """Create a dated guardian link after validating people and the range."""
        self._authorise(context, "guardians.manage")
        require_ordered_dates(from_date, to_date or from_date)
        fetch_in_school(Student, school_id=context.school_id, row_id=student_id)
        fetch_in_school(Guardian, school_id=context.school_id, row_id=guardian_id)
        self._refuse_overlapping_link(
            context.school_id,
            student_id=student_id,
            guardian_id=guardian_id,
            from_date=from_date,
            to_date=to_date,
        )
        now = self.clock.now()
        row = GuardianLink(
            school_id=context.school_id,
            student_id=student_id,
            guardian_id=guardian_id,
            visibility=visibility,
            from_date=from_date,
            to_date=to_date,
        )
        stamp_new(row, now=now)
        row.save()
        return row

    def update_link(
        self,
        context: RequestContext,
        *,
        link_id: UUID,
        visibility: str,
        from_date: date,
        to_date: date | None,
        expected_version: int,
    ) -> GuardianLink:
        """Replace a link's dated fields under optimistic locking."""
        self._authorise(context, "guardians.manage")
        require_ordered_dates(from_date, to_date or from_date)
        with transaction.atomic():
            row = fetch_in_school(
                GuardianLink, school_id=context.school_id, row_id=link_id, for_update=True
            )
            require_expected_version(row, expected_version)
            self._refuse_overlapping_link(
                context.school_id,
                student_id=row.student_id,
                guardian_id=row.guardian_id,
                from_date=from_date,
                to_date=to_date,
                excluding_id=row.id,
            )
            row.visibility = visibility
            row.from_date = from_date
            row.to_date = to_date
            stamp_update(row, now=self.clock.now())
            row.save()
        return row

    def list_links(
        self,
        context: RequestContext,
        *,
        student_id: UUID | None,
        after_id: UUID | None,
        page_size: int,
    ) -> tuple[tuple[GuardianLink, ...], bool]:
        """Return one cursor page of links, optionally filtered by student."""
        self._authorise(context, "guardians.manage")
        queryset = GuardianLink.objects.filter(school_id=context.school_id).order_by("id")
        if student_id is not None:
            fetch_in_school(Student, school_id=context.school_id, row_id=student_id)
            queryset = queryset.filter(student_id=student_id)
        if after_id is not None:
            queryset = queryset.filter(id__gt=after_id)
        rows = tuple(queryset[: page_size + 1])
        return rows[:page_size], len(rows) > page_size

    def _refuse_overlapping_link(
        self,
        school_id: UUID,
        *,
        student_id: UUID,
        guardian_id: UUID,
        from_date: date,
        to_date: date | None,
        excluding_id: UUID | None = None,
    ) -> None:
        """Raise StateConflict when the same pair already has an overlapping link."""
        from contracts.errors import StateConflict

        for existing in GuardianLink.objects.filter(
            school_id=school_id, student_id=student_id, guardian_id=guardian_id
        ):
            if excluding_id is not None and existing.id == excluding_id:
                continue
            if ranges_overlap(
                left_from=from_date,
                left_to=to_date,
                right_from=existing.from_date,
                right_to=existing.to_date,
            ):
                raise StateConflict("registry.error.enrolment_overlap")

    @staticmethod
    def active_guardian_link(
        *,
        school_id: UUID,
        guardian_id: UUID,
        student_id: UUID,
        effective_date: date,
    ) -> GuardianLink | None:
        """Return the guardian link in force on a date, if any.

        Does not authorise the caller. Used by RegistryPort read paths only.
        """
        for row in GuardianLink.objects.filter(
            school_id=school_id, guardian_id=guardian_id, student_id=student_id
        ):
            if range_covers(
                from_date=row.from_date, to_date=row.to_date, effective_date=effective_date
            ):
                return row
        return None
