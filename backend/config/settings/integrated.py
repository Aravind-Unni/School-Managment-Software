"""Integrated profile: the host wires approved registrations and real ports.

Differs from standalone in exactly two ways that matter:
  * every approved module's app is installed, in dependency order
  * real provider adapters are selected, not fakes

Still a development/verification profile: the persona path may be enabled on
loopback. Production is a separate profile that refuses it.

C02 grows APPROVED_MODULE_IDS. Integrated refuses to start when a real provider
is missing rather than silently binding a fake.
"""

from __future__ import annotations

import importlib

from config import env
from config.real_ports import build_real_providers, required_ports_for
from config.settings.base import *
from config.settings.base import HARNESS_APPS, INSTALLED_APPS, MIDDLEWARE, SCHOOL_CLOCK
from shared import fixtures
from shared.module_catalog import MODULE_SLUGS
from shared.ports import PortRegistry

APP_ENV = "integrated"

#: One-school deployment identity for this integrated verification stack.
#: Same synthetic School A used by module seeds; never invent a real campus id.
SCHOOL_ID = env.optional("SCHOOL_ID") or str(fixtures.SCHOOL_A)

#: Assembly order from the C02 packet (B00 foundation first via M00, then M14
#: platform, identity+registry, files, timetable/attendance, assessment, fees/
#: transport, library/alumni, performance/communications/reports).
APPROVED_MODULE_IDS: tuple[str, ...] = (
    "M00",
    "M14",
    "M01",
    "M02",
    "M12",
    "M03",
    "M04",
    "M05",
    "M07",
    "M08",
    "M09",
    "M10",
    "M06",
    "M11",
    "M13",
)

INSTALLED_APPS = (
    INSTALLED_APPS
    + HARNESS_APPS
    + [f"modules.{MODULE_SLUGS[module_id]}" for module_id in APPROVED_MODULE_IDS]
)

DATABASES = {"default": env.parse_database_url(env.require("DATABASE_URL")).as_django()}

#: Integrated verification uses real M01 sessions — no synthetic persona.
DEV_PERSONA = None
DEV_PERSONA_MODE = "off"
DEV_PERSONA_TRUSTED_NETWORKS: tuple[str, ...] = ()

TOTP_ENCRYPTION_KEY = env.optional("TOTP_ENCRYPTION_KEY")

DEMO_FIXTURES_ENABLED = env.flag("DEMO_FIXTURES_ENABLED", default=False)
WORKER_AVAILABLE = env.flag("WORKER_AVAILABLE", default=False)

CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://(localhost|127\.0\.0\.1):\d+$"]
CORS_ALLOW_CREDENTIALS = True

#: Re-export for adapters that read settings.SCHOOL_CLOCK.
SCHOOL_CLOCK = SCHOOL_CLOCK


def _load_approved_registrations() -> list:
    """Import every approved ModuleRegistration in assembly order."""
    registrations = []
    for module_id in APPROVED_MODULE_IDS:
        slug = MODULE_SLUGS[module_id]
        module = importlib.import_module(f"modules.{slug}.registration")
        registrations.append(module.REGISTRATION)
    return registrations


def build_port_registry(registration=None) -> PortRegistry:
    """Bind real provider adapters for the union of approved consumers.

    ``registration`` may be a single ModuleRegistration (standalone-shaped call
    sites) or ignored when the host passes None and we load all approved ones.

    Raises ConfigurationError when a port has no real provider yet.

    Does not handle: partial integration with intentional fakes.
    """
    del registration  # integrated always binds the full approved consumer set
    registrations = _load_approved_registrations()
    required = required_ports_for(registrations)
    providers = build_real_providers(required)

    registry = PortRegistry(app_env=APP_ENV)
    for port_name, (factory, kind) in providers.items():
        registry.register(port_name, factory, kind=kind)
    return registry


# --- middleware and public paths from every approved registration ------------
_APPROVED_REGISTRATIONS = _load_approved_registrations()

_shared_mw = "shared.http.middleware.RequestContextMiddleware"
_middleware = [m for m in MIDDLEWARE if m != _shared_mw]
_index = _middleware.index("django.middleware.common.CommonMiddleware") + 1
_extra_mw: list[str] = []
_public: list[str] = []
for _reg in _APPROVED_REGISTRATIONS:
    _extra_mw.extend(list(_reg.middleware or ()))
    _public.extend(list(_reg.absolute_public_paths))
MIDDLEWARE = [
    *_middleware[:_index],
    *_extra_mw,
    _shared_mw,
    *_middleware[_index:],
]
SCHOOL_PUBLIC_PATH_PREFIXES = tuple(_public)
