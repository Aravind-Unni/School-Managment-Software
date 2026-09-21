"""Assemble platform services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.adapter import PlatformAdapter
from ..services.audit import AuditService
from ..services.authority import AuthorityGate
from ..services.facade import PlatformFacade
from ..services.health_backup import BackupService, HealthService
from ..services.jobs import JobService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build Access gate."""
    ports, clock = _ports()
    return AuthorityGate(access=ports.resolve("access"), clock=clock)


def platform_adapter() -> PlatformAdapter:
    """Return the real platform adapter bound for M14."""
    ports, _clock = _ports()
    return ports.resolve("platform")  # type: ignore[return-value]


def job_service() -> JobService:
    """Job read/retry service."""
    _ports_unused, clock = _ports()
    return JobService(gate=gate(), platform=platform_adapter(), clock=clock)


def audit_service() -> AuditService:
    """Audit list service."""
    _ports_unused, clock = _ports()
    return AuditService(gate=gate(), clock=clock)


def health_service() -> HealthService:
    """Health endpoints."""
    return HealthService(gate=gate())


def backup_service() -> BackupService:
    """Restore rehearsal service."""
    ports, clock = _ports()
    return BackupService(
        gate=gate(),
        platform=platform_adapter(),
        clock=clock,
        object_storage=ports.resolve("object_storage"),
    )


def facade() -> PlatformFacade:
    """Ergonomic Platform helpers for sample producer tests."""
    _ports_unused, clock = _ports()
    return PlatformFacade(platform=platform_adapter(), clock=clock)
