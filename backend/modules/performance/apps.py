"""M06 performance Django app."""

from __future__ import annotations

from django.apps import AppConfig


class PerformanceConfig(AppConfig):
    """Registers performance tables and projection tasks."""

    name = "modules.performance"
    label = "performance"
    verbose_name = "M06 analytics warnings and interventions"
    default_auto_field = "django.db.models.BigAutoField"
