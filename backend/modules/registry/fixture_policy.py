"""Fixture grants for the profiles that bind a FAKE Access adapter.

**This is test and development fixture data. It is not a production grant.**
The integrated and production profiles bind the real M01 Access and never import
this file; the architecture check forbids a production config selecting a fake.

It exists because the shared fake denies by default and the host factory passes
no module rules, so without it every M02 endpoint would 403 in standalone -- and
the tempting fix is a test-only bypass in the service, which would mean the
authorisation path shipped untested.

Each action is enumerated explicitly. There is no allow-all and no wildcard: an
action absent from this table is denied in standalone exactly as it would be in
production, which is what makes a missing grant visible during development.
"""

from __future__ import annotations

from datetime import timedelta

from contracts.identity import AuthLevel
from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

#: The reviewed step-up window for sensitive writes: 300 seconds. Stated once,
#: as data, so the number is changed in one place and reviewed as a number.
RECENT_TWO_FACTOR_WINDOW = timedelta(seconds=300)

#: Relationships that may read a pupil's record. Administrative school-wide
#: reads are a separate grant and are NOT folded in here.
READING_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    # Configuration and reference data are school-scoped staff work: there is no
    # single subject, so a relationship-gated rule would deny every list call.
    PolicyRule(action="staff.assign", allowed_relationships=frozenset()),
    # Directory reads are school-scoped; per-record reads are relationship-gated.
    PolicyRule(action="students.read", allowed_relationships=frozenset()),
    PolicyRule(action="students.read_record", allowed_relationships=READING_RELATIONSHIPS),
    # Sensitive writes: fresh second factor, within the reviewed window.
    PolicyRule(
        action="students.update",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
    PolicyRule(
        action="guardians.manage",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
    PolicyRule(
        action="registry.manage",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
)
