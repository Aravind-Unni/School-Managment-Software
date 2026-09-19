"""M01's permission catalogue. DATA, not code branches.

The catalogue is CLOSED: an action absent from here is denied by default rather
than treated as unrestricted. Adding a row is a reviewed change, which is what
stops a new endpoint from shipping with no policy.

``requires_recent_two_factor`` marks actions sensitive enough to demand a freshly
asserted factor regardless of which role holds them, so step-up is a property of
the action rather than something each call site must remember.
"""

from __future__ import annotations

from dataclasses import dataclass

from .scopes import ScopeType


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    """One action in the catalogue."""

    code: str
    description: str
    requires_recent_two_factor: bool = False
    #: Scopes this action can meaningfully be granted at. A grant outside this set
    #: is rejected at write time, so an unenforceable grant cannot be stored.
    allowed_scopes: tuple[ScopeType, ...] = (ScopeType.SCHOOL,)


#: The permission codes M01 owns, under the prefixes auth./roles./accounts.
CATALOGUE: tuple[PermissionSpec, ...] = (
    PermissionSpec(
        code="roles.manage",
        description="Create roles and replace their grants.",
        requires_recent_two_factor=True,
        allowed_scopes=(ScopeType.SCHOOL,),
    ),
    PermissionSpec(
        code="roles.delegate",
        description=(
            "Grant a subset of one's own permissions to a role, bounded by the "
            "delegator's own scope."
        ),
        requires_recent_two_factor=True,
        allowed_scopes=(ScopeType.SCHOOL, ScopeType.SECTION, ScopeType.SUBJECT),
    ),
    PermissionSpec(
        code="accounts.manage",
        description="Create, deactivate and list accounts.",
        requires_recent_two_factor=True,
        allowed_scopes=(ScopeType.SCHOOL,),
    ),
    PermissionSpec(
        code="auth.factor.manage_self",
        description="Enrol, replace or disable one's OWN second factor.",
        requires_recent_two_factor=False,
        allowed_scopes=(ScopeType.SELF,),
    ),
    PermissionSpec(
        code="auth.factor.reset_other",
        description=(
            "Approve another account's lost-device case and reset their factor. "
            "Never usable on oneself."
        ),
        requires_recent_two_factor=True,
        allowed_scopes=(ScopeType.SCHOOL,),
    ),
)

CATALOGUE_BY_CODE: dict[str, PermissionSpec] = {spec.code: spec for spec in CATALOGUE}

#: Actions M01 exposes but which are NOT permissions: they are reachable before a
#: business session exists, so a permission check would be meaningless. Listed
#: explicitly so that "every endpoint is either public or permissioned" is
#: checkable rather than assumed.
PUBLIC_ACTIONS: frozenset[str] = frozenset(
    {
        "auth.login",
        "auth.totp_verify",
        "auth.recover",
    }
)

#: Actions any authenticated account may perform on its own account without a
#: grant. Narrow by design: reading one's own sessions and logging out.
SELF_SERVICE_ACTIONS: frozenset[str] = frozenset(
    {
        "auth.logout",
        "auth.read_own_session",
        "auth.revoke_own_session",
        "auth.request_factor_reset",
    }
)


def is_known_action(action: str) -> bool:
    """Return whether the action is in the catalogue or explicitly unpermissioned."""
    return (
        action in CATALOGUE_BY_CODE
        or action in PUBLIC_ACTIONS
        or action in SELF_SERVICE_ACTIONS
    )
