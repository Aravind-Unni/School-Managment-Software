"""M14 platform Django app — real audit, outbox, jobs and backup."""

from __future__ import annotations

from django.apps import AppConfig


class PlatformConfig(AppConfig):
    """Registers platform operational tables."""

    name = "modules.platform"
    label = "platform"
    verbose_name = "M14 audit, jobs, backup and observability"
    default_auto_field = "django.db.models.BigAutoField"
