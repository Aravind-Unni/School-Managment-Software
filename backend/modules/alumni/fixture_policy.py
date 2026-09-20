"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from shared.fakes.access import PolicyRule

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="alumni.review", allowed_relationships=frozenset()),
    PolicyRule(action="alumni.manage", allowed_relationships=frozenset()),
    PolicyRule(action="alumni.read", allowed_relationships=frozenset()),
    PolicyRule(action="alumni.export", allowed_relationships=frozenset()),
    PolicyRule(action="alumni.contact_self", allowed_relationships=frozenset()),
)
