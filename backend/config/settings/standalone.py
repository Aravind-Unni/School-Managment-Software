"""Standalone profile: exactly one business app, harness, deterministic fakes.

What makes this profile standalone, and what the architecture check verifies:
  * INSTALLED_APPS contains the target module and NO other business module.
  * Every dependency port is bound to a deterministic fake, never to another
    module's real provider.
  * The module's real migrations run against its own isolated PostgreSQL
    database, named per developer/worktree/module.
  * The module's real REST API and React routes are served.

Real authentication and 2FA remain explicitly pending: this profile derives a
fixed synthetic persona server-side, on loopback only.
"""

from __future__ import annotations

from config import env
from config.settings.base import *
from config.settings.base import (
    HARNESS_APPS,
    INSTALLED_APPS,
    MODULE_ID,
    SCHOOL_CLOCK,
)
from contracts.registration import ModuleRegistration
from shared import fixtures
from shared.http.context import DevPersona
from shared.module_catalog import address_for
from shared.ports import PortRegistry, build_fake_registry

APP_ENV = "standalone"

#: The single module this process serves.
MODULE_ADDRESS = address_for(MODULE_ID)

INSTALLED_APPS = INSTALLED_APPS + HARNESS_APPS + [MODULE_ADDRESS.django_app]

DATABASES = {"default": env.parse_database_url(env.require("DATABASE_URL")).as_django()}

SCHOOL_ID = env.optional("SCHOOL_ID") or str(fixtures.SCHOOL_A)

#: Development persona: chosen here, server-side. The browser cannot select it.
#: Defaults to T1, class teacher of C1, so a developer opening the demo page
#: can list, read and write. Authorisation tests build their own contexts for
#: S1/G1/G2/T1/T2 rather than relying on this persona.
#: M01 owns real login, sessions and 2FA, so it must NOT get a synthetic
#: persona -- one would bypass the flow under test. Every other module uses it.
DEV_PERSONA = (
    None
    if MODULE_ID == "M01"
    else DevPersona(actor_id=fixtures.TEACHER_T1, school_id=fixtures.SCHOOL_A)
)
DEV_PERSONA_MODE = "off" if MODULE_ID == "M01" else env.optional("DEV_PERSONA_MODE", "fixed")

#: Peer networks, beyond loopback, from which the fixed persona is accepted.
#: EMPTY unless the runner sets it. The containerised stack sets it because it
#: publishes the API to 127.0.0.1 ONLY and Docker then NATs the connection, so
#: the peer the container sees is the bridge gateway rather than loopback --
#: which refused every browser request with 401. See
#: shared/http/context.is_trusted_persona_peer for the full reasoning.
#:
#: A developer running the API directly on the host sets nothing and keeps
#: loopback-only. Production never reaches this code: the persona branch refuses
#: APP_ENV=production outright, and PortRegistry.assert_production_safe refuses
#: to start with DEV_PERSONA_MODE set at all.
DEV_PERSONA_TRUSTED_NETWORKS = tuple(
    network.strip()
    for network in (env.optional("DEV_PERSONA_TRUSTED_NETWORKS", "") or "").split(",")
    if network.strip()
)

#: Fernet key for TOTP seeds at rest. Held OUTSIDE the database. dev.py generates
#: one into dev/secrets/ and passes it in; there is no default, because a default
#: would mean every developer's seeds were encrypted with the same known key.
TOTP_ENCRYPTION_KEY = env.optional("TOTP_ENCRYPTION_KEY")

#: Demo fixtures are the placeholder module's seed data, allowed here only.
DEMO_FIXTURES_ENABLED = env.flag("DEMO_FIXTURES_ENABLED", default=True)

#: True only when Compose actually started a broker and worker for this module.
#: Defaults False so that asynchronous assertions fail honestly by default.
WORKER_AVAILABLE = env.flag("WORKER_AVAILABLE", default=False)

CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://(localhost|127\.0\.0\.1):\d+$"]


def build_port_registry(registration: ModuleRegistration | None) -> PortRegistry:
    """Bind dependency ports; M14 overrides platform with its real adapter.

    Delegates to shared.ports.build_fake_registry so the standalone runner and
    the local test profile bind ports identically. A module that declares a
    consumer it never uses, or uses one it never declared, fails at boot.

    Does not handle: real providers for unfinished modules. Selecting those is
    integrated mode only.
    """
    from shared.ports.registry import AdapterKind

    overrides = None
    if registration is not None and registration.id == "M14":
        from modules.platform.services.adapter import PlatformAdapter

        overrides = {
            "platform": (
                lambda: PlatformAdapter(
                    worker_available=WORKER_AVAILABLE, clock=SCHOOL_CLOCK
                ),
                AdapterKind.REAL,
            )
        }
    return build_fake_registry(
        registration,
        app_env=APP_ENV,
        clock=SCHOOL_CLOCK,
        worker_available=WORKER_AVAILABLE,
        overrides=overrides,
    )


# --- module-contributed middleware and public paths --------------------------
# A module that owns authentication declares middleware and unauthenticated paths
# in its registration; the host installs them rather than each profile hardcoding
# a module name. Imported lazily so a module with no implementation yet simply
# contributes nothing instead of breaking settings import.
try:
    import importlib

    _registration = importlib.import_module(
        f"{MODULE_ADDRESS.django_app}.registration"
    ).REGISTRATION
except (ModuleNotFoundError, AttributeError):  # module not implemented yet
    _registration = None

if _registration is not None and _registration.middleware:
    _shared = "shared.http.middleware.RequestContextMiddleware"
    MIDDLEWARE = [
        *[m for m in MIDDLEWARE if m != _shared],
    ]
    # The module's middleware runs BEFORE the shared one, so it can resolve a real
    # session; the shared one then yields to whatever context it produced.
    _index = MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1
    MIDDLEWARE = [
        *MIDDLEWARE[:_index],
        *_registration.middleware,
        _shared,
        *MIDDLEWARE[_index:],
    ]

SCHOOL_PUBLIC_PATH_PREFIXES = (
    _registration.absolute_public_paths if _registration is not None else ()
)
