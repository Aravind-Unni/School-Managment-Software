"""Authorisation decision values, owned by M01 access.

M01 specifies ``Access.authorize(ctx, action, scope_facts) -> Decision{allowed,
reason_code}``. B00 had frozen only a raising ``check()``. This module adds the
decision type additively: ``check()`` is now a thin wrapper over ``authorize()``,
so every existing call site keeps working and there is one decision path rather
than two implementations that can disagree.

Does not handle: the policy itself. M01's real implementation decides; this only
names the answers.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class ReasonCode(enum.StrEnum):
    """Why a decision came out the way it did.

    Stable and machine-readable: these appear in audit records and in denial
    telemetry, so renaming one is a contract revision. Adding a member is
    additive and safe.

    Deliberately coarse. A reason code explains the *class* of refusal without
    revealing which grant or relationship was missing, because a precise reason
    is an information leak to an actor who is already unauthorised.
    """

    ALLOWED = "ALLOWED"
    #: The resource belongs to another school. Renders 404, never 403.
    SCHOOL_MISMATCH = "SCHOOL_MISMATCH"
    #: No grant covers this action for this actor.
    NO_GRANT = "NO_GRANT"
    #: A grant exists but its validity window does not include the effective date.
    GRANT_EXPIRED = "GRANT_EXPIRED"
    #: The action requires a relationship to the subject that the actor lacks.
    RELATIONSHIP_REQUIRED = "RELATIONSHIP_REQUIRED"
    #: The action is not in the permission catalogue at all. Deny by default.
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    #: The account exists but is deactivated.
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    #: A second factor has never been asserted at this level. The remedy is to
    #: complete (or enrol) the factor.
    TWO_FACTOR_REQUIRED = "TWO_FACTOR_REQUIRED"
    #: A second factor WAS asserted but too long ago. The remedy is to re-assert.
    #: Kept distinct from TWO_FACTOR_REQUIRED because the two lead to different
    #: screens, and collapsing them told a stale user to enrol a factor they
    #: already have.
    AUTH_STEP_UP_REQUIRED = "AUTH_STEP_UP_REQUIRED"
    #: No authenticated business session at all.
    UNAUTHENTICATED = "UNAUTHENTICATED"


@dataclass(frozen=True, slots=True)
class Decision:
    """The result of one authorisation question.

    ``allowed`` and ``reason_code`` must agree: an allowed decision always
    carries ReasonCode.ALLOWED, and a denied one never does. Enforced in
    ``__post_init__`` because a decision that says both would be worse than a
    crash -- it would be logged as a denial and acted on as an approval.
    """

    allowed: bool
    reason_code: ReasonCode

    def __post_init__(self) -> None:
        """Reject a decision whose flag and reason disagree."""
        if self.allowed and self.reason_code is not ReasonCode.ALLOWED:
            raise ValueError(f"allowed decision must carry ALLOWED, got {self.reason_code}")
        if not self.allowed and self.reason_code is ReasonCode.ALLOWED:
            raise ValueError("denied decision must carry a refusal reason")

    @classmethod
    def allow(cls) -> Decision:
        """Return the single allowed decision."""
        return cls(allowed=True, reason_code=ReasonCode.ALLOWED)

    @classmethod
    def deny(cls, reason_code: ReasonCode) -> Decision:
        """Return a denial carrying its reason."""
        return cls(allowed=False, reason_code=reason_code)

    def to_wire(self) -> dict[str, object]:
        """Serialise for audit records and diagnostics.

        Never returned to a browser as-is: the HTTP layer maps a denial to the
        frozen error envelope so that reason codes stay server-side.
        """
        return {"allowed": self.allowed, "reason_code": str(self.reason_code)}


#: Reason codes that must render as 404 rather than 403, so that probing cannot
#: distinguish "exists but not yours" from "does not exist".
NOT_FOUND_REASONS: frozenset[ReasonCode] = frozenset({ReasonCode.SCHOOL_MISMATCH})

#: Reason codes that must render as 401, because the remedy is to authenticate
#: again rather than to acquire a permission.
UNAUTHENTICATED_REASONS: frozenset[ReasonCode] = frozenset(
    {
        ReasonCode.AUTH_STEP_UP_REQUIRED,
        ReasonCode.TWO_FACTOR_REQUIRED,
        ReasonCode.UNAUTHENTICATED,
    }
)
