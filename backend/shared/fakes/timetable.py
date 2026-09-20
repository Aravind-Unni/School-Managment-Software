"""Deterministic fake Timetable adapter for standalone consumers (M04+).

Returns schema-shaped PeriodSessionDTO / TeachingAuthorityDTO / CalendarDayDTO
values for the M04 baseline cast. Records calls for assertions. Does not import
the timetable ORM or make network calls.

Does not handle: inventing school policy. Periods, holidays and substitutions
are fixture data only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.timetable import CalendarDayDTO, PeriodSessionDTO, TeachingAuthorityDTO
from contracts.values import SCHOOL_TIMEZONE

from .. import fixtures
from .failures import FailureInjector

#: Same namespace M03 uses for dated session identity.
TIMETABLE_SESSION_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://school.example/contracts/M03/timetable-session"
)
TIMETABLE_ID = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://school.example/contracts/M04/fake-timetable"
)


def session_id_for(
    *, school_id: UUID, section_id: UUID, on: date, slot_code: str
) -> UUID:
    """Return the stable dated period id (school, section, date, slot_code)."""
    return uuid.uuid5(
        TIMETABLE_SESSION_NAMESPACE,
        f"{school_id}:{section_id}:{on.isoformat()}:{slot_code}",
    )


def _local_window(on: date, start: time, end: time) -> tuple[datetime, datetime]:
    """Convert school-local wall times on a date to timezone-aware UTC instants."""
    start_local = datetime.combine(on, start, tzinfo=SCHOOL_TIMEZONE)
    end_local = datetime.combine(on, end, tzinfo=SCHOOL_TIMEZONE)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


@dataclass
class _PeriodSpec:
    """One synthetic period definition for the fake."""

    slot_code: str
    slot_id: UUID
    subject_id: UUID
    assigned_teacher_id: UUID
    starts_local: time
    ends_local: time
    substitute_teacher_id: UUID | None = None
    cancelled: bool = False
    timetable_version: int = 2


@dataclass
class FakeTimetable:
    """Fixture-backed TimetablePort implementation.

    Default baseline matches contracts/M04/fixtures/scenario.json on
    TERM_SAMPLE_DATE for CLASS_C1: P1 maths/T1, P2 english/T2 with live T3
    substitute. Holidays and School B ids are inaccessible or empty.
    """

    failures: FailureInjector = field(default_factory=FailureInjector)
    calls: list[tuple[str, object]] = field(default_factory=list)
    _clock_now: datetime | None = None
    _version_bump: int = 0
    _cancelled_ids: set[UUID] = field(default_factory=set)
    _holiday_dates: set[date] = field(default_factory=lambda: {date(2026, 7, 16)})
    _extra_cancelled_slot: bool = True

    def __post_init__(self) -> None:
        """Seed default period specs for School A C1."""
        self._periods_by_date: dict[date, list[_PeriodSpec]] = {}
        sample = fixtures.TERM_SAMPLE_DATE
        self._periods_by_date[sample] = [
            _PeriodSpec(
                slot_code="P1",
                slot_id=fixtures.fixture_uuid("m04.slot.p1"),
                subject_id=fixtures.SUBJECT_MATHS,
                assigned_teacher_id=fixtures.TEACHER_T1,
                starts_local=time(8, 45),
                ends_local=time(9, 30),
            ),
            _PeriodSpec(
                slot_code="P2",
                slot_id=fixtures.fixture_uuid("m04.slot.p2"),
                subject_id=fixtures.SUBJECT_ENGLISH,
                assigned_teacher_id=fixtures.TEACHER_T2,
                starts_local=time(9, 30),
                ends_local=time(10, 15),
                substitute_teacher_id=fixtures.TEACHER_T3,
            ),
        ]
        if self._extra_cancelled_slot:
            self._periods_by_date[sample].append(
                _PeriodSpec(
                    slot_code="P3",
                    slot_id=fixtures.fixture_uuid("m04.slot.p3"),
                    subject_id=fixtures.SUBJECT_MATHS,
                    assigned_teacher_id=fixtures.TEACHER_T1,
                    starts_local=time(10, 30),
                    ends_local=time(11, 15),
                    cancelled=True,
                )
            )

    def set_clock(self, now: datetime) -> None:
        """Fix 'now' for substitution liveness checks."""
        self._clock_now = now

    def bump_timetable_version(self, delta: int = 1) -> None:
        """Raise published timetable_version so consumers see roster_stale."""
        self._version_bump += delta

    def cancel_session(self, timetable_session_id: UUID) -> None:
        """Mark one dated period cancelled after the fact."""
        self._cancelled_ids.add(timetable_session_id)

    def now(self) -> datetime:
        """Return the fake's clock, defaulting to the scenario frozen instant."""
        if self._clock_now is not None:
            return self._clock_now
        return datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

    def get_sessions(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
    ) -> tuple[PeriodSessionDTO, ...]:
        """Return teaching periods for a section on a date."""
        self.failures.maybe_fail("timetable.get_sessions")
        self.calls.append(("get_sessions", (section_id, effective_date)))
        if context.school_id != fixtures.SCHOOL_A:
            return ()
        if section_id != fixtures.CLASS_C1:
            return ()
        if effective_date in self._holiday_dates:
            return ()
        return tuple(
            self._to_session(spec, on=effective_date)
            for spec in self._periods_by_date.get(effective_date, [])
        )

    def get_session(
        self, context: RequestContext, timetable_session_id: UUID
    ) -> PeriodSessionDTO:
        """Return one period or raise ObjectInaccessible."""
        self.failures.maybe_fail("timetable.get_session")
        self.calls.append(("get_session", timetable_session_id))
        found = self._find(timetable_session_id)
        if found is None:
            raise ObjectInaccessible("error.object_inaccessible")
        on, spec = found
        if context.school_id != fixtures.SCHOOL_A:
            raise ObjectInaccessible("error.object_inaccessible")
        return self._to_session(spec, on=on)

    def get_calendar(
        self, context: RequestContext, from_date: date, to_date: date
    ) -> tuple[CalendarDayDTO, ...]:
        """Return school-day flags for each date in an inclusive range."""
        self.failures.maybe_fail("timetable.get_calendar")
        self.calls.append(("get_calendar", (from_date, to_date)))
        if to_date < from_date:
            return ()
        days: list[CalendarDayDTO] = []
        cursor = from_date
        while cursor <= to_date:
            holiday = cursor in self._holiday_dates
            weekday = cursor.isoweekday() <= 5
            is_school = weekday and not holiday and context.school_id == fixtures.SCHOOL_A
            days.append(
                CalendarDayDTO(
                    date=cursor,
                    is_school_day=is_school,
                    reason_key="timetable.reason.holiday" if holiday else None,
                    kinds=("holiday",) if holiday else (("weekday",) if is_school else ("weekend",)),
                )
            )
            cursor = cursor + timedelta(days=1)
        return tuple(days)

    def get_teaching_authority(
        self, context: RequestContext, timetable_session_id: UUID
    ) -> TeachingAuthorityDTO:
        """Return who may mark attendance for one dated period."""
        self.failures.maybe_fail("timetable.get_teaching_authority")
        self.calls.append(("get_teaching_authority", timetable_session_id))
        found = self._find(timetable_session_id)
        if found is None or context.school_id != fixtures.SCHOOL_A:
            raise ObjectInaccessible("error.object_inaccessible")
        on, spec = found
        session = self._to_session(spec, on=on)
        holiday = on in self._holiday_dates
        cancelled = session.cancelled
        live_sub = session.substitute_teacher_id
        valid_until = None
        if live_sub is not None:
            # End of school day Asia/Kolkata exclusive, matching M03 decision.
            end_local = datetime.combine(on, time(23, 59, 59), tzinfo=SCHOOL_TIMEZONE)
            valid_until = (end_local + timedelta(seconds=1)).astimezone(UTC)
            if self.now() >= valid_until:
                live_sub = None
                valid_until = None
        return TeachingAuthorityDTO(
            timetable_session_id=session.timetable_session_id,
            school_id=session.school_id,
            section_id=session.section_id,
            subject_id=session.subject_id,
            date=session.date,
            assigned_teacher_id=session.assigned_teacher_id,
            substitute_teacher_id=live_sub,
            substitution_valid_until=valid_until,
            cancelled=cancelled,
            eligible_for_attendance=bool(not holiday and not cancelled),
        )

    def _find(self, timetable_session_id: UUID) -> tuple[date, _PeriodSpec] | None:
        """Locate a period spec by stable session id."""
        for on, specs in self._periods_by_date.items():
            for spec in specs:
                sid = session_id_for(
                    school_id=fixtures.SCHOOL_A,
                    section_id=fixtures.CLASS_C1,
                    on=on,
                    slot_code=spec.slot_code,
                )
                if sid == timetable_session_id:
                    return on, spec
        # School B probe id — never found for School A context.
        return None

    def _to_session(self, spec: _PeriodSpec, *, on: date) -> PeriodSessionDTO:
        """Build a PeriodSessionDTO from a period spec."""
        sid = session_id_for(
            school_id=fixtures.SCHOOL_A,
            section_id=fixtures.CLASS_C1,
            on=on,
            slot_code=spec.slot_code,
        )
        starts_at, ends_at = _local_window(on, spec.starts_local, spec.ends_local)
        cancelled = spec.cancelled or sid in self._cancelled_ids
        return PeriodSessionDTO(
            timetable_session_id=sid,
            school_id=fixtures.SCHOOL_A,
            section_id=fixtures.CLASS_C1,
            date=on,
            slot_id=spec.slot_id,
            slot_code=spec.slot_code,
            subject_id=spec.subject_id,
            assigned_teacher_id=spec.assigned_teacher_id,
            substitute_teacher_id=spec.substitute_teacher_id,
            starts_at=starts_at,
            ends_at=ends_at,
            starts_at_local=spec.starts_local,
            ends_at_local=spec.ends_local,
            cancelled=cancelled,
            cancellation_reason_key="timetable.reason.cancelled" if cancelled else None,
            room_code=None,
            timetable_id=TIMETABLE_ID,
            timetable_version=spec.timetable_version + self._version_bump,
        )
