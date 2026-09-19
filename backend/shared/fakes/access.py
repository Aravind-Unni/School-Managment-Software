"""Deterministic fake Access adapter. Used by every module except M01.

This is NOT allow_all. It evaluates an explicit policy table against the
action, the school and the actor-to-subject relationship carried in ScopeFacts,
and it denies anything the table does not name. It also simulates stale 2FA so
that modules are forced to handle a 401 on sensitive writes during development
rather than discovering it when real Access lands.

The policy table is DATA (POLICY_RULES). Adding a rule means adding a row, not
adding a branch.

Does not handle: real authentication, sessions, TOTP or recovery. Those are
M01's real implementation. A module using this fake leaves real
authentication/2FA integration explicitly pending -- see docs/foundation/handoff.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible, StaleAuth
from contracts.identity import AuthLevel, RequestContext
from contracts.scope import Relationship, ScopeFacts

from .failures import FailureInjector


@dataclass(frozen=True, slots=True)
class PolicyRule:
    """One allow rule. Absence of a matching rule means deny.

    ``allowed_relationships`` empty means the rule does not care about the
    relationship (a staff-wide action). ``max_auth_age`` None means the action
    has no freshness requirement.
    """

    action: str
    allowed_relationships: frozenset[Relationship]
    minimum_auth_level: AuthLevel = AuthLevel.PASSWORD
    max_auth_age: timedelta | None = None


#: The fake's entire policy. Deliberately small: it exists to exercise the
#: shapes (self / guardian / assigned teacher / staff, fresh vs stale 2FA), not
#: to model the real school's permission set, which M01 owns.
POLICY_RULES: tuple[PolicyRule, ...] = (
    # A person, or their guardian, may read that person's own records.
    PolicyRule(
        action="demo.read_own_note",
        allowed_relationships=frozenset({Relationship.SELF, Relationship.GUARDIAN}),
    ),
    # An assigned teacher may read notes for a section they teach.
    PolicyRule(
        action="demo.read_section_note",
        allowed_relationships=frozenset(
            {Relationship.ASSIGNED_TEACHER, Relationship.CLASS_TEACHER}
        ),
    ),
    # Writing requires an assigned teacher AND recently asserted 2FA.
    PolicyRule(
        action="demo.write_section_note",
        allowed_relationships=frozenset(
            {Relationship.ASSIGNED_TEACHER, Relationship.CLASS_TEACHER}
        ),
        minimum_auth_level=AuthLevel.TWO_FACTOR,
        max_auth_age=timedelta(minutes=15),
    ),
)

#: Actions the fake treats as sensitive enough to always demand fresh 2FA,
#: regardless of rule, so that a module cannot accidentally ship a write path
#: that never saw a StaleAuth in development.
DEFAULT_STALE_AUTH_WINDOW = timedelta(minutes=15)


class FakeAccess:
    """Policy-table Access adapter satisfying AccessPort.

    Deny-by-default: ``check`` raises ActionDenied for any action absent from
    POLICY_RULES. Cross-school access raises ObjectInaccessible (404), never
    ActionDenied (403), so that probing cannot distinguish the two.
    """

    def __init__(
        self,
        *,
        extra_rules: tuple[PolicyRule, ...] = (),
        failures: FailureInjector | None = None,
    ) -> None:
        """Build the adapter.

        ``extra_rules`` lets a module's own test suite declare its actions
        without editing this shared file. Rules are matched by exact action
        name; a duplicate action raises rather than silently shadowing.
        """
        rules = POLICY_RULES + extra_rules
        table: dict[str, PolicyRule] = {}
        for rule in rules:
            if rule.action in table:
                raise ValueError(f"duplicate policy rule for action {rule.action!r}")
            table[rule.action] = rule
        self._rules = table
        self._failures = failures or FailureInjector()

    def check(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> None:
        """Authorise, or raise ObjectInaccessible / ActionDenied / StaleAuth.

        Order matters and is part of the contract:
          1. school mismatch  -> 404 (do not reveal existence)
          2. unknown action   -> 403 (deny by default)
          3. relationship     -> 403
          4. auth level/age   -> 401
        Checking school first is what keeps cross-tenant probing silent.
        """
        self._failures.maybe_fail("access.check")

        if facts.resource_school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        rule = self._rules.get(action)
        if rule is None:
            raise ActionDenied("error.action_denied")

        if rule.allowed_relationships:
            relationship = facts.relationship or Relationship.NONE
            if relationship not in rule.allowed_relationships:
                raise ActionDenied("error.action_denied")

        if context.auth_level.rank < rule.minimum_auth_level.rank:
            raise StaleAuth("error.two_factor_required")

        if rule.max_auth_age is not None:
            age = self._auth_age(context)
            if age > rule.max_auth_age:
                raise StaleAuth("error.two_factor_stale")

    def is_allowed(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> bool:
        """Return True when ``check`` would pass. For navigation only."""
        try:
            self.check(context, action, facts)
        except (ActionDenied, ObjectInaccessible, StaleAuth):
            return False
        return True

    def _auth_age(self, context: RequestContext) -> timedelta:
        """Return how long ago 2FA was asserted, per the injected clock.

        Assumes the caller's RequestContext.auth_time is UTC-aware, which
        RequestContext enforces at construction.
        """
        return self._now() - context.auth_time

    def _now(self):
        """Return current time.

        Overridden in tests by assigning ``adapter._now = clock.now`` so that
        stale-2FA behaviour is reproducible without waiting.
        """
        from contracts.values import now_utc

        return now_utc()


def stale_context(context: RequestContext, *, older_than: timedelta | None = None) -> RequestContext:
    """Return a copy of ``context`` whose 2FA is deliberately too old.

    Convenience for tests asserting the 401 path. Default age is one minute
    beyond DEFAULT_STALE_AUTH_WINDOW.
    """
    from dataclasses import replace

    age = (older_than or DEFAULT_STALE_AUTH_WINDOW) + timedelta(minutes=1)
    return replace(context, auth_time=context.auth_time - age)
