"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from datetime import timedelta

from contracts.identity import AuthLevel
from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

RECENT_TWO_FACTOR_WINDOW = timedelta(seconds=300)

STATEMENT_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="fees.configure", allowed_relationships=frozenset()),
    PolicyRule(action="fees.read", allowed_relationships=frozenset()),
    PolicyRule(action="fees.record_payment", allowed_relationships=frozenset()),
    PolicyRule(action="fees.concede", allowed_relationships=frozenset()),
    PolicyRule(
        action="fees.reverse_payment",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
    PolicyRule(
        action="fees.refund",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=RECENT_TWO_FACTOR_WINDOW,
    ),
)
