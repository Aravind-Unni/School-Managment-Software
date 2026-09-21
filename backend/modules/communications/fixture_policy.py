"""Fixture Access grants for standalone/test profiles. Not a production policy."""

from __future__ import annotations

from shared.fakes.access import PolicyRule

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="notices.create", allowed_relationships=frozenset()),
    PolicyRule(action="notices.publish", allowed_relationships=frozenset()),
    PolicyRule(action="messages.send", allowed_relationships=frozenset()),
    PolicyRule(action="messages.read_status", allowed_relationships=frozenset()),
    PolicyRule(action="sms.configure", allowed_relationships=frozenset()),
)
