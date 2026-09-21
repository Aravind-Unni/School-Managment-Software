"""Teaching assignments and subject offerings.

Does not handle: timetable publication. M03 consumes assignments through
RegistryPort and must not reach these tables directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.errors import ActionDenied, StateConflict, ValidationFailed
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts
from contracts.values import school_date

from ..models import (
    AcademicYear,
    Section,
    StaffProfile,
    Subject,
    SubjectOffering,
    TeachingAssignment,
)
from .configuration import require_ordered_dates
from .effective import range_covers
from .subject_defaults import enrol_section_pupils_in_offering
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update


@dataclass(frozen=True, slots=True)
class TeachingAssignmentService:
    """Reads and writes staff assignments and subject offerings."""

    access: object
    clock: object

    def _authorise(self, context: RequestContext, action: str) -> None:
        """Ask Access whether this school-scoped action is permitted."""
        self.access.check(context, action, ScopeFacts(resource_school_id=context.school_id))

    def create_assignment(
        self,
        context: RequestContext,
        *,
        staff_id: UUID,
        section_id: UUID,
        subject_id: UUID,
        from_date: date,
        to_date: date | None,
    ) -> TeachingAssignment:
        """Create a dated teaching assignment."""
        self._authorise(context, "staff.assign")
        require_ordered_dates(from_date, to_date or from_date)
        fetch_in_school(StaffProfile, school_id=context.school_id, row_id=staff_id)
        section = fetch_in_school(Section, school_id=context.school_id, row_id=section_id)
        fetch_in_school(Subject, school_id=context.school_id, row_id=subject_id)
        if section.archived:
            raise ValidationFailed("registry.error.referenced_record")
        now = self.clock.now()
        row = TeachingAssignment(
            school_id=context.school_id,
            staff_id=staff_id,
            section_id=section_id,
            subject_id=subject_id,
            from_date=from_date,
            to_date=to_date,
        )
        stamp_new(row, now=now)
        row.save()
        return row

    def update_assignment(
        self,
        context: RequestContext,
        *,
        assignment_id: UUID,
        staff_id: UUID,
        section_id: UUID,
        subject_id: UUID,
        from_date: date,
        to_date: date | None,
        expected_version: int,
    ) -> TeachingAssignment:
        """Replace an assignment under optimistic locking."""
        self._authorise(context, "staff.assign")
        require_ordered_dates(from_date, to_date or from_date)
        fetch_in_school(StaffProfile, school_id=context.school_id, row_id=staff_id)
        section = fetch_in_school(Section, school_id=context.school_id, row_id=section_id)
        fetch_in_school(Subject, school_id=context.school_id, row_id=subject_id)
        if section.archived:
            raise ValidationFailed("registry.error.referenced_record")
        with transaction.atomic():
            row = fetch_in_school(
                TeachingAssignment,
                school_id=context.school_id,
                row_id=assignment_id,
                for_update=True,
            )
            require_expected_version(row, expected_version)
            row.staff_id = staff_id
            row.section_id = section_id
            row.subject_id = subject_id
            row.from_date = from_date
            row.to_date = to_date
            stamp_update(row, now=self.clock.now())
            row.save()
        return row

    def get_assignment(
        self, context: RequestContext, assignment_id: UUID
    ) -> TeachingAssignment:
        """Return one assignment row."""
        self._authorise(context, "staff.assign")
        return fetch_in_school(
            TeachingAssignment, school_id=context.school_id, row_id=assignment_id
        )

    def list_assignments(
        self,
        context: RequestContext,
        *,
        after_id: UUID | None,
        page_size: int,
    ) -> tuple[tuple[TeachingAssignment, ...], bool]:
        """Return one cursor page of assignments.

        Whoever assigns staff sees every assignment; anyone else sees only
        their own (a teacher needs to know what they teach).
        """
        queryset = TeachingAssignment.objects.filter(school_id=context.school_id).order_by("id")
        try:
            self._authorise(context, "staff.assign")
        except ActionDenied:
            queryset = queryset.filter(staff_id=context.actor_id)
        if after_id is not None:
            queryset = queryset.filter(id__gt=after_id)
        rows = tuple(queryset[: page_size + 1])
        return rows[:page_size], len(rows) > page_size

    def create_subject_offering(
        self,
        context: RequestContext,
        *,
        year_id: UUID,
        section_id: UUID,
        subject_id: UUID,
        optional_group: str | None,
    ) -> SubjectOffering:
        """Publish a subject for a section within a year."""
        self._authorise(context, "registry.manage")
        year = fetch_in_school(AcademicYear, school_id=context.school_id, row_id=year_id)
        section = fetch_in_school(Section, school_id=context.school_id, row_id=section_id)
        fetch_in_school(Subject, school_id=context.school_id, row_id=subject_id)
        if section.year_id != year.id:
            raise ValidationFailed("registry.error.referenced_record")
        if year.state in ("closed", "archived"):
            raise StateConflict("registry.error.year_closed")
        now = self.clock.now()
        row = SubjectOffering(
            school_id=context.school_id,
            year_id=year_id,
            section_id=section_id,
            subject_id=subject_id,
            optional_group=optional_group,
        )
        stamp_new(row, now=now)
        try:
            row.save()
        except Exception as exc:
            from django.db import IntegrityError

            if isinstance(exc, IntegrityError):
                raise StateConflict("registry.error.referenced_record") from exc
            raise
        # Pupils already in the section take a new compulsory subject from today.
        enrol_section_pupils_in_offering(row, on=school_date(now), now=now)
        return row

    def list_subject_offerings(
        self,
        context: RequestContext,
        *,
        after_id: UUID | None,
        page_size: int,
    ) -> tuple[tuple[SubjectOffering, ...], bool]:
        """Return one cursor page of subject offerings."""
        self._authorise(context, "registry.manage")
        queryset = SubjectOffering.objects.filter(school_id=context.school_id).order_by("id")
        if after_id is not None:
            queryset = queryset.filter(id__gt=after_id)
        rows = tuple(queryset[: page_size + 1])
        return rows[:page_size], len(rows) > page_size

    @staticmethod
    def assignments_for_staff(
        *,
        school_id: UUID,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[TeachingAssignment, ...]:
        """Return assignments in force for a staff member on a date.

        Does not authorise the caller. Used by RegistryPort only.
        """
        return tuple(
            row
            for row in TeachingAssignment.objects.filter(school_id=school_id, staff_id=staff_id)
            if range_covers(
                from_date=row.from_date, to_date=row.to_date, effective_date=effective_date
            )
        )
