"""Celery tasks for projection rebuild and daily reconcile."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task
from django.conf import settings

from contracts.errors import ObjectInaccessible
from contracts.identity import AuthLevel, RequestContext
from contracts.values import school_date
from shared.people import system_actor_id
from shared.ports import runtime

from .services.wire import projection_service, warning_service


@shared_task(name="modules.performance.tasks.rebuild_projections")
def rebuild_projections(school_id: str, student_ids: list[str] | None = None) -> int:
    """Rebuild projections and evaluate warnings for listed pupils, or all current ones.

    Runs as the school's "automatic jobs" account (read-only grants, cannot
    sign in), so it only computes; it never grants anyone access. Assumes
    Assessment, Attendance and Registry ports are bound.
    """
    school = UUID(school_id)
    ctx = RequestContext(
        actor_id=system_actor_id(school),
        school_id=school,
        request_id="performance-rebuild",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=settings.SCHOOL_CLOCK.now(),
    )
    if student_ids:
        ids = [UUID(s) for s in student_ids]
    else:
        registry = runtime.get_registry().resolve("registry")
        ids = list(registry.active_student_ids(ctx, school_date(settings.SCHOOL_CLOCK.now())))
    count = projection_service().rebuild_school(ctx, ids)
    warnings = warning_service()
    for student_id in ids:
        try:
            warnings.evaluate_student(ctx, student_id)
        except ObjectInaccessible:
            continue
    return count


@shared_task(name="modules.performance.tasks.reconcile_projections")
def reconcile_projections() -> int:
    """Nightly reconcile for every current pupil of this deployment's school."""
    return rebuild_projections(str(settings.SCHOOL_ID))
