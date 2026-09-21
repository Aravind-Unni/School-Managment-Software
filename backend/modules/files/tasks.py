"""Celery tasks for compress, purge and orphan cleanup."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task

from .api import deps
from .services.constants import PROFILE_DEFAULT


@shared_task(name="modules.files.tasks.process_file")
def process_file(file_id: str, profile: str = PROFILE_DEFAULT) -> None:
    """Decode/compress one file. Does not claim crash coverage when eager."""
    deps.lifecycle_service().process_file(UUID(file_id), profile=profile)


@shared_task(name="modules.files.tasks.purge_source")
def purge_source(file_id: str) -> None:
    """Attempt economical source purge for one file."""
    deps.retention_service().attempt_purge(UUID(file_id))


@shared_task(name="modules.files.tasks.cleanup_orphans")
def cleanup_orphans() -> int:
    """Abandon expired open upload sessions and remove quarantine objects."""
    return deps.retention_service().cleanup_orphans()
