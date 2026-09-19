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

from contracts.decisions import Decision, ReasonCode
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
#: shapes -- school-scoped staff action, relationship-gated read, and a write
#: needing fresh 2FA -- not to model the real school's permission set, which M01
#: owns.
#:
#: An empty ``allowed_relationships`` means the rule is school-scoped and does
#: not consider the actor-subject relationship at all. That distinction matters:
#: a collection endpoint has no single subject, so a relationship-gated rule
#: would deny every list call.
POLICY_RULES: tuple[PolicyRule, ...] = (
    # Listing is school-scoped staff work: no subject, so no relationship.
    PolicyRule(
        action="demo.list_notes",
        allowed_relationships=frozenset(),
    ),
    # Reading one note: the subject, their guardian, or a teacher of their
    # section. This is the rule that makes G2 -> S1 a 403.
    PolicyRule(
        action="demo.read_note",
        allowed_relationships=frozenset(
            {
                Relationship.SELF,
                Relationship.GUARDIAN,
                Relationship.ASSIGNED_TEACHER,
                Relationship.CLASS_TEACHER,
            }
        ),
    ),
    # Writing: teachers only, and only with recently asserted 2FA. A guardian
    # who may read is deliberately still denied here.
    PolicyRule(
        action="demo.write_note",
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


def _exception_for(reason_code: ReasonCode) -> Exception:
    """Return the exception a denial reason renders as.

    SCHOOL_MISMATCH becomes 404 rather than 403, deliberately, so that probing
    cannot distinguish "exists but not yours" from "does not exist".
    """
    if reason_code is ReasonCode.SCHOOL_MISMATCH:
        return ObjectInaccessible("error.object_inaccessible")
    if reason_code is ReasonCode.TWO_FACTOR_REQUIRED:
        return StaleAuth("error.two_factor_required")
    if reason_code is ReasonCode.AUTH_STEP_UP_REQUIRED:
        return StaleAuth("error.two_factor_stale")
    return ActionDenied("error.action_denied")


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

    def authorize(
        self,
        context: RequestContext,
        action: str,
        scope_facts: ScopeFacts,
    ) -> Decision:
        """Return a Decision. The primitive; everything else derives from it.

        Evaluation order matters and is part of the contract:
          1. school mismatch  -> SCHOOL_MISMATCH  (renders 404, hides existence)
          2. unknown action   -> UNKNOWN_ACTION   (deny by default)
          3. relationship     -> RELATIONSHIP_REQUIRED
          4. auth level/age   -> AUTH_STEP_UP_REQUIRED
        Checking school first is what keeps cross-tenant probing silent.
        """
        self._failures.maybe_fail("access.check")

        if scope_facts.resource_school_id != context.school_id:
            return Decision.deny(ReasonCode.SCHOOL_MISMATCH)

        rule = self._rules.get(action)
        if rule is None:
            return Decision.deny(ReasonCode.UNKNOWN_ACTION)

        if rule.allowed_relationships:
            relationship = scope_facts.relationship or Relationship.NONE
            if relationship not in rule.allowed_relationships:
                return Decision.deny(ReasonCode.RELATIONSHIP_REQUIRED)

        if context.auth_level.rank < rule.minimum_auth_level.rank:
            # Never asserted at this level: the actor must complete or enrol a
            # factor. Distinct from having one that went stale.
            return Decision.deny(ReasonCode.TWO_FACTOR_REQUIRED)

        if rule.max_auth_age is not None:
            if self._auth_age(context) > rule.max_auth_age:
                return Decision.deny(ReasonCode.AUTH_STEP_UP_REQUIRED)

        return Decision.allow()

    def check(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> None:
        """Authorise, or raise the exception matching the decision's reason.

        A thin wrapper over ``authorize`` so the raising and non-raising paths can
        never disagree. The message keys are preserved from the B00 behaviour so
        existing consumer fixtures keep matching.
        """
        decision = self.authorize(context, action, facts)
        if decision.allowed:
            return
        raise _exception_for(decision.reason_code)

    def is_allowed(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> bool:
        """Return True when ``authorize`` allows. For navigation only."""
        return self.authorize(context, action, facts).allowed

    def require_recent_2fa(
        self,
        context: RequestContext,
        max_age_seconds: int = 300,
    ) -> None:
        """Raise StaleAuth unless 2FA was asserted within the window.

        Checks the level first: an actor who never completed a second factor needs
        to enrol, not merely to re-assert, and the message key says so.
        """
        if context.auth_level.rank < AuthLevel.TWO_FACTOR.rank:
            raise StaleAuth("error.two_factor_required")
        if self._auth_age(context) > timedelta(seconds=max_age_seconds):
            raise StaleAuth("error.two_factor_stale")

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


def stale_context(
    context: RequestContext, *, older_than: timedelta | None = None
) -> RequestContext:
    """Return a copy of ``context`` whose 2FA is deliberately too old.

    Convenience for tests asserting the 401 path. Default age is one minute
    beyond DEFAULT_STALE_AUTH_WINDOW.
    """
    from dataclasses import replace

    age = (older_than or DEFAULT_STALE_AUTH_WINDOW) + timedelta(minutes=1)
    return replace(context, auth_time=context.auth_time - age)
