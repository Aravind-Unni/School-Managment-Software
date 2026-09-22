"""The school calendar: exceptions, staff unavailability, and the day answer.

What makes a date a teaching day is decided in ``reads.py`` and nowhere else, so
the calendar endpoint, every schedule view and the service port cannot disagree.
This module owns the WRITES and the range guard.

Nothing is deleted. An exception or an unavailability window is withdrawn,
because a published schedule may already cite it and a row that vanishes takes
its history with it.

Does not handle: what a holiday means for attendance. A holiday has no eligible
teaching period; that consequence lives in the reader and in the port.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from django.db import transaction

from contracts.errors import FieldError, ValidationFailed
from contracts.identity import RequestContext

from ..models import CalendarException, TeacherUnavailable
from .journal import record_audit
from .reads import MAX_RANGE_DAYS, CalendarDay, ScheduleReader
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update


@dataclass(frozen=True, slots=True)
class CalendarService:
    """Reads the calendar and maintains the rows behind it."""

    scope: object
    platform: object
    clock: object
    reader: ScheduleReader

    # --- reading ------------------------------------------------------------

    def days(
        self, context: RequestContext, *, from_date: date, to_date: date
    ) -> tuple[CalendarDay, ...]:
        """Return one answer per date in an inclusive, bounded range.

        Reading the calendar needs only ``timetable.read_calendar``, which every role
        holds: term dates and holidays are what families plan around.
        """
        self.scope.require_school_action(context, "timetable.read_calendar")
        require_bounded_range(from_date, to_date)
        return self.reader.calendar_days(
            school_id=context.school_id, from_date=from_date, to_date=to_date
        )

    def list_exceptions(
        self,
        context: RequestContext,
        *,
        from_date: date | None,
        to_date: date | None,
        kind: str | None,
    ):
        """Return the school's calendar exceptions, oldest first."""
        self.scope.require_school_action(context, "timetable.read")
        queryset = CalendarException.objects.filter(school_id=context.school_id)
        if from_date is not None:
            queryset = queryset.filter(date__gte=from_date)
        if to_date is not None:
            queryset = queryset.filter(date__lte=to_date)
        if kind is not None:
            queryset = queryset.filter(kind=kind)
        # Ordered by exactly the keys the cursor carries -- see the same note in
        # services/drafts.py. Two exceptions can share a date, so the tiebreaker
        # must be the one the cursor compares.
        return queryset.order_by("date", "id")

    def list_unavailability(
        self,
        context: RequestContext,
        *,
        staff_id: UUID | None,
        from_date: date | None,
        to_date: date | None,
    ):
        """Return recorded unavailability windows, earliest first.

        Behind ``timetable.edit`` rather than ``timetable.read``: why a colleague
        is away is staff rostering information, not part of a class schedule.
        """
        self.scope.require_school_action(context, "timetable.edit")
        queryset = TeacherUnavailable.objects.filter(school_id=context.school_id)
        if staff_id is not None:
            queryset = queryset.filter(staff_id=staff_id)
        if from_date is not None:
            queryset = queryset.filter(ends_at__date__gte=from_date)
        if to_date is not None:
            queryset = queryset.filter(starts_at__date__lte=to_date)
        return queryset.order_by("starts_at", "id")

    # --- exceptions ---------------------------------------------------------

    def create_exception(
        self,
        context: RequestContext,
        *,
        on: date,
        kind: str,
        reason_key: str | None,
    ) -> CalendarException:
        """Record one exception, or reinstate the withdrawn one for that date.

        A live duplicate is refused. Reinstating a withdrawn row rather than
        inserting a second one is what makes "withdraw, never delete" usable: the
        same date and kind must be recordable again afterwards.
        """
        self.scope.require_school_action(context, "timetable.edit")
        now = self.clock.now()
        with transaction.atomic():
            existing = (
                CalendarException.objects.select_for_update()
                .filter(school_id=context.school_id, date=on, kind=kind)
                .first()
            )
            if existing is not None and not existing.withdrawn:
                raise ValidationFailed(
                    "error.validation_failed",
                    field_errors=(FieldError("date", "error.validation_failed"),),
                )
            if existing is not None:
                existing.withdrawn = False
                existing.reason_key = reason_key
                stamp_update(existing, now=now)
                existing.save()
                row = existing
            else:
                row = CalendarException(
                    school_id=context.school_id, date=on, kind=kind, reason_key=reason_key
                )
                stamp_new(row, now=now)
                row.save()
            record_audit(
                self.platform,
                context,
                action="timetable.record_calendar_exception",
                resource_id=row.id,
                before={},
                after={"date": on.isoformat(), "kind": kind, "withdrawn": False},
                now=now,
            )
        return row

    def update_exception(
        self,
        context: RequestContext,
        *,
        exception_id: UUID,
        kind: str,
        reason_key: str | None,
        withdrawn: bool,
        expected_version: int,
    ) -> CalendarException:
        """Amend or withdraw an exception under optimistic locking."""
        self.scope.require_school_action(context, "timetable.edit")
        now = self.clock.now()
        with transaction.atomic():
            row = fetch_in_school(
                CalendarException,
                school_id=context.school_id,
                row_id=exception_id,
                for_update=True,
            )
            require_expected_version(row, expected_version)
            before = {"kind": row.kind, "withdrawn": row.withdrawn}
            row.kind = kind
            row.reason_key = reason_key
            row.withdrawn = withdrawn
            stamp_update(row, now=now)
            row.save()
            record_audit(
                self.platform,
                context,
                action="timetable.update_calendar_exception",
                resource_id=row.id,
                before=before,
                after={"kind": kind, "withdrawn": withdrawn},
                now=now,
            )
        return row

    # --- unavailability -----------------------------------------------------

    def create_unavailability(
        self,
        context: RequestContext,
        *,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        reason_key: str | None,
    ) -> TeacherUnavailable:
        """Record that a staff member cannot teach over a half-open interval."""
        self.scope.require_school_action(context, "timetable.edit")
        require_ordered_interval(starts_at, ends_at)
        now = self.clock.now()
        with transaction.atomic():
            row = TeacherUnavailable(
                school_id=context.school_id,
                staff_id=staff_id,
                starts_at=starts_at,
                ends_at=ends_at,
                reason_key=reason_key,
            )
            stamp_new(row, now=now)
            row.save()
            record_audit(
                self.platform,
                context,
                action="timetable.record_unavailability",
                resource_id=row.id,
                before={},
                after={"staff_id": str(staff_id), "starts_at": starts_at.isoformat()},
                now=now,
            )
        return row

    def update_unavailability(
        self,
        context: RequestContext,
        *,
        unavailability_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        reason_key: str | None,
        withdrawn: bool,
        expected_version: int,
    ) -> TeacherUnavailable:
        """Amend or withdraw an unavailability window under optimistic locking."""
        self.scope.require_school_action(context, "timetable.edit")
        require_ordered_interval(starts_at, ends_at)
        now = self.clock.now()
        with transaction.atomic():
            row = fetch_in_school(
                TeacherUnavailable,
                school_id=context.school_id,
                row_id=unavailability_id,
                for_update=True,
            )
            require_expected_version(row, expected_version)
            before = {"withdrawn": row.withdrawn, "starts_at": row.starts_at.isoformat()}
            row.starts_at = starts_at
            row.ends_at = ends_at
            row.reason_key = reason_key
            row.withdrawn = withdrawn
            stamp_update(row, now=now)
            row.save()
            record_audit(
                self.platform,
                context,
                action="timetable.update_unavailability",
                resource_id=row.id,
                before=before,
                after={"withdrawn": withdrawn, "starts_at": starts_at.isoformat()},
                now=now,
            )
        return row


def require_bounded_range(from_date: date, to_date: date) -> None:
    """Refuse a backwards or unbounded calendar range.

    Bounded so one request cannot expand an arbitrarily long date walk. The limit
    is data (MAX_RANGE_DAYS), not a number hidden in a branch.
    """
    if to_date < from_date:
        raise ValidationFailed(
            "timetable.error.to_date_before_from_date",
            field_errors=(FieldError("to_date", "timetable.error.to_date_before_from_date"),),
        )
    if (to_date - from_date).days + 1 > MAX_RANGE_DAYS:
        raise ValidationFailed(
            "timetable.error.range_too_wide",
            field_errors=(FieldError("to_date", "timetable.error.range_too_wide"),),
        )


def require_ordered_interval(starts_at: datetime, ends_at: datetime) -> None:
    """Refuse an interval that does not end strictly after it starts.

    Half-open [start, end): a zero-length interval covers nothing, so accepting it
    would store a row that can never match a period and can never be explained.
    """
    if ends_at <= starts_at:
        raise ValidationFailed(
            "timetable.error.unavailability_end_not_after_start",
            field_errors=(
                FieldError("ends_at", "timetable.error.unavailability_end_not_after_start"),
            ),
        )
