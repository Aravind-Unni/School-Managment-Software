"""The one place a dated schedule is resolved.

Every school view -- a class's day, a teacher's day, a pupil's day, the calendar
and the service port -- comes through here, because the packet requires that they
all use the same effective source. Two readers would eventually disagree about
whether a holiday has lessons.

Nothing here raises for absence. A date no published revision covers resolves to
a day with no timetable, and the CALLER decides whether that is a 409 (a browser
asking for a schedule) or an empty answer (a consumer asking what is on).

Does not handle: authorisation. Services check Access before reading.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from django.db.models import Q

from ..models import (
    CalendarException,
    SessionCancellation,
    Substitution,
    TimetableVersion,
)
from ..sessions import DatedSlot, expand_day, session_id_for

#: How far a single request may walk the calendar, and how far back the reverse
#: session lookup searches. Bounded so one request cannot expand an unbounded
#: date range.
MAX_RANGE_DAYS = 400


@dataclass(frozen=True, slots=True)
class SessionView:
    """One dated period with its day overrides folded in.

    ``substitute_teacher_id`` is reported whether or not the substitution has
    expired: the schedule is a record of who taught, and last week's schedule must
    still say so. Expiry is an AUTHORISATION question and is answered by
    ``teaching_authority``, not here.
    """

    dated: DatedSlot
    timetable_id: UUID
    timetable_version: int
    cancelled: bool = False
    cancellation_reason_key: str | None = None
    substitute_teacher_id: UUID | None = None
    substitution_valid_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class CalendarDay:
    """Whether one date is a teaching day, and why not when it is not."""

    date: date
    is_school_day: bool
    reason_key: str | None
    kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DayView:
    """One section's dated schedule, with the calendar answer that produced it."""

    date: date
    section_id: UUID
    day: CalendarDay
    timetable: TimetableVersion | None
    sessions: tuple[SessionView, ...]


