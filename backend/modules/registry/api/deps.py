"""How M02's views obtain their dependencies.

Two different sources, for a reason worth stating once:

  * Ports come from ``shared.ports.runtime``, the process-level holder the host
    populates at URLconf import. Reading ``settings.SCHOOL_PORTS`` instead breaks
    under ``override_settings``, which every test that touches a setting uses.
  * The clock comes from settings, so a test can freeze time by assigning
    ``settings.SCHOOL_CLOCK`` without rebuilding the whole port registry.

Does not handle: caching either. A service held per process would capture a
stale clock, and the tests that freeze time would then pass while proving
nothing.
"""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.configuration import ConfigurationService
from ..services.people import PeopleService


def access_port():
    """Return the bound Access adapter for this profile."""
    return runtime.get_registry().resolve("access")


def clock():
    """Return the injected clock."""
    return settings.SCHOOL_CLOCK


def configuration_service() -> ConfigurationService:
    """Assemble the configuration service from the profile's bound ports."""
    return ConfigurationService(access=access_port(), clock=clock())


def people_service() -> PeopleService:
    """Assemble the people service from the profile's bound ports."""
    return PeopleService(access=access_port(), clock=clock())
