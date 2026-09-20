"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from datetime import timedelta

from contracts.identity import AuthLevel
from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

RECENT_TWO_FACTOR_WINDOW = timedelta(seconds=300)

READING_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="attendance.read", allowed_relationships=frozenset()),
    PolicyRule(action="attendance.mark", allowed_relationships=frozenset()),
    PolicyRule(action="attendance.submit", allowed_relationships=frozenset()),
    PolicyRule(
        action="attendance.correct",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
    # Person-scoped summary reads use the same action with relationship facts.
    PolicyRule(action="attendance.read_student", allowed_relationships=READING_RELATIONSHIPS),
)
