"""How M03's views obtain their dependencies.

Two different sources, for the reason M02 states once and this module inherits:

  * Ports come from ``shared.ports.runtime``, the process-level holder the host
    populates at URLconf import. Reading ``settings.SCHOOL_PORTS`` instead breaks
    under ``override_settings``, which every test that touches a setting uses.
  * The clock comes from settings, so a test can freeze or advance time by
    assigning ``settings.SCHOOL_CLOCK`` without rebuilding the port registry.

Does not handle: caching either. A service held per process would capture a stale
clock, and the tests that advance time would then pass while proving nothing.
"""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.calendar import CalendarService
from ..services.drafts import DraftService
from ..services.port import TimetableService
from ..services.publication import PublicationService
from ..services.reads import ScheduleReader
from ..services.schedules import ScheduleService
from ..services.scope import TimetableScope
from ..services.substitutions import SubstitutionService


def access_port():
    """Return the bound Access adapter for this profile."""
    return runtime.get_registry().resolve("access")


def registry_port():
    """Return the bound Registry adapter for this profile."""
    return runtime.get_registry().resolve("registry")


def platform_port():
    """Return the bound Platform adapter for this profile."""
    return runtime.get_registry().resolve("platform")


def clock():
    """Return the injected clock."""
    return settings.SCHOOL_CLOCK


def scope() -> TimetableScope:
    """Return the module-local section scope resolver."""
    return TimetableScope(access=access_port(), registry=registry_port())


def reader() -> ScheduleReader:
    """Return the single reader every schedule view goes through."""
    return ScheduleReader(clock=clock())


def draft_service() -> DraftService:
    """Assemble the draft editor from the profile's bound ports."""
    return DraftService(
        scope=scope(), registry=registry_port(), platform=platform_port(), clock=clock()
    )


def publication_service() -> PublicationService:
    """Assemble the publication service from the profile's bound ports."""
    return PublicationService(
        scope=scope(),
        access=access_port(),
        registry=registry_port(),
        platform=platform_port(),
        clock=clock(),
    )


def calendar_service() -> CalendarService:
    """Assemble the calendar service from the profile's bound ports."""
    return CalendarService(
        scope=scope(), platform=platform_port(), clock=clock(), reader=reader()
    )


def substitution_service() -> SubstitutionService:
    """Assemble the substitution service from the profile's bound ports."""
    return SubstitutionService(
        scope=scope(), platform=platform_port(), clock=clock(), reader=reader()
    )


def schedule_service() -> ScheduleService:
    """Assemble the read-only schedule views from the profile's bound ports."""
    return ScheduleService(scope=scope(), registry=registry_port(), reader=reader())


def timetable_port() -> TimetableService:
    """Return the in-process service another module consumes.

    Exposed here so a future host can bind it as ``TimetablePort`` without M03
    changing: adding that Protocol to the shared contracts package is review item
    2 and has not happened yet.
    """
    return TimetableService(scope=scope(), clock=clock(), reader=reader())
