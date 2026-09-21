"""Scenario actor ids from contracts/M11 fixtures. Not production policy."""

from __future__ import annotations

from uuid import UUID

from shared import fixtures

PUBLISHER_ACTOR_ID = fixtures.PRINCIPAL_P1
SENDER_ACTOR_ID = UUID("6a201b7b-fdb5-5b6f-c6f0-d3e887d0400f")
UNRELATED_ACTOR_ID = UUID("7b302c8c-0ec6-5c7f-d701-e4f998e15110")

GUARDIAN_CONTACT_REF = fixtures.GUARDIAN_G1
REVOKED_GUARDIAN_CONTACT_REF = fixtures.GUARDIAN_G2

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

STAFF_ACTORS: frozenset[UUID] = frozenset(
    {
        PUBLISHER_ACTOR_ID,
        SENDER_ACTOR_ID,
        fixtures.TEACHER_T1,
        fixtures.TEACHER_T2,
        fixtures.TEACHER_T3,
    }
)
