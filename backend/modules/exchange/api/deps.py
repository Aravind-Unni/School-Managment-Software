"""Assemble exchange services from the ports the host bound."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..adapters import ExportPorts
from ..services.authority import AuthorityGate
from ..services.exports import ExportService
from ..services.imports import ImportService
from ..services.port import ExchangeService
from ..services.reportcards import ReportCardService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build the Access + Registry authority gate."""
    ports, clock = _ports()
    return AuthorityGate(
        access=ports.resolve("access"),
        registry=ports.resolve("registry"),
        clock=clock,
    )


def export_ports() -> ExportPorts:
    """Bundle the read-only ports export adapters are allowed to use."""
    ports, clock = _ports()
    return ExportPorts(
        registry=ports.resolve("registry"),
        attendance=ports.resolve("attendance"),
        assessment=ports.resolve("assessment"),
        fees=ports.resolve("fees"),
        clock=clock,
    )


def import_service() -> ImportService:
    """Validate and commit bulk imports."""
    ports, clock = _ports()
    return ImportService(
        gate=gate(),
        files=ports.resolve("files"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def export_service() -> ExportService:
    """Create, render and serve dataset exports."""
    ports, clock = _ports()
    return ExportService(
        gate=gate(),
        files=ports.resolve("files"),
        platform=ports.resolve("platform"),
        clock=clock,
        ports=export_ports(),
    )


def report_card_service() -> ReportCardService:
    """Generate report cards and manage their snapshots."""
    ports, clock = _ports()
    return ReportCardService(
        gate=gate(),
        files=ports.resolve("files"),
        assessment=ports.resolve("assessment"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def exchange_port() -> ExchangeService:
    """In-process ExchangePort for other modules."""
    return ExchangeService(report_cards=report_card_service())
