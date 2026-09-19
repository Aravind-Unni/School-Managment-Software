"""The permission codes M02 owns.

Declaring a code is not granting it. There is no role rank and no implied
superuser here: ``registry.manage`` does not silently imply ``students.read``,
because a clerk who maintains the calendar is not thereby entitled to every
pupil's record. The grant table must enumerate each action for each actor.

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


#: Sensitive writes require a recently asserted second factor. The reviewed
#: window is 300 seconds and lives in the fixture policy, not here: this file
#: says WHICH actions are sensitive, not how fresh "recent" is.
CATALOGUE: tuple[PermissionSpec, ...] = (
    PermissionSpec(
        code="registry.manage",
        description="Maintain school configuration, calendar and reference data.",
    ),
    PermissionSpec(
        code="students.read",
        description="Read student records within an authorised scope.",
    ),
    PermissionSpec(
        code="students.update",
        description="Admit a student and amend their profile.",
        requires_recent_two_factor=True,
    ),
    PermissionSpec(
        code="guardians.manage",
        description="Maintain guardian records and their dated links.",
        requires_recent_two_factor=True,
    ),
    PermissionSpec(
        code="staff.assign",
        description="Maintain staff profiles and teaching assignments.",
    ),
    PermissionSpec(
        code="year.close",
        description="Close an academic year, blocking new lifecycle writes.",
        requires_recent_two_factor=True,
    ),
    PermissionSpec(
        code="students.promote",
        description="Preview and commit a reviewed promotion mapping.",
        requires_recent_two_factor=True,
    ),
    PermissionSpec(
        code="students.withdraw",
        description="Record a dated withdrawal and raise its access review.",
        requires_recent_two_factor=True,
    ),
)

#: Codes only, for the registration declaration and the host's collision check.
PERMISSION_CODES: tuple[str, ...] = tuple(spec.code for spec in CATALOGUE)
