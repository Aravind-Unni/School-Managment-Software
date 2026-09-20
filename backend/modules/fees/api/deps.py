"""Assemble fee services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.charges import ChargeService, PlanService
from ..services.corrections import CorrectionService
from ..services.payments import PaymentService
from ..services.port import FeesService
from ..services.statements import StatementService


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


def plan_service() -> PlanService:
    """Fee plan create."""
    ports, clock = _ports()
    return PlanService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def charge_service() -> ChargeService:
    """Charge posting."""
    ports, clock = _ports()
    return ChargeService(
        gate=gate(),
        registry=ports.resolve("registry"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def payment_service() -> PaymentService:
    """Payment posting."""
    ports, clock = _ports()
    return PaymentService(
        gate=gate(),
        registry=ports.resolve("registry"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def correction_service() -> CorrectionService:
    """Reversals, concessions, refunds."""
    ports, clock = _ports()
    return CorrectionService(
        gate=gate(),
        registry=ports.resolve("registry"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def statement_service() -> StatementService:
    """Statements and summaries."""
    ports, clock = _ports()
    return StatementService(gate=gate(), registry=ports.resolve("registry"), clock=clock)


def fees_port() -> FeesService:
    """In-process FeesPort."""
    return FeesService(
        charges=charge_service(),
        corrections=correction_service(),
        statements=statement_service(),
        gate=gate(),
    )
