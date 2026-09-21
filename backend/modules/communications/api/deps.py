"""Assemble communications services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.deliveries import DeliveryService
from ..services.notices import NoticeService


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


def notice_service() -> NoticeService:
    """Notice create/publish."""
    ports, clock = _ports()
    return NoticeService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def delivery_service() -> DeliveryService:
    """Message enqueue, process and callbacks."""
    ports, clock = _ports()
    return DeliveryService(gate=gate(), platform=ports.resolve("platform"), clock=clock)
