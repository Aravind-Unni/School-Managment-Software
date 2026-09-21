"""Assemble performance services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from .authority import AuthorityGate
from .dashboard import DashboardService
from .interventions import InterventionService
from .port import PerformanceService
from .projections import ProjectionService
from .warnings import WarningService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build Registry + Access gate."""
    ports, clock = _ports()
    return AuthorityGate(
        access=ports.resolve("access"),
        registry=ports.resolve("registry"),
        clock=clock,
    )


def projection_service() -> ProjectionService:
    """Projection rebuild."""
    ports, clock = _ports()
    return ProjectionService(
        assessment=ports.resolve("assessment"),
        attendance=ports.resolve("attendance"),
        clock=clock,
        platform=ports.resolve("platform"),
        registry=ports.resolve("registry"),
    )


def warning_service() -> WarningService:
    """Warning rules and transitions."""
    ports, clock = _ports()
    return WarningService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def intervention_service() -> InterventionService:
    """Interventions and meetings."""
    ports, clock = _ports()
    return InterventionService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def dashboard_service() -> DashboardService:
    """Dashboard and export."""
    _ports_unused, clock = _ports()
    return DashboardService(gate=gate(), clock=clock)


def performance_port() -> PerformanceService:
    """In-process PerformancePort."""
    return PerformanceService(
        dashboard=dashboard_service(),
        interventions=intervention_service(),
    )
