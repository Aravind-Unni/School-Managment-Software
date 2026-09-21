"""Assemble files services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.lifecycle import FilesLifecycle
from ..services.port import FilesService
from ..services.retention import RetentionService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build Access gate."""
    ports, clock = _ports()
    return AuthorityGate(
        access=ports.resolve("access"), clock=clock, registry=ports.resolve("registry")
    )


def lifecycle_service() -> FilesLifecycle:
    """Upload/process/quality lifecycle."""
    ports, clock = _ports()
    return FilesLifecycle(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def retention_service() -> RetentionService:
    """Hold, purge and orphan cleanup."""
    ports, clock = _ports()
    return RetentionService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def files_port() -> FilesService:
    """In-process FilesPort."""
    ports, clock = _ports()
    life = lifecycle_service()
    return FilesService(
        gate=gate(), platform=ports.resolve("platform"), clock=clock, lifecycle=life
    )
