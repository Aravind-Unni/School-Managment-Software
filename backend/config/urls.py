"""Root URLconf. Mounts exactly the modules this profile installed.

In standalone mode one registration is loaded and mounted at its declared
``api_prefix``. In integrated mode the host mounts every approved registration.
A module is never mounted by importing it for a side effect.
"""

from __future__ import annotations

import importlib
import os

from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from shared.module_catalog import address_for


def _load_registrations() -> list:
    """Import the registrations this profile should mount.

    Standalone loads only MODULE_ID. Integrated loads APPROVED_MODULE_IDS.
    Raises ImproperlyConfigured-style errors early, at import time, so a missing
    module fails at boot rather than on first request.
    """
    if settings.APP_ENV == "integrated":
        module_ids = list(getattr(settings, "APPROVED_MODULE_IDS", ()))
    else:
        module_ids = [settings.MODULE_ID]

    registrations = []
    for module_id in module_ids:
        address = address_for(module_id)
        try:
            module = importlib.import_module(address.registration_path)
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                f"module {module_id} ({address.slug}) has no implementation yet: "
                f"{address.registration_path} is absent. This command fails "
                "honestly rather than serving an empty app."
            ) from exc
        registrations.append(module.REGISTRATION)
    return registrations


REGISTRATIONS = _load_registrations()


def _build_port_registry():
    """Build the PortRegistry using the active profile's factory.

    Each profile module defines ``build_port_registry``. Calling it here, at
    URLconf import, is what makes "production refuses a fake adapter" a startup
    failure rather than a request-time surprise.
    """
    # settings.SETTINGS_MODULE is None whenever settings are wrapped by
    # override_settings (which pytest-django's `settings` fixture uses), so the
    # environment variable is the reliable source. This surfaced as an
    # import_module(None) crash the first time a test overrode a setting BEFORE the
    # URLconf had loaded.
    profile_path = os.environ.get("DJANGO_SETTINGS_MODULE") or settings.SETTINGS_MODULE
    if not profile_path:
        raise RuntimeError(
            "cannot determine the settings profile: DJANGO_SETTINGS_MODULE is unset "
            "and settings.SETTINGS_MODULE is None"
        )
    profile = importlib.import_module(profile_path)
    builder = getattr(profile, "build_port_registry", None)
    if builder is None:
        raise RuntimeError(
            f"settings module {settings.SETTINGS_MODULE} defines no "
            "build_port_registry; every profile must declare how ports are bound"
        )
    if settings.APP_ENV == "integrated":
        from contracts.registration import assert_no_registration_collisions

        assert_no_registration_collisions(tuple(REGISTRATIONS))
        return builder(None)
    primary = REGISTRATIONS[0] if REGISTRATIONS else None
    return builder(primary)


#: Bound once at import and installed in the process-level holder. Views read it
#: via shared.ports.runtime.get_registry(); settings.SCHOOL_PORTS remains only for
#: backward compatibility with B00's assertions.
#:
#: When the URLconf is re-imported (pytest-django settings overrides can force
#: that), keep the already-bound registry so in-memory fakes retain state.
from shared.ports import runtime as _port_runtime  # noqa: E402

_existing_ports = _port_runtime.peek()
if _existing_ports is None:
    settings.SCHOOL_PORTS = _port_runtime.set_registry(_build_port_registry())
else:
    settings.SCHOOL_PORTS = _existing_ports


def healthz(_request):
    """Liveness: the process is up. Does not touch the database."""
    return JsonResponse({"status": "ok", "app_env": settings.APP_ENV})


def readyz(_request):
    """Readiness: run every registered health check and report each result.

    Returns 503 when any check fails, with the per-check detail, so a developer
    sees which dependency is missing rather than a bare failure.
    """
    results = []
    for registration in REGISTRATIONS:
        for check in registration.health_checks:
            module_path, _, attribute = check.callable_path.rpartition(".")
            try:
                function = getattr(importlib.import_module(module_path), attribute)
                results.append(function())
            except Exception as exc:
                results.append({"name": check.name, "ok": False, "detail": type(exc).__name__})

    from config import env

    ok = all(result.get("ok") for result in results)
    return JsonResponse(
        {
            "status": "ready" if ok else "not_ready",
            "app_env": settings.APP_ENV,
            "module_id": settings.MODULE_ID,
            "checks": results,
            "ports": {name: str(kind) for name, kind in settings.SCHOOL_PORTS.kinds().items()},
            # Redacted: describe() never returns a secret value.
            "config": env.describe(),
        },
        status=200 if ok else 503,
    )


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

#: Mount each registration at its declared prefix.
for _registration in REGISTRATIONS:
    urlpatterns.append(
        path(
            _registration.api_prefix.lstrip("/"),
            include(f"modules.{_registration.slug}.urls"),
        )
    )
