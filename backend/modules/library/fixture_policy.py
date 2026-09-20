"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="library.catalogue.manage", allowed_relationships=frozenset()),
    PolicyRule(action="library.issue", allowed_relationships=frozenset()),
    PolicyRule(action="library.return", allowed_relationships=frozenset()),
    PolicyRule(action="library.renew", allowed_relationships=frozenset()),
    PolicyRule(action="library.read_overdues", allowed_relationships=frozenset()),
    PolicyRule(
        action="library.read_own",
        allowed_relationships=frozenset(
            {Relationship.SELF, Relationship.GUARDIAN, Relationship.NONE}
        ),
    ),
)
