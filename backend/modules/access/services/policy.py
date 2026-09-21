"""Pure authorisation logic. No database, no clock, no Django.

Separated from ``services/authorize.py`` so the rules can be tested exhaustively
without a database, and so it is obvious by construction that a policy decision
cannot reach into a consumer module's ORM.

The rule M01 is built on: authorise by ACTION and EFFECTIVE RELATIONSHIP, never by
role rank. There is no notion of one role outranking another, so a "senior" role
cannot acquire a permission it was not granted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.decisions import Decision, ReasonCode
from contracts.scope import Relationship, ScopeFacts

from ..permissions import SELF_SERVICE_ACTIONS, is_known_action, lookup_permission
from ..scopes import ScopeType


@dataclass(frozen=True, slots=True)
class GrantFact:
    """One grant, flattened for pure evaluation.

    A plain value object rather than an ORM row, so the rules below can be tested
    with literals and cannot accidentally trigger a query.
    """

    action: str
    scope_type: ScopeType
    scope_id: UUID | None
    valid_from: date
    valid_to: date | None

    def is_in_force(self, effective_date: date) -> bool:
        """Return whether this grant is active on a school-local date.

        Both bounds inclusive, matching how a school states a delegation ("from 1
        June to 31 March"). An expired grant does not authorise, which is how a
        temporary delegation lapses without anyone remembering to remove it.
        """
        if effective_date < self.valid_from:
            return False
        return self.valid_to is None or effective_date <= self.valid_to


@dataclass(frozen=True, slots=True)
class ActorFacts:
    """Who is asking, as far as policy is concerned.

    ``person_id`` is the Registry person this account acts as, when it has one. It
    is what makes a SELF-scoped grant meaningful: the account acts on its own
    records, identified as a person rather than as a login.
    """

    user_id: UUID
    school_id: UUID
    active: bool
    person_id: UUID | None = None


#: Relationships that count as "acting on one's own records" for a SELF grant.
SELF_RELATIONSHIPS: frozenset[Relationship] = frozenset(
    {Relationship.SELF, Relationship.GUARDIAN}
)


def evaluate(
    *,
    actor: ActorFacts,
    action: str,
    facts: ScopeFacts,
    grants: tuple[GrantFact, ...],
    effective_date: date,
) -> Decision:
    """Decide whether an action is permitted. Pure.

    Order is part of the contract and deliberately puts the tenant check first:

      1. school mismatch  -> SCHOOL_MISMATCH   (renders 404, hides existence)
      2. inactive account -> ACCOUNT_INACTIVE
      3. unknown action   -> UNKNOWN_ACTION    (deny by default)
      4. self-service     -> allowed on one's own account only
      5. a grant in force whose scope covers the resource -> allowed
      6. otherwise        -> NO_GRANT, or GRANT_EXPIRED when the only candidate
                             grants were outside their validity window (which
                             covers not-yet-valid as well as lapsed)

    Distinguishing NO_GRANT from GRANT_EXPIRED matters for the audit trail: an
    expired delegation looks like a misconfiguration, a missing one looks like an
    attempt. Neither reaches the client, which sees one message key.
    """
    if facts.resource_school_id != actor.school_id:
        return Decision.deny(ReasonCode.SCHOOL_MISMATCH)

    if not actor.active:
        return Decision.deny(ReasonCode.ACCOUNT_INACTIVE)

    if not is_known_action(action):
        return Decision.deny(ReasonCode.UNKNOWN_ACTION)

    if action in SELF_SERVICE_ACTIONS:
        return _evaluate_self_service(actor, facts)

    candidates = tuple(grant for grant in grants if grant.action == action)
    if not candidates:
        return Decision.deny(ReasonCode.NO_GRANT)

    in_force = tuple(grant for grant in candidates if grant.is_in_force(effective_date))
    if not in_force:
        return Decision.deny(ReasonCode.GRANT_EXPIRED)

    for grant in in_force:
        if _scope_covers(grant, actor=actor, facts=facts):
            return Decision.allow()

    # A grant exists and is current, but its scope does not reach this resource.
    # Reported as a relationship requirement because that is what the actor is
    # missing: a link to this section, subject or person.
    return Decision.deny(ReasonCode.RELATIONSHIP_REQUIRED)


def _evaluate_self_service(actor: ActorFacts, facts: ScopeFacts) -> Decision:
    """Allow a self-service action only on the actor's own account."""
    subject = facts.subject_person_id
    if subject is None or subject in {actor.user_id, actor.person_id}:
        return Decision.allow()
    return Decision.deny(ReasonCode.RELATIONSHIP_REQUIRED)


def _scope_covers(grant: GrantFact, *, actor: ActorFacts, facts: ScopeFacts) -> bool:
    """Return whether a grant's scope reaches the resource described by ``facts``.

    Assumes the school has already matched. Each scope kind is checked explicitly
    rather than by a general rule, because a general rule here is exactly where an
    over-broad match would hide.
    """
    if grant.scope_type is ScopeType.SCHOOL:
        return True

    if grant.scope_type is ScopeType.SECTION:
        # ScopeFacts describes the ONE resource being acted on, so the grant must
        # name that resource's section. It deliberately does not consider every
        # section the actor happens to cover: that would let a grant for section C1
        # authorise an action on section C2 merely because the actor teaches both.
        return grant.scope_id is not None and grant.scope_id == facts.section_id

    if grant.scope_type is ScopeType.SUBJECT:
        return grant.scope_id is not None and grant.scope_id == facts.subject_id

    if grant.scope_type is ScopeType.SELF:
        subject = facts.subject_person_id
        if subject is None:
            return False
        if subject in {actor.user_id, actor.person_id}:
            return True
        # A guardian acting for their own child is still "self" scope, but only
        # when Registry actually reported that relationship. The relationship is
        # never taken from the client.
        return facts.relationship in SELF_RELATIONSHIPS

    return False


def action_requires_recent_two_factor(action: str) -> bool:
    """Return whether the catalogue marks this action as needing fresh 2FA.

    A property of the ACTION, so a call site cannot forget to demand step-up on a
    sensitive write.
    """
    spec = lookup_permission(action)
    return spec is not None and spec.requires_recent_two_factor
