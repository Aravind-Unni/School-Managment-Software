"""Fixture grants for the profiles that bind a FAKE Access adapter.

**This is test and development fixture data. It is not a production grant.**
The integrated and production profiles bind the real M01 Access and never import
this file; the architecture check forbids a production config selecting a fake.

It exists because the shared fake denies by default and the host factory passes
no module rules, so without it every M03 endpoint would 403 in standalone -- and
the tempting fix is a test-only bypass in the service, which would mean the
authorisation path shipped untested.

Each action is enumerated explicitly. There is no allow-all and no wildcard: an
action absent from this table is denied in standalone exactly as it would be in
production, which is what makes a missing grant visible during development.

Known limit of the shared fake, recorded rather than worked around: it has no
per-actor grants, so every persona holds every school-scoped action. A denial
that depends on WHO the actor is -- a teacher who may not publish -- cannot be
demonstrated here, only against real Access. The relationship-gated rules below
are the ones whose denials this module can and does prove.
"""

from __future__ import annotations

from datetime import timedelta

from contracts.identity import AuthLevel
from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

#: The reviewed step-up window for publication: 300 seconds, the same number M02
#: uses. Stated once, as data, so it is changed in one place and reviewed as a
#: number rather than hunted for in a branch.
RECENT_TWO_FACTOR_WINDOW = timedelta(seconds=300)

#: Relationships that may see a section's or a pupil's schedule. A school-wide
#: administrative read is a separate grant and is NOT folded in here.
READING_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    # School-scoped staff work: there is no single subject person, so a
    # relationship-gated rule would deny every list and calendar call.
    PolicyRule(action="timetable.read", allowed_relationships=frozenset()),
    # The calendar is what families plan around, so every role holds this.
    PolicyRule(action="timetable.read_calendar", allowed_relationships=frozenset()),
    PolicyRule(action="timetable.edit", allowed_relationships=frozenset()),
    PolicyRule(action="timetable.substitute", allowed_relationships=frozenset()),
    # Relationship-gated reads. These are what make "unrelated class denied" real.
    PolicyRule(action="timetable.read_section", allowed_relationships=READING_RELATIONSHIPS),
    PolicyRule(action="timetable.read_student", allowed_relationships=READING_RELATIONSHIPS),
    # A teacher reads their OWN day. Someone else's is timetable.edit work.
    PolicyRule(
        action="timetable.read_teacher",
        allowed_relationships=frozenset({Relationship.SELF}),
    ),
    # Publication: a fresh second factor, inside the reviewed window.
    PolicyRule(
        action="timetable.publish",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
)
