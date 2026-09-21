"""Dispatch queued jobs to the worker and run them there.

``PlatformAdapter.enqueue`` records a Job; this module is what makes it
happen. Dispatch waits for the enqueuing transaction to commit, so a worker
never picks up a job whose rows the API later rolled back. The worker marks
the job running, calls the handler with the stored payload, and records
succeeded or failed. A failed job can be retried from the operator jobs page.

Does not handle: automatic retry with backoff (an operator retries), or
handlers that are not importable dotted paths (bookkeeping kinds stay queued).
"""

from __future__ import annotations

import importlib
import inspect
import logging
from collections.abc import Callable
from uuid import UUID

from django.db import transaction

logger = logging.getLogger(__name__)

#: Celery task name registered in config/celery.py.
RUN_JOB_TASK = "school.run_platform_job"


def resolve_handler(task_path: str) -> Callable | None:
    """Return the callable at a dotted path, or None when it is not importable."""
    module_path, _, attribute = task_path.rpartition(".")
    if not module_path or not module_path.startswith("modules."):
        return None
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        return None
    return getattr(module, attribute, None)


def call_with_payload(handler: Callable, payload: dict) -> object:
    """Call a handler, passing the payload the way its signature asks for it.

    A handler taking one ``payload`` parameter gets the whole dict; any other
    handler gets the payload keys that match its parameter names.
    """
    target = getattr(handler, "run", handler)  # a Celery task: call its body
    parameters = inspect.signature(target).parameters
    if list(parameters) == ["payload"]:
        return target(payload)
    return target(**{name: payload[name] for name in parameters if name in payload})


def dispatch_after_commit(job_id: UUID) -> None:
    """Send the job to the worker once the current transaction commits."""

    def _send() -> None:
        from config.celery import app

        app.send_task(RUN_JOB_TASK, args=[str(job_id)])

    transaction.on_commit(_send)


def run_job(job_id: str, *, now: Callable) -> str:
    """Run one queued job to completion. Returns its final state.

    Idempotent against duplicate delivery: a job not in ``queued`` is left
    alone, so a redelivered message cannot run the handler twice.
    """
    from ..models import Job, JobState

    with transaction.atomic():
        job = Job.objects.select_for_update().filter(id=UUID(job_id)).first()
        if job is None or job.state != JobState.QUEUED:
            return job.state if job is not None else "missing"
        handler = resolve_handler(job.task_path)
        if handler is None:
            return job.state
        job.state = JobState.RUNNING
        job.version += 1
        job.updated_at = now()
        job.save(update_fields=["state", "version", "updated_at"])

    try:
        call_with_payload(handler, dict(job.payload or {}))
    except Exception as exc:
        logger.exception("job %s (%s) failed", job.id, job.task_path)
        Job.objects.filter(id=job.id).update(
            state=JobState.FAILED,
            error_code=type(exc).__name__[:128],
            updated_at=now(),
        )
        return JobState.FAILED
    Job.objects.filter(id=job.id).update(
        state=JobState.SUCCEEDED, progress=100, updated_at=now()
    )
    return JobState.SUCCEEDED
