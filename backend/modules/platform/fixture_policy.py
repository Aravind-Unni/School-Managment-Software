"""Fixture Access grants for standalone/test. Not production policy.

Company-ops identity for restore rehearsals is enforced in services after
Access grants ``backups.manage`` — FakeAccess cannot encode ops vs school role.
"""

from __future__ import annotations

from datetime import timedelta

from contracts.identity import AuthLevel
from shared.fakes.access import PolicyRule

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="platform.read_health", allowed_relationships=frozenset()),
    PolicyRule(action="jobs.read", allowed_relationships=frozenset()),
    PolicyRule(action="jobs.retry", allowed_relationships=frozenset()),
    PolicyRule(action="audit.read", allowed_relationships=frozenset()),
    PolicyRule(
        action="backups.manage",
        allowed_relationships=frozenset(),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=timedelta(minutes=5),
    ),
)
