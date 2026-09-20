"""Synthetic seed scenarios for M03.

All data here is synthetic and derived from ``shared.fixtures``, so the same
scenario produces byte-identical rows on every machine. Nothing here describes a
real school, a real person, a real holiday or a real curriculum: the school
publishes its own period pattern, subject list and calendar.

The weekly pattern below -- two periods on five weekdays -- is FIXTURE DATA. It
is not a claim about any school's week, and nothing in this module assumes one:
which weekdays a school teaches is entirely its own period templates.

Mirrors ``contracts/M03/fixtures/scenario.json``, which is the reviewed
description of the same rows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time

from shared import fixtures

from .models import (
    CalendarException,
    PeriodTemplate,
    Slot,
    Substitution,
    TeacherUnavailable,
    TimetableVersion,
)
from .sessions import end_of_school_day, session_id_for

#: Fixed instant for seeded rows, inside the fixture school term. A fixed instant
#: rather than "now" keeps seeded data deterministic, which cursor ordering and
#: substitution-expiry assertions both depend on.
SEED_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

#: Namespace for seeded row ids, so re-running is idempotent rather than
#: accumulating duplicates. Derived from a URL so the derivation is auditable.
SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://school.example/contracts/M03/seed")

#: The synthetic academic year the seeded revision belongs to. Stored opaquely:
#: the frozen RegistryPort exposes no academic year to check it against.
SEED_YEAR_ID = uuid.uuid5(SEED_NAMESPACE, "academic_year.2026-2027")

TEACHING_WEEKDAYS = (1, 2, 3, 4, 5)
PERIODS = (("P1", time(8, 45), time(9, 30)), ("P2", time(9, 30), time(10, 15)))
EFFECTIVE_FROM = date(2026, 6, 1)
HOLIDAY = date(2026, 7, 16)
EXAM_DAY = date(2026, 7, 22)
ACTIVE_SUBSTITUTION_DATE = date(2026, 7, 15)
EXPIRED_SUBSTITUTION_DATE = date(2026, 7, 8)


def _seed_id(label: str) -> uuid.UUID:
    """Return a stable id for a seeded row label."""
    return uuid.uuid5(SEED_NAMESPACE, label)


def _grid() -> tuple[tuple[str, uuid.UUID, uuid.UUID, uuid.UUID, str | None], ...]:
    """Return the seeded slots as (slot_code, section, subject, teacher, room)."""
    return (
        ("P1", fixtures.CLASS_C1, fixtures.SUBJECT_MATHS, fixtures.TEACHER_T1, "R1"),
        ("P2", fixtures.CLASS_C1, fixtures.SUBJECT_MALAYALAM, fixtures.TEACHER_T1, "R1"),
        ("P1", fixtures.CLASS_C2, fixtures.SUBJECT_MALAYALAM, fixtures.TEACHER_T2, None),
        ("P2", fixtures.CLASS_C2, fixtures.SUBJECT_MATHS, fixtures.TEACHER_T2, None),
    )


def baseline(school_id: uuid.UUID | None = None) -> dict[str, int]:
    """Install the reviewed baseline scenario, idempotently.

    One published revision, a holiday, an exam day, one unavailability window and
    two dated substitutions -- one still live at the seeded instant and one
    already expired, so a consumer can be tested against both.

    Running it twice leaves the same rows and does not advance any version.
    """
    resolved = school_id or fixtures.SCHOOL_A
    counts = {"timetables": 0, "periods": 0, "slots": 0, "exceptions": 0, "substitutions": 0}

    version, created = TimetableVersion.objects.get_or_create(
        id=_seed_id("timetable.v1"),
        defaults={
            "school_id": resolved,
            "year_id": SEED_YEAR_ID,
            "effective_from": EFFECTIVE_FROM,
            "effective_to": None,
            "state": "published",
            "published_at": SEED_INSTANT,
            "version": 2,
            "created_at": SEED_INSTANT,
            "updated_at": SEED_INSTANT,
        },
    )
    counts["timetables"] = 1 if created else 0

    periods: dict[tuple[int, str], PeriodTemplate] = {}
    for weekday in TEACHING_WEEKDAYS:
        for code, starts, ends in PERIODS:
            period, made = PeriodTemplate.objects.get_or_create(
                id=_seed_id(f"period.{weekday}.{code}"),
                defaults={
                    "school_id": resolved,
                    "timetable": version,
                    "day_of_week": weekday,
                    "slot_code": code,
                    "starts_at_local": starts,
                    "ends_at_local": ends,
                    "created_at": SEED_INSTANT,
                    "updated_at": SEED_INSTANT,
                },
            )
            periods[(weekday, code)] = period
            counts["periods"] += 1 if made else 0

    slots: dict[tuple[int, str, uuid.UUID], Slot] = {}
    for weekday in TEACHING_WEEKDAYS:
        for code, section_id, subject_id, teacher_id, room in _grid():
            slot, made = Slot.objects.get_or_create(
                id=_seed_id(f"slot.{weekday}.{code}.{section_id}"),
                defaults={
                    "school_id": resolved,
                    "timetable": version,
                    "period": periods[(weekday, code)],
                    "section_id": section_id,
                    "subject_id": subject_id,
                    "teacher_id": teacher_id,
                    "room_code": room,
                    "created_at": SEED_INSTANT,
                    "updated_at": SEED_INSTANT,
                },
            )
            slots[(weekday, code, section_id)] = slot
            counts["slots"] += 1 if made else 0

    counts["exceptions"] += _exception(resolved, HOLIDAY, "holiday", "timetable.reason.holiday")
    counts["exceptions"] += _exception(resolved, EXAM_DAY, "exam", "timetable.reason.exam")

    _unavailability(resolved)

    for label, on in (
        ("active", ACTIVE_SUBSTITUTION_DATE),
        ("expired", EXPIRED_SUBSTITUTION_DATE),
    ):
        counts["substitutions"] += _substitution(
            resolved, label=label, on=on, slot=slots[(on.isoweekday(), "P1", fixtures.CLASS_C1)]
        )

    return counts


def _exception(school_id: uuid.UUID, on: date, kind: str, reason_key: str) -> int:
    """Install one calendar exception. Returns 1 when it was created."""
    _row, created = CalendarException.objects.get_or_create(
        id=_seed_id(f"exception.{on}.{kind}"),
        defaults={
            "school_id": school_id,
            "date": on,
            "kind": kind,
            "reason_key": reason_key,
            "withdrawn": False,
            "created_at": SEED_INSTANT,
            "updated_at": SEED_INSTANT,
        },
    )
    return 1 if created else 0


def _unavailability(school_id: uuid.UUID) -> int:
    """Install the one seeded unavailability window for T1."""
    _row, created = TeacherUnavailable.objects.get_or_create(
        id=_seed_id("unavailable.t1"),
        defaults={
            "school_id": school_id,
            "staff_id": fixtures.TEACHER_T1,
            "starts_at": datetime(2026, 7, 20, 3, 0, tzinfo=UTC),
            "ends_at": datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
            "reason_key": "timetable.reason.unavailable",
            "withdrawn": False,
            "created_at": SEED_INSTANT,
            "updated_at": SEED_INSTANT,
        },
    )
    return 1 if created else 0


def _substitution(school_id: uuid.UUID, *, label: str, on: date, slot: Slot) -> int:
    """Install one dated substitution covering C1's first period."""
    _row, created = Substitution.objects.get_or_create(
        id=_seed_id(f"substitution.{label}"),
        defaults={
            "school_id": school_id,
            "date": on,
            "slot": slot,
            "timetable_session_id": session_id_for(
                school_id=school_id, section_id=slot.section_id, on=on, slot_code="P1"
            ),
            "section_id": slot.section_id,
            "subject_id": slot.subject_id,
            "original_teacher_id": slot.teacher_id,
            "substitute_teacher_id": fixtures.TEACHER_T2,
            "reason": "synthetic fixture",
            "valid_until": end_of_school_day(on),
            "withdrawn": False,
            "created_at": SEED_INSTANT,
            "updated_at": SEED_INSTANT,
        },
    )
    return 1 if created else 0
