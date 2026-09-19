"""The real Access implementation. M01 provides this; it consumes no Access port.

Satisfies ``contracts.ports.AccessPort``. ``authorize`` is the primitive and
``check`` derives from it, so the raising and non-raising paths cannot disagree.

Two rules this file exists to keep:
  * It reads ONLY M01's own tables. It never touches a consumer module's ORM, and
    it never calls Registry -- the host scope resolver has already done that and
    folded the answer into ScopeFacts. That is what prevents a recursive
    Access -> Registry -> Access call.
  * It caches nothing. Every call reads current grants, so a grant change takes
    effect on the next request rather than when some cache expires.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q

from contracts.decisions import Decision, ReasonCode
from contracts.errors import ActionDenied, ObjectInaccessible, StaleAuth
from contracts.identity import AuthLevel, RequestContext
from contracts.scope import ScopeFacts
from contracts.values import school_date

from ..models.accounts import AuthLevelChoices
from ..scopes import ScopeType
from .policy import ActorFacts, GrantFact, evaluate

#: Default freshness window for a step-up check, as proposed by M01.
DEFAULT_STEP_UP_WINDOW_SECONDS = 300


class AccessService:
    """Authorisation over M01's own tables.

    Holds a ClockPort so that freshness checks are testable without sleeping.
    """

    def __init__(self, *, clock) -> None:
        """Store the injected clock."""
        self._clock = clock

    # --- the primitive -----------------------------------------------------

    def authorize(
        self,
        context: RequestContext,
        action: str,
        scope_facts: ScopeFacts,
    ) -> Decision:
        """Return a Decision for one action. Never raises for a policy outcome.

        Loads the actor and their grants, then delegates to the pure ``evaluate``.
        Two queries at most, and no caching, so a grant change is visible on the
        very next call.
        """
        actor = self._load_actor(context)
        if actor is None:
            # The session names an account that does not exist in this school.
            # Reported as a school mismatch so it renders 404 rather than telling
            # a caller that an account id is valid elsewhere.
            return Decision.deny(ReasonCode.SCHOOL_MISMATCH)

        effective_date = scope_facts.effective_date or school_date(self._clock.now())
        grants = self._load_grants(actor, action)
        return evaluate(
            actor=actor,
            action=action,
            facts=scope_facts,
            grants=grants,
            effective_date=effective_date,
        )

    # --- derived conveniences ---------------------------------------------

    def check(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> None:
        """Authorise or raise. A thin wrapper over ``authorize``."""
        decision = self.authorize(context, action, facts)
        if decision.allowed:
            return
        raise exception_for(decision.reason_code)

    def is_allowed(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> bool:
        """Return whether the action is permitted. For navigation only."""
        return self.authorize(context, action, facts).allowed

    def require_recent_2fa(
        self,
        context: RequestContext,
        max_age_seconds: int = DEFAULT_STEP_UP_WINDOW_SECONDS,
    ) -> None:
        """Return None if the second factor is fresh enough, else raise StaleAuth.

        Checks the level before the age: an actor who never completed a factor
        needs to enrol, and telling them to "re-confirm" a factor they do not have
        is a dead end. A recovery-level session never satisfies this, because a
        recovery session exists only to re-enrol a factor.
        """
        if context.auth_level is not AuthLevel.TWO_FACTOR:
            raise StaleAuth("error.two_factor_required")
        age = self._clock.now() - context.auth_time
        if age > timedelta(seconds=max_age_seconds):
            raise StaleAuth("error.two_factor_stale")

    def require_action(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> None:
        """Authorise an action AND enforce its step-up requirement.

        The order matters: step-up is demanded only AFTER the action is otherwise
        permitted. Prompting an unauthorised actor to re-confirm their factor would
        tell them the action exists and that they nearly have it.
        """
        self.check(context, action, facts)
        from .policy import action_requires_recent_two_factor

        if action_requires_recent_two_factor(action):
            self.require_recent_2fa(context)

    # --- loading -----------------------------------------------------------

    def held_grants(self, context: RequestContext) -> tuple[GrantFact, ...]:
        """Return EVERY grant the actor holds, direct and via roles.

        Used by the escalation check, which must compare a requested grant against
        the actor's whole permission set rather than one action at a time. Kept
        separate from the per-action loader in ``authorize`` because that path must
        stay narrow: answering one question should not pull an actor's entire
        permission set.
        """
        from ..models import Grant

        actor = self._load_actor(context)
        if actor is None:
            return ()
        rows = (
            Grant.objects.filter(school_id=actor.school_id)
            .filter(Q(user_id=actor.user_id) | Q(role__user_links__user_id=actor.user_id))
            .values("action", "scope_type", "scope_id", "valid_from", "valid_to")
            .distinct()
        )
        return tuple(
            GrantFact(
                action=row["action"],
                scope_type=ScopeType(row["scope_type"]),
                scope_id=row["scope_id"],
                valid_from=row["valid_from"],
                valid_to=row["valid_to"],
            )
            for row in rows
        )

    def _load_actor(self, context: RequestContext) -> ActorFacts | None:
        """Return the acting account's policy facts, or None if absent.

        Filters by BOTH id and school, so a session naming an account in another
        school resolves to None rather than to that account.
        """
        from ..models import User

        row = (
            User.objects.filter(id=context.actor_id, school_id=context.school_id)
            .values("id", "school_id", "active", "person_id")
            .first()
        )
        if row is None:
            return None
        return ActorFacts(
            user_id=row["id"],
            school_id=row["school_id"],
            active=row["active"],
            person_id=row["person_id"],
        )

    def _load_grants(self, actor: ActorFacts, action: str) -> tuple[GrantFact, ...]:
        """Return the actor's grants for one action, direct and via roles.

        Filtered by action in SQL rather than in Python: an account in a
        many-role school should not pull its whole permission set to answer one
        question.
        """
        from ..models import Grant

        rows = (
            Grant.objects.filter(school_id=actor.school_id, action=action)
            .filter(Q(user_id=actor.user_id) | Q(role__user_links__user_id=actor.user_id))
            .values("action", "scope_type", "scope_id", "valid_from", "valid_to")
            .distinct()
        )
        return tuple(
            GrantFact(
                action=row["action"],
                scope_type=ScopeType(row["scope_type"]),
                scope_id=row["scope_id"],
                valid_from=row["valid_from"],
                valid_to=row["valid_to"],
            )
            for row in rows
        )


def exception_for(reason_code: ReasonCode) -> Exception:
    """Map a denial reason to the exception it renders as.

    SCHOOL_MISMATCH becomes 404, never 403, so probing cannot distinguish "exists
    but not yours" from "does not exist". Every other denial collapses to one
    message key, because a precise reason tells an unauthorised actor what to
    acquire; the precise ReasonCode goes to the audit row instead.
    """
    if reason_code is ReasonCode.SCHOOL_MISMATCH:
        return ObjectInaccessible("error.object_inaccessible")
    if reason_code is ReasonCode.TWO_FACTOR_REQUIRED:
        return StaleAuth("error.two_factor_required")
    if reason_code is ReasonCode.AUTH_STEP_UP_REQUIRED:
        return StaleAuth("error.two_factor_stale")
    return ActionDenied("error.action_denied")


def auth_level_from_session(stored: str) -> AuthLevel:
    """Map a stored session auth level to the shared AuthLevel.

    A RECOVERY session maps to PASSWORD, deliberately: it must never satisfy a
    two-factor requirement, and mapping it to TWO_FACTOR would let a recovery
    session perform sensitive writes.
    """
    if stored == AuthLevelChoices.PASSWORD_TOTP:
        return AuthLevel.TWO_FACTOR
    return AuthLevel.PASSWORD


def is_recovery_session(stored: str) -> bool:
    """Return whether a stored level is a recovery session."""
    return stored == AuthLevelChoices.RECOVERY
