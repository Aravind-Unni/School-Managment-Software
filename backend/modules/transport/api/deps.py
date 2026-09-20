"""Assemble transport services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.adjustments import AdjustmentService
from ..services.authority import AuthorityGate
from ..services.billing import BillingService
from ..services.buses import BusService
from ..services.participations import ParticipationService
from ..services.port import TransportService
from ..services.reconciliation import ReconciliationService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build Access + Registry gate."""
    ports, clock = _ports()
    return AuthorityGate(
        access=ports.resolve("access"),
        registry=ports.resolve("registry"),
        clock=clock,
    )


def bus_service() -> BusService:
    """Bus create/list."""
    ports, clock = _ports()
    return BusService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def participation_service() -> ParticipationService:
    """Participation CRUD and participant list."""
    ports, clock = _ports()
    return ParticipationService(
        gate=gate(),
        registry=ports.resolve("registry"),
        fees=ports.resolve("fees"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def billing_service() -> BillingService:
    """Billing runs and charge requests."""
    ports, clock = _ports()
    return BillingService(
        gate=gate(),
        fees=ports.resolve("fees"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def reconciliation_service() -> ReconciliationService:
    """Billing reconciliation."""
    ports, _clock = _ports()
    return ReconciliationService(gate=gate(), fees=ports.resolve("fees"))


def adjustment_service() -> AdjustmentService:
    """Build the adjustment credit service."""
    ports, clock = _ports()
    return AdjustmentService(
        gate=gate(),
        fees=ports.resolve("fees"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def transport_port() -> TransportService:
    """In-process TransportPort."""
    return TransportService(gate=gate(), billing=billing_service())
