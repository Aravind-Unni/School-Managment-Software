"""Dated teaching periods: their stable identity and their wall-clock windows.

Pure. No IO, no clock, no globals: every function takes what it needs and returns
a value, so the identity rule can be asserted without a database and cannot drift
between the API, the service port and a worker.

The one property this module exists to protect: **a dated period keeps the same
id across a timetable revision.** Attendance is written against that id, so if it
moved when a school republished its grid, every past register would orphan.

Does not handle: whether a session is eligible for attendance. That depends on the
calendar and on cancellation, which are stored state; ``services/reads.py`` folds
those in.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from contracts.values import SCHOOL_TIMEZONE

#: Namespace for dated session identities. Derived from a URL rather than written
#: as an opaque literal so the derivation is auditable, and fixed forever: changing
#: it would renumber every session in every school's history.
TIMETABLE_SESSION_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://school.example/contracts/M03/timetable-session"
)


def session_id_for(
    *, school_id: uuid.UUID, section_id: uuid.UUID, on: date, slot_code: str
) -> uuid.UUID:
    """Return the stable identity of one section's period on one date.

    Keyed on school, section, date and SLOT CODE. Deliberately not on the
    timetable version, the slot row id or the period's start time: all three
    change when a school publishes a revision, and the identity must not.

    Assumes ``slot_code`` is the school's own code ("P1") and is stable across
    revisions, which is what the editor enforces by keying the grid on it.

    Does not handle: collisions between two sections sharing a code on one date.
    There are none, because the section is part of the key.
    """
    return uuid.uuid5(
        TIMETABLE_SESSION_NAMESPACE,
        f"{school_id}:{section_id}:{on.isoformat()}:{slot_code}",
    )


def utc_window(
    on: date, starts_at_local: time, ends_at_local: time
) -> tuple[datetime, datetime]:
    """Return the UTC instants a local period occupies on a date.

    Periods are stated in school wall-clock time because that is how a school
    states them; instants are stored and compared in UTC because that is the only
    representation that survives a timezone database update.

    Assumes the local times are valid on that date. India has no daylight saving,
    so there is no ambiguous or skipped local time to resolve; a deployment in a
    zone that has one would need a rule here, and does not have one.
    """
    return (
        datetime.combine(on, starts_at_local, tzinfo=SCHOOL_TIMEZONE).astimezone(UTC),
        datetime.combine(on, ends_at_local, tzinfo=SCHOOL_TIMEZONE).astimezone(UTC),
    )


def end_of_school_day(on: date) -> datetime:
    """Return the exclusive instant at which a school date ends.

    Midnight at the start of the following day, in school time. Used as the
    default and the ceiling for a substitution's ``valid_until``: the reviewed
    decision (review item 7) is that a substitute's authority lasts to the end of
    the day they substituted on, never beyond it.
    """
    return datetime.combine(
        on + timedelta(days=1), time(0, 0), tzinfo=SCHOOL_TIMEZONE
    ).astimezone(UTC)


def windows_overlap(
    first: tuple[datetime, datetime], second: tuple[datetime, datetime]
) -> bool:
    """Return whether two half-open instant ranges overlap.

    Half-open [start, end): a period ending at 09:30 and one starting at 09:30 do
    not overlap, because that is an ordinary school day and not a clash.
    """
    return first[0] < second[1] and second[0] < first[1]


def local_windows_overlap(first: tuple[time, time], second: tuple[time, time]) -> bool:
    """Return whether two half-open local time ranges overlap on one weekday."""
    return first[0] < second[1] and second[0] < first[1]


@dataclass(frozen=True, slots=True)
class DatedSlot:
    """One slot resolved onto one date: everything a session needs but its state.

    Produced by expanding a published grid over a date. Carries no cancellation
    and no substitution, because those are stored per date and are folded in by
    the reader, not by this pure expansion.
    """

    timetable_session_id: uuid.UUID
    school_id: uuid.UUID
    section_id: uuid.UUID
    date: date
    slot_id: uuid.UUID
    slot_code: str
    subject_id: uuid.UUID
    teacher_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    starts_at_local: time
    ends_at_local: time
    room_code: str | None


def expand_day(
    *,
    school_id: uuid.UUID,
    on: date,
    rows: tuple[
        tuple[uuid.UUID, uuid.UUID, str, time, time, uuid.UUID, uuid.UUID, str | None], ...
    ],
) -> tuple[DatedSlot, ...]:
    """Expand a day's slot rows into dated sessions, ordered by start time.

    ``rows`` is a tuple of
    ``(slot_id, section_id, slot_code, starts_at_local, ends_at_local, subject_id,
    teacher_id, room_code)`` -- plain values rather than ORM objects, so this stays
    pure and testable without a database.

    Does not handle: filtering by calendar or by cancellation. A caller that
    expands a holiday gets the periods that WOULD have run; deciding that they do
    not is the reader's job, and keeping that decision in one place is what stops
    two endpoints disagreeing about whether a holiday has lessons.
    """
    sessions = []
    for slot_id, section_id, slot_code, starts, ends, subject_id, teacher_id, room in rows:
        window = utc_window(on, starts, ends)
        sessions.append(
            DatedSlot(
                timetable_session_id=session_id_for(
                    school_id=school_id, section_id=section_id, on=on, slot_code=slot_code
                ),
                school_id=school_id,
                section_id=section_id,
                date=on,
                slot_id=slot_id,
                slot_code=slot_code,
                subject_id=subject_id,
                teacher_id=teacher_id,
                starts_at=window[0],
                ends_at=window[1],
                starts_at_local=starts,
                ends_at_local=ends,
                room_code=room,
            )
        )
    return tuple(sorted(sessions, key=lambda s: (s.starts_at, s.slot_code, str(s.section_id))))
