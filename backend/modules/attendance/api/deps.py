"""Assemble attendance services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.corrections import CorrectionService
from ..services.drafts import DraftService
from ..services.port import AttendanceService
from ..services.reconcile import ReconcileService
from ..services.submit import SubmitService
from ..services.summary import SummaryService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build the period-teacher + Access gate."""
    ports, _clock = _ports()
    return AuthorityGate(access=ports.resolve("access"), timetable=ports.resolve("timetable"))


def draft_service() -> DraftService:
    """Draft create/save/list."""
    ports, clock = _ports()
    return DraftService(
        gate=gate(),
        registry=ports.resolve("registry"),
        platform=ports.resolve("platform"),
        clock=clock,
        timetable=ports.resolve("timetable"),
    )


def submit_service() -> SubmitService:
    """Submit with idempotency."""
    ports, clock = _ports()
    return SubmitService(
        drafts=draft_service(), gate=gate(), platform=ports.resolve("platform"), clock=clock
    )


def correction_service() -> CorrectionService:
    """Audited corrections."""
    ports, clock = _ports()
    return CorrectionService(
        access=ports.resolve("access"), platform=ports.resolve("platform"), clock=clock
    )


def summary_service() -> SummaryService:
    """Period summaries."""
    ports, clock = _ports()
    return SummaryService(
        access=ports.resolve("access"),
        registry=ports.resolve("registry"),
        timetable=ports.resolve("timetable"),
        clock=clock,
    )


def reconcile_service() -> ReconcileService:
    """Post-submit reconciliation."""
    ports, clock = _ports()
    return ReconcileService(
        access=ports.resolve("access"),
        timetable=ports.resolve("timetable"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def attendance_port() -> AttendanceService:
    """In-process port for other modules."""
    return AttendanceService(summary=summary_service())
