"""How a module declares itself to the host.

In standalone mode exactly one registration is loaded (the target module). In
integrated mode the host wires every approved registration and binds real
ports centrally. A module never reaches into another module's registration.

Does not handle: import of the module's code. The host imports by dotted path
declared here, so an unapproved module cannot self-install by side effect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Permission codes are dotted, lowercase snake, with TWO OR MORE segments:
#: 'demo.list_notes', 'roles.manage', 'auth.factor.manage_self'.
#:
#: B00 originally required exactly two segments and forced every code to begin
#: with the module slug. M01's real permission vocabulary is neither -- its codes
#: are 'roles.manage' and 'auth.factor.manage_self' -- so the rule was relaxed to
#: allow multi-segment codes, and ownership is now expressed by declared PREFIXES
#: instead. The property that actually mattered is preserved: a module can only
#: declare codes under a prefix it owns, so it still cannot grant itself another
#: module's permission.
PERMISSION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
#: A permission prefix is a code root ending in a dot: 'auth.', 'roles.'.
PERMISSION_PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.$")
#: Either a per-module root ('/api/demo/') or a shared version root ('/api/v1/').
API_PREFIX_PATTERN = re.compile(r"^/api/[a-z][a-z0-9\-]*/$")
#: A path root a module owns beneath a shared version prefix: 'auth/', 'roles/'.
API_PATH_ROOT_PATTERN = re.compile(r"^[a-z][a-z0-9\-]*/$")
#: Prefixes that are a shared version root rather than a per-module namespace.
#: A module mounting here MUST declare which path roots it owns, so the host can
#: detect two modules claiming the same one.
SHARED_API_PREFIXES: frozenset[str] = frozenset({"/api/v1/"})
MODULE_ID_PATTERN = re.compile(r"^M(?:0[0-9]|1[0-4])$")


@dataclass(frozen=True, slots=True)
class FrontendRoute:
    """One React route owned by the module, with its navigation metadata.

    Navigation metadata lives beside the feature rather than in a central menu
    file, so deleting a feature directory cannot leave a dangling menu entry.
    """

    path: str
    component: str
    nav_label_key: str | None = None
    required_permission: str | None = None


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    """A periodic job the module owns.

    ``cron`` is interpreted in SCHOOL_TIMEZONE, because "run at 18:00 after
    school" means school time, not UTC.
    """

    name: str
    cron: str
    task_path: str


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """A named readiness probe the module contributes to /healthz."""

    name: str
    callable_path: str


@dataclass(frozen=True, slots=True)
class ModuleRegistration:
    """The complete, immutable declaration of one module.

    ``consumers`` names the service ports this module *requires* from others.
    In standalone mode each is bound to a deterministic fake; in integrated mode
    to the real provider. Declaring a consumer it does not use, or using one it
    did not declare, both fail the architecture check.

    Does not handle: version negotiation. A module binds whatever revision the
    manifest froze; a mismatch is a contract revision, not a runtime fallback.
    """

    id: str
    slug: str
    api_prefix: str
    frontend_routes: tuple[FrontendRoute, ...] = ()
    permission_codes: tuple[str, ...] = ()
    #: Code roots this module owns, e.g. ('auth.', 'roles.'). Empty means the
    #: module owns only '<slug>.', which is the B00 default and keeps every
    #: existing registration valid unchanged.
    permission_prefixes: tuple[str, ...] = ()
    #: Path roots this module owns beneath a shared api_prefix, e.g. ('auth/',).
    #: Required when api_prefix is a shared version root; must be empty otherwise.
    api_path_roots: tuple[str, ...] = ()
    consumers: tuple[str, ...] = ()
    #: Dotted middleware paths this module contributes, in order, installed BEFORE
    #: the shared request-context middleware. Needed by a module that owns
    #: authentication (M01): without it the shared middleware would reject the very
    #: login endpoints that create a session.
    middleware: tuple[str, ...] = ()
    #: Paths under ``api_prefix`` reachable with NO session at all, e.g. login.
    #: Declared rather than inferred, so "which endpoints are unauthenticated" is
    #: reviewable in one place instead of scattered across views.
    public_paths: tuple[str, ...] = ()
    scheduled_jobs: tuple[ScheduledJob, ...] = ()
    migration_dependencies: tuple[str, ...] = ()
    health_checks: tuple[HealthCheck, ...] = ()
    django_app: str = ""

    def __post_init__(self) -> None:
        """Validate the declaration shape at import time.

        Failing here rather than at first request means a malformed
        registration cannot reach a running server.
        """
        if not MODULE_ID_PATTERN.match(self.id):
            raise ValueError(f"module id must be M00..M14: {self.id!r}")
        if not API_PREFIX_PATTERN.match(self.api_prefix):
            raise ValueError(f"api_prefix must look like '/api/<slug>/': {self.api_prefix!r}")
        owned = self.owned_permission_prefixes
        for prefix in self.permission_prefixes:
            if not PERMISSION_PREFIX_PATTERN.match(prefix):
                raise ValueError(
                    f"malformed permission prefix {prefix!r}; it must be dotted "
                    "and end in a dot, e.g. 'auth.'"
                )
        for code in self.permission_codes:
            if not PERMISSION_CODE_PATTERN.match(code):
                raise ValueError(f"malformed permission code: {code!r}")
            if not any(code.startswith(prefix) for prefix in owned):
                raise ValueError(
                    f"permission {code!r} is outside this module's owned prefixes "
                    f"{sorted(owned)}; declare the prefix or rename the code"
                )

        if self.api_prefix in SHARED_API_PREFIXES:
            if not self.api_path_roots:
                raise ValueError(
                    f"api_prefix {self.api_prefix!r} is a shared version root, so "
                    "api_path_roots must declare which paths this module owns; "
                    "otherwise two modules silently collide in the URLconf"
                )
        elif self.api_path_roots:
            raise ValueError(
                f"api_path_roots is only meaningful under a shared api_prefix; "
                f"{self.api_prefix!r} is already module-specific"
            )
        for root in self.api_path_roots:
            if not API_PATH_ROOT_PATTERN.match(root):
                raise ValueError(f"malformed api path root {root!r}; expected e.g. 'auth/'")
        declared = {route.required_permission for route in self.frontend_routes}
        unknown = {p for p in declared if p is not None} - set(self.permission_codes)
        if unknown:
            raise ValueError(f"routes require undeclared permissions: {sorted(unknown)}")

    @property
    def absolute_public_paths(self) -> tuple[str, ...]:
        """Return this module's public paths as absolute URL prefixes."""
        return tuple(f"{self.api_prefix}{path.lstrip('/')}" for path in self.public_paths)

    @property
    def owned_permission_prefixes(self) -> frozenset[str]:
        """Return the code roots this module may declare codes under.

        Defaults to ``'<slug>.'`` so every registration written against B00
        remains valid without change.
        """
        return frozenset(self.permission_prefixes or (f"{self.slug}.",))


