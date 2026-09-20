"""Conflict detection for a timetable draft.

Pure. Everything it needs -- the grid, recorded unavailability, Registry's
teaching assignments and the set of sections Registry confirmed -- arrives as
arguments, so the rules can be asserted without a database and a caller cannot
accidentally make detection depend on the clock.

The rules are DATA: ``CONFLICT_SPECS`` names each code, its message key and
whether it blocks publication. Adding a rule adds a row and one detector, not a
branch inside another rule.

Does not handle: room clashes. There is no Room aggregate -- rooms were not among
the module's owned records, and ``room_code`` is free text (review item 5).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from contracts.people import TeachingAssignment

from .sessions import local_windows_overlap, utc_window, windows_overlap


@dataclass(frozen=True, slots=True)
class ConflictSpec:
    """One conflict rule's identity, as reviewed and frozen in the contract."""

    code: str
    message_key: str
    blocking: bool


#: The whole closed set, mirroring contracts/M03/error-codes.json. Exactly one is
#: non-blocking, for the reason recorded in review item 4: Registry's assignment
#: table commonly lags the grid, and the frozen port cannot tell an unknown
#: teacher from an unassigned one.
CONFLICT_SPECS: tuple[ConflictSpec, ...] = (
    ConflictSpec("teacher_double_booked", "timetable.conflict.teacher_double_booked", True),
    ConflictSpec("section_double_booked", "timetable.conflict.section_double_booked", True),
    ConflictSpec("teacher_unavailable", "timetable.conflict.teacher_unavailable", True),
    ConflictSpec("period_overlap", "timetable.conflict.period_overlap", True),
    ConflictSpec(
        "slot_references_unknown_period",
        "timetable.conflict.slot_references_unknown_period",
        True,
    ),
    ConflictSpec(
        "section_unknown_to_registry", "timetable.conflict.section_unknown_to_registry", True
    ),
    ConflictSpec("teacher_not_assigned", "timetable.conflict.teacher_not_assigned", False),
)

SPEC_BY_CODE: Mapping[str, ConflictSpec] = {spec.code: spec for spec in CONFLICT_SPECS}

#: How far an open-ended version is walked when expanding an unavailability
#: window. The interval itself bounds the walk in practice; this is the backstop
#: so a version with no end date can never produce an unbounded loop.
MAX_EXPANSION_DAYS = 400


@dataclass(frozen=True, slots=True)
class PeriodRow:
    """One period template, as the detector sees it."""

    period_id: uuid.UUID
    day_of_week: int
    slot_code: str
    starts_at_local: time
    ends_at_local: time


@dataclass(frozen=True, slots=True)
class SlotRow:
    """One slot, as the detector sees it."""

    slot_id: uuid.UUID
    period_id: uuid.UUID
    section_id: uuid.UUID
    subject_id: uuid.UUID
    teacher_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class UnavailabilityRow:
    """One staff member's half-open unavailable interval, in UTC."""

    staff_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True, slots=True)
class Conflict:
    """One detected problem, ready to render as the frozen ConflictDTO."""

    code: str
    message_key: str
    blocking: bool
    slot_ids: tuple[uuid.UUID, ...] = ()
    teacher_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    date: date | None = None

    @property
    def sort_key(self) -> tuple:
        """Return a total order, so two runs over the same grid agree exactly."""
        return (
            self.code,
            tuple(str(slot_id) for slot_id in self.slot_ids),
            str(self.teacher_id or ""),
            str(self.section_id or ""),
            self.date.isoformat() if self.date else "",
        )


def _conflict(code: str, **fields) -> Conflict:
    """Build a Conflict from its spec, so code, key and blocking never disagree."""
    spec = SPEC_BY_CODE[code]
    return Conflict(
        code=spec.code, message_key=spec.message_key, blocking=spec.blocking, **fields
    )


