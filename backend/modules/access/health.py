"""Readiness checks contributed by M01."""

from __future__ import annotations


def check_tables() -> dict[str, object]:
    """Return whether M01's tables are queryable."""
    from .models import User

    try:
        User.objects.exists()
    except Exception as exc:
        return {"name": "access_tables", "ok": False, "detail": type(exc).__name__}
    return {"name": "access_tables", "ok": True}


def check_totp_key() -> dict[str, object]:
    """Return whether the TOTP encryption key is usable.

    Reports unready rather than raising: a profile with no key must not accept an
    enrolment, and a readiness probe is how an operator finds that out before
    users do. Never reports the key itself.
    """
    from .services.crypto import SecretConfigurationError, encrypt_secret

    try:
        encrypt_secret("PROBE")
    except SecretConfigurationError as exc:
        return {"name": "totp_key_present", "ok": False, "detail": str(exc)[:80]}
    except Exception as exc:
        return {"name": "totp_key_present", "ok": False, "detail": type(exc).__name__}
    return {"name": "totp_key_present", "ok": True}
