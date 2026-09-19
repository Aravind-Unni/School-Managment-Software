"""How a module declares itself to the host.

In standalone mode exactly one registration is loaded (the target module). In
integrated mode the host wires every approved registration and binds real
ports centrally. A module never reaches into another module's registration.

Does not handle: import of the module's code. The host imports by dotted path
declared here, so an unapproved module cannot self-install by side effect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Permission codes are '<module_slug>.<verb>_<noun>', lowercase snake.
PERMISSION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
API_PREFIX_PATTERN = re.compile(r"^/api/[a-z][a-z0-9\-]*/$")
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
    consumers: tuple[str, ...] = ()
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
            raise ValueError(
                f"api_prefix must look like '/api/<slug>/': {self.api_prefix!r}"
            )
        for code in self.permission_codes:
            if not PERMISSION_CODE_PATTERN.match(code):
                raise ValueError(f"malformed permission code: {code!r}")
            if not code.startswith(f"{self.slug}."):
                raise ValueError(
                    f"permission {code!r} must be namespaced to slug {self.slug!r}"
                )
        declared = {route.required_permission for route in self.frontend_routes}
        unknown = {p for p in declared if p is not None} - set(self.permission_codes)
        if unknown:
            raise ValueError(f"routes require undeclared permissions: {sorted(unknown)}")
