"""Environment reading, DSN parsing and diagnostic redaction.

Every setting comes from the environment named in ``.env.example``; nothing is
read from a committed file. ``describe()`` produces the redacted view used by
``scripts/dev.py doctor`` and by ``/healthz``, so a diagnostic dump can never
print a secret.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

#: Variables whose values are never printed, in full or in part.
SECRET_NAMES: frozenset[str] = frozenset(
    {
        "SESSION_SECRET",
        "TOTP_ENCRYPTION_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
        "OBJECT_STORAGE_ACCESS_KEY",
    }
)

#: Variables that embed credentials inside a URL and need structural redaction.
DSN_NAMES: frozenset[str] = frozenset({"DATABASE_URL", "BROKER_URL"})

VALID_APP_ENVS: frozenset[str] = frozenset({"standalone", "integrated", "production"})
VALID_PERSONA_MODES: frozenset[str] = frozenset({"off", "fixed", ""})


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or contradictory.

    Always raised at startup, never at request time, so a misconfigured
    deployment fails before it can serve a wrong answer.
    """


def require(name: str) -> str:
    """Return a required environment variable, or raise ConfigurationError."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"{name} is required but unset; see .env.example for its meaning"
        )
    return value


def optional(name: str, default: str = "") -> str:
    """Return an optional environment variable, stripped, or ``default``."""
    return os.environ.get(name, default).strip()


def flag(name: str, default: bool = False) -> bool:
    """Return a boolean environment variable.

    Accepts 1/true/yes/on case-insensitively. Anything else is False, so a
    typo'd flag fails closed.
    """
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """A parsed PostgreSQL DSN, ready for Django's DATABASES setting."""

    name: str
    user: str
    password: str
    host: str
    port: int

    def as_django(self) -> dict[str, object]:
        """Return the Django DATABASES['default'] dictionary.

        ``ATOMIC_REQUESTS`` is deliberately False: audit and outbox writes must
        join an explicitly opened transaction so that rollback assertions mean
        something, and a hidden per-request transaction makes that ambiguous.
        """
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": str(self.port),
            "ATOMIC_REQUESTS": False,
            "CONN_MAX_AGE": 0,
        }


def parse_database_url(dsn: str) -> DatabaseConfig:
    """Parse a ``postgresql://user:pass@host:port/dbname`` DSN.

    Raises ConfigurationError on a non-PostgreSQL scheme, because the platform
    depends on PostgreSQL behaviour (JSONB, uuid, transactional DDL) and a
    silently-accepted SQLite URL would pass tests that production then fails.

    Does not handle: query-string options such as sslmode. M14 adds those for
    production deployment.
    """
    parsed = urlparse(dsn)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ConfigurationError(
            f"DATABASE_URL must be a postgresql:// DSN, got {parsed.scheme!r}://"
        )
    if not parsed.path.lstrip("/"):
        raise ConfigurationError("DATABASE_URL is missing a database name")
    return DatabaseConfig(
        name=parsed.path.lstrip("/"),
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
    )


def redact(name: str, value: str) -> str:
    """Return a value safe to print in diagnostics.

    Secrets become ``"<set>"`` or ``"<unset>"`` -- never a prefix, because even
    a few characters of a key narrows a brute-force search. DSNs keep their
    structure but lose the password, since host and database name are exactly
    what a developer needs from ``doctor``.
    """
    if not value:
        return "<unset>"
    if name in SECRET_NAMES:
        return "<set>"
    if name in DSN_NAMES:
        parsed = urlparse(value)
        if parsed.password:
            netloc = f"{parsed.username}:<redacted>@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return f"{parsed.scheme}://{netloc}{parsed.path}"
        return value
    return value


#: The full set of names documented in .env.example.
DOCUMENTED_NAMES: tuple[str, ...] = (
    "APP_ENV",
    "MODULE_ID",
    "SCHOOL_ID",
    "DATABASE_URL",
    "BROKER_URL",
    "OBJECT_STORAGE_ENDPOINT",
    "OBJECT_STORAGE_BUCKET",
    "OBJECT_STORAGE_ACCESS_KEY",
    "OBJECT_STORAGE_SECRET_KEY",
    "SESSION_SECRET",
    "TOTP_ENCRYPTION_KEY",
    "DEV_PERSONA_MODE",
    "ALLOWED_HOSTS",
    "WORKER_AVAILABLE",
    "OWNER_LOGIN",
    "OWNER_PASSWORD",
    "OWNER_DISPLAY_NAME",
)


def describe() -> dict[str, str]:
    """Return every documented variable, redacted, for doctor and healthz."""
    return {name: redact(name, os.environ.get(name, "")) for name in DOCUMENTED_NAMES}
