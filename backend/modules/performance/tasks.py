"""Celery tasks for projection rebuild and daily reconcile."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task
from django.conf import settings

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .services.wire import projection_service, warning_service


@shared_task(name="modules.performance.tasks.rebuild_projections")
def rebuild_projections(school_id: str, student_ids: list[str] | None = None) -> int:
    """Full rebuild for listed pupils (or baseline S1/S2). Returns count.

    Assumes Assessment and Attendance ports are bound. Does not claim crash/retry
    coverage when invoked synchronously in tests.
    """
    school = UUID(school_id)
    ids = [
        UUID(s) for s in (student_ids or [str(fixtures.STUDENT_S1), str(fixtures.STUDENT_S2)])
    ]
    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=school,
        request_id="performance-rebuild",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=settings.SCHOOL_CLOCK.now(),
    )
    count = projection_service().rebuild_school(ctx, ids)
    warnings = warning_service()
    for student_id in ids:
        warnings.evaluate_student(ctx, student_id)
    return count


@shared_task(name="modules.performance.tasks.reconcile_projections")
def reconcile_projections() -> int:
    """Daily reconcile for School A baseline pupils."""
    return rebuild_projections(str(fixtures.SCHOOL_A))
