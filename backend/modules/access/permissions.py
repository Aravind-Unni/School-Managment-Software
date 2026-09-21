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


#: Module actions costly enough to misuse that they demand a freshly asserted
#: second factor, whichever role holds them. Only enforced where the caller uses
#: ``require_action``; modules with their own step-up keep it.
SENSITIVE_MODULE_ACTIONS: frozenset[str] = frozenset(
    {
        "fees.refund",
        "fees.reverse_payment",
        "results.reopen",
        "year.close",
        "backups.manage",
    }
)

#: Every scope kind; a module action may be granted school-wide, to one section
#: or subject, or to the grantee's own records (guardian/student self-service).
MODULE_ACTION_SCOPES: tuple[ScopeType, ...] = (
    ScopeType.SCHOOL,
    ScopeType.SECTION,
    ScopeType.SUBJECT,
    ScopeType.SELF,
)


def installed_module_actions() -> frozenset[str]:
    """Return the permission codes declared by every business module installed.

    The host settings collect them from each approved ModuleRegistration into
    ``SCHOOL_MODULE_PERMISSION_CODES``, so M01 never imports another module.
    Assumes nothing about Django being configured: with no settings (the
    contract suite, arch_check) the answer is empty, i.e. deny by default.
    Does not handle: modules added at runtime; the set is fixed per process.
    """
    from django.conf import settings

    if not settings.configured:
        return frozenset()
    return frozenset(getattr(settings, "SCHOOL_MODULE_PERMISSION_CODES", ()))


def lookup_permission(action: str) -> PermissionSpec | None:
    """Return the spec for an M01 action or an installed module action, or None.

    Module actions have no hand-written spec; they get one derived here with
    every scope allowed and step-up only for SENSITIVE_MODULE_ACTIONS.
    Does not handle: public or self-service actions, which are not grantable.
    """
    spec = CATALOGUE_BY_CODE.get(action)
    if spec is not None:
        return spec
    if action in installed_module_actions():
        return PermissionSpec(
            code=action,
            description=f"Module action {action}.",
            requires_recent_two_factor=action in SENSITIVE_MODULE_ACTIONS,
            allowed_scopes=MODULE_ACTION_SCOPES,
        )
    return None


def full_catalogue() -> tuple[PermissionSpec, ...]:
    """Return M01's catalogue followed by every installed module action, sorted.

    What the owner is granted at install and what a role editor may offer.
    Does not handle: filtering by what a particular actor may delegate.
    """
    module_specs = tuple(
        spec
        for spec in (lookup_permission(code) for code in sorted(installed_module_actions()))
        if spec is not None and spec.code not in CATALOGUE_BY_CODE
    )
    return CATALOGUE + module_specs


def is_known_action(action: str) -> bool:
    """Return whether the action is grantable here or explicitly unpermissioned."""
    return (
        lookup_permission(action) is not None
        or action in PUBLIC_ACTIONS
        or action in SELF_SERVICE_ACTIONS
    )
