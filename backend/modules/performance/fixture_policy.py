"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

READING_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="performance.read", allowed_relationships=READING_RELATIONSHIPS),
    PolicyRule(action="warnings.manage", allowed_relationships=frozenset()),
    PolicyRule(action="interventions.manage", allowed_relationships=frozenset()),
    PolicyRule(action="meetings.record", allowed_relationships=frozenset()),
    PolicyRule(action="observations.read_sensitive", allowed_relationships=frozenset()),
)
