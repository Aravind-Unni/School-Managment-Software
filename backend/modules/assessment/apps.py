"""Django app config for M05 assessment."""

from __future__ import annotations

from django.apps import AppConfig


class AssessmentConfig(AppConfig):
    """Registers assessment tables."""

    name = "modules.assessment"
    label = "assessment"
    verbose_name = "M05 assessments and grades"
    default_auto_field = "django.db.models.BigAutoField"