def assert_no_registration_collisions(
    registrations: tuple[ModuleRegistration, ...],
) -> None:
    """Fail when two modules claim the same permission prefix or API path root.

    Called by the host before mounting in integrated mode. Two modules sharing a
    path root would have one silently shadow the other in the URLconf; two sharing
    a permission prefix would let either grant the other's permissions. Both are
    the kind of fault that surfaces months later as a privilege bug, so the host
    refuses to start.

    Does not handle: ordering. Mount order is the host's concern, not a conflict.
    """
    seen_prefix: dict[str, str] = {}
    seen_root: dict[str, str] = {}
    problems: list[str] = []

    for registration in registrations:
        for prefix in sorted(registration.owned_permission_prefixes):
            owner = seen_prefix.get(prefix)
            if owner is not None and owner != registration.id:
                problems.append(
                    f"permission prefix {prefix!r} claimed by both {owner} and "
                    f"{registration.id}"
                )
            seen_prefix[prefix] = owner or registration.id
        for root in registration.api_path_roots:
            key = f"{registration.api_prefix}{root}"
            owner = seen_root.get(key)
            if owner is not None and owner != registration.id:
                problems.append(
                    f"API path {key!r} claimed by both {owner} and {registration.id}"
                )
            seen_root[key] = owner or registration.id

    if problems:
        raise ValueError("registration collisions: " + "; ".join(problems))
