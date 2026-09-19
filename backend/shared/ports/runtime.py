"""Process-level holder for the bound PortRegistry.

B00 stashed the registry on ``settings.SCHOOL_PORTS`` at URLconf import. That works
until something wraps settings: ``override_settings`` (which pytest's ``settings``
fixture uses) copies attributes into a temporary holder, and when the override pops
the attribute is GONE -- so a view resolving a port mid-test raises
AttributeError. The registry is process state, not configuration, so it belongs
here.

``settings.SCHOOL_PORTS`` is still populated for backward compatibility, but nothing
should read it.
"""

from __future__ import annotations

from .registry import PortRegistry

_REGISTRY: PortRegistry | None = None


def set_registry(registry: PortRegistry) -> PortRegistry:
    """Install the process's port registry. Called once, at URLconf import."""
    global _REGISTRY
    _REGISTRY = registry
    return registry


def get_registry() -> PortRegistry:
    """Return the installed registry, building it on demand.

    Building on demand matters for a management command or a worker, which may
    resolve a port without ever importing the URLconf.
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_from_profile()
    return _REGISTRY


def reset() -> None:
    """Forget the registry. For tests that need a different binding."""
    global _REGISTRY
    _REGISTRY = None


def _build_from_profile() -> PortRegistry:
    """Build the registry from the active settings profile.

    Reads DJANGO_SETTINGS_MODULE rather than ``settings.SETTINGS_MODULE``, which is
    None whenever settings are wrapped.
    """
    import importlib
    import os

    from django.conf import settings

    profile_path = os.environ.get("DJANGO_SETTINGS_MODULE") or settings.SETTINGS_MODULE
    if not profile_path:
        raise RuntimeError("cannot determine the settings profile to bind ports from")
    profile = importlib.import_module(profile_path)
    builder = getattr(profile, "build_port_registry", None)
    if builder is None:
        raise RuntimeError(f"settings module {profile_path} defines no build_port_registry")
    registration = None
    try:
        from shared.module_catalog import address_for

        module = importlib.import_module(
            f"{address_for(settings.MODULE_ID).django_app}.registration"
        )
        registration = module.REGISTRATION
    except (ModuleNotFoundError, AttributeError, KeyError):
        registration = None
    return builder(registration)
