"""Assemble assessment services from bound ports."""

from __future__ import annotations

from django.conf import settings

from shared.ports import runtime

from ..services.authority import AuthorityGate
from ..services.create import CreateService
from ..services.evidence import EvidenceService
from ..services.marks import MarksService
from ..services.port import AssessmentService
from ..services.publish import PublishService
from ..services.reopen import ReopenService
from ..services.workflow import WorkflowService


def _ports():
    """Resolve the profile's port registry and clock."""
    registry = runtime.get_registry()
    return registry, settings.SCHOOL_CLOCK


def gate() -> AuthorityGate:
    """Build the teaching-assignment + Access gate."""
    ports, clock = _ports()
    return AuthorityGate(
        access=ports.resolve("access"),
        registry=ports.resolve("registry"),
        clock=clock,
    )


def create_service() -> CreateService:
    """Assessment create."""
    ports, clock = _ports()
    return CreateService(
        gate=gate(),
        registry=ports.resolve("registry"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def marks_service() -> MarksService:
    """Mark PATCH."""
    ports, clock = _ports()
    return MarksService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def evidence_service() -> EvidenceService:
    """Evidence bind and view."""
    ports, clock = _ports()
    return EvidenceService(
        gate=gate(),
        files=ports.resolve("files"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def workflow_service() -> WorkflowService:
    """Submit and approve."""
    ports, clock = _ports()
    return WorkflowService(
        gate=gate(),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def publish_service() -> PublishService:
    """Publish with idempotency."""
    ports, clock = _ports()
    return PublishService(
        gate=gate(),
        files=ports.resolve("files"),
        platform=ports.resolve("platform"),
        clock=clock,
    )


def reopen_service() -> ReopenService:
    """Reopen published batches."""
    ports, clock = _ports()
    return ReopenService(gate=gate(), platform=ports.resolve("platform"), clock=clock)


def assessment_port() -> AssessmentService:
    """In-process port for other modules."""
    ports, clock = _ports()
    return AssessmentService(
        gate=gate(),
        access=ports.resolve("access"),
        registry=ports.resolve("registry"),
        clock=clock,
    )
