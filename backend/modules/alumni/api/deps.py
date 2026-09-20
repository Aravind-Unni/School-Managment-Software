"""Assemble alumni services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.candidates import CandidateService
from ..services.exports import ExportService
from ..services.port import AlumniService
from ..services.profiles import ProfileService


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


def candidate_service() -> CandidateService:
    """Candidate create/list/approve."""
    ports, clock = _ports()
    return CandidateService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def profile_service() -> ProfileService:
    """Directory and contact patch."""
    ports, clock = _ports()
    return ProfileService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def export_service() -> ExportService:
    """Export job acceptance."""
    ports, clock = _ports()
    return ExportService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def alumni_port() -> AlumniService:
    """In-process AlumniPort."""
    ports, clock = _ports()
    g = gate()
    return AlumniService(
        gate=g,
        candidates=CandidateService(gate=g, platform=ports.resolve("platform"), clock=clock),
        profiles=ProfileService(gate=g, platform=ports.resolve("platform"), clock=clock),
        clock=clock,
    )
