"""Celery application for modules that own asynchronous work.

Started only when the target module declares scheduled_jobs or owns jobs, so a
module with no async work runs no broker and no worker at all.

``task_always_eager`` is never enabled here. Eager execution cannot demonstrate
crash or retry behaviour, and B00 forbids claiming those results; the Platform
test adapter raises instead.
"""

from __future__ import annotations

import os

from celery import Celery

from config import env

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.standalone")

app = Celery("school")
app.conf.broker_url = env.optional("BROKER_URL") or None
app.conf.task_always_eager = False
app.conf.timezone = "UTC"
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
app.autodiscover_tasks()

#: Cron expressions in module registrations are written in school time.
app.conf.timezone = "Asia/Kolkata"
app.conf.enable_utc = True


@app.task(name="school.run_scheduled_job")
def run_scheduled_job(task_path: str):
    """Import and run one registered periodic job by its dotted path.

    One wrapper serves every module, whether the job is a plain function or a
    Celery task (called directly, inside this worker). The path comes only
    from ModuleRegistration.scheduled_jobs, never from a request.
    """
    import importlib

    module_path, _, attribute = task_path.rpartition(".")
    target = getattr(importlib.import_module(module_path), attribute)
    return target()


@app.task(name="school.run_platform_job", acks_late=True)
def run_platform_job(job_id: str) -> str:
    """Run one queued platform Job (see modules.platform.services.job_runner)."""
    from django.conf import settings

    from modules.platform.services.job_runner import run_job

    return run_job(job_id, now=settings.SCHOOL_CLOCK.now)


def crontab_from_expression(expression: str):
    """Turn "m h dom mon dow" into a celery crontab. Raises on a malformed one."""
    from celery.schedules import crontab

    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"cron expression needs five fields: {expression!r}")
    minute, hour, day_of_month, month_of_year, day_of_week = fields
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def build_beat_schedule(registrations) -> dict:
    """Return a beat schedule entry for every job the registrations declare."""
    schedule = {}
    for registration in registrations:
        for job in registration.scheduled_jobs or ():
            schedule[job.name] = {
                "task": "school.run_scheduled_job",
                "schedule": crontab_from_expression(job.cron),
                "args": (job.task_path,),
            }
    return schedule


@app.on_after_configure.connect
def _install_beat_schedule(sender, **_kwargs) -> None:
    """Schedule every approved module's jobs when running the full assembly."""
    from django.conf import settings

    registrations = getattr(settings, "_APPROVED_REGISTRATIONS", None)
    if registrations:
        sender.conf.beat_schedule = build_beat_schedule(registrations)
