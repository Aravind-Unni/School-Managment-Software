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
