"""Dated substitutions and single-period cancellations.

Both are DAY OVERRIDES. Neither mutates the recurring schedule and neither
creates a revision, so last week's grid is still last week's grid.

A substitution is an explicit dated assignment with an expiry. It supports
attendance access for that exact date and period and then lapses; it never
becomes a standing class permission for the replacement teacher.

Does not handle: deciding whether the substitute may mark attendance. That is
Access policy combined with the trusted fact this module publishes through
``services/port.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    FieldError,
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.identity import RequestContext

from ..models import SessionCancellation, Slot, Substitution
from ..sessions import end_of_school_day, session_id_for, utc_window
from .journal import append_event, record_audit
from .reads import ScheduleReader, SessionView
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update


@dataclass(frozen=True, slots=True)
class SubstitutionService:
    """Assigns, withdraws and cancels. Holds ports, never global state."""

    scope: object
    platform: object
    clock: object
    reader: ScheduleReader

    def listing(
        self,
        context: RequestContext,
        *,
        on: date | None,
        section_id: UUID | None,
        teacher_id: UUID | None,
    ):
        """Return substitutions matching the filters, earliest first."""
        self.scope.require_school_action(context, "timetable.read")
        queryset = Substitution.objects.filter(school_id=context.school_id)
        if on is not None:
            queryset = queryset.filter(date=on)
        if section_id is not None:
            queryset = queryset.filter(section_id=section_id)
        if teacher_id is not None:
            queryset = queryset.filter(substitute_teacher_id=teacher_id)
        return queryset.order_by("date", "id")

    def assign(
        self,
        context: RequestContext,
        *,
        on: date,
        slot_id: UUID,
        teacher_id: UUID,
        reason: str,
        valid_until: datetime | None,
    ) -> Substitution:
        """Assign a substitute to one dated period.

        The checks run in the order a person would ask them: is this date covered
        by the schedule at all, is it a teaching day, is this period taught on it,
        has it been cancelled, and only then who is covering and for how long.
        """
        self.scope.require_school_action(context, "timetable.substitute")
        now = self.clock.now()

        with transaction.atomic():
            slot = fetch_in_school(Slot, school_id=context.school_id, row_id=slot_id)
            effective = self.reader.effective_version(school_id=context.school_id, on=on)
            if effective is None or effective.id != slot.timetable_id:
                raise ValidationFailed(
                    "timetable.error.date_outside_effective_range",
                    field_errors=(
                        FieldError("date", "timetable.error.date_outside_effective_range"),
                    ),
                )

            day = self.reader.calendar_day(school_id=context.school_id, on=on)
            if "holiday" in day.kinds:
                raise StateConflict("timetable.error.date_is_holiday")
            if slot.period.day_of_week != on.isoweekday():
                raise ValidationFailed(
                    "timetable.error.slot_not_taught_on_date",
                    field_errors=(
                        FieldError("date", "timetable.error.slot_not_taught_on_date"),
                    ),
                )

            session_id = session_id_for(
                school_id=context.school_id,
                section_id=slot.section_id,
                on=on,
                slot_code=slot.period.slot_code,
            )
            cancellation = SessionCancellation.objects.filter(
                school_id=context.school_id, timetable_session_id=session_id, cancelled=True
            ).first()
            if cancellation is not None:
                raise StateConflict("timetable.error.session_cancelled")

            if teacher_id == slot.teacher_id:
                raise ValidationFailed(
                    "timetable.error.substitute_same_as_assigned",
                    field_errors=(
                        FieldError("teacher_id", "timetable.error.substitute_same_as_assigned"),
                    ),
                )

            live = (
                Substitution.objects.select_for_update()
                .filter(school_id=context.school_id, date=on, slot=slot, withdrawn=False)
                .first()
            )
            if live is not None:
                raise StateConflict("timetable.error.substitution_exists")

            expires = resolve_valid_until(
                requested=valid_until,
                on=on,
                session_ends_at=utc_window(
                    on, slot.period.starts_at_local, slot.period.ends_at_local
                )[1],
            )

            row = Substitution(
                school_id=context.school_id,
                date=on,
                slot=slot,
                timetable_session_id=session_id,
                section_id=slot.section_id,
                subject_id=slot.subject_id,
                original_teacher_id=slot.teacher_id,
                substitute_teacher_id=teacher_id,
                reason=reason,
                valid_until=expires,
            )
            stamp_new(row, now=now)
            row.save()

            record_audit(
                self.platform,
                context,
                action="timetable.assign_substitution",
                resource_id=row.id,
                before={},
                after={
                    "date": on.isoformat(),
                    "timetable_session_id": str(session_id),
                    "substitute_teacher_id": str(teacher_id),
                    "valid_until": expires.isoformat(),
                },
                now=now,
            )
            append_event(
                self.platform,
                context,
                event_type="timetable.substitution_assigned",
                aggregate_id=row.id,
                aggregate_version=row.version,
                payload={
                    "section_id": str(slot.section_id),
                    "slot_id": str(slot.id),
                    "timetable_session_id": str(session_id),
                    "teacher_id": str(teacher_id),
                    "date": on.isoformat(),
                    "valid_until": expires.isoformat(),
                },
                now=now,
            )
        return row

    def withdraw(
        self,
        context: RequestContext,
        *,
        substitution_id: UUID,
        withdrawn: bool,
        expected_version: int,
    ) -> Substitution:
        """Withdraw a substitution under optimistic locking.

        Withdrawn rather than deleted: a register may already cite it, and the
        period must be free to be covered again afterwards.
        """
        self.scope.require_school_action(context, "timetable.substitute")
        now = self.clock.now()
        with transaction.atomic():
            row = fetch_in_school(
                Substitution,
                school_id=context.school_id,
                row_id=substitution_id,
                for_update=True,
            )
            require_expected_version(row, expected_version)
            before = {"withdrawn": row.withdrawn}
            row.withdrawn = withdrawn
            stamp_update(row, now=now)
            row.save()
            record_audit(
                self.platform,
                context,
                action="timetable.withdraw_substitution",
                resource_id=row.id,
                before=before,
                after={"withdrawn": withdrawn},
                now=now,
            )
        return row

    def set_cancellation(
        self,
        context: RequestContext,
        *,
        session_id: UUID,
        cancelled: bool,
        reason_key: str | None,
        expected_version: int | None,
    ) -> SessionView:
        """Cancel or restore one dated period, and return the session as it now is.

        ``expected_version`` is None on the first cancellation of a session,
        because there is no record yet. Sending None once a record exists is a
        version conflict, not a silent overwrite.
        """
        self.scope.require_school_action(context, "timetable.edit")
        now = self.clock.now()
        with transaction.atomic():
            session, _day = self.reader.session_ignoring_calendar(
                school_id=context.school_id, session_id=session_id
            )
            if session is None:
                raise ObjectInaccessible("error.object_inaccessible")

            row = (
                SessionCancellation.objects.select_for_update()
                .filter(school_id=context.school_id, timetable_session_id=session_id)
                .first()
            )
            if row is None:
                if expected_version is not None:
                    raise VersionConflict(
                        expected_version=expected_version, actual_version=None
                    )
                row = SessionCancellation(
                    school_id=context.school_id,
                    date=session.dated.date,
                    slot_id=session.dated.slot_id,
                    timetable_session_id=session_id,
                    section_id=session.dated.section_id,
                    cancelled=cancelled,
                    reason_key=reason_key,
                )
                stamp_new(row, now=now)
                row.save()
                before: dict[str, object] = {}
            else:
                if expected_version is None:
                    raise VersionConflict(expected_version=None, actual_version=row.version)
                require_expected_version(row, expected_version)
                before = {"cancelled": row.cancelled}
                row.cancelled = cancelled
                row.reason_key = reason_key
                stamp_update(row, now=now)
                row.save()

            record_audit(
                self.platform,
                context,
                action="timetable.set_session_cancellation",
                resource_id=row.id,
                before=before,
                after={"cancelled": cancelled, "timetable_session_id": str(session_id)},
                now=now,
            )

        updated, _day = self.reader.session_ignoring_calendar(
            school_id=context.school_id, session_id=session_id
        )
        if updated is None:  # pragma: no cover - the row was just read in-transaction
            raise ObjectInaccessible("error.object_inaccessible")
        return updated


def resolve_valid_until(
    *, requested: datetime | None, on: date, session_ends_at: datetime
) -> datetime:
    """Return when a substitute's authority lapses, or refuse the request.

    Default: the end of the session's own school day, Asia/Kolkata, as an
    exclusive instant -- the reviewed decision (review item 7). A teacher commonly
    marks the register after the lesson, sometimes at the end of the day, so the
    period's own end would lock out a legitimate late entry.

    A caller may ask for earlier but never later, and never before the period it
    covers has finished; both are 422, because a substitution that outlives its
    day is a standing permission by another name.
    """
    ceiling = end_of_school_day(on)
    if requested is None:
        return ceiling
    if requested > ceiling:
        raise ValidationFailed(
            "timetable.error.valid_until_after_session_day",
            field_errors=(
                FieldError("valid_until", "timetable.error.valid_until_after_session_day"),
            ),
        )
    if requested < session_ends_at:
        raise ValidationFailed(
            "timetable.error.valid_until_before_session_end",
            field_errors=(
                FieldError("valid_until", "timetable.error.valid_until_before_session_end"),
            ),
        )
    return requested
