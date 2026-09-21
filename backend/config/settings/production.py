"""Production profile: full school assembly with real adapters only.

Assembles every approved business module (C02 order), binds real port
providers, and refuses personas, fakes and demo fixtures. The development
harness app is absent: M14 owns real audit/outbox tables.
"""

from __future__ import annotations

import importlib

from config import env
from config.real_ports import build_real_providers, required_ports_for
from config.settings.base import *
from config.settings.base import INSTALLED_APPS, MIDDLEWARE
from shared.clock import SystemClock
from shared.module_catalog import MODULE_SLUGS
from shared.ports import PortRegistry, ProductionSafetyError

APP_ENV = "production"
DEBUG = False

SECRET_KEY = env.require("SESSION_SECRET")
SCHOOL_ID = env.require("SCHOOL_ID")
DATABASES = {"default": env.parse_database_url(env.require("DATABASE_URL")).as_django()}

ALLOWED_HOSTS = [
    host.strip() for host in env.require("ALLOWED_HOSTS").split(",") if host.strip()
]

#: One deployment serves the whole school product, not a single MODULE_ID.
MODULE_ID = "ALL"

#: Same assembly order as integrated. M00 remains for foundation regression only;
#: the product UI hides it from school roles.
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

#: Never install the development harness in production.
INSTALLED_APPS = list(INSTALLED_APPS) + [
    f"modules.{MODULE_SLUGS[module_id]}" for module_id in APPROVED_MODULE_IDS
]

DEV_PERSONA = None
DEV_PERSONA_MODE = "off"
DEMO_FIXTURES_ENABLED = False

TOTP_ENCRYPTION_KEY = env.require("TOTP_ENCRYPTION_KEY")
BROKER_URL = env.require("BROKER_URL")
WORKER_AVAILABLE = True

OBJECT_STORAGE_ENDPOINT = env.require("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_BUCKET = env.require("OBJECT_STORAGE_BUCKET")
OBJECT_STORAGE_ACCESS_KEY = env.require("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = env.require("OBJECT_STORAGE_SECRET_KEY")

#: Wall clock — not the test FixedClock from base.
SCHOOL_CLOCK = SystemClock()

SECURE_SSL_REDIRECT = env.flag("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_SSL_REDIRECT
#: nginx terminates TLS and forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

#: Production is same-origin behind nginx; keep CORS empty.
CORS_ALLOWED_ORIGINS: list[str] = []
CORS_ALLOW_CREDENTIALS = True

if env.optional("DEV_PERSONA_MODE", "off") not in ("", "off"):
    raise ProductionSafetyError(
        "DEV_PERSONA_MODE must be 'off' in production; refusing to start"
    )
if "shared.harness" in INSTALLED_APPS:
    raise ProductionSafetyError(
        "the development harness app must not be installed in production"
    )


def _load_approved_registrations() -> list:
    """Import every approved ModuleRegistration in assembly order."""
    registrations = []
    for module_id in APPROVED_MODULE_IDS:
        slug = MODULE_SLUGS[module_id]
        module = importlib.import_module(f"modules.{slug}.registration")
        registrations.append(module.REGISTRATION)
    return registrations


def build_port_registry(registration=None) -> PortRegistry:
    """Bind real providers for every approved consumer; refuse fakes.

    ``registration`` is ignored: production always binds the full assembly.
    Raises when a required real provider is missing.
    """
    del registration
    registrations = _load_approved_registrations()
    required = required_ports_for(registrations)
    providers = build_real_providers(required)

    registry = PortRegistry(app_env=APP_ENV)
    for port_name, (factory, kind) in providers.items():
        registry.register(port_name, factory, kind=kind)
    registry.assert_production_safe(
        dev_persona_mode=env.optional("DEV_PERSONA_MODE", "off"),
        demo_fixtures_enabled=DEMO_FIXTURES_ENABLED,
    )
    return registry


_APPROVED_REGISTRATIONS = _load_approved_registrations()


#: Every installed module's permission codes, for M01's catalogue. M01's own
#: codes are already in its closed catalogue and are skipped here.
SCHOOL_MODULE_PERMISSION_CODES: tuple[str, ...] = tuple(
    code
    for _reg in _APPROVED_REGISTRATIONS
    if _reg.id != "M01"
    for code in (_reg.permission_codes or ())
)

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

#: Optional: restrict backup management to these account ids (comma-separated)
#: on top of the backups.manage grant. Empty means the grant plus fresh 2FA.
PLATFORM_OPS_ACTOR_IDS: tuple[str, ...] = tuple(
    part.strip()
    for part in (env.optional("PLATFORM_OPS_ACTOR_IDS", "") or "").split(",")
    if part.strip()
)

#: The API container publishes no port; only this stack's nginx reaches it and
#: nginx overwrites X-Real-IP, so the header is the real client address.
TRUST_X_REAL_IP = env.flag("TRUST_X_REAL_IP", default=True)
