"""Celery task entry for period billing runs."""

from __future__ import annotations

from uuid import UUID

from contracts.identity import AuthLevel, RequestContext


def process_billing_run(payload: dict[str, object]) -> int:
    """Process one billing run payload. Called by worker or sync fallback.

    Assumes payload carries school_id, period, actor_id and request_id from the
    API that enqueued the job. Does not invent actor identity.
    """
    from django.conf import settings

    from ..api import deps

    ctx = RequestContext(
        actor_id=UUID(str(payload["actor_id"])),
        school_id=UUID(str(payload["school_id"])),
        request_id=str(payload.get("request_id") or "billing-run"),
        auth_level=AuthLevel.PASSWORD,
        auth_time=settings.SCHOOL_CLOCK.now(),
    )
    return deps.billing_service().process_period(ctx, period=str(payload["period"]))