def detect_conflicts(
    *,
    periods: Sequence[PeriodRow],
    slots: Sequence[SlotRow],
    unavailability: Sequence[UnavailabilityRow],
    assignments: Mapping[uuid.UUID, Sequence[TeachingAssignment]],
    known_sections: frozenset[uuid.UUID],
    effective_from: date,
    effective_to: date | None,
) -> tuple[Conflict, ...]:
    """Return every conflict in a grid, in a deterministic order.

    Pure and total: the same inputs always produce the same tuple, and no input
    shape raises. Order-independent by construction -- every detector groups and
    sorts before comparing -- which the suite asserts by shuffling the input.

    Does not handle: deciding whether to publish. The caller asks whether any
    returned conflict is ``blocking``; keeping that decision out of here means the
    editor can show a non-blocking conflict without the rule having to know who is
    asking.
    """
    by_period = {period.period_id: period for period in periods}
    found: list[Conflict] = []

    found.extend(_overlapping_period_templates(periods))
    found.extend(_orphan_slots(slots, by_period))
    found.extend(_double_bookings(slots, by_period))
    found.extend(_unknown_sections(slots, known_sections))
    found.extend(_unassigned_teachers(slots, assignments, effective_from))
    found.extend(
        _unavailable_teachers(slots, by_period, unavailability, effective_from, effective_to)
    )

    return tuple(sorted(set(found), key=lambda conflict: conflict.sort_key))


def _overlapping_period_templates(periods: Sequence[PeriodRow]) -> list[Conflict]:
    """Return a conflict for each pair of periods sharing time on one weekday.

    The write boundary already refuses these, so this is defence in depth: a
    version stored before the rule existed must still be caught rather than
    published because nothing looked again.
    """
    found: list[Conflict] = []
    by_day: dict[int, list[PeriodRow]] = {}
    for period in periods:
        by_day.setdefault(period.day_of_week, []).append(period)
    for day_periods in by_day.values():
        ordered = sorted(day_periods, key=lambda p: (p.starts_at_local, p.slot_code))
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if local_windows_overlap(
                    (first.starts_at_local, first.ends_at_local),
                    (second.starts_at_local, second.ends_at_local),
                ):
                    found.append(_conflict("period_overlap"))
    return found


def _orphan_slots(
    slots: Sequence[SlotRow], by_period: Mapping[uuid.UUID, PeriodRow]
) -> list[Conflict]:
    """Return a conflict for each slot whose period the version no longer has."""
    return [
        _conflict("slot_references_unknown_period", slot_ids=(slot.slot_id,))
        for slot in sorted(slots, key=lambda s: str(s.slot_id))
        if slot.period_id not in by_period
    ]


def _double_bookings(
    slots: Sequence[SlotRow], by_period: Mapping[uuid.UUID, PeriodRow]
) -> list[Conflict]:
    """Return every teacher and section booked twice in overlapping periods.

    Compared as half-open local windows on the same weekday, so abutting periods
    are not a clash. One conflict is emitted per colliding PAIR, naming both slot
    ids, because an editor has to be told which two cells to change.
    """
    found: list[Conflict] = []
    placed = [
        (slot, by_period[slot.period_id]) for slot in slots if slot.period_id in by_period
    ]

    for key, code, attribute in (
        (lambda item: item[0].teacher_id, "teacher_double_booked", "teacher_id"),
        (lambda item: item[0].section_id, "section_double_booked", "section_id"),
    ):
        grouped: dict[tuple[uuid.UUID, int], list[tuple[SlotRow, PeriodRow]]] = {}
        for item in placed:
            grouped.setdefault((key(item), item[1].day_of_week), []).append(item)
        for (owner, _day), items in grouped.items():
            ordered = sorted(
                items, key=lambda item: (item[1].starts_at_local, str(item[0].slot_id))
            )
            for index, (first_slot, first_period) in enumerate(ordered):
                for second_slot, second_period in ordered[index + 1 :]:
                    if not local_windows_overlap(
                        (first_period.starts_at_local, first_period.ends_at_local),
                        (second_period.starts_at_local, second_period.ends_at_local),
                    ):
                        continue
                    found.append(
                        _conflict(
                            code,
                            slot_ids=tuple(
                                sorted((first_slot.slot_id, second_slot.slot_id), key=str)
                            ),
                            **{attribute: owner},
                        )
                    )
    return found


