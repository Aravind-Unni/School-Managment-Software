"""Settings shared by every profile.

Contains nothing profile-specific: no database, no INSTALLED_APPS entry for any
business module, and no adapter binding. Each profile module supplies those, so
reading one profile file tells you exactly what that profile runs.
"""

from __future__ import annotations

from pathlib import Path

from config import env
from shared.fakes.clock import FixedClock

#: backend/ -- the Python import root. Both ``contracts`` and ``shared`` are
#: top-level packages under it, which is why no module needs a ``backend.``
#: prefix and why the architecture check can reason about import paths.
BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

APP_ENV = env.optional("APP_ENV", "standalone")
MODULE_ID = env.optional("MODULE_ID", "M00").upper()
DEV_PERSONA_MODE = env.optional("DEV_PERSONA_MODE", "off")

if APP_ENV not in env.VALID_APP_ENVS:
    raise env.ConfigurationError(
        f"APP_ENV must be one of {sorted(env.VALID_APP_ENVS)}, got {APP_ENV!r}"
    )
if DEV_PERSONA_MODE not in env.VALID_PERSONA_MODES:
    raise env.ConfigurationError(
        f"DEV_PERSONA_MODE must be 'off' or 'fixed', got {DEV_PERSONA_MODE!r}"
    )

#: Real secret in deployed profiles; the test profile supplies its own.
SECRET_KEY = env.optional("SESSION_SECRET", "unset-secret-for-collectstatic-only")

DEBUG = APP_ENV != "production"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"] if DEBUG else []

#: Django apps every profile needs. No business module appears here.
DJANGO_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
]
#: The shared harness app owns the audit/outbox test tables. Installed in
#: standalone and integrated; explicitly absent in production.
HARNESS_APPS = ["shared.harness"]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "shared.http.middleware.RequestContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

#: Instants are UTC everywhere. Civil dates use contracts.values.SCHOOL_TIMEZONE
#: (Asia/Kolkata) explicitly at the call site, never implicitly via TIME_ZONE.
USE_TZ = True
TIME_ZONE = "UTC"
USE_I18N = True
#: English and Malayalam. The backend returns message_key values; the frontend
#: renders them, so no .po files live here.
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ml", "Malayalam")]

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "shared.http.errors.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Authentication and permissions are supplied by the profile: standalone
    # binds the fake Access port, production binds M01. There is deliberately
    # no permissive default here.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "School platform API",
    "DESCRIPTION": "Per-module REST API. One module is served per standalone profile.",
    "VERSION": "school-contracts-v3-draft",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {"ErrorCode": "contracts.errors.ErrorCode"},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

#: Injected clock. Replaced by a FixedClock in tests so that stale-2FA and
#: date-boundary behaviour is reproducible.
SCHOOL_CLOCK = FixedClock()

#: Set by each profile. Never True in production.
DEMO_FIXTURES_ENABLED = False
