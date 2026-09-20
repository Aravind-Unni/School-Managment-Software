"""Django app config for M03 timetable."""

from __future__ import annotations

from django.apps import AppConfig


class TimetableConfig(AppConfig):
    """Registers the central timetable's tables."""

    name = "modules.timetable"
    label = "timetable"
    verbose_name = "M03 central timetable and calendar"
    default_auto_field = "django.db.models.BigAutoField"
