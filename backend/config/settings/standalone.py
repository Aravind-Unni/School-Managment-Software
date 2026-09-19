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
    """Bind every dependency port the module declares to a deterministic fake.

    Delegates to shared.ports.build_fake_registry so the standalone runner and
    the local test profile bind ports identically. A module that declares a
    consumer it never uses, or uses one it never declared, fails at boot.

    Does not handle: real providers. Selecting a real adapter is integrated mode
    only, which keeps a half-finished provider out of standalone runs.
    """
    return build_fake_registry(
        registration,
        app_env=APP_ENV,
        clock=SCHOOL_CLOCK,
        worker_available=WORKER_AVAILABLE,
    )
