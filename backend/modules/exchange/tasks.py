"""Celery tasks for validate, commit, export and report-card rendering.

None of these claims crash or retry coverage. TestPlatformAdapter refuses to
enqueue without a real broker, and the services fall back to running inline, so
a suite without a worker gets correct results and an honest ``not-run`` for the
asynchronous behaviour itself.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from celery import shared_task

from .api import deps
from .models import ExportJob, ImportJob, ImportJobState, JobState

#: How long an import may sit unvalidated before the nightly job retires it.
STALE_IMPORT_AGE = timedelta(days=7)


@shared_task(name="modules.exchange.tasks.process_import_validate")
def process_import_validate(job_id: str) -> None:
    """Parse and validate one uploaded import file."""
    deps.import_service().validate(UUID(job_id))


@shared_task(name="modules.exchange.tasks.process_import_commit")
def process_import_commit(job_id: str, idempotency_key: str) -> None:
    """Apply one import job's accepted rows under an idempotency key."""
    deps.import_service().apply_commit(UUID(job_id), idempotency_key)


@shared_task(name="modules.exchange.tasks.process_export")
def process_export(job_id: str) -> None:
    """Render and store one export artifact."""
    deps.export_service().process(UUID(job_id))


@shared_task(name="modules.exchange.tasks.process_report_card")
def process_report_card(job_id: str) -> None:
    """Render one report card and bind its snapshot."""
    deps.report_card_service().process(UUID(job_id))


@shared_task(name="modules.exchange.tasks.cleanup_stale_imports")
def cleanup_stale_imports() -> int:
    """Retire imports left validating past the stale window; return the count.

    Marks them ``validation_failed`` rather than deleting them: the reviewer
    who uploaded the file should be able to see what became of it.
    """
    from django.conf import settings

    cutoff = settings.SCHOOL_CLOCK.now() - STALE_IMPORT_AGE
    return ImportJob.objects.filter(
        state=ImportJobState.VALIDATING, created_at__lt=cutoff
    ).update(state=ImportJobState.VALIDATION_FAILED, updated_at=settings.SCHOOL_CLOCK.now())


@shared_task(name="modules.exchange.tasks.audit_expired_artifacts")
def audit_expired_artifacts() -> int:
    """Count ready exports whose artifact window has closed; return the count.

    Counts rather than deletes. Removing the artifact is M12's retention
    decision, not M13's, and deleting another module's object from here would
    be reaching across a boundary.
    """
    from django.conf import settings

    now = settings.SCHOOL_CLOCK.now()
    return ExportJob.objects.filter(state=JobState.READY, expires_at__lt=now).count()
