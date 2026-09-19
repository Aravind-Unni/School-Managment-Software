"""Integrated profile: the host wires approved registrations and real ports.

Differs from standalone in exactly two ways that matter:
  * every approved module's app is installed, in dependency order
  * real provider adapters are selected, not fakes

Still a development/verification profile: the persona path may be enabled on
loopback. Production is a separate profile that refuses it.
"""

from __future__ import annotations

from config import env
from config.settings.base import *
from config.settings.base import HARNESS_APPS, INSTALLED_APPS
from shared.module_catalog import MODULE_SLUGS
from shared.ports import AdapterKind, PortRegistry

APP_ENV = "integrated"

#: Modules approved for integration, as ids. Empty until a module's contract is
#: frozen in contracts/manifest.json and its implementation is merged. C02 grows
#: this list; B00 deliberately ships it containing only the placeholder.
APPROVED_MODULE_IDS: tuple[str, ...] = ("M00",)

INSTALLED_APPS = (
    INSTALLED_APPS
    + HARNESS_APPS
    + [f"modules.{MODULE_SLUGS[module_id]}" for module_id in APPROVED_MODULE_IDS]
)

DATABASES = {"default": env.parse_database_url(env.require("DATABASE_URL")).as_django()}

DEMO_FIXTURES_ENABLED = env.flag("DEMO_FIXTURES_ENABLED", default=False)
WORKER_AVAILABLE = env.flag("WORKER_AVAILABLE", default=False)


def build_port_registry(registration=None) -> PortRegistry:
    """Bind real provider adapters for every approved module.

    Raises ConfigurationError when a port has no real provider yet, rather than
    falling back to a fake: an integrated run that silently used a fake would
    prove nothing about integration.

    Does not handle: partial integration. Either the provider module is approved
    and its adapter is real, or integrated mode refuses to start.
    """
    registry = PortRegistry(app_env=APP_ENV)
    real_providers: dict[str, object] = {}

    missing = sorted(set(getattr(registration, "consumers", ()) or ()) - set(real_providers))
    if missing:
        raise env.ConfigurationError(
            "integrated mode has no real provider for ports "
            f"{missing}; approve and implement the owning module first, or run "
            "the standalone profile instead"
        )
    for port_name, factory in real_providers.items():
        registry.register(port_name, factory, kind=AdapterKind.REAL)  # type: ignore[arg-type]
    return registry
