"""The permission codes M03 owns.

Declaring a code is not granting it. There is no role rank and no implied
superuser here: ``timetable.edit`` does not silently imply ``timetable.publish``,
because the person who builds the grid is not always the person authorised to make
it the school's schedule. The grant table must enumerate each action.

The packet names four codes. The three extra read codes are the split between a
school-scoped read and a relationship-gated one -- the same split M02 makes
between ``students.read`` and ``students.read_record``. Without it, "an unrelated
class is denied" cannot be expressed at all: a single school-scoped read rule
would let any authenticated actor read any class's schedule.

Does not handle: deciding any of them. M01 access owns decisions; this module
calls the port and obeys the answer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    """One action this module will ask Access about."""

    code: str
    description: str
    requires_recent_two_factor: bool = False


#: Publication is the only action needing a fresh second factor. The window is
#: 300 seconds and lives in fixture_policy.py, not here: this file says WHICH
#: actions are sensitive, not how fresh "recent" is.
CATALOGUE: tuple[PermissionSpec, ...] = (
    PermissionSpec(
        code="timetable.read",
        description="Read the school's own timetable metadata and calendar.",
    ),
    PermissionSpec(
        code="timetable.read_calendar",
        description="Read the school calendar: which days are school days, and why not.",
    ),
    PermissionSpec(
        code="timetable.read_section",
        description="Read one section's effective schedule, within an authorised relationship.",
    ),
    PermissionSpec(
        code="timetable.read_teacher",
        description="Read one's own dated teaching schedule.",
    ),
    PermissionSpec(
        code="timetable.read_student",
        description="Read one pupil's dated schedule, within an authorised relationship.",
    ),
    PermissionSpec(
        code="timetable.edit",
        description="Build and amend a draft grid, the calendar and unavailability.",
    ),
    PermissionSpec(
        code="timetable.publish",
        description="Make a draft revision the school's effective schedule.",
        requires_recent_two_factor=True,
    ),
    PermissionSpec(
        code="timetable.substitute",
        description="Assign or withdraw a dated substitute for one period.",
    ),
)

#: Codes only, for the registration declaration and the host's collision check.
PERMISSION_CODES: tuple[str, ...] = tuple(spec.code for spec in CATALOGUE)
