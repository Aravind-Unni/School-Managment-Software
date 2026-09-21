"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from datetime import timedelta

from contracts.identity import AuthLevel
from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

RECENT_TWO_FACTOR_WINDOW = timedelta(seconds=300)

READ_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="files.upload", allowed_relationships=frozenset()),
    PolicyRule(action="files.review_quality", allowed_relationships=frozenset()),
    PolicyRule(action="files.read", allowed_relationships=READ_RELATIONSHIPS),
    PolicyRule(
        action="files.retention.manage",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
)
