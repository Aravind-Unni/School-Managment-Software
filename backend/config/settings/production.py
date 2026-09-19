"""Production profile. Refuses fakes, personas and demo fixtures at startup.

The refusal is enforced three ways, deliberately redundant because each catches
a different mistake:
  1. PortRegistry.register raises on any FAKE adapter under this profile.
  2. assert_production_safe re-checks at boot, covering persona and demo flags.
  3. scripts/arch_check.py fails CI when a production config selects a fake.

The harness app is absent here: its audit/outbox tables are test infrastructure,
and M14 owns the real ones.
"""

from __future__ import annotations

from config import env
from config.settings.base import *
from config.settings.base import INSTALLED_APPS
from shared.ports import PortRegistry, ProductionSafetyError

APP_ENV = "production"
DEBUG = False

SECRET_KEY = env.require("SESSION_SECRET")
SCHOOL_ID = env.require("SCHOOL_ID")
DATABASES = {"default": env.parse_database_url(env.require("DATABASE_URL")).as_django()}

ALLOWED_HOSTS = [
    host.strip() for host in env.require("ALLOWED_HOSTS").split(",") if host.strip()
]

#: Never installed in production: harness tables are test infrastructure.
INSTALLED_APPS = list(INSTALLED_APPS)

DEV_PERSONA = None
DEV_PERSONA_MODE = "off"
DEMO_FIXTURES_ENABLED = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

if env.optional("DEV_PERSONA_MODE", "off") not in ("", "off"):
    raise ProductionSafetyError(
        "DEV_PERSONA_MODE must be 'off' in production; refusing to start"
    )
if "shared.harness" in INSTALLED_APPS:
    raise ProductionSafetyError(
        "the development harness app must not be installed in production"
    )


def build_port_registry(registration=None) -> PortRegistry:
    """Return a production registry, which cannot hold a fake adapter.

    Real adapters are registered by M14's deployment wiring. B00 ships this
    function returning an empty-but-validated registry so that the refusal path
    is testable before any module exists.
    """
    registry = PortRegistry(app_env=APP_ENV)
    registry.assert_production_safe(
        dev_persona_mode=env.optional("DEV_PERSONA_MODE", "off"),
        demo_fixtures_enabled=DEMO_FIXTURES_ENABLED,
    )
    return registry