def _unknown_sections(
    slots: Sequence[SlotRow], known_sections: frozenset[uuid.UUID]
) -> list[Conflict]:
    """Return one conflict per section Registry does not report for this school."""
    unknown = sorted(
        {slot.section_id for slot in slots if slot.section_id not in known_sections}, key=str
    )
    return [
        _conflict(
            "section_unknown_to_registry",
            section_id=section_id,
            slot_ids=tuple(
                sorted((s.slot_id for s in slots if s.section_id == section_id), key=str)
            ),
        )
        for section_id in unknown
    ]


def _unassigned_teachers(
    slots: Sequence[SlotRow],
    assignments: Mapping[uuid.UUID, Sequence[TeachingAssignment]],
    effective_from: date,
) -> list[Conflict]:
    """Return one NON-BLOCKING conflict per teacher/section/subject Registry lacks.

    Checked on the version's first effective date. A dated assignment that has
    lapsed does not count, which is what ``TeachingAssignment.covers`` decides.
    """
    found: list[Conflict] = []
    seen: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = set()
    for slot in sorted(slots, key=lambda s: str(s.slot_id)):
        key = (slot.teacher_id, slot.section_id, slot.subject_id)
        if key in seen:
            continue
        seen.add(key)
        covering = [
            assignment
            for assignment in assignments.get(slot.teacher_id, ())
            if assignment.section_id == slot.section_id
            and assignment.subject_id == slot.subject_id
            and assignment.covers(effective_from)
        ]
        if not covering:
            found.append(
                _conflict(
                    "teacher_not_assigned",
                    slot_ids=(slot.slot_id,),
                    teacher_id=slot.teacher_id,
                    section_id=slot.section_id,
                )
            )
    return found


def _unavailable_teachers(
    slots: Sequence[SlotRow],
    by_period: Mapping[uuid.UUID, PeriodRow],
    unavailability: Sequence[UnavailabilityRow],
    effective_from: date,
    effective_to: date | None,
) -> list[Conflict]:
    """Return one conflict per dated period a recorded unavailability covers.

    Walks only the dates where the unavailability interval and the version's
    effective range actually intersect, so the loop is bounded by the interval --
    a teacher is unavailable for days, not for years. MAX_EXPANSION_DAYS is the
    backstop for an open-ended version.
    """
    found: list[Conflict] = []
    for interval in sorted(unavailability, key=lambda row: (row.starts_at, str(row.staff_id))):
        teaching = [
            (slot, by_period[slot.period_id])
            for slot in slots
            if slot.period_id in by_period and slot.teacher_id == interval.staff_id
        ]
        if not teaching:
            continue
        for on in _dates_in_scope(interval, effective_from, effective_to):
            for slot, period in sorted(
                teaching, key=lambda item: (item[1].starts_at_local, str(item[0].slot_id))
            ):
                if period.day_of_week != on.isoweekday():
                    continue
                if windows_overlap(
                    utc_window(on, period.starts_at_local, period.ends_at_local),
                    (interval.starts_at, interval.ends_at),
                ):
                    found.append(
                        _conflict(
                            "teacher_unavailable",
                            slot_ids=(slot.slot_id,),
                            teacher_id=interval.staff_id,
                            section_id=slot.section_id,
                            date=on,
                        )
                    )
    return found


def _dates_in_scope(
    interval: UnavailabilityRow, effective_from: date, effective_to: date | None
) -> list[date]:
    """Return the dates an interval and a version's range share.

    Uses the school-local dates of the interval's own instants, because a period
    is a school-local thing; the overlap comparison afterwards is in UTC, where it
    is exact.
    """
    from contracts.values import school_date

    start = max(effective_from, school_date(interval.starts_at))
    latest = effective_to or effective_from + timedelta(days=MAX_EXPANSION_DAYS)
    end = min(latest, school_date(interval.ends_at))
    if end < start:
        return []
    span = min((end - start).days, MAX_EXPANSION_DAYS)
    return [start + timedelta(days=offset) for offset in range(span + 1)]


def has_blocking(conflicts: Sequence[Conflict]) -> bool:
    """Return whether any conflict blocks publication."""
    return any(conflict.blocking for conflict in conflicts)
