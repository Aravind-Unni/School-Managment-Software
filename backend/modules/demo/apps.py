"""Django app config for the demo placeholder."""

from __future__ import annotations

from django.apps import AppConfig


class DemoConfig(AppConfig):
    """Registers the demo module's single table."""

    name = "modules.demo"
    label = "demo"
    verbose_name = "M00 demo placeholder"
    default_auto_field = "django.db.models.BigAutoField"
