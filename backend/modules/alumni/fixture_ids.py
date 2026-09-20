"""Scenario actor ids and leaving snapshot defaults from contracts/M10 fixtures.

Values match contracts/M10/fixtures/scenario.json. Not production school policy.
"""

from __future__ import annotations

from uuid import UUID

from shared import fixtures

#: Reviewer actor from the frozen scenario (same UUID as PRINCIPAL_P1).
REVIEWER_ACTOR_ID = fixtures.PRINCIPAL_P1

#: Manager actor declared in the frozen scenario (synthetic, not a Registry person).
MANAGER_ACTOR_ID = UUID("6a201b7b-fdb5-5b6f-c6f0-d3e887d0400f")

#: Unrelated actor declared in the frozen scenario (must be denied alumni staff).
UNRELATED_ACTOR_ID = UUID("7b302c8c-0ec6-5c7f-d701-e4f998e15110")

#: Fixture last_standard for baseline students (scenario graduate/transfer rows).
FIXTURE_LAST_STANDARD: dict[UUID, int] = {
    fixtures.STUDENT_S1: 12,
    fixtures.STUDENT_S2: 10,
}

#: Actors that FakeAccess would allow school-scoped but must not use alumni staff APIs.
NON_STAFF_ACTORS: frozenset[UUID] = frozenset(
    {
        fixtures.STUDENT_S1,
        fixtures.STUDENT_S2,
        fixtures.STUDENT_S3,
        fixtures.GUARDIAN_G1,
        fixtures.GUARDIAN_G2,
        fixtures.STUDENT_S1_SCHOOL_B,
        UNRELATED_ACTOR_ID,
    }
)

#: Staff actors allowed alumni.* fixture grants in standalone.
STAFF_ACTORS: frozenset[UUID] = frozenset(
    {
        REVIEWER_ACTOR_ID,
        MANAGER_ACTOR_ID,
        fixtures.TEACHER_T1,
        fixtures.TEACHER_T2,
        fixtures.TEACHER_T3,
    }
)
