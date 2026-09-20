"""M10 alumni Django app."""

from __future__ import annotations

from django.apps import AppConfig


class AlumniConfig(AppConfig):
    """Registers alumni candidate and profile tables."""

    name = "modules.alumni"
    label = "alumni"
    verbose_name = "M10 alumni records and contact permissions"
    default_auto_field = "django.db.models.BigAutoField"