@dataclass(frozen=True, slots=True)
class ScheduleReader:
    """Resolves effective schedules. Holds only the injected clock."""

    clock: object

    # --- effective revision -------------------------------------------------

    def effective_version(self, *, school_id: UUID, on: date) -> TimetableVersion | None:
        """Return the revision in force on a date, or None.

        Both ``published`` and ``superseded`` are eligible: a superseded revision
        is still authoritative for the dates inside its own closed range, which is
        what makes historical attendance reconcilable.

        Ties are broken by the later ``effective_from``, then by the later
        publication, so a correction published afterwards wins.
        """
        return (
            TimetableVersion.objects.filter(
                school_id=school_id,
                state__in=("published", "superseded"),
                effective_from__lte=on,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on))
            .order_by("-effective_from", "-published_at", "-id")
            .first()
        )

    # --- the calendar -------------------------------------------------------

    def calendar_days(
        self, *, school_id: UUID, from_date: date, to_date: date
    ) -> tuple[CalendarDay, ...]:
        """Return one answer per date in an inclusive range.

        A date is a school day when the effective revision defines at least one
        period for that weekday AND no holiday is in force. The weekly pattern is
        entirely the school's own period templates: this module never assumes
        which weekdays a school teaches (review item 9).
        """
        exceptions = self._exceptions_by_date(
            school_id=school_id, from_date=from_date, to_date=to_date
        )
        versions = self._versions_covering(
            school_id=school_id, from_date=from_date, to_date=to_date
        )
        days: list[CalendarDay] = []
        for offset in range((to_date - from_date).days + 1):
            on = from_date + timedelta(days=offset)
            version = self._pick_version(versions, on)
            weekdays = self._teaching_weekdays(version)
            rows = exceptions.get(on, ())
            kinds = tuple(sorted({row.kind for row in rows}))
            holiday = next((row for row in rows if row.kind == "holiday"), None)
            has_periods = on.isoweekday() in weekdays
            if holiday is not None:
                days.append(
                    CalendarDay(
                        date=on,
                        is_school_day=False,
                        reason_key=holiday.reason_key or "timetable.reason.holiday",
                        kinds=kinds,
                    )
                )
            elif not has_periods:
                days.append(
                    CalendarDay(
                        date=on,
                        is_school_day=False,
                        reason_key="timetable.reason.no_periods",
                        kinds=kinds,
                    )
                )
            else:
                days.append(
                    CalendarDay(date=on, is_school_day=True, reason_key=None, kinds=kinds)
                )
        return tuple(days)

    def calendar_day(self, *, school_id: UUID, on: date) -> CalendarDay:
        """Return the calendar answer for one date."""
        return self.calendar_days(school_id=school_id, from_date=on, to_date=on)[0]

    # --- dated schedules ----------------------------------------------------

    def day_for_section(self, *, school_id: UUID, section_id: UUID, on: date) -> DayView:
        """Return one section's effective schedule for a date.

        A holiday yields no sessions, because a holiday has no eligible teaching
        period to attend. A cancelled period IS returned, with ``cancelled`` set,
        so the UI can show it rather than silently losing it.
        """
        version = self.effective_version(school_id=school_id, on=on)
        day = self.calendar_day(school_id=school_id, on=on)
        if version is None or not day.is_school_day:
            return DayView(
                date=on, section_id=section_id, day=day, timetable=version, sessions=()
            )
        sessions = self._sessions(
            school_id=school_id, version=version, on=on, section_id=section_id
        )
        return DayView(
            date=on, section_id=section_id, day=day, timetable=version, sessions=sessions
        )

    def sessions_for_teacher(
        self, *, school_id: UUID, staff_id: UUID, on: date
    ) -> tuple[CalendarDay, tuple[SessionView, ...]]:
        """Return a teacher's dated periods: assigned to them, or substituted by them.

        A period the teacher is assigned to but someone else is covering stays in
        their day, marked with the substitute, because it is still their class.
        """
        version = self.effective_version(school_id=school_id, on=on)
        day = self.calendar_day(school_id=school_id, on=on)
        if version is None or not day.is_school_day:
            return day, ()
        everything = self._sessions(
            school_id=school_id, version=version, on=on, section_id=None
        )
        mine = tuple(
            session
            for session in everything
            if session.dated.teacher_id == staff_id or session.substitute_teacher_id == staff_id
        )
        return day, mine

    def session_by_identity(self, *, school_id: UUID, session_id: UUID) -> SessionView | None:
        """Return one dated period by its stable identity, or None.

        Resolution is two-stage. A period that carries a substitution or a
        cancellation is found directly, because those rows store the identity. Any
        other period needs a REVERSE lookup, and a uuid5 cannot be reversed, so the
        search recomputes identities over the published revisions' own date ranges
        and stops at the first match.

        Does not handle: doing that cheaply at scale. The search is bounded by
        MAX_RANGE_DAYS per revision and by the sections and slot codes each
        revision actually declares, which is small for one school -- but a
        materialised session index is the obvious optimisation and is recorded as a
        follow-up in docs/modules/M03/handoff.md.
        """
        session, day = self.session_ignoring_calendar(
            school_id=school_id, session_id=session_id
        )
        if day is None or not day.is_school_day:
            return None
        return session

    def session_ignoring_calendar(
        self, *, school_id: UUID, session_id: UUID
    ) -> tuple[SessionView | None, CalendarDay | None]:
        """Return a session and its calendar day, even when the day is not a school day.

        The teaching-authority answer needs both: on a holiday M04 must be told
        "this period exists and is not eligible", not handed a 404 that it cannot
        distinguish from a bad id. Every browser-facing read uses
        ``session_by_identity`` instead, which hides a period that does not run.
        """
        located = self._locate_identity(school_id=school_id, session_id=session_id)
        if located is None:
            return None, None
        section_id, on = located
        day = self.calendar_day(school_id=school_id, on=on)
        version = self.effective_version(school_id=school_id, on=on)
        if version is None:
            return None, day
        sessions = self._sessions(
            school_id=school_id, version=version, on=on, section_id=section_id
        )
        found = next((s for s in sessions if s.dated.timetable_session_id == session_id), None)
        return found, day

    # --- internals ----------------------------------------------------------

    def _sessions(
        self,
        *,
        school_id: UUID,
        version: TimetableVersion,
        on: date,
        section_id: UUID | None,
    ) -> tuple[SessionView, ...]:
        """Expand a revision's slots onto a date and fold in the day's overrides."""
        slots = version.slots.select_related("period").filter(
            period__day_of_week=on.isoweekday()
        )
        if section_id is not None:
            slots = slots.filter(section_id=section_id)
        rows = tuple(
            (
                slot.id,
                slot.section_id,
                slot.period.slot_code,
                slot.period.starts_at_local,
                slot.period.ends_at_local,
                slot.subject_id,
                slot.teacher_id,
                slot.room_code,
            )
            for slot in slots
        )
        dated = expand_day(school_id=school_id, on=on, rows=rows)
        identities = [item.timetable_session_id for item in dated]
        substitutions = {
            row.timetable_session_id: row
            for row in Substitution.objects.filter(
                school_id=school_id, timetable_session_id__in=identities, withdrawn=False
            )
        }
        cancellations = {
            row.timetable_session_id: row
            for row in SessionCancellation.objects.filter(
                school_id=school_id, timetable_session_id__in=identities
            )
        }
        views = []
        for item in dated:
            substitution = substitutions.get(item.timetable_session_id)
            cancellation = cancellations.get(item.timetable_session_id)
            views.append(
                SessionView(
                    dated=item,
                    timetable_id=version.id,
                    timetable_version=version.version,
                    cancelled=bool(cancellation and cancellation.cancelled),
                    cancellation_reason_key=(
                        cancellation.reason_key
                        if cancellation and cancellation.cancelled
                        else None
                    ),
                    substitute_teacher_id=(
                        substitution.substitute_teacher_id if substitution else None
                    ),
                    substitution_valid_until=substitution.valid_until if substitution else None,
                )
            )
        return tuple(views)

    def _exceptions_by_date(
        self, *, school_id: UUID, from_date: date, to_date: date
    ) -> dict[date, tuple[CalendarException, ...]]:
        """Return the live exceptions in a range, grouped by date."""
        grouped: dict[date, list[CalendarException]] = {}
        for row in CalendarException.objects.filter(
            school_id=school_id, withdrawn=False, date__gte=from_date, date__lte=to_date
        ):
            grouped.setdefault(row.date, []).append(row)
        return {on: tuple(rows) for on, rows in grouped.items()}

    def _versions_covering(
        self, *, school_id: UUID, from_date: date, to_date: date
    ) -> tuple[TimetableVersion, ...]:
        """Return every servable revision overlapping a range, newest range first."""
        return tuple(
            TimetableVersion.objects.filter(
                school_id=school_id,
                state__in=("published", "superseded"),
                effective_from__lte=to_date,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=from_date))
            .prefetch_related("periods")
            .order_by("-effective_from", "-published_at", "-id")
        )

    def _pick_version(
        self, versions: tuple[TimetableVersion, ...], on: date
    ) -> TimetableVersion | None:
        """Return the first revision from a prefetched list that covers a date."""
        for version in versions:
            if version.effective_from <= on and (
                version.effective_to is None or on <= version.effective_to
            ):
                return version
        return None

    def _teaching_weekdays(self, version: TimetableVersion | None) -> frozenset[int]:
        """Return the weekdays a revision defines periods for."""
        if version is None:
            return frozenset()
        return frozenset(period.day_of_week for period in version.periods.all())

    def _locate_identity(
        self, *, school_id: UUID, session_id: UUID
    ) -> tuple[UUID, date] | None:
        """Return the (section, date) a session identity belongs to, or None."""
        for model in (Substitution, SessionCancellation):
            row = model.objects.filter(
                school_id=school_id, timetable_session_id=session_id
            ).first()
            if row is not None:
                return row.section_id, row.date

        for version in TimetableVersion.objects.filter(
            school_id=school_id, state__in=("published", "superseded")
        ).prefetch_related("periods", "slots"):
            sections = sorted({slot.section_id for slot in version.slots.all()}, key=str)
            codes = sorted({period.slot_code for period in version.periods.all()})
            if not sections or not codes:
                continue
            last = version.effective_to or version.effective_from + timedelta(
                days=MAX_RANGE_DAYS
            )
            span = min((last - version.effective_from).days, MAX_RANGE_DAYS)
            for offset in range(span + 1):
                on = version.effective_from + timedelta(days=offset)
                for section_id in sections:
                    for code in codes:
                        candidate = session_id_for(
                            school_id=school_id, section_id=section_id, on=on, slot_code=code
                        )
                        if candidate == session_id:
                            return section_id, on
        return None
