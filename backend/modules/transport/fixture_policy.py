"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from shared.fakes.access import PolicyRule

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="transport.manage", allowed_relationships=frozenset()),
    PolicyRule(action="transport.read", allowed_relationships=frozenset()),
    PolicyRule(action="transport.bill", allowed_relationships=frozenset()),
)
