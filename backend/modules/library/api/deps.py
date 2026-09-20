"""Assemble library services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.catalogue import CatalogueService
from ..services.imports import ImportService
from ..services.loans import LoanService
from ..services.overdues import OverdueService
from ..services.port import LibraryService


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


def catalogue_service() -> CatalogueService:
    """Title/copy catalogue."""
    ports, clock = _ports()
    return CatalogueService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def loan_service() -> LoanService:
    """Issue/return/renew."""
    ports, clock = _ports()
    return LoanService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def overdue_service() -> OverdueService:
    """Overdue queue."""
    ports, clock = _ports()
    return OverdueService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def import_service() -> ImportService:
    """Catalogue imports."""
    ports, clock = _ports()
    return ImportService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def library_port() -> LibraryService:
    """In-process LibraryPort."""
    _ports_unused, clock = _ports()
    return LibraryService(gate=gate(), clock=clock)
