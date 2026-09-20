"""Django app config for M04 attendance."""

from __future__ import annotations

from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    """Registers attendance tables."""

    name = "modules.attendance"
    label = "attendance"
    verbose_name = "M04 teacher attendance"
    default_auto_field = "django.db.models.BigAutoField"
